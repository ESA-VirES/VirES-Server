#-------------------------------------------------------------------------------
#
# Filtered data retrieval
#
# Project: VirES
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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
# pylint: disable=too-many-arguments, too-many-locals, missing-docstring
# pylint: disable=no-self-use, too-many-branches

from os import remove
from os.path import join, exists
from uuid import uuid4
from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import izip
import numpy as np
from django.conf import settings
from eoxserver.services.ows.wps.exceptions import ExecuteError
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, AllowedRange, CDFile, FormatBinaryRaw,
)
from eoxserver.backends.access import connect
from vires.aux import query_kp_int, query_dst_int
from vires.config import SystemConfigReader
from vires.util import datetime_array_slice, between
from vires.time_util import (
    datetime_to_decimal_year, naive_to_utc, TZ_UTC, datetime_mean,
    timedelta_to_iso_duration,
)
from vires.cdf_util import (
    cdf_open, cdf_rawtime_to_mjd2000, cdf_rawtime_to_decimal_year_fast,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch, get_formatter,
)
from vires.models import ProductCollection, Product
from vires.perf_util import ElapsedTimeLogger
from vires.processes.base import WPSProcess
from vires.processes.util import parse_models, parse_filters, format_filters
from eoxmagmod import vnorm, GEOCENTRIC_SPHERICAL
from eoxmagmod.qd import eval_qdlatlon, eval_mlt

# TODO: Make the limits configurable.
# Limit response size (equivalent to 5 daily SWARM LR products).
MAX_SAMPLES_COUNT = 432000

# time selection tolerance
TIME_TOLERANCE = timedelta(microseconds=10)

# display sample period
DISPLAY_SAMPLE_PERIOD = timedelta(seconds=5)

# maximum allowed time selection period
MAX_TIME_SELECTION = timedelta(days=16)

# Auxiliary data query function and file sources
AUX_INDEX = {
    "kp": (query_kp_int, settings.VIRES_AUX_DB_KP),
    "dst": (query_dst_int, settings.VIRES_AUX_DB_DST),
}

# Magnetic field vector components
B_NEC_COMPONENTS = {"B_N": 0, "B_E": 1, "B_C": 2}

CDF_RAW_TIME_CONVERTOR = {
    "ISO date-time": cdf_rawtime_to_datetime,
    "MJD2000": cdf_rawtime_to_mjd2000,
    "Unix epoch": cdf_rawtime_to_unix_epoch,
}


