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

import json
from collections import OrderedDict
from datetime import datetime, timedelta
from itertools import izip
import cStringIO
import numpy as np

from django.conf import settings
from eoxserver.core import Component, implements
from eoxserver.services.ows.wps.interfaces import ProcessInterface
from eoxserver.services.ows.wps.exceptions import (
    ExecuteError, InvalidInputValueError,
)
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, AllowedRange, BoundingBoxData,
    CDFileWrapper,
)

from eoxserver.backends.access import connect
from vires import models as db_models
from vires.aux import query_kp_int, query_dst_int
from vires.util import (
    get_model, datetime_array_slice, between, datetime_mean,
)
from vires.time_util import datetime_to_decimal_year, naive_to_utc
from vires.cdf_util import (
    cdf_open, cdf_rawtime_to_mjd2000, cdf_rawtime_to_decimal_year_fast,
    cdf_rawtime_to_datetime, cdf_rawtime_to_unix_epoch, get_formatter,
)

import eoxmagmod as mm

# TODO: Make following parameters configurable.
# Limit response size (equivalent to 1/2 daily SWARM LR product).
MAX_SAMPLES_COUNT_PER_COLLECTION = 43200

# time selection tolerance (10us)
TIME_TOLERANCE = timedelta(microseconds=10)

# display sample period
DISPLAY_SAMPLE_PERIOD = timedelta(seconds=15)

REQUIRED_FIELDS = [
    "Timestamp", "Latitude", "Longitude", "Radius", "F", "F_error", "B_NEC",
    "B_error"
]

DROPPED_FIELDS = [
    "B_VFM", "SyncStatus", "q_NEC_CRF", "Att_error", "Flags_F", "Flags_B",
    "Flags_q", "Flags_Platform", "ASM_Freq_Dev", "dB_AOCS", "dB_other",
    "dF_AOCS", "dF_other"
]

CDF_RAW_TIME_CONVERTOR = {
    "ISO date-time": cdf_rawtime_to_datetime,
    "MJD2000": cdf_rawtime_to_mjd2000,
    "Unix epoch": cdf_rawtime_to_unix_epoch,
}


