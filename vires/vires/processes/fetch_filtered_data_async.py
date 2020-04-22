#-------------------------------------------------------------------------------
#
# WPS fetch filtered download data
#
# Authors: Martin Paces <martin.paces@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
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
# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,
# pylint: disable=too-many-branches,too-many-statements,unused-argument

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
from vires.models import ProductCollection, Job, get_user
from vires.util import unique, exclude, include
from vires.access_util import get_vires_permissions
from vires.time_util import (
    naive_to_utc, timedelta_to_iso_duration,
)
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    timedelta_to_cdf_rawtime, get_formatter, CDF_EPOCH_TYPE, cdf_open,
)
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    CACHED_PRODUCT_FILE, AUX_DB_KP, AUX_DB_DST, SPACECRAFTS,
    ORBIT_COUNTER_FILE, ORBIT_DIRECTION_GEO_FILE, ORBIT_DIRECTION_MAG_FILE,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_model_list, parse_variables, parse_filters2,
    VariableResolver, group_subtracted_variables, get_subtracted_variables,
    extract_product_names,
)
from vires.processes.util.time_series import (
    ProductTimeSeries,
    IndexKp10, IndexDst, IndexF107,
    OrbitCounter, OrbitDirection, QDOrbitDirection,
)
from vires.processes.util.models import (
    MagneticModelResidual, QuasiDipoleCoordinates, MagneticLocalTime,
    SpacecraftLabel, SunPosition, SubSolarPoint,
    SatSatSubtraction, MagneticDipole, DipoleTiltAngle,
    IndexKpFromKp10,
    BnecToF,
)
from vires.processes.util.filters import (
    MinStepSampler, GroupingSampler, ExtraSampler,
)

# TODO: Make the limits configurable.
# Limit number of active jobs (ACCEPTED or STARTED) per user
MAX_ACTIVE_JOBS = 2

# Limit response size (equivalent to 50 daily SWARM LR products).
MAX_SAMPLES_COUNT = 4320000