class RetrieveDataFiltered(WPSProcess):
    """ Process retrieving subset of the registered Swarm data based
    on collection, time interval and optional additional custom filters.
    This precess is designed to be used for the data download.
    """
    identifier = "retrieve_data_filtered"
    title = "Retrieve filtered Swarm data."
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("collection_ids", LiteralData(
            'collection_ids', str, optional=False,
            title="Collection identifiers",
            abstract="Semicolon separated list of collection identifiers.",
        )),
        ("shc", ComplexData(
            'shc', optional=True, title="Custom model coefficients.",
            abstract=(
                "Custom forward magnetic field model coefficients encoded "
                " in the SHC plain-text format."
            ),
            formats=(FormatText('text/plain'),)
        )),
        ("model_ids", LiteralData(
            'model_ids', str, optional=True, default="",
            title="Model identifiers",
            abstract="One one or more forward magnetic model identifiers.",
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
        ("parameters", LiteralData(
            'parameters', str, optional=True, default="",
            abstract=(
                "Set of semi-colon-separated parameters which define " 
                "parameters requested to be in the resultung download file"
            ),
        )),
        ("sampling_step", LiteralData(
            'sampling_step', int, optional=True, title="Data sampling step.",
            allowed_values=AllowedRange(1, None, dtype=int), default=1,
            abstract=(
                "Optional output data sampling step used to reduce the amount "
                "of the returned data. If set to 1 all matched product samples "
                "will be returned. If not used the server tries to find the "
                "optimal data sampling."
            ),
        )),
        ("csv_time_format", LiteralData(
            'csv_time_format', str, optional=True, title="CSV time  format",
            abstract="Optional time format used by the CSV output.",
            allowed_values=("ISO date-time", "MJD2000", "Unix epoch"),
            default="ISO date-time",
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

    def execute(self, collection_ids, shc, model_ids, begin_time, end_time, 
                filters, parameters, sampling_step, csv_time_format, output, 
                **kwarg):
        # get configurations
        conf_sys = SystemConfigReader()

        # parse models and filters
        models = parse_models("model_ids", model_ids, shc)
        filters = parse_filters("filters", filters)

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

        collection_ids = collection_ids.split(",") if collection_ids else []

        self.access_logger.info(
            "request parameters: toi: (%s, %s), collections: (%s), "
            "models: (%s), filters: {%s}",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            ", ".join(collection_ids), ", ".join(models), ", ".join(
                "%s: (%g, %g)" % (k, v[0], v[1]) for k, v in filters.iteritems()
            )
        )

        collections = ProductCollection.objects.filter(
            identifier__in=collection_ids
        )

        # TODO: Graceful handling of an empty collection list.

        data_fields = [
            field.identifier for field in collections[0].range_type
        ]

        # If custom parameters are specified remove all data_fields not 
        # contained in provided parameter list
        if (parameters!=""):
            parameters = parameters.split(";")
            #data_fields = [x for x in data_fields if x in parameters]
            data_fields = parameters

        # TODO: assert that the range_type is equal for all collections

        total_count = 0

        # FIXME: Product type in the file name!
        result_basename = "%s_%s_%s_MDR_MAG_Filtered" % (
            "_".join(collection_ids),
            begin_time.astimezone(TZ_UTC).strftime("%Y%m%dT%H%M%S"),
            end_time.astimezone(TZ_UTC).strftime("%Y%m%dT%H%M%S"),
        )
        temp_basename = uuid4().hex

        def generate_results():
            """ Result generator. """
            total_count = 0
            for collection_id in collection_ids:
                products_qs = Product.objects.filter(
                    collections__identifier=collection_id,
                    begin_time__lte=(end_time + TIME_TOLERANCE),
                    end_time__gte=(begin_time - TIME_TOLERANCE),
                ).order_by('begin_time')

                for product in (item.cast() for item in products_qs):
                    time_first, time_last = product.time_extent
                    low, high = datetime_array_slice(
                        begin_time, end_time, time_first, time_last,
                        product.sampling_period, TIME_TOLERANCE
                    )

                    filtered_fraction = float(high - low) / (
                        float(sampling_step) * float(product.size_x)
                    )
                    with ElapsedTimeLogger("%.2g%% of %s extracted in" % (
                        100.0 * filtered_fraction, product.identifier,
                    ), self.logger) as etl:
                        result, count, cdf_vars = self.handle(
                            product, data_fields, low, high, sampling_step,
                            models, filters
                        )
                        etl.message = ("%d samples from " % count) + etl.message

                    self.access_logger.info(
                        "collection: %s, product: %s, count: %d"
                        " sampling: %gs",
                        collection_id, product.identifier, count,
                        product.sampling_period.total_seconds() * sampling_step
                    )

                    total_count += count
                    if total_count > MAX_SAMPLES_COUNT:
                        self.access_logger.error(
                            "The sample count %d exceeds the maximum allowed "
                            "count of %d samples!",
                            total_count, MAX_SAMPLES_COUNT,
                        )
                        raise ExecuteError(
                            "Requested data is too large and exceeds the "
                            "maximum limit of %d records! Please refine "
                            "your filters." % MAX_SAMPLES_COUNT
                        )

                    yield collection_id, product, result, cdf_vars, count

            self.access_logger.info(
                "response: count: %d samples, mime-type: %s",
                total_count, output['mime_type']
            )


        if output['mime_type'] == "text/csv":
            temp_filename = join(conf_sys.path_temp, temp_basename + ".csv")
            result_filename = result_basename + ".csv"
            initialize = True

            with open(temp_filename, "w") as fout:
                for item in generate_results():
                    collection_id, product, result, cdf_vars, count = item
                    # convert the time format
                    if 'Timestamp' in result:
                        result['Timestamp'] = (
                            CDF_RAW_TIME_CONVERTOR[csv_time_format](
                                result['Timestamp'], cdf_vars['Timestamp']['type']
                            )
                        )

                    if initialize:
                        fout.write(",".join(result.keys()))
                        fout.write("\r\n")
                        initialize = False

                    formatters = [
                        get_formatter(
                            result[field], cdf_vars.get(field, {}).get('type')
                        )
                        for field in result
                    ]

                    for row in izip(*result.itervalues()):
                        fout.write(
                            ",".join(f(v) for f, v in zip(formatters, row))
                        )
                        fout.write("\r\n")

        elif output['mime_type'] in ("application/cdf", "application/x-cdf"):
            temp_filename = join(conf_sys.path_temp, temp_basename + ".cdf")
            result_filename = result_basename + ".cdf"
            initialize = True

            if exists(temp_filename):
                remove(temp_filename)

            product_list = []
            with cdf_open(temp_filename, 'w') as cdf:
                for item in generate_results():
                    collection_id, product, result, cdf_vars, count = item
                    product_list.append(product.identifier)
                    if initialize:
                        initialize = False
                        for field, values in result.iteritems():
                            cdf.new(
                                field, values,
                                cdf_vars.get(field, {}).get('type')
                            )
                            cdf[field].attrs.update(
                                cdf_vars.get(field, {}).get('attrs', {})
                            )
                    else:
                        for field, values in result.iteritems():
                            cdf[field].extend(values)
                # add the global attributes
                cdf.attrs.update({
                    "TITLE": result_filename,
                    "DATA_TIMESPAN": ("%s/%s" % (
                        begin_time.isoformat(), end_time.isoformat()
                    )).replace("+00:00", "Z"),
                    "DATA_FILTERS": format_filters(filters),
                    "ORIGINAL_PRODUCT_NAMES:": product_list,
                })
        else:
            ExecuteError(
                "Unexpected output format %r requested!" % output['mime_type']
            )

        return CDFile(temp_filename, filename=result_filename, **output)

    def handle(self, product, fields, low, high, step, models, filters):
        """ Single product retrieval. """

        # read initial subset of the CDF data
        cdf_vars = {}
        data = OrderedDict()

        # dict to save data that is required to compute other parameter
        req_fields = ["Latitude", "Longitude", "Radius", "Timestamp", "F",
                      "B_NEC"]
        req_data = OrderedDict()

        with cdf_open(connect(product.data_items.all()[0])) as cdf:
            time_mean = datetime_mean(cdf['Timestamp'][0], cdf['Timestamp'][-1])
            for field in fields:
                if field in cdf:
                    cdf_var = cdf.raw_var(field)
                    cdf_vars[field] = {
                        'type': cdf_var.type(),
                        'attrs': dict(cdf_var.attrs),
                    }
                    data[field] = cdf_var[low:high:step]

            for field in req_fields:
                if field in cdf:
                    cdf_var = cdf.raw_var(field)
                    cdf_vars[field] = {
                        'type': cdf_var.type(),
                        'attrs': dict(cdf_var.attrs),
                    }
                    req_data[field] = cdf_var[low:high:step]

        # initialize full index array
        if data:
            index = np.arange(len(data[data.keys()[0]]))
        else:
            # If no parameters from the rangetype are requested use length of
            # required parameters
            index = np.arange(len(req_data[req_data.keys()[0]]))

        # apply data filters
        for field, bounds in filters.items():
            if field in fields: # filter scalar data field
                if field in data:
                    filtered_data = data[field][index]

            elif field in B_NEC_COMPONENTS: # filter vector component
                cidx = B_NEC_COMPONENTS[field]
                filtered_data = data["B_NEC"][index, cidx]

            elif field in AUX_INDEX: # filter auxiliary data
                query, filename = AUX_INDEX[field]
                filtered_data = query(
                    filename, cdf_rawtime_to_mjd2000(
                        data['Timestamp'][index], cdf_vars['Timestamp']['type']
                    )
                )[field]

            else: # skip unknown filters
                continue

            # update index array
            if 'filtered_data' in locals():
                index = index[between(filtered_data, bounds[0], bounds[1])]

        # apply Quasi-dipole Latitude and Magnetic Local Time filters
        appex_fields = set(filters) & set(("qdlat", "mlt"))
        # Check if custom parameters/fields are provided for download 
        appex_download_fields = set(fields) & set(("qdlat", "qdlon", "mlt"))

        # If filtering or download is requested for appex fields they need to be
        # calculated
        if appex_fields or appex_download_fields:
            qdlat, qdlon = eval_qdlatlon(
                req_data["Latitude"][index],
                req_data["Longitude"][index],
                req_data["Radius"][index] * 1e-3, # radius in km
                cdf_rawtime_to_decimal_year_fast(
                    req_data["Timestamp"][index],
                    cdf_vars['Timestamp']['type'],
                    time_mean.year
                )
            )
            mlt = eval_mlt(
                qdlon,
                cdf_rawtime_to_mjd2000(
                    req_data["Timestamp"][index],
                    cdf_vars['Timestamp']['type']
                )
            )

        # Filtering for appex data
        if appex_fields:
            mask = True
            if "qdlat" in appex_fields:
                bounds = filters["qdlat"]
                mask &= between(qdlat, bounds[0], bounds[1])

            if "mlt" in appex_fields:
                bounds = filters["mlt"]
                mask &= between(mlt, bounds[0], bounds[1])

            # update index array
            index = index[mask]

        # Add appex data to result output
        if appex_download_fields:
            if "qdlat" in appex_download_fields:
                data["qdlat"] = qdlat
            if "qdlon" in appex_download_fields:
                data["qdlon"] = qdlon
            if "mlt" in appex_download_fields:
                data["mlt"] = mlt
                


        # apply model filters
        for model_id, model in models.iteritems():

            model_res_fields = set(filters) & set(
                "%s_res_%s" % (var_id, model_id)
                for var_id in ("B_N", "B_E", "B_C", "F")
            )
            model_res_download_fields = set(fields) & set(
                "%s_res_%s" % (var_id, model_id)
                for var_id in ("B_NEC", "F")
            )
            # skip model evaluation if no residual filter is requested
            # residuals not requested as custom download parameters
            if model_res_fields or model_res_download_fields:
                coords_sph = np.vstack((
                    req_data["Latitude"][index],
                    req_data["Longitude"][index],
                    req_data["Radius"][index] * 1e-3, # radius in km
                )).T

                model_data = model.eval(
                    coords_sph,
                    datetime_to_decimal_year(time_mean),
                    GEOCENTRIC_SPHERICAL,
                    check_validity=False
                )
                model_data[:, 2] *= -1

            if model_res_fields:
                mask = True
                for field in model_res_fields:
                    bounds = filters[field]

                    if field.startswith("F"):
                        mask &= between(
                            req_data["F"][index] - vnorm(model_data),
                            bounds[0], bounds[1]
                        )

                    elif field[:3] in B_NEC_COMPONENTS:
                        cidx = B_NEC_COMPONENTS[field[:3]]
                        mask &= between(
                            req_data["B_NEC"][index, cidx] - model_data[:, cidx],
                            bounds[0], bounds[1]
                        )

                # update index array
                index = index[mask]

            # Include all requested parameters for download
            if model_res_download_fields:
                for field in model_res_download_fields:

                    if field.startswith("F"):
                        data[field] = req_data["F"][index] - vnorm(model_data)

                    elif field[:5] in "B_NEC":
                        # with ElapsedTimeLogger("%.2g%% of %s extracted in" % (100, "bla",), self.logger) as etl:
                        #     etl.message = ("%s" % field[:5])
                        data[field] = req_data["B_NEC"] - model_data

        # filter the actual data
        data = OrderedDict(
            (field, values[index]) for field, values in data.iteritems()
        )

        return data, len(data[data.keys()[0]]), cdf_vars