class RetrieveData(Component):
    """ Process retrieving registered Swarm data based on collection, time
    interval and additional optional parameters.
    This precess is designed to be used by the web-client.
    """
    implements(ProcessInterface)

    identifier = "retrieve_data"
    title = "Retrieve Swarm data"
    metadata = {}
    profiles = ["vires"]

    inputs = [
        ("collection_ids", LiteralData(
            'collection_ids', str, optional=False,
            title="Collection identifiers",
            abstract="Semicolon separated list of collection identifiers.",
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
        ("bbox", BoundingBoxData(
            "bbox", crss=(4326,), optional=True, title="Bounding box",
            abstract="Optional selection bounding box.", default=None,
        )),
        ("sampling_step", LiteralData(
            'sampling_step', int, optional=True, title="Data sampling step.",
            allowed_values=AllowedRange(1, None, dtype=int), default=None,
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
            'output', title="Output data",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def parse_models(self, model_ids, shc):
        """ Parse filters' string. """
        models = OrderedDict()
        if model_ids.strip():
            for model_id in (id_.strip() for id_ in model_ids.split(",")):
                model = get_model(model_id)
                if model is None:
                    raise InvalidInputValueError(
                        "model_ids",
                        "Invalid model identifier '%s'!" % model_id
                    )
                models[model_id] = model
        if shc:
            try:
                models["Custom_Model"] = mm.read_model_shc(shc)
            except ValueError:
                raise InvalidInputValueError(
                    "shc", "Failed to parse the custom model coefficients."
                )
        return models

    def execute(self, collection_ids, shc, model_ids, begin_time, end_time,
                bbox, sampling_step, csv_time_format, output, **kwarg):
        # parse models
        models = self.parse_models(model_ids, shc)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)

        output_fobj = cStringIO.StringIO()

        collection_ids = collection_ids.split(",") if collection_ids else []

        collections = db_models.ProductCollection.objects.filter(
            identifier__in=collection_ids
        )

        if not collections or end_time < begin_time:
            http_headers = (
                ("X-EOX-Source-Data-Sampling-Period", json.dumps({})),
                ("X-EOX-Output-Data-Sampling-Period", json.dumps({})),
            )
            return CDFileWrapper(output_fobj, headers=http_headers, **output)

        # TODO: assert that the range_type is equal for all collections
        # prepare fields
        data_fields = [
            field.identifier for field in collections[0].range_type
            if field.identifier in REQUIRED_FIELDS
        ]

        # write CSV header flag
        initialize = True
        # per-collection sampling periods in seconds
        source_sampling_period = {}
        output_sampling_period = {}

        total_count = 0

        if bbox:
            relative_area = (
                (bbox.upper[0] - bbox.lower[0]) *
                (bbox.lower[1] - bbox.upper[1])
            ) / 64800.0
        else:
            relative_area = 1.0
        day_count = (end_time - begin_time).total_seconds() / 86400.0

        for collection_id in collection_ids:
            collection_count = 0
            products_qs = db_models.Product.objects.filter(
                collections__identifier=collection_id,
                begin_time__lte=(end_time + TIME_TOLERANCE),
                end_time__gte=(begin_time - TIME_TOLERANCE),
            ).order_by('begin_time')

            for product in (item.cast() for item in products_qs):
                if sampling_step is None:
                    # automatic adaptive sampling
                    relative_period = (
                        DISPLAY_SAMPLE_PERIOD.total_seconds() /
                        product.sampling_period.total_seconds()
                    )
                    step = max(1, int(
                        relative_area * max(1.0, day_count) * relative_period
                    ))
                else:
                    # user defined sampling
                    step = sampling_step

                #NOTE: How to get sampling period for an empty collection?
                #TODO: Move outside of the product loop.
                source_sampling_period[collection_id] = (
                    product.sampling_period.total_seconds()
                )
                output_sampling_period[collection_id] = (
                    step * product.sampling_period.total_seconds()
                )

                time_first, time_last = product.time_extent
                low, high = datetime_array_slice(
                    begin_time, end_time, time_first, time_last,
                    product.sampling_period, TIME_TOLERANCE
                )
                data, count, cdf_type = self.handle(
                    product, data_fields, low, high, step, models, bbox
                )
                total_count += count
                collection_count += count

                # Check current amount of features and decide if to continue
                if collection_count > MAX_SAMPLES_COUNT_PER_COLLECTION:
                    raise ExecuteError(
                        "Requested data is too large and exceeds the "
                        "maximum limit of %d records per collection!" %
                        MAX_SAMPLES_COUNT_PER_COLLECTION
                    )

                # convert the time format
                data['Timestamp'] = (
                    CDF_RAW_TIME_CONVERTOR[csv_time_format](
                        data['Timestamp'], cdf_type['Timestamp']
                    )
                )

                if initialize:
                    output_fobj.write("id,")
                    output_fobj.write(",".join(data.keys()))
                    output_fobj.write("\r\n")
                    initialize = False

                cid_prefix = "%s," % collection_id
                formatters = [
                    get_formatter(data[field], cdf_type.get(field))
                    for field in data
                ]

                for row in izip(*data.itervalues()):
                    output_fobj.write(cid_prefix)
                    output_fobj.write(
                        ",".join(f(v) for f, v in zip(formatters, row))
                    )
                    output_fobj.write("\r\n")

        # HTTP headers
        http_headers = (
            (
                "X-EOX-Source-Data-Sampling-Period",
                json.dumps(source_sampling_period)
            ),
            (
                "X-EOX-Output-Data-Sampling-Period",
                json.dumps(output_sampling_period)
            ),
        )
        return CDFileWrapper(output_fobj, headers=http_headers, **output)

    def handle(self, product, fields, low, high, step, models, bbox=None):
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

        # bounding box filter
        if bbox:
            # initialize indices
            index = np.arange(len(data['Timestamp']))
            # filter the indices
            index = index[
                between(data["Longitude"][index], bbox.lower[1], bbox.upper[1])
            ]
            index = index[
                between(data["Latitude"][index], bbox.lower[0], bbox.upper[0])
            ]
            # data update
            data = OrderedDict(
                (field, values[index]) for field, values in data.iteritems()
            )

        # get auxiliary data
        mjd2000_times = cdf_rawtime_to_mjd2000(
            data['Timestamp'], cdf_type['Timestamp']
        )
        data.update(query_dst_int(settings.VIRES_AUX_DB_DST, mjd2000_times))
        data.update(query_kp_int(settings.VIRES_AUX_DB_KP, mjd2000_times))

        # get Quasi-dipole Latitude and Magnetic Local Time
        data["qdlat"], _, data["mlt"] = mm.eval_apex(
            data["Latitude"],
            data["Longitude"],
            data["Radius"] * 1e-3, # radius in km
            cdf_rawtime_to_decimal_year_fast(
                data["Timestamp"], cdf_type['Timestamp'], time_mean.year
            )
        )

        # evaluate models
        if models:
            coords_sph = np.vstack((
                data["Latitude"],
                data["Longitude"],
                data["Radius"] * 1e-3, # radius in km
            )).T

            for model_id, model in models.iteritems():
                model_data = model.eval(
                    coords_sph,
                    datetime_to_decimal_year(time_mean),
                    mm.GEOCENTRIC_SPHERICAL,
                    check_validity=False
                )
                model_data[:, 2] *= -1
                # store residuals
                # TODO: check if the residual evaluation is correct
                data["F_res_%s" % model_id] = data["F"] - mm.vnorm(model_data)
                data["B_NEC_%s" % model_id] = data["B_NEC"] - model_data

        return data, len(data['Timestamp']), cdf_type
