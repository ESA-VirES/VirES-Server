#-------------------------------------------------------------------------------
#
# Project: VirES
# Authors: Daniel Santillan <daniel.santillan@eox.at>
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

from os import remove
from os.path import join, exists
from uuid import uuid4
from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import izip
import numpy as np

from django.conf import settings
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import (
    ExecuteError, InvalidInputValueError,
)
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, AllowedRange, CDFile, FormatBinaryRaw,
)

from eoxserver.backends.access import connect
from vires import models as db_models
from vires.aux import query_kp_int, query_dst_int
from vires.config import SystemConfigReader
from vires.util import (
    get_model, datetime_array_slice, between, datetime_mean,
)
from vires.time_util import datetime_to_decimal_year, naive_to_utc, TZ_UTC
from vires.cdf_util import (
    cdf_open, cdf_rawtime_to_mjd2000, cdf_rawtime_to_decimal_year_fast,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch, get_formatter,
)

import eoxmagmod as mm

# TODO: Make the limits configurable.
# Limit response size (equivalent to 5 daily SWARM LR products).
MAX_SAMPLES_COUNT = 432000

# time selection tolerance (10us)
TIME_TOLERANCE = timedelta(microseconds=10)

# display sample period
DISPLAY_SAMPLE_PERIOD = timedelta(seconds=5)

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


