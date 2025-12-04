#-------------------------------------------------------------------------------
#
# WPS fetch filtered download data
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
# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,
# pylint: disable=too-many-branches,too-many-statements,unused-argument
# pylint: disable=consider-using-f-string

from os import remove
from os.path import exists
from itertools import chain
from datetime import datetime, timedelta
from numpy import nan, full
from django.utils.timezone import utc
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, AllowedRange, Reference,
    FormatText, FormatJSON, FormatBinaryRaw, RequestParameter,
)
from eoxserver.services.ows.wps.exceptions import (
    InvalidInputValueError, InvalidOutputDefError, ServerBusy,
)
from vires.models import Job, get_user
from vires.util import unique, exclude, include, pretty_list, LazyString
from vires.access_util import get_vires_permissions
from vires.time_util import naive_to_utc, format_timedelta, format_datetime
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    timedelta_to_cdf_rawtime, get_formatter, cdf_open,
    CDF_CHAR_TYPE, CDF_TIME_TYPES,
)
from vires.cache_util import cache_path
from vires.data.vires_settings import CACHED_PRODUCT_FILE
from vires.filters import (
    format_filters, MinStepSampler, GroupingSampler, ExtraSampler,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_model_list, parse_variables, parse_filters,
    VariableResolver, group_subtracted_variables, get_subtracted_variables,
    extract_product_names, get_time_limit, get_orbit_sources,
    build_response_basename,
)
from vires.processes.util.time_series import (
    get_product_time_series,
    TimeSeries, ProductTimeSeries,
    IndexF107,
)
from vires.processes.util.models import (
    QuasiDipoleCoordinates, MagneticLocalTime,
    SpacecraftLabel, SunPosition, SubSolarPoint,
    SatSatSubtraction, MagneticDipole, DipoleTiltAngle,
    Identity,
    BnecToF,
    Geodetic2GeocentricCoordinates,
    generate_magnetic_model_sources,
)

TIME_PRECISION = timedelta(microseconds=1)

# TODO: Make the limits configurable.
# Limit number of active jobs (ACCEPTED or STARTED) per user
MAX_ACTIVE_JOBS = 2

# Limit response size (equivalent to 80 daily 1Hz products).
MAX_SAMPLES_COUNT = 6912000

# maximum allowed time selection period for 1 second sampled data
# 35525 days is ~100 years >> mission life-time
MAX_TIME_SELECTION = timedelta(days=35525)

# set of the minimum required variables
MANDATORY_VARIABLES = [
    ProductTimeSeries.COLLECTION_INDEX_VARIABLE,
    "Spacecraft", "Timestamp", "Latitude", "Longitude", "Radius"
]

# time converters
CDF_RAW_TIME_FORMATS = ("ISO date-time", "MJD2000", "Unix epoch")
CDF_RAW_TIME_CONVERTOR = {
    "ISO date-time": cdf_rawtime_to_datetime,
    "MJD2000": cdf_rawtime_to_mjd2000,
    "Unix epoch": cdf_rawtime_to_unix_epoch,
}


