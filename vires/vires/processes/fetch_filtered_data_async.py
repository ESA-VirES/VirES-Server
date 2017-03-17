#-------------------------------------------------------------------------------
#
# WPS fetch filtered download data
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
# pylint: disable=too-many-arguments, too-many-locals, too-many-branches,
# pylint: disable=too-many-branches, too-many-statements
# pylint: disable=missing-docstring, unused-argument

from functools import wraps
from os import remove
from os.path import exists #, join
#from uuid import uuid4
from itertools import chain, izip
from datetime import datetime, timedelta
from django.conf import settings
from django.utils.timezone import utc
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, RequestParameter, Reference,
    FormatText, FormatJSON, FormatBinaryRaw,
)
from eoxserver.services.ows.wps.exceptions import ExecuteError, ServerBusy
from vires.models import Job
from vires.util import unique, exclude, include
from vires.time_util import (
    naive_to_utc, timedelta_to_iso_duration,
)
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    get_formatter, CDF_EPOCH_TYPE, cdf_open,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_models2, parse_filters2, IndexKp, IndexDst,
    MagneticModelResidual, QuasiDipoleCoordinates, MagneticLocalTime,
    with_cache_session, get_username, get_user,
)

# TODO: Make the limits configurable.
# Limit number of active jobs (ACCEPTED or STARTED) per user
MAX_ACTIVE_JOBS = 2

# Limit response size (equivalent to 50 daily SWARM LR products).
MAX_SAMPLES_COUNT = 4320000

# maximum allowed time selection period (~100years >> mission life-time)
MAX_TIME_SELECTION = timedelta(days=35525)

