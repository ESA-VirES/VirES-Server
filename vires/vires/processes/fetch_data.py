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
# pylint: disable=too-many-arguments, too-many-locals

from itertools import chain, izip
from datetime import datetime, timedelta
from cStringIO import StringIO
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    LiteralData,
    BoundingBoxData,
    ComplexData,
    FormatText, FormatJSON,
    CDFileWrapper,
)
from eoxserver.services.ows.wps.exceptions import ExecuteError
from vires.util import unique, exclude, include
from vires.time_util import (
    naive_to_utc,
    timedelta_to_iso_duration,
)
from vires.cdf_util import (
    cdf_rawtime_to_datetime, cdf_rawtime_to_mjd2000, cdf_rawtime_to_unix_epoch,
    get_formatter, CDF_EPOCH_TYPE,
)
from vires.processes.base import WPSProcess
from vires.processes.util import (
    parse_collections, parse_models,
    IndexKp, IndexDst,
)


# maximum allowed time selection period
MAX_TIME_SELECTION = timedelta(days=16)

# set of the minimum required variables
REQUIRED_VARIABLES = ["Timestamp", "Latitude", "Longitude", "Radius"]

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
    This precess is designed to be used by the web-client.
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
            'output', title="Output data", formats=FormatText('text/csv')
        )),
    ]

    def execute(self, collection_ids, begin_time, end_time, bbox,
                requested_variables, model_ids, shc,
                csv_time_format, output, **kwarg):
        """ Execute process """
        # parse inputs
        sources = parse_collections('collection_ids', collection_ids.data)
        models = parse_models("model_ids", model_ids, shc)
        if requested_variables is None:
            requested_variables = None
        else:
            requested_variables = [
                var.strip() for var in requested_variables.split(',')
            ]
        self.logger.debug("requested variables: %s", requested_variables)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

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
            "request: toi: (%s, %s), aoi: %s, collections: (%s), "
            "models: (%s), ",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            bbox[0]+bbox[1] if bbox else (-90, -180, 90, 180),
            ", ".join(
                s.collection.identifier for l in sources.values() for s in l
            ), ", ".join(models),
        )

        # prepare list of the extracted non-mandatory variables
        if sources:
            available_variables = list(exclude(unique(chain.from_iterable(
                source.variables for source in sources.itervalues().next()
            )), REQUIRED_VARIABLES)) + ['Kp', 'Dst']

            if requested_variables is not None:
                # make sure the requested variables exist and the minimum
                # required variables are present
                variables = list(include(
                    requested_variables, available_variables
                ))
            else:
                # by default all variables are returned
                variables = available_variables
        else:
            # no collection selected
            variables = []

        def _generate_data_():
            index_kp = IndexKp(settings.VIRES_AUX_DB_KP)
            index_dst = IndexDst(settings.VIRES_AUX_DB_DST)
            for label, merged_sources in sources.iteritems():
                ts_master, ts_slaves = merged_sources[0], merged_sources[1:]
                # NOTE: the mandatory variables are always taken from the master
                dataset_iterator = ts_master.subset(
                    begin_time, end_time, REQUIRED_VARIABLES + variables,
                )
                for dataset in dataset_iterator:
                    times = dataset[ts_master.TIME_VARIABLE]
                    cdf_type = dataset.cdf_type[ts_master.TIME_VARIABLE]
                    # subordinate interpolated datasets
                    for ts_slave in ts_slaves:
                        dataset.merge(
                            ts_slave.interpolate(times, variables, {}, cdf_type)
                        )
                    # auxiliary datasets
                    dataset.merge(
                        index_kp.interpolate(times, variables, None, cdf_type)
                    )
                    dataset.merge(
                        index_dst.interpolate(times, variables, None, cdf_type)
                    )
                    yield label, dataset

        # write the output
        output_fobj = StringIO()

        initialize = True
        for label, dataset in _generate_data_():

            # time-format conversion
            for variable, data in dataset.iteritems():
                cdf_type = dataset.cdf_type.get(variable)
                if cdf_type == CDF_EPOCH_TYPE:
                    dataset[variable] = CDF_RAW_TIME_CONVERTOR[csv_time_format](
                        data, cdf_type
                    )

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

        http_headers = ()
        return CDFileWrapper(output_fobj, headers=http_headers, **output)