# maximum allowed time selection period (~100years >> mission life-time)
MAX_TIME_SELECTION = timedelta(days=35525)

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
        ('permissions', RequestParameter(get_vires_permissions)),
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
        ("sampling_step", LiteralData(
            'sampling_step', timedelta, optional=True, title="Sampling step",
            allowed_values=AllowedRange(timedelta(0), None, dtype=timedelta),
            abstract="Optional output data sampling step.",
        )),
        ("filters", LiteralData(
            'filters', str, optional=True, default="",
            abstract=(
                "Set of semi-colon-separated filters. The identifier and "
                "extent are separated by a colon and the range bounds "
                "are separated by a comma. "
                "E.g., 'F:10000,20000;Latitude:-50,50'"
            ),
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
                FormatBinaryRaw("application/cdf"),
                FormatBinaryRaw("application/x-cdf"),
            )
        )),
        ("source_products", ComplexData(
            'source_products', title="List of source products.", formats=(
                FormatText('text/plain'),
            )
        )),
    ]

    @staticmethod
    def on_started(context, progress, message):
        """ Callback executed when an asynchronous Job gets started. """
        try:
            job = update_job(
                get_job_by_id(context.identifier),
                status=Job.STARTED,
                started=datetime.now(utc),
            )
            context.logger.info(
                "Job started after %.3gs waiting.",
                (job.started - job.created).total_seconds()
            )
        except Job.DoesNotExist:
            context.logger.warn(
                "Failed to update the job status! The job does not exist!"
            )

    @staticmethod
    def on_succeeded(context, outputs):
        """ Callback executed when an asynchronous Job finishes. """
        try:
            job = update_job(
                get_job_by_id(context.identifier),
                status=Job.SUCCEEDED,
                stopped=datetime.now(utc),
            )
            context.logger.info(
                "Job finished after %.3gs running.",
                (job.stopped - job.started).total_seconds()
            )
        except Job.DoesNotExist:
            context.logger.warn(
                "Failed to update the job status! The job does not exist!"
            )

    @staticmethod
    def on_failed(context, exception):
        """ Callback executed when an asynchronous Job fails. """
        try:
            job = update_job(
                get_job_by_id(context.identifier),
                status=Job.FAILED,
                stopped=datetime.now(utc),
            )
            context.logger.info(
                "Job failed after %.3gs running.",
                (job.stopped - job.started).total_seconds()
            )
        except Job.DoesNotExist:
            context.logger.warn(
                "Failed to update the job status! The job does not exist!"
            )

    def initialize(self, context, inputs, outputs, parts):
        """ Asynchronous process initialization. """
        context.logger.info(
            "Received %s WPS request from %s.",
            self.identifier, inputs['\\username'] or "an anonymous user"
        )

        user = get_user(inputs['\\username'])

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

    @staticmethod
    def discard(context):
        """ Asynchronous process removal. """
        context.logger.info("removing %s" % context.identifier)
        job = get_job_by_id(context.identifier, raise_exception=False)
        if job:
            job.delete()
            context.logger.info("Job removed.")

    def execute(self, permissions, collection_ids, begin_time, end_time,
                filters, sampling_step, requested_variables, model_ids, shc,
                csv_time_format, output, source_products, context, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)
        #workspace_dir = ""

        # parse inputs
        sources = parse_collections(
            'collection_ids', collection_ids.data, permissions=permissions,
        )
        requested_models, source_models = parse_model_list(
            "model_ids", model_ids, shc
        )
        filters = parse_filters2("filters", filters)
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
            access_logger.warning(message)
            raise InvalidInputValueError('end_time', message)

        # log the request
        access_logger.info(
            "request parameters: toi: (%s, %s), collections: (%s), "
            "models: (%s), filters: {%s}",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            ", ".join(
                s.collection_identifier for l in sources.values() for s in l
            ),
            ", ".join(
                "%s = %s" % (model.name, model.full_expression)
                for model in requested_models
            ),
            ", ".join(
                "%s: (%g, %g)" % (f.label, f.vmin, f.vmax) for f in filters
            ),
        )

        if sampling_step is not None:
            self.logger.debug("sampling step: %s", sampling_step)

        # resolve data sources, models and filters and variables dependencies
        resolvers = dict()

        if sources:
            orbit_info = {
                spacecraft: [
                    OrbitCounter(
                        "OrbitCounter" + spacecraft,
                        cache_path(ORBIT_COUNTER_FILE[spacecraft])
                    ),
                    OrbitDirection(
                        "OrbitDirection" + spacecraft,
                        cache_path(ORBIT_DIRECTION_GEO_FILE[spacecraft])
                    ),
                    QDOrbitDirection(
                        "QDOrbitDirection" + spacecraft,
                        cache_path(ORBIT_DIRECTION_MAG_FILE[spacecraft])
                    ),
                ]
                for spacecraft in SPACECRAFTS
            }
            index_kp10 = IndexKp10(cache_path(AUX_DB_KP))
            index_dst = IndexDst(cache_path(AUX_DB_DST))
            index_f10 = IndexF107(cache_path(CACHED_PRODUCT_FILE["AUX_F10_2_"]))
            index_imf = ProductTimeSeries(
                ProductCollection.objects.get(type__identifier="SW_AUX_IMF_2_")
            )
            model_bnec_intensity = BnecToF()
            model_kp = IndexKpFromKp10()
            model_qdc = QuasiDipoleCoordinates()
            model_mlt = MagneticLocalTime()
            model_sun = SunPosition()
            model_subsol = SubSolarPoint()
            model_dipole = MagneticDipole()
            model_tilt_angle = DipoleTiltAngle()

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
            # optional sub-sampling filters
            if sampling_step:
                sampler = MinStepSampler('Timestamp', timedelta_to_cdf_rawtime(
                    sampling_step, CDF_EPOCH_TYPE
                ))
                grouping_sampler = GroupingSampler('Timestamp')
            else:
                sampler, grouping_sampler = None, None

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
                    resolver.add_slave(slave, 'Timestamp')

                    # optional extra sampling for selected collections
                    if sampler and slave.metadata.get('extraSampled'):
                        resolver.add_filter(ExtraSampler(
                            'Timestamp', slave.collection_identifier, slave
                        ))

                # optional sample grouping
                if grouping_sampler and master.metadata.get('groupSamples'):
                    resolver.add_filter(grouping_sampler)

                # auxiliary slaves
                for slave in (index_kp10, index_dst, index_f10, index_imf):
                    resolver.add_slave(slave, 'Timestamp')

                # satellite specific slaves
                spacecraft = master.metadata.get('spacecraft')
                resolver.add_model(SpacecraftLabel(spacecraft or '-'))

                for item in orbit_info.get(spacecraft, []):
                    resolver.add_slave(item, 'Timestamp')

                # prepare spacecraft to spacecraft differences
                subtracted_variables = get_subtracted_variables(unique(chain(
                    requested_variables, chain.from_iterable(
                        filter_.required_variables for filter_ in filters
                    )
                )))
                self.logger.debug("residual variables: %s", ", ".join(
                    var for var, _ in subtracted_variables
                ))
                grouped_diff_vars = group_subtracted_variables(
                    product_sources, subtracted_variables
                )
                for (msc, ssc), cols in grouped_diff_vars.items():
                    resolver.add_model(SatSatSubtraction(msc, ssc, cols))

                # models
                aux_models = chain((
                    model_bnec_intensity,
                    model_kp, model_qdc, model_mlt, model_sun,
                    model_subsol, model_dipole, model_tilt_angle,
                ), models_with_residuals)
                for model in aux_models:
                    resolver.add_model(model)

                # add remaining filters
                resolver.add_filters(filters)

                # add output variables
                resolver.add_output_variables(MANDATORY_VARIABLES)
                resolver.add_output_variables(requested_variables)

                # reduce dependencies
                resolver.reduce()

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
                    ", ".join(resolver.output_variables)
                )
                self.logger.debug(
                    "%s: applicable filters: %s", label,
                    "; ".join(str(f) for f in resolver.filters)
                )
                self.logger.debug(
                    "%s: unresolved filters: %s", label, "; ".join(
                        str(f) for f in resolver.unresolved_filters
                    )
                )

            # collect the common output variables
            output_variables = tuple(unique(chain.from_iterable(
                resolver.output_variables for resolver in resolvers.values()
            )))

        else:
            # empty output
            output_variables = ()

            self.logger.debug("output variables: %s", ", ".join(output_variables))

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
                    times = dataset[resolver.master.time_variable]
                    cdf_type = dataset.cdf_type[resolver.master.time_variable]
                    for slave in resolver.slaves:
                        dataset.merge(
                            slave.interpolate(times, variables, {}, cdf_type)
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
                            'filters',
                            "Failed to apply some of the filters "
                            "due to missing source variables! filters: %s" %
                            "; ".join(str(f) for f in filters_left)
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
                            'end_time',
                            "Requested data exceeds the maximum limit of %d "
                            "records!" % MAX_SAMPLES_COUNT
                        )

                    yield label, dataset

            access_logger.info(
                "response: count: %d samples, mime-type: %s, variables: (%s)",
                total_count, output['mime_type'], ", ".join(output_variables)
            )

        # === OUTPUT ===

        # get configurations
        #temp_basename = join(workspace_dir, "vires_" + uuid4().hex)
        #result_basename = "%s_%s_%s_Filtered" % (
        temp_basename = "%s_%s_%s_Filtered" % (
            "_".join(
                s.collection_identifier for l in sources.values() for s in l
            ),
            begin_time.strftime("%Y%m%dT%H%M%S"),
            end_time.strftime("%Y%m%dT%H%M%S"),
        )

        if output['mime_type'] == "text/csv":
            temp_filename = temp_basename + ".csv"
            #result_filename = result_basename + ".csv"
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
                    for row in zip(*(item for item in data if item is not None)):
                        print(
                            format_ % tuple(f(v) for f, v in zip(formatters, row)),
                            file=output_fobj
                        )

            product_names = extract_product_names(resolvers.values())

        elif output['mime_type'] in ("application/cdf", "application/x-cdf"):
            # TODO: proper no-data value configuration
            temp_filename = temp_basename + ".cdf"
            result_filename = temp_filename #result_basename + ".cdf"

            if exists(temp_filename):
                remove(temp_filename)

            record_count = 0
            with cdf_open(temp_filename, 'w') as cdf:
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
                        shape = (record_count,) + dataset[variable].shape[1:]
                        cdf.new(
                            variable, full(shape, nan),
                            dataset.cdf_type.get(variable)
                        )
                        cdf[variable].attrs.update(
                            dataset.cdf_attr.get(variable, {})
                        )

                    if dataset.length > 0: # write the follow-on dataset
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
                    "DATA_TIMESPAN": ("%s/%s" % (
                        begin_time.isoformat(), end_time.isoformat()
                    )).replace("+00:00", "Z"),
                    "DATA_FILTERS": [str(f) for f in filters],
                    "MAGNETIC_MODELS": [
                        "%s = %s" % (model.name, model.full_expression)
                        for model in requested_models
                    ],
                    "SOURCES": list(sources.keys()),
                    "ORIGINAL_PRODUCT_NAMES": product_names,
                })

        else:
            raise InvalidOutputDefError(
                'output',
                "Unexpected output format %r requested!" % output['mime_type']
            )

        source_products_filename = temp_basename + "_sources.txt"
        with open(source_products_filename, "w", encoding="utf-8", newline="\r\n") as output_fobj:
            for product_name in product_names:
                print(product_name, file=output_fobj)

        return {
            'output': Reference(*context.publish(temp_filename), **output),
            'source_products': Reference(
                *context.publish(source_products_filename), **source_products
            ),
        }


def get_job_by_id(identifier, raise_exception=True):
    """ Get job for the given job identifier. """
    try:
        return Job.objects.get(identifier=identifier)
    except Job.DoesNotExist:
        if raise_exception:
            raise
    return None


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
