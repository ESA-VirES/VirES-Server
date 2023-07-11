#-------------------------------------------------------------------------------
#
# WPS process fetching data from multiple collection to the client.
#
# Authors: Martin Paces <martin.paces@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------
# pylint: disable=too-many-arguments,too-many-locals,too-many-branches
# pylint: disable=too-many-statements,unused-argument,consider-using-f-string

from itertools import chain
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from numpy import nan, full
import msgpack
from eoxserver.services.ows.wps.parameters import (
    LiteralData, BoundingBoxData, ComplexData, FormatText, FormatJSON,
    CDFileWrapper, FormatBinaryRaw, CDObject, RequestParameter, AllowedRange,
)
from eoxserver.services.ows.wps.exceptions import (
    InvalidInputValueError, InvalidOutputDefError,
)
from vires.models import ProductCollection
from vires.util import unique, exclude, pretty_list, LazyString
from vires.access_util import get_user, get_vires_permissions
from vires.time_util import naive_to_utc, format_timedelta, format_datetime
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    timedelta_to_cdf_rawtime, get_formatter, CDF_TIME_TYPES,
)
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    CACHED_PRODUCT_FILE, AUX_DB_KP, AUX_DB_DST, SPACECRAFTS, DEFAULT_MISSION,
    ORBIT_COUNTER_FILE, ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
)
from vires.filters import (
    format_filters, MinStepSampler, GroupingSampler, ExtraSampler,
    BoundingBoxFilter,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_model_list, parse_variables,
    VariableResolver, group_subtracted_variables, get_subtracted_variables,
    extract_product_names,
)
from vires.processes.util.time_series import (
    TimeSeries, ProductTimeSeries, CustomDatasetTimeSeries,
    IndexKp10, IndexDst, IndexDDst, IndexF107,
    OrbitCounter, OrbitDirection, QDOrbitDirection,
)
from vires.processes.util.models import (
    QuasiDipoleCoordinates, MagneticLocalTime,
    SpacecraftLabel, SunPosition, SubSolarPoint,
    SatSatSubtraction, MagneticDipole, DipoleTiltAngle,
    IndexKpFromKp10,
    Identity,
    BnecToF,
    Geodetic2GeocentricCoordinates,
    generate_magnetic_model_sources,
)

# TODO: Make the following parameters configurable.
# Limit response size (equivalent to 1/2 daily SWARM MAG LR product).
MAX_SAMPLES_COUNT_PER_COLLECTION = 43200

# maximum allowed time selection period
MAX_TIME_SELECTION = timedelta(days=31)

# maximum allowed time selection period
BASE_SAMPLIG_STEP = timedelta(seconds=20)
BASE_MIN_STEP = timedelta(seconds=7)
BASE_TIME_UNIT = timedelta(days=1)

# set of the minimum required variables
MANDATORY_VARIABLES = [
    "Spacecraft", "Timestamp", "Latitude", "Longitude", "Radius"
]

# time converters
CDF_RAW_TIME_FORMATS = ("ISO date-time", "MJD2000", "Unix epoch")
CDF_RAW_TIME_CONVERTOR = {
    "ISO date-time": cdf_rawtime_to_datetime,
    "MJD2000": cdf_rawtime_to_mjd2000,
    "Unix epoch": cdf_rawtime_to_unix_epoch,
}