class FetchFilteredDataAsync(WPSProcess):
    """ Process retrieving subset of the registered Swarm data based
    on collection, time interval and optional additional custom filters.
    This process is designed to be used for the data download.
    """
    identifier = "vires:fetch_filtered_data_async"
    title = "Fetch merged SWARM products."
    metadata = {}
    profiles = ["vires"]
    synchronous = False
    asynchronous = True

    inputs = WPSProcess.inputs + [
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
        ("filters", LiteralData(
            "filters", str, optional=True, default="",
            abstract=("Filters' expression."),
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
                "the cached models and to calculate the cached models "
                "on-the-fly. The cached LR model values, when used, are "
                "always interpolated for HR datasets. "
                "The model caching is a performance optimisation and "
                "its disabling makes the calculation significantly slower."
            ),
        )),
        ("do_not_interpolate_models", LiteralData(
            "do_not_interpolate_models", bool, optional=True, default=False,
            abstract=(
                "Optional boolean flag forcing the server not to interpolate"
                "non-cached models for HR datasets from the LR ones."
                "The model interpolation is a performance optimisation and "
                "its disabling makes the calculation significantly slower."
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
                FormatBinaryRaw("application/cdf"),
                FormatBinaryRaw("application/x-cdf"),
            )
        )),
        ("source_products", ComplexData(
            "source_products", title="List of source products.", formats=(
                FormatText("text/plain"),
            )
        )),
    ]

    @staticmethod
    def on_started(context, progress, message):
        """ Callback executed when an asynchronous Job gets started. """
        try:
            job = update_job(
                Job.objects.get(identifier=context.identifier),
                status=Job.STARTED,
                started=datetime.now(utc),
            )
            context.logger.info(
                "Job started after %.3gs waiting.",
                (job.started - job.created).total_seconds()
            )
        except Job.DoesNotExist:
            context.logger.warning(
                "Failed to update the job status! The job does not exist!"
            )

    @staticmethod
    def on_succeeded(context, outputs):
        """ Callback executed when an asynchronous Job finishes. """
        try:
            job = update_job(
                Job.objects.get(identifier=context.identifier),
                status=Job.SUCCEEDED,
                stopped=datetime.now(utc),
            )
            context.logger.info(
                "Job finished after %.3gs running.",
                (job.stopped - job.started).total_seconds()
            )
        except Job.DoesNotExist:
            context.logger.warning(
                "Failed to update the job status! The job does not exist!"
            )

    @staticmethod
    def on_failed(context, exception):
        """ Callback executed when an asynchronous Job fails. """
        # The failure may happen before the Job is fully started and the start
        # timestamp set.
        try:
            timestamp = datetime.now(utc)
            job = Job.objects.get(identifier=context.identifier)
            job = update_job(
                job,
                status=Job.FAILED,
                started=(job.started or timestamp),
                stopped=timestamp,
            )
            if job.started:
                context.logger.info(
                    "Job failed after %.3gs running.",
                    (job.stopped - job.started).total_seconds()
                )
        except Job.DoesNotExist:
            context.logger.warning(
                "Failed to update the job status! The job does not exist!"
            )

    @staticmethod
    def discard(context):
        """ Asynchronous process removal. """
        try:
            Job.objects.get(identifier=context.identifier).delete()
            context.logger.info("Job removed.")
        except Job.DoesNotExist:
            pass

    def initialize(self, context, inputs, outputs, *args):
        """ Asynchronous process initialization. """
        del args
        context.logger.info(
            "Received %s WPS request from %s.",
            self.identifier, inputs["\\username"] or "an anonymous user"
        )

        user = get_user(inputs["\\username"])

        if count_active_jobs(user) >= MAX_ACTIVE_JOBS:
            message = (
                "Per user maximum number of allowed active asynchronous "
                "download requests exceeded!"
            )
            context.logger.warning("Job rejected! %s", message)
            raise ServerBusy(message)

        # create DB record for this WPS job
        update_job(
            Job(),
            status=Job.ACCEPTED,
            owner=user,
            process_id=self.identifier,
            identifier=context.identifier,
            response_url=context.status_location,
        )

    def execute(self, permissions, collection_ids, begin_time, end_time,
                filters, sampling_step, requested_variables, model_ids, shc,
                csv_time_format, output, source_products, ignore_cached_models,
                do_not_interpolate_models, context, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)
        #workspace_dir = ""

        # parse inputs
        sources = parse_collections(
            "collection_ids", collection_ids.data, permissions=permissions,
        )
        requested_models, source_models = parse_model_list(
            "model_ids", model_ids, shc
        )
        filters = parse_filters("filters", filters)
        requested_variables = parse_variables(
            "requested_variables", requested_variables
        )
        self.logger.debug(
            "requested variables: %s", pretty_list(requested_variables)
        )

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = max(naive_to_utc(end_time), begin_time)

        # adjust the time limit to the data sampling
        time_limit = get_time_limit(sources, sampling_step, MAX_TIME_SELECTION)
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
            "request parameters: toi: (%s, %s), collections: (%s), "
            "models: (%s), filters: {%s}",
            format_datetime(begin_time), format_datetime(end_time),
            ", ".join(
                s.collection_identifier for l in sources.values() for s in l
            ),
            ", ".join(
                f"{model.name} = {model.expression}"
                for model in requested_models
            ),
            format_filters(filters)
        )

        if sampling_step is not None:
            self.logger.debug("sampling step: %s", sampling_step)

        # resolve data sources, models and filters and variables dependencies
        resolvers = {}

        if sources:
            index_kp = get_product_time_series("GFZ_KP")
            index_dst = get_product_time_series("WDC_DST")
            index_f10 = IndexF107(cache_path(CACHED_PRODUCT_FILE["AUX_F10_2_"]))
            index_imf = get_product_time_series("OMNI_HR_1min_avg20min_delay10min")
            model_bnec_intensity = BnecToF()
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

            # optional sub-sampling filters
            if sampling_step:
                sampler = MinStepSampler("Timestamp", timedelta_to_cdf_rawtime(
                    sampling_step, TimeSeries.TIMESTAMP_TYPE
                ))
                grouping_sampler = GroupingSampler("Timestamp")
            else:
                sampler, grouping_sampler = None, None

            add_spacecraft_label = False
            for _, product_sources in sources.items():
                master = product_sources[0]
                mission = master.metadata.get("mission")
                if mission:
                    add_spacecraft_label = True

            # resolving variable dependencies for each label separately
            for label, product_sources in sources.items():
                resolvers[label] = resolver = VariableResolver()

                # master
                master = product_sources[0]
                resolver.add_master(master)

                # optional time sampling
                if sampler:
                    resolver.add_filter(sampler)

                # slaves
                for slave in product_sources[1:]:
                    resolver.add_slave(slave)

                    # optional extra sampling for selected collections
                    if sampler and slave.metadata.get("extraSampled"):
                        resolver.add_filter(ExtraSampler(
                            "Timestamp", slave.collection_identifier, slave
                        ))

                # optional sample grouping
                if grouping_sampler and master.metadata.get("groupSamples"):
                    resolver.add_filter(grouping_sampler)

                # auxiliary slaves
                for slave in (index_kp, index_dst, index_f10, index_imf):
                    resolver.add_slave(slave)

                # satellite specific slaves
                mission = master.metadata.get("mission")
                spacecraft = master.metadata.get("spacecraft")
                grade = master.metadata.get("grade")

                if add_spacecraft_label:
                    #TODO: add mission label
                    resolver.add_model(SpacecraftLabel(spacecraft or "-"))

                for item in get_orbit_sources(mission, spacecraft, grade):
                    resolver.add_slave(item)

                if mission == "Swarm" and spacecraft in ("A", "B", "C"):
                    # prepare spacecraft to spacecraft differences
                    subtracted_variables = get_subtracted_variables(unique(chain(
                        requested_variables, chain.from_iterable(
                            filter_.required_variables for filter_ in filters
                        )
                    )))
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
                        model_qdc, model_mlt, model_sun,
                        model_subsol, model_dipole, model_tilt_angle,
                    ),
                    generate_magnetic_model_sources(
                        mission, spacecraft, grade,
                        requested_models, source_models,
                        no_cache=ignore_cached_models,
                        no_interpolation=do_not_interpolate_models,
                        master=master,
                    ),
                    copied_variables,
                ):
                    resolver.add_consumer(model)

                # add remaining filters
                resolver.add_filters(filters)

                # add output variables
                resolver.add_output_variables(MANDATORY_VARIABLES)
                resolver.add_output_variables(master.essential_variables)
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
                    LazyString(format_filters, resolver.filters)
                )
                self.logger.debug(
                    "%s: unresolved filters: %s", label,
                    LazyString(format_filters, resolver.unresolved_filters)
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
            product_count = 0

            # count products
            collection_product_counts = dict(
                (label, resolver.master.subset_count(begin_time, end_time))
                for label, resolver in resolvers.items()
            )
            total_product_count = sum(collection_product_counts.values())


            for label, resolver in resolvers.items():

                all_variables = resolver.required
                variables = tuple(exclude(
                    all_variables, resolver.master.variables
                ))

                # master
                dataset_iterator = resolver.master.subset(
                    begin_time, end_time, all_variables
                )

                for product_idx, dataset in enumerate(dataset_iterator, 1):
                    # In case of no product selected the iterator yields one
                    # empty dataset which should not be counted as a product.
                    if collection_product_counts[label] > 0:
                        context.update_progress(
                            (product_count * 100) // total_product_count,
                            "Filtering collection %s, product %d of %d." % (
                                label, product_idx,
                                collection_product_counts[label]
                            )
                        )
                        product_count += 1


                    self.logger.debug(
                        "dataset length before applying filters: %s",
                        dataset.length
                    )

                    # master filters
                    dataset, filters_left = dataset.filter(resolver.filters)

                    # subordinate interpolated datasets
                    for slave in resolver.slaves:
                        dataset.merge(
                            slave.interpolate(
                                variables=variables,
                                times=dataset[resolver.master.time_variable],
                                cdf_type=dataset.cdf_type[resolver.master.time_variable],
                            )
                        )
                        dataset, filters_left = dataset.filter(filters_left)

                    # models
                    for model in resolver.models:
                        dataset.merge(model.eval(dataset, variables))
                        dataset, filters_left = dataset.filter(filters_left)

                    self.logger.debug(
                        "dataset length after applying filters: %s",
                        dataset.length
                    )

                    if filters_left:
                        # NOTE: Technically this error should not happen
                        # the unresolved filters should be detected by the
                        # resolver.
                        raise InvalidInputValueError(
                            "filters",
                            "Failed to apply some of the filters "
                            "due to missing source variables! filters: %s" %
                            " AND ".join(str(f) for f in filters_left)
                        )

                    # check if the number of samples is within the allowed limit
                    total_count += dataset.length
                    if total_count > MAX_SAMPLES_COUNT:
                        access_logger.warning(
                            "The sample count %d exceeds the maximum allowed "
                            "count of %d samples!",
                            total_count, MAX_SAMPLES_COUNT,
                        )
                        raise InvalidInputValueError(
                            "end_time",
                            "Requested data exceeds the maximum limit of %d "
                            "records!" % MAX_SAMPLES_COUNT
                        )

                    yield label, dataset

            access_logger.info(
                "response: count: %d samples, mime-type: %s, variables: (%s)",
                total_count, output["mime_type"], ", ".join(output_variables)
            )

        # === OUTPUT ===

        # get configurations
        temp_basename = build_response_basename(
            template=(
                "{collection_ids}_{start_time:%Y%m%dT%H%M%S}_"
                "{end_time:%Y%m%dT%H%M%S}_Filtered"
            ),
            collection_ids=[
                s.collection_identifier for l in sources.values() for s in l
            ],
            start_time=begin_time,
            end_time=(end_time - TIME_PRECISION),
            max_size=225,
            prefix_size=2,
            suffix_size=40,
        )

        if output["mime_type"] == "text/csv":
            temp_filename = temp_basename + ".csv"
            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]

            with open(temp_filename, "w", encoding="utf-8", newline="\r\n") as output_fobj:

                if sources:
                    # write CSV header
                    print(",".join(output_variables), file=output_fobj)

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
                    # iterate the rows and write the CSV records
                    for row in zip(*(item for item in data if item is not None)):
                        print(
                            format_ % tuple(f(v) for f, v in zip(formatters, row)),
                            file=output_fobj
                        )

            product_names = extract_product_names(resolvers.values())

        elif output["mime_type"] in ("application/cdf", "application/x-cdf"):
            # TODO: proper no-data value configuration
            temp_filename = temp_basename + ".cdf"
            result_filename = temp_filename #result_basename + ".cdf"

            if exists(temp_filename):
                remove(temp_filename)

            record_count = 0
            with cdf_open(temp_filename, "w") as cdf:
                for _, dataset in _generate_data_():

                    available = tuple(include(output_variables, dataset))
                    inserted = tuple(exclude(available, cdf))
                    missing = tuple(exclude(cdf, available))

                    self.logger.debug(
                        "CDF: available variables: %s", ", ".join(available)
                    )
                    self.logger.debug(
                        "CDF: inserted variables: %s", ", ".join(inserted)
                    )
                    self.logger.debug(
                        "CDF: missing variables: %s", ", ".join(missing)
                    )

                    for variable in inserted: # create the initial datasets
                        cdf_type = dataset.cdf_type.get(variable)
                        data_array = dataset[variable]
                        if cdf_type == CDF_CHAR_TYPE:
                            itemsize, nodata = data_array.dtype.itemsize, b""
                        else:
                            itemsize, nodata = 1, nan
                        shape = (record_count,) + data_array.shape[1:]
                        cdf.new(
                            variable, full(shape, nodata),
                            cdf_type, n_elements=itemsize
                        )
                        cdf[variable].attrs.update(
                            dataset.cdf_attr.get(variable, {})
                        )

                    if not dataset.is_empty: # write the follow-on dataset
                        for variable in available:
                            cdf[variable].extend(dataset[variable])

                        for variable in missing:
                            shape = (dataset.length,) + cdf[variable].shape[1:]
                            cdf[variable].extend(full(shape, nan))

                        record_count += dataset.length

                product_names = extract_product_names(resolvers.values())

                # add the global attributes
                cdf.attrs.update({
                    "TITLE": result_filename,
                    "DATA_TIMESPAN": "%s/%s" % (
                        format_datetime(begin_time),
                        format_datetime(end_time),
                    ),
                    "DATA_FILTERS": [str(f) for f in filters],
                    "MAGNETIC_MODELS": [
                        f"{model.name} = {model.expression}"
                        for model in requested_models
                    ],
                    "SOURCES": list(sources.keys()),
                    "ORIGINAL_PRODUCT_NAMES": product_names,
                })

        else:
            raise InvalidOutputDefError(
                "output",
                f"Unexpected output format {output['mime_type']!r} requested!"
            )

        source_products_filename = temp_basename + "_sources.txt"
        with open(source_products_filename, "w", encoding="utf-8", newline="\r\n") as output_fobj:
            for product_name in product_names:
                print(product_name, file=output_fobj)

        return {
            "output": Reference(*context.publish(temp_filename), **output),
            "source_products": Reference(
                *context.publish(source_products_filename), **source_products
            ),
        }


def count_active_jobs(user):
    """ Get number of active jobs owned by the given user. """
    return Job.objects.filter(
        owner=user, status__in=(Job.ACCEPTED, Job.STARTED)
    ).count()


def update_job(job, **kwargs):
    """ Update given job object. """
    for key, value in kwargs.items():
        setattr(job, key, value)
    job.save()
    return job