class RetrieveDataFiltered(Component):
    """ Process retrieving subset of the registered Swarm data based
    on collection, time interval and optional additional custom filters.
    This precess is designed to be used for the data download.
    """
    implements(ProcessInterface)

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

    def parse_filters(self, filter_string):
        """ Parse filters' string. """
        try:
            filter_ = {}
            if filter_string:
                for item in filter_string.split(";"):
                    name, bounds = item.split(":")
                    lower, upper = [float(v) for v in bounds.split(",")]
                    filter_[name] = (lower, upper)
        except ValueError as exc:
            raise InvalidInputValueError("filters", exc)
        return filter_


    def execute(self, collection_ids, shc, model_ids, begin_time, end_time,
                filters, sampling_step, csv_time_format, output, **kwarg):

        # get configurations
        conf_sys = SystemConfigReader()

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

        collection_ids = collection_ids.split(",") if collection_ids else []

        collections = db_models.ProductCollection.objects.filter(
            identifier__in=collection_ids
        )

        filters = self.parse_filters(filters)


        # collect models
        models = OrderedDict(
            (name, model) for name, model in (
                (name, get_model(name)) for name
                in (model_ids.split(",") if model_ids else [])
            ) if model is not None
        )
        if shc:
            models["Custom_Model"] = mm.read_model_shc(shc)

        data_fields = [
            field.identifier for field in collections[0].range_type
        ]

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
                products_qs = db_models.Product.objects.filter(
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

                    result, count, cdf_type = self.handle(
                        product, data_fields, low, high, sampling_step,
                        models, filters
                    )

                    total_count += count
                    if total_count > MAX_SAMPLES_COUNT:
                        raise ExecuteError(
                            "Requested data is too large and exceeds the "
                            "maximum limit of %d records! Please refine "
                            "your filters." % MAX_SAMPLES_COUNT
                        )

                    yield collection_id, product, result, cdf_type, count


        if output['mime_type'] == "text/csv":
            temp_filename = join(conf_sys.path_temp, temp_basename + ".csv")
            result_filename = result_basename + ".csv"
            initialize = True

            with open(temp_filename, "w") as fout:
                for item in generate_results():
                    collection_id, product, result, cdf_type, count = item
                    # convert the time format
                    result['Timestamp'] = (
                        CDF_RAW_TIME_CONVERTOR[csv_time_format](
                            result['Timestamp'], cdf_type['Timestamp']
                        )
                    )

                    if initialize:
                        fout.write(",".join(result.keys()))
                        fout.write("\r\n")
                        initialize = False

                    formatters = [
                        get_formatter(result[field], cdf_type.get(field))
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

            with cdf_open(temp_filename, 'w') as cdf:
                for item in generate_results():
                    collection_id, product, result, cdf_type, count = item
                    if initialize:
                        initialize = False
                        for field, values in result.iteritems():
                            cdf.new(field, values, cdf_type.get(field))
                    else:
                        for field, values in result.iteritems():
                            cdf[field].extend(values)

        else:
            ExecuteError(
                "Unexpected output format %r requested!" % output['mime_type']
            )

        return CDFile(temp_filename, filename=result_filename, **output)

    def handle(self, product, fields, low, high, step, models, filters):
        """ Single product retrieval. """

        # read initial subset of the CDF data
        cdf_type = {}
        data = OrderedDict()
        with cdf_open(connect(product.data_items.all()[0])) as cdf:
            time_mean = datetime_mean(cdf['Timestamp'][0], cdf['Timestamp'][-1])
            for field in fields:
                cdf_var = cdf.raw_var(field)
                cdf_type[field] = cdf_var.type()
                data[field] = cdf_var[low:high:step]

        # initialize full index array
        index = np.arange(len(data['Timestamp']))

        # apply data filters
        for field, bounds in filters.items():
            if field in fields: # filter scalar data field
                filtered_data = data[field][index]

            elif field in B_NEC_COMPONENTS: # filter vector component
                cidx = B_NEC_COMPONENTS[field]
                filtered_data = data["B_NEC"][index, cidx]

            elif field in AUX_INDEX: # filter auxiliary data
                query, filename = AUX_INDEX[field]
                filtered_data = query(
                    filename, cdf_rawtime_to_mjd2000(
                        data['Timestamp'][index], cdf_type['Timestamp']
                    )
                )

            else: # skip unknown filters
                continue

            # update index array
            index = index[between(filtered_data, bounds[0], bounds[1])]

        # apply Quasi-dipole Latitude and Magnetic Local Time filters
        appex_fields = set(filters) & set(("qdlat", "mlt"))

        if appex_fields:
            qdlat, qdlon, mlt = mm.eval_apex(
                data["Latitude"][index],
                data["Longitude"][index],
                data["Radius"][index] * 1e-3, # radius in km
                cdf_rawtime_to_decimal_year_fast(
                    data["Timestamp"], cdf_type['Timestamp'],
                    time_mean.year
                )
            )

            mask = True
            if "qdlat" in appex_fields:
                bounds = filters["qdlat"]
                mask &= between(qdlat, bounds[0], bounds[1])

            if "mlt" in appex_fields:
                bounds = filters["mlt"]
                mask &= between(mlt, bounds[0], bounds[1])

            # update index array
            index = index[mask]

        # apply model filters
        for model_id, model in models.iteritems():
            model_res_fields = set(filters) & set(
                "%s_res_%s" % (var_id, model_id)
                for var_id in ("B_N", "B_E", "B_C", "F")
            )

            # skip model evaluation if no residual filter is requested
            if not model_res_fields:
                continue

            coords_sph = np.vstack((
                data["Latitude"][index],
                data["Longitude"][index],
                data["Radius"][index] * 1e-3, # radius in km
            )).T

            model_data = model.eval(
                coords_sph,
                datetime_to_decimal_year(time_mean),
                mm.GEOCENTRIC_SPHERICAL,
                check_validity=False
            )
            model_data[:, 2] *= -1

            mask = True
            for field in model_res_fields:
                bounds = filters[field]

                if field.startswith("F"):
                    mask &= between(
                        data["F"][index] - mm.vnorm(model_data),
                        bounds[0], bounds[1]
                    )

                elif field[:3] in B_NEC_COMPONENTS:
                    cidx = B_NEC_COMPONENTS[field[:3]]
                    mask &= between(
                        data["B_NEC"][index, cidx] - model_data[:, cidx],
                        bounds[0], bounds[1]
                    )

            # update index array
            index = index[mask]

        # filter the actual data
        data = OrderedDict(
            (field, values[index]) for field, values in data.iteritems()
        )

        return data, len(data['Timestamp']), cdf_type