# set of the minimum required variables
REQUIRED_VARIABLES = ["Timestamp", "Latitude", "Longitude", "Radius"]

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

    inputs = [
        ("username", RequestParameter(get_username)),
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
    ]


    @staticmethod
    def on_started(context, progress, message):
        """ Callback executed when an asynchronous Job gets started. """
        job = Job.objects.get(identifier=context.identifier)
        job.status = Job.STARTED
        job.started = datetime.now(utc)
        job.save()
        context.logger.info(
            "Job started after %.3gs waiting.",
            (job.started - job.created).total_seconds()
        )

    @staticmethod
    def on_succeeded(context, outputs):
        """ Callback executed when an asynchronous Job finishes. """
        job = Job.objects.get(identifier=context.identifier)
        job.status = Job.SUCCEEDED
        job.stopped = datetime.now(utc)
        job.save()
        context.logger.info(
            "Job finished after %.3gs running.",
            (job.stopped - job.started).total_seconds()
        )

    @staticmethod
    def on_failed(context, exception):
        """ Callback executed when an asynchronous Job fails. """
        job = Job.objects.get(identifier=context.identifier)
        job.status = Job.FAILED
        job.stopped = datetime.now(utc)
        job.save()
        context.logger.info(
            "Job failed after %.3gs running.",
            (job.stopped - job.started).total_seconds()
        )

    def initialize(self, context, inputs, outputs, parts):
        """ Asynchronous process initialization. """
        context.logger.info(
            "Received %s WPS request from %s.",
            self.identifier, inputs['\\username'] or "an anonymous user"
        )

        user = get_user(inputs['\\username'])
        active_jobs_count = Job.objects.filter(
            owner=user, status__in=(Job.ACCEPTED, Job.STARTED)
        ).count()

        if active_jobs_count >= MAX_ACTIVE_JOBS:
            raise ServerBusy(
                "Maximum number of allowed active asynchronous download "
                "requests exceeded!"
            )

        # create DB record for this WPS job
        job = Job()
        job.status = Job.ACCEPTED
        job.owner = user
        job.process_id = self.identifier
        job.identifier = context.identifier
        job.response_url = context.status_location
        job.save()

    @with_cache_session
    def execute(self, collection_ids, begin_time, end_time, filters,
                requested_variables, model_ids, shc,
                csv_time_format, output, context, **kwarg):
        """ Execute process """
        workspace_dir = ""

        # parse inputs
        sources = parse_collections('collection_ids', collection_ids.data)
        models = parse_models2("model_ids", model_ids, shc)
        filters = parse_filters2("filters", filters)

        if requested_variables is not None:
            requested_variables = [
                var.strip() for var in requested_variables.split(',')
            ] if requested_variables else []
        self.logger.debug("requested variables: %s", requested_variables)

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
            raise ExecuteError(message)

        # log the request
        self.access_logger.info(
            "request parameters: toi: (%s, %s), collections: (%s), "
            "models: (%s), filters: {%s}",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            ", ".join(
                s.collection.identifier for l in sources.values() for s in l
            ),
            ", ".join(model.name for model in models),
            ", ".join(
                "%s: (%g, %g)" % (f.label, f.vmin, f.vmax) for f in filters
            )
        )

        # prepare list of the extracted non-mandatory variables
        if sources:
            index_kp = IndexKp(settings.VIRES_AUX_DB_KP)
            index_dst = IndexDst(settings.VIRES_AUX_DB_DST)
            model_qdc = QuasiDipoleCoordinates()
            model_mlt = MagneticLocalTime()

            available_variables = list(exclude(unique(chain.from_iterable(
                source.variables for source in sources.itervalues().next()
            )), REQUIRED_VARIABLES)) + [
                'Kp', 'Dst', 'QDLat', 'QDLon', 'MLT'
            ]

            model_residuals = []
            for model in models:
                available_variables.extend(model.variables)
                # prepare residuals' sources
                for variable in model.BASE_VARIABLES:
                    model_residual = MagneticModelResidual(model.name, variable)
                    model_residuals.append(model_residual)
                    available_variables.extend(model_residual.variables)

            if requested_variables is not None:
                # make sure the requested variables exist and the minimum
                # required variables are present
                output_variables = list(include(
                    unique(requested_variables), available_variables
                ))
            else:
                # by default all variables are returned
                output_variables = available_variables

            # resolve sources and filters' dependencies
            # by adding intermediate variables
            _varset = set(output_variables)
            for filter_ in filters:
                _varset.update(filter_.required_variables)
            for model_residual in model_residuals:
                if _varset.intersection(model_residual.variables):
                    _varset.update(model_residual.required_variables)
            if _varset.intersection(model_mlt.variables):
                _varset.update(model_mlt.required_variables)
            # make sure only the available variables are evaluated
            _varset.intersection_update(available_variables)
            variables = list(_varset)

            # make sure the mandatory variables in the output
            output_variables = REQUIRED_VARIABLES + output_variables

            self.logger.debug("available variables: %s", available_variables)
            self.logger.debug("evaluated variables: %s", variables)
            self.logger.debug("returned variables: %s", output_variables)
        else:
            # no collection selected
            output_variables = variables = []

        def _generate_data_():
            samples_count = 0
            product_count = 0

            # count matched product to be bale
            collection_product_counts = dict(
                (label, merged_sources[0].subset_count(begin_time, end_time))
                for label, merged_sources in sources.iteritems()
            )
            total_product_count = sum(collection_product_counts.values())

            # generate the data
            for label, merged_sources in sources.iteritems():
                ts_master, ts_slaves = merged_sources[0], merged_sources[1:]
                # NOTE: the mandatory variables are always taken from the master
                dataset_iterator = ts_master.subset(
                    begin_time, end_time, REQUIRED_VARIABLES + variables,
                )
                for idx, dataset in enumerate(dataset_iterator, 1):
                    # update status
                    context.update_progress(
                        (product_count * 100) // total_product_count,
                        "Filtering collection %r, product %d of %d." % (
                            label, idx, collection_product_counts[label]
                        )
                    )
                    product_count += 1
                    #
                    time_variable = ts_master.TIME_VARIABLE
                    cdf_type = dataset.cdf_type[time_variable]
                    dataset, filters_left = dataset.filter(filters)
                    # subordinate interpolated datasets
                    for ts_slave in ts_slaves:
                        dataset.merge(ts_slave.interpolate(
                            dataset[time_variable], variables, None, cdf_type
                        ))
                        dataset, filters_left = dataset.filter(filters_left)
                    self.logger.debug("dataset.length: %s", dataset.length)
                    # auxiliary datasets
                    dataset.merge(index_kp.interpolate(
                        dataset[time_variable], variables, None, cdf_type
                    ))
                    dataset, filters_left = dataset.filter(filters_left)
                    dataset.merge(index_dst.interpolate(
                        dataset[time_variable], variables, None, cdf_type
                    ))
                    dataset, filters_left = dataset.filter(filters_left)
                    # quasi-dipole coordinates and magnetic local time
                    dataset.merge(model_qdc.eval(dataset, variables))
                    dataset, filters_left = dataset.filter(filters_left)
                    dataset.merge(model_mlt.eval(dataset, variables))
                    dataset, filters_left = dataset.filter(filters_left)
                    # spherical harmonics expansion models
                    for model in models:
                        dataset.merge(model.eval(dataset, variables))
                        dataset, filters_left = dataset.filter(filters_left)
                    # model residuals
                    for model_residual in model_residuals:
                        dataset.merge(model_residual.eval(dataset, variables))
                        dataset, filters_left = dataset.filter(filters_left)

                    if filters_left:
                        raise ExecuteError(
                            "Failed to apply some of the filters "
                            "due to missing source variables! filters: %s" %
                            "; ".join(str(f) for f in filters_left)
                        )

                    # check if the number of samples is within the allowed limit
                    samples_count += dataset.length
                    if samples_count > MAX_SAMPLES_COUNT:
                        self.access_logger.error(
                            "The sample count %d exceeds the maximum allowed "
                            "count of %d samples!",
                            samples_count, MAX_SAMPLES_COUNT,
                        )
                        raise ExecuteError(
                            "Requested data exceeds the maximum limit of %d "
                            "records!" % MAX_SAMPLES_COUNT
                        )

                    yield label, dataset.extract(output_variables)

            self.access_logger.info(
                "response: count: %d samples, mime-type: %s, variables: (%s)",
                samples_count, output['mime_type'], ", ".join(output_variables)
            )

        # === OUTPUT ===

        # get configurations
        #temp_basename = join(workspace_dir, "vires_" + uuid4().hex)
        #result_basename = "%s_%s_%s_Filtered" % (
        temp_basename = "%s_%s_%s_Filtered" % (
            "_".join(
                s.collection.identifier for l in sources.values() for s in l
            ),
            begin_time.strftime("%Y%m%dT%H%M%S"),
            (end_time - timedelta(seconds=1)).strftime("%Y%m%dT%H%M%S"),
        )

        if output['mime_type'] == "text/csv":
            temp_filename = temp_basename + ".csv"
            #result_filename = result_basename + ".csv"
            time_convertor = CDF_RAW_TIME_CONVERTOR[csv_time_format]
            initialize = True

            with open(temp_filename, "wb") as output_fobj:

                for label, dataset in _generate_data_():
                    # convert all time variables to the target file-format
                    for variable, data in dataset.iteritems():
                        cdf_type = dataset.cdf_type.get(variable)
                        if cdf_type == CDF_EPOCH_TYPE:
                            dataset[variable] = time_convertor(data, cdf_type)

                    if initialize:
                        output_fobj.write("id,")
                        output_fobj.write(",".join(dataset.iterkeys()))
                        output_fobj.write("\r\n")
                        formatters = [
                            get_formatter(data, dataset.cdf_type.get(variable))
                            for variable, data in dataset.iteritems()
                        ]
                        initialize = False

                    label_prefix = "%s," % label
                    for row in izip(*dataset.itervalues()):
                        output_fobj.write(label_prefix)
                        output_fobj.write(
                            ",".join(f(v) for f, v in zip(formatters, row))
                        )
                        output_fobj.write("\r\n")


        elif output['mime_type'] in ("application/cdf", "application/x-cdf"):
            temp_filename = temp_basename + ".cdf"
            result_filename = temp_filename #result_basename + ".cdf"
            initialize = True

            if exists(temp_filename):
                remove(temp_filename)

            with cdf_open(temp_filename, 'w') as cdf:
                for _, dataset in _generate_data_():
                    if initialize: # write the first dataset
                        initialize = False
                        for variable, values in dataset.iteritems():
                            cdf.new(
                                variable, values, dataset.cdf_type.get(variable)
                            )
                            cdf[variable].attrs.update(
                                dataset.cdf_attr.get(variable, {})
                            )
                    else: # write follow-on dataset
                        for field, values in dataset.iteritems():
                            cdf[field].extend(values)

                # add the global attributes
                cdf.attrs.update({
                    "TITLE": result_filename,
                    "DATA_TIMESPAN": ("%s/%s" % (
                        begin_time.isoformat(), end_time.isoformat()
                    )).replace("+00:00", "Z"),
                    "DATA_FILTERS": [str(f) for f in filters],
                    "MAGNETIC_MODELS": [model.name for model in models],
                    "SOURCES": sources.keys(),
                    "ORIGINAL_PRODUCT_NAMES": sum(
                        (s.products for l in sources.values() for s in l), []
                    )
                })

        else:
            ExecuteError(
                "Unexpected output format %r requested!" % output['mime_type']
            )

        return Reference(*context.publish(temp_filename), **output)
