#-------------------------------------------------------------------------------
#
# WPS process fetching data from multiple collection to the client.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments, too-many-locals, too-many-branches

from itertools import chain, izip
from datetime import datetime, timedelta
from cStringIO import StringIO
import msgpack
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData,
    BoundingBoxData,
    ComplexData,
    FormatText, FormatJSON,
    CDFileWrapper,
    FormatBinaryRaw,
    CDObject,
)
from eoxserver.services.ows.wps.exceptions import (
    InvalidInputValueError, InvalidOutputDefError,
)
from vires.util import unique, exclude, include
from vires.time_util import (
    naive_to_utc,
    timedelta_to_iso_duration,
)
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    timedelta_to_cdf_rawtime, get_formatter, CDF_EPOCH_TYPE,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_composed_models, parse_variables,
    IndexKp, IndexDst, IndexF107, OrbitCounter, ProductTimeSeries,
    MinStepSampler, GroupingSampler, BoundingBoxFilter,
    MagneticModelResidual, QuasiDipoleCoordinates, MagneticLocalTime,
    VariableResolver, SpacecraftLabel, SunPosition, SubSolarPoint,
    Sat2SatResidual, group_residual_variables, get_residual_variables,
    MagneticDipole, DipoleTiltAngle,
)


# TODO: Make following parameters configurable.
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

    inputs = [
        ("collection_ids", ComplexData(
            'collection_ids', title="Collection identifiers", abstract=(
                "JSON object defining the merged data collections. "
                "The input is required to be the following form: "
                "{<label1>: [<collection11>, <collection12>, ...], "
                " <label2>: [<collection21>, <collection22>, ...], "
                "... } "
            ), formats=FormatJSON()
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=False, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=False, title="End time",
            abstract="End of the selection time interval",
        )),
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=True, title="Bounding box",
            abstract="Optional selection bounding box.", default=None,
        )),
        ("requested_variables", LiteralData(
            'variables', str, optional=True, default=None,
            title="Data variables",
            abstract="Comma-separated list of the extracted data variables."
        )),
        ("model_ids", LiteralData(
            'model_ids', str, optional=True, default="",
            title="Model identifiers",
            abstract=(
                "Optional list of the forward Earth magnetic field model "
                "identifiers."
            ),
        )),
        ("shc", ComplexData(
            'shc',
            title="Custom model coefficients.",
            abstract=(
                "Custom forward magnetic field model coefficients encoded "
                " in the SHC plain-text format."
            ),
            optional=True,
            formats=(FormatText('text/plain'),)
        )),
        ("csv_time_format", LiteralData(
            'csv_time_format', str, optional=True, title="CSV time  format",
            abstract="Optional time format used by the CSV output.",
            allowed_values=CDF_RAW_TIME_FORMATS,
            default=CDF_RAW_TIME_FORMATS[0],
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Output data", formats=(
                FormatText('text/csv'),
                FormatBinaryRaw("application/msgpack"),
                FormatBinaryRaw("application/x-msgpack"),
            )
        )),
    ]

    def execute(self, collection_ids, begin_time, end_time, bbox,
                requested_variables, model_ids, shc,
                csv_time_format, output, **kwarg):
        """ Execute process """
        # parse inputs
        sources = parse_collections('collection_ids', collection_ids.data)
        requested_models, source_models = parse_composed_models(
            "model_ids", model_ids, shc
        )
        requested_variables = parse_variables(
            'requested_variables', requested_variables
        )
        self.logger.debug(
            "requested variables: %s", ", ".join(requested_variables)
        )

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = max(naive_to_utc(end_time), begin_time)

        # check the time-selection limit
        if (end_time - begin_time) > MAX_TIME_SELECTION:
            message = (
                "Time selection limit (%s) has been exceeded!" %
                timedelta_to_iso_duration(MAX_TIME_SELECTION)
            )
            self.access_logger.error(message)
            raise InvalidInputValueError('end_time', message)

        # log the request
        self.access_logger.info(
            "request: toi: (%s, %s), aoi: %s, collections: (%s), "
            "models: (%s), ",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180),
            ", ".join(
                s.collection.identifier for l in sources.values() for s in l
            ),
            ", ".join(
                "%s = %s" % (model.name, model.full_expression)
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

        min_step = timedelta(0) if relative_time <= 1 else BASE_MIN_STEP
        sampling_step = timedelta(seconds=(
            relative_area * (
                min_step.total_seconds() +
                relative_time * (BASE_SAMPLIG_STEP - min_step).total_seconds()
            )
        ))

        self.logger.debug("sampling step: %s", sampling_step)

        # resolve data sources, models and filters and variables dependencies
        resolvers = dict()

        if sources:
            orbit_counter = dict(
                (satellite, OrbitCounter("OrbitCounter" + satellite, path))
                for satellite, path in settings.VIRES_ORBIT_COUNTER_DB.items()
            )
            index_kp = IndexKp(settings.VIRES_AUX_DB_KP)
            index_dst = IndexDst(settings.VIRES_AUX_DB_DST)
            index_f10 = IndexF107(settings.VIRES_CACHED_PRODUCTS["AUX_F10_2_"])
            index_imf = ProductTimeSeries(settings.VIRES_AUX_IMF_2__COLLECTION)
            model_qdc = QuasiDipoleCoordinates()
            model_mlt = MagneticLocalTime()
            model_sun = SunPosition()
            model_subsol = SubSolarPoint()
            model_dipole = MagneticDipole()
            model_tilt_angle = DipoleTiltAngle()
            sampler = MinStepSampler('Timestamp', timedelta_to_cdf_rawtime(
                sampling_step, CDF_EPOCH_TYPE
            ))
            grouping_sampler = GroupingSampler('Timestamp')
            filters = [sampler, grouping_sampler]
            if bbox:
                filters.append(
                    BoundingBoxFilter(['Latitude', 'Longitude'], bbox)
                )

            # collect all spherical-harmonics models and residuals
            models_with_residuals = []
            for model in source_models:
                models_with_residuals.append(model)
            for model in requested_models:
                models_with_residuals.append(model)
                for variable in model.BASE_VARIABLES:
                    models_with_residuals.append(
                        MagneticModelResidual(model.name, variable)
                    )

            # resolving variable dependencies for each label separately
            for label, product_sources in sources.iteritems():
                resolver = VariableResolver(
                    requested_variables, MANDATORY_VARIABLES
                )

                resolvers[label] = resolver

                # master
                master = product_sources[0]
                resolver.add_master(master)

                # slaves
                for slave in product_sources[1:]:
                    resolver.add_slave(slave, 'Timestamp')

                # auxiliary slaves
                for slave in (index_kp, index_dst, index_f10, index_imf):
                    resolver.add_slave(slave, 'Timestamp')

                # satellite specific slaves
                spacecraft = (
                    settings.VIRES_COL2SAT.get(master.collection.identifier)
                )
                resolver.add_model(SpacecraftLabel(spacecraft or '-'))
                if spacecraft in orbit_counter:
                    resolver.add_slave(
                        orbit_counter[spacecraft], 'Timestamp'
                    )

                # prepare spacecraft to spacecraft residuals
                # NOTE: No residual variables required by the filters.
                residual_variables = get_residual_variables(requested_variables)
                self.logger.debug("residual variables: %s", ", ".join(
                    var for var, _ in residual_variables
                ))
                grouped_res_vars = group_residual_variables(
                    product_sources, residual_variables
                )
                for (msc, ssc), cols in grouped_res_vars.items():
                    resolver.add_model(Sat2SatResidual(msc, ssc, cols))

                # models
                aux_models = chain((
                    model_qdc, model_mlt, model_sun,
                    model_subsol, model_dipole, model_tilt_angle,
                ), models_with_residuals)
                for model in aux_models:
                    resolver.add_model(model)

                # filters
                for filter_ in filters:
                    resolver.add_filter(filter_)

                self.logger.debug(
                    "%s: available variables: %s", label,
                    ", ".join(resolver.available)
                )
                self.logger.debug(
                    "%s: evaluated variables: %s", label,
                    ", ".join(resolver.required)
                )
                self.logger.debug(
                    "%s: output variables: %s", label,
                    ", ".join(resolver.output)
                )
                self.logger.debug(
                    "%s: applicable filters: %s", label,
                    "; ".join(str(f) for f in resolver.resolved_filters)
                )
                self.logger.debug(
                    "%s: unresolved filters: %s", label, "; ".join(
                        str(f) for f in resolver.unresolved_filters
                    )
                )

            # collect the common output variables
            output_variables = tuple(unique(chain.from_iterable(
                resolver.output for resolver in resolvers.values()
            )))

        else:
            # empty output
            output_variables = ()

        self.logger.debug("output variables: %s", ", ".join(output_variables))

        def _generate_data_():
            total_count = 0

            for label, resolver in resolvers.iteritems():
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
                        self.access_logger.error(
                            "The sample count %d exceeds the maximum allowed "
                            "count of %d samples per collection!",
                            collection_count, MAX_SAMPLES_COUNT_PER_COLLECTION
                        )
                        raise InvalidInputValueError(
                            'end_time',
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

            self.access_logger.info(
                "response: count: %d samples, mime-type: %s, variables: (%s)",
                total_count, output['mime_type'], ", ".join(output_variables)
            )

        if output['mime_type'] == "text/csv":
            # write the output
            output_fobj = StringIO()
            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]

            if sources:
                # write CSV header
                output_fobj.write("id,")
                output_fobj.write(",".join(output_variables))
                output_fobj.write("\r\n")

            for label, dataset in _generate_data_():
                formatters = []
                data = []
                for variable in output_variables:
                    data_item = dataset.get(variable)
                    # convert time variables to the target file-format
                    cdf_type = dataset.cdf_type.get(variable)
                    if cdf_type == CDF_EPOCH_TYPE:
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
                # iterate the rows and write the CSV records
                label_prefix = "%s," % label
                for row in izip(*(item for item in data if item is not None)):
                    output_fobj.write(label_prefix)
                    output_fobj.write(
                        format_ % tuple(f(v) for f, v in zip(formatters, row))
                    )
                    output_fobj.write("\r\n")

            http_headers = ()
            return CDFileWrapper(output_fobj, headers=http_headers, **output)

        elif output['mime_type'] in ("application/msgpack", "application/x-msgpack"):

            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]


            output_dict = {}
            for label, dataset in _generate_data_():
                available = tuple(include(output_variables, dataset))
                for variable in available:
                    data_item = dataset.get(variable)
                    cdf_type = dataset.cdf_type.get(variable)
                    if cdf_type == CDF_EPOCH_TYPE:
                        data_item = time_convertor(data_item, cdf_type)
                    if variable in output_dict:
                        output_dict[variable].extend(data_item.tolist())
                    else:
                        output_dict[variable] = data_item.tolist()

            # encode as messagepack
            encoded = StringIO(msgpack.dumps(output_dict))

            return CDObject(
                encoded, filename="swarm_data.mp", **output
            )
        else:
            InvalidOutputDefError(
                'output',
                "Unexpected output format %r requested!" % output['mime_type']
            )