class FetchData(WPSProcess):
    """ Process retrieving registered Swarm data based on collection, time
    interval and additional optional parameters.
    This process is designed to be used by the web-client.
    """
    identifier = "vires:fetch_data"
    title = "Fetch merged SWARM products."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("user", RequestParameter(get_user)),
        ("permissions", RequestParameter(get_vires_permissions)),
        ("collection_ids", ComplexData(
            "collection_ids", title="Collection identifiers", abstract=(
                "JSON object defining the merged data collections. "
                "The input is required to be the following form: "
                "{<label1>: [<collection11>, <collection12>, ...], "
                " <label2>: [<collection21>, <collection22>, ...], "
                "... } "
            ), formats=FormatJSON()
        )),
        ("begin_time", LiteralData(
            "begin_time", datetime, optional=False, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            "end_time", datetime, optional=False, title="End time",
            abstract="End of the selection time interval",
        )),
        ("sampling_step", LiteralData(
            "sampling_step", timedelta, optional=True, title="Sampling step",
            allowed_values=AllowedRange(timedelta(0), None, dtype=timedelta),
            abstract="Optional output data sampling step.",
        )),
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=True, title="Bounding box",
            abstract="Optional selection bounding box.", default=None,
        )),
        ("requested_variables", LiteralData(
            "variables", str, optional=True, default=None,
            title="Data variables",
            abstract="Comma-separated list of the extracted data variables."
        )),
        ("model_ids", LiteralData(
            "model_ids", str, optional=True, default="",
            title="Model identifiers",
            abstract=(
                "Optional list of the forward Earth magnetic field model "
                "identifiers."
            ),
        )),
        ("ignore_cached_models", LiteralData(
            "ignore_cached_models", bool, optional=True, default=False,
            abstract=(
                "Optional boolean flag forcing the server to ignore "
                "the cached models and to calculate the models on-the-fly."
            ),
        )),
        ("shc", ComplexData(
            "shc",
            title="Custom model coefficients.",
            abstract=(
                "Custom forward magnetic field model coefficients encoded "
                " in the SHC plain-text format."
            ),
            optional=True,
            formats=(FormatText("text/plain"),)
        )),
        ("csv_time_format", LiteralData(
            "csv_time_format", str, optional=True, title="CSV time  format",
            abstract="Optional time format used by the CSV output.",
            allowed_values=CDF_RAW_TIME_FORMATS,
            default=CDF_RAW_TIME_FORMATS[0],
        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="Output data", formats=(
                FormatText("text/csv"),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
            )
        )),
    ]

    def execute(self, user, permissions, collection_ids, begin_time, end_time,
                sampling_step, bbox, requested_variables, model_ids, shc,
                csv_time_format, output, ignore_cached_models, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)

        # parse inputs
        sources = parse_collections(
            "collection_ids", collection_ids.data, permissions=permissions,
            custom_dataset=CustomDatasetTimeSeries.COLLECTION_IDENTIFIER,
            user=user,
        )
        requested_models, source_models = parse_model_list(
            "model_ids", model_ids, shc
        )
        requested_variables = parse_variables(
            "requested_variables", requested_variables
        )
        self.logger.debug(
            "requested variables: %s", pretty_list(requested_variables)
        )

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = max(naive_to_utc(end_time), begin_time)

        # fixed selection time-limit
        time_limit = MAX_TIME_SELECTION
        self.logger.debug(
            "time-selection limit: %s",
            LazyString(lambda: format_timedelta(time_limit))
        )

        # check the time-selection limit
        if (end_time - begin_time) > time_limit:
            message = (
                "Time selection limit (%s) has been exceeded!" %
                format_timedelta(time_limit)
            )
            access_logger.warning(message)
            raise InvalidInputValueError("end_time", message)

        # log the request
        access_logger.info(
            "request: toi: (%s, %s), aoi: %s, collections: (%s), "
            "models: (%s), ",
            format_datetime(begin_time), format_datetime(end_time),
            bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180),
            ", ".join(
                s.collection_identifier for l in sources.values() for s in l
            ),
            ", ".join(
                f"{model.name} = {model.expression}"
                for model in requested_models
            ),
        )

        if bbox:
            relative_area = abs(
                (bbox.upper[0] - bbox.lower[0]) *
                (bbox.upper[1] - bbox.lower[1])
            ) / 64800.0
        else:
            relative_area = 1.0

        relative_time = (
            (end_time - begin_time).total_seconds() /
            BASE_TIME_UNIT.total_seconds()
        )

        self.logger.debug("relative area: %s", relative_area)
        self.logger.debug("relative time: %s", relative_time)

        if sampling_step is None:
            min_step = timedelta(0) if relative_time <= 1 else BASE_MIN_STEP
            sampling_step = timedelta(seconds=(
                relative_area * (
                    min_step.total_seconds() +
                    relative_time * (BASE_SAMPLIG_STEP - min_step).total_seconds()
                )
            ))

        self.logger.debug("sampling step: %s", sampling_step)

        # resolve data sources, models and filters and variables dependencies
        resolvers = {}

        if sources:
            orbit_info = {
                spacecraft: [
                    OrbitCounter(
                        ":".join(["OrbitCounter", spacecraft[0], spacecraft[1] or ""]),
                        cache_path(ORBIT_COUNTER_FILE[spacecraft])
                    ),
                    OrbitDirection(
                        ":".join(["OrbitDirection", spacecraft[0], spacecraft[1] or ""]),
                        cache_path(ORBIT_DIRECTION_GEO_FILE[spacecraft])
                    ),
                    QDOrbitDirection(
                        ":".join(["QDOrbitDirection", spacecraft[0], spacecraft[1] or ""]),
                        cache_path(ORBIT_DIRECTION_MAG_FILE[spacecraft])
                    ),
                ]
                for spacecraft in SPACECRAFTS
            }
            index_kp10 = IndexKp10(cache_path(AUX_DB_KP))
            index_dst = IndexDst(cache_path(AUX_DB_DST))
            index_ddst = IndexDDst(cache_path(AUX_DB_DST))
            index_f10 = IndexF107(cache_path(CACHED_PRODUCT_FILE["AUX_F10_2_"]))
            index_imf = ProductTimeSeries(
                ProductCollection.objects.get(
                    identifier="OMNI_HR_1min_avg20min_delay10min"
                )
            )
            model_bnec_intensity = BnecToF()
            model_kp = IndexKpFromKp10()
            model_qdc = QuasiDipoleCoordinates()
            model_mlt = MagneticLocalTime()
            model_sun = SunPosition()
            model_subsol = SubSolarPoint()
            model_dipole = MagneticDipole()
            model_tilt_angle = DipoleTiltAngle()
            model_gd2gc = Geodetic2GeocentricCoordinates()
            copied_variables = [
                Identity("MLT_QD", "MLT"),
                Identity("Latitude_QD", "QDLat"),
                Identity("Longitude_QD", "QDLon"),
            ]

            # sampling filter
            sampler = MinStepSampler("Timestamp", timedelta_to_cdf_rawtime(
                sampling_step, TimeSeries.TIMESTAMP_TYPE
            ))
            grouping_sampler = GroupingSampler("Timestamp")
            filters = []
            if bbox:
                filters.append(BoundingBoxFilter("Latitude", "Longitude", bbox))

            # resolving variable dependencies for each label separately
            for label, product_sources in sources.items():
                resolvers[label] = resolver = VariableResolver()

                # master
                master = product_sources[0]
                resolver.add_master(master)

                # time sampling
                resolver.add_filter(sampler)

                # slaves
                for slave in product_sources[1:]:
                    resolver.add_slave(slave)

                    # extra sampling for selected collections
                    if slave.metadata.get("extraSampled"):
                        resolver.add_filter(ExtraSampler(
                            "Timestamp", slave.collection_identifier, slave
                        ))

                # optional sample grouping
                if master.metadata.get("groupSamples"):
                    resolver.add_filter(grouping_sampler)

                # auxiliary slaves
                for slave in (index_kp10, index_dst, index_ddst, index_f10, index_imf):
                    resolver.add_slave(slave)

                # satellite specific slaves
                spacecraft = (
                    master.metadata.get("mission") or DEFAULT_MISSION,
                    master.metadata.get("spacecraft")
                )
                #TODO: add mission label
                resolver.add_model(SpacecraftLabel(spacecraft[1] or "-"))

                for item in orbit_info.get(spacecraft, []):
                    resolver.add_slave(item)

                if spacecraft[0] == "Swarm" and spacecraft[1] in ("A", "B", "C"):
                    # prepare spacecraft to spacecraft differences
                    # NOTE: No residual variables required by the filters.
                    subtracted_variables = get_subtracted_variables(requested_variables)
                    self.logger.debug("residual variables: %s",
                        pretty_list(var for var, _ in subtracted_variables)
                    )
                    grouped_diff_vars = group_subtracted_variables(
                        product_sources, subtracted_variables
                    )
                    for (msc, ssc), cols in grouped_diff_vars.items():
                        resolver.add_model(SatSatSubtraction(msc, ssc, cols))

                # models
                for model in chain(
                    (
                        model_gd2gc, model_bnec_intensity,
                        model_kp, model_qdc, model_mlt, model_sun,
                        model_subsol, model_dipole, model_tilt_angle,
                    ),
                    generate_magnetic_model_sources(
                        *spacecraft, requested_models, source_models,
                        no_cache=ignore_cached_models,
                        master=master,
                    ),
                    copied_variables,
                ):
                    resolver.add_consumer(model)

                # add remaining filters
                resolver.add_filters(filters)

                # add output variables
                resolver.add_output_variables(MANDATORY_VARIABLES)
                resolver.add_output_variables(requested_variables)

                # reduce dependencies
                resolver.reduce()

                self.logger.debug(
                    "%s: available variables: %s", label,
                    pretty_list(resolver.available)
                )
                self.logger.debug(
                    "%s: evaluated variables: %s", label,
                    pretty_list(resolver.required)
                )
                self.logger.debug(
                    "%s: output variables: %s", label,
                    pretty_list(resolver.output_variables)
                )
                self.logger.debug(
                    "%s: applicable filters: %s", label,
                    LazyString(lambda: format_filters(resolver.filters))
                )
                self.logger.debug(
                    "%s: unresolved filters: %s", label,
                    LazyString(lambda: format_filters(resolver.unresolved_filters))
                )

            # collect the common output variables
            output_variables = tuple(unique(chain.from_iterable(
                resolver.output_variables for resolver in resolvers.values()
            )))

        else:
            # empty output
            output_variables = ()

        self.logger.debug("output variables: %s", pretty_list(output_variables))

        def _generate_data_():
            total_count = 0

            for label, resolver in resolvers.items():
                collection_count = 0

                all_variables = resolver.required
                variables = tuple(exclude(
                    all_variables, resolver.master.variables
                ))

                # master
                dataset_iterator = resolver.master.subset(
                    begin_time, end_time, all_variables
                )

                for dataset in dataset_iterator:
                    self.logger.debug(
                        "dataset length before applying filters: %s",
                        dataset.length
                    )
                    # master filters
                    dataset, _ = dataset.filter(resolver.filters)

                    # check if the number of samples is within the allowed limit
                    total_count += dataset.length
                    collection_count += dataset.length
                    if collection_count > MAX_SAMPLES_COUNT_PER_COLLECTION:
                        access_logger.warning(
                            "The sample count %d exceeds the maximum allowed "
                            "count of %d samples per collection!",
                            collection_count, MAX_SAMPLES_COUNT_PER_COLLECTION
                        )
                        raise InvalidInputValueError(
                            "end_time",
                            "Requested data exceeds the maximum limit of %d "
                            "samples per collection!" %
                            MAX_SAMPLES_COUNT_PER_COLLECTION
                        )

                    # subordinate interpolated datasets
                    times = dataset[resolver.master.time_variable]
                    cdf_type = dataset.cdf_type[resolver.master.time_variable]
                    for slave in resolver.slaves:
                        dataset.merge(
                            slave.interpolate(times, variables, {}, cdf_type)
                        )

                    # models
                    for model in resolver.models:
                        dataset.merge(model.eval(dataset, variables))

                    self.logger.debug(
                        "dataset length after applying filters: %s",
                        dataset.length
                    )

                    yield label, dataset

            access_logger.info(
                "response: count: %d samples, mime-type: %s, variables: (%s)",
                total_count, output["mime_type"], ", ".join(output_variables)
            )

        if output["mime_type"] == "text/csv":
            # write the output
            output_fobj = StringIO(newline="\r\n")
            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]

            if sources:
                # write CSV header
                print("id,%s" % ",".join(output_variables), file=output_fobj)

            for label, dataset in _generate_data_():
                formatters = []
                data = []
                for variable in output_variables:
                    data_item = dataset.get(variable)
                    # convert time variables to the target file-format
                    cdf_type = dataset.cdf_type.get(variable)
                    if cdf_type in CDF_TIME_TYPES:
                        data_item = time_convertor(data_item, cdf_type)
                    # collect all data items
                    data.append(data_item)
                    # collect formatters for the available data items
                    if data_item is not None:
                        formatters.append(get_formatter(data_item, cdf_type))
                # construct format string
                format_ = ",".join(
                    "nan" if item is None else "%s" for item in data
                )
                format_ = "%s,%s" % (label, format_)
                # iterate the rows and write the CSV records
                for row in zip(*(item for item in data if item is not None)):
                    print(
                        format_ % tuple(f(v) for f, v in zip(formatters, row)),
                        file=output_fobj
                    )

            http_headers = ()
            return CDFileWrapper(output_fobj, headers=http_headers, **output)

        if output["mime_type"] in ("application/msgpack", "application/x-msgpack"):

            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]

            output_dict = {}
            output_shape = {}
            data_lenght = 0
            for label, dataset in _generate_data_():
                for variable in output_variables:
                    data_item = dataset.get(variable)
                    output_data = output_dict.get(variable)

                    if data_item is None:
                        if output_data is not None:
                            output_data.extend(
                                [] if dataset.length == 0 else full(
                                    (dataset.length,) + output_shape[variable], nan
                                ).tolist()
                            )
                    else:
                        cdf_type = dataset.cdf_type.get(variable)
                        if cdf_type in CDF_TIME_TYPES:
                            data_item = time_convertor(data_item, cdf_type)

                        if output_data is None:
                            output_shape[variable] = data_item.shape[1:]
                            output_dict[variable] = output_data = (
                                [] if data_lenght == 0 else full(
                                    (data_lenght,) + data_item.shape[1:], nan
                                ).tolist()
                            )
                        output_data.extend(data_item.tolist())

                data_lenght += dataset.length

            # additional metadata
            output_dict["__info__"] = {
                "sources": extract_product_names(resolvers.values()),
                "variables": {
                    label: resolver.output_variables
                    for label, resolver in resolvers.items()
                },
            }
            # encode as messagepack
            encoded = BytesIO(msgpack.dumps(output_dict))

            return CDObject(
                encoded, filename="swarm_data.mp", **output
            )

        raise InvalidOutputDefError(
            "output",
            f"Unexpected output format {output['mime_type']!r} requested!"
        )
