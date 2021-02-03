#-------------------------------------------------------------------------------
#
# WPS process fetching list of available observatories and their time ranges
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
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
# pylint: disable=no-self-use,unused-argument


import re
from io import StringIO
from datetime import datetime
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, FormatJSON, CDObject, CDFileWrapper,
)
from eoxserver.services.ows.wps.exceptions import (
    InvalidInputValueError, InvalidOutputDefError,
)
from vires.models import ProductCollection
from vires.time_util import naive_to_utc
from vires.processes.base import WPSProcess


ALLOWED_PRODUCT_TYPES = ["SW_AUX_OBSx2_", "SW_AUX_OBSH2_", "SW_VOBS_xM_2_"]


class GetObservatories(WPSProcess):
    """ Process for retrieving list of available magnetic observatories.
    """
    identifier = "vires:get_observatories"
    title = "Get available magnetic observatories."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("collection_id", LiteralData(
            'collection_id', str, optional=False,
            title="AUX_OBS or VOBS collection identifier",
            abstract="AUX_OBS or VOBS collection identifier",
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=True, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=True, title="End time",
            abstract="End of the selection time interval",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'output', title="Output data", formats=(
                FormatText('text/csv'),
                FormatJSON('application/json'),
            )
        )),
    ]

    def execute(self, collection_id, begin_time, end_time, output, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        base_collection_id, _, dataset_id = collection_id.partition(':')

        try:
            collection = (
                ProductCollection.objects
                .select_related('type')
                .filter(type__identifier__in=ALLOWED_PRODUCT_TYPES)
                .get(identifier=base_collection_id)
            )
        except ProductCollection.DoesNotExist:
            raise InvalidInputValueError(
                "collection_id",
                "Invalid collection identifier %r!" % collection_id
            )

        if dataset_id and dataset_id != collection.type.get_base_dataset_id(dataset_id):
            raise InvalidInputValueError(
                "collection_id",
                "Invalid collection identifier %r!" % collection_id
            )

        base_datasets = set(collection.type.definition['datasets'])

        access_logger.info(
            "request: collection: %s, toi: (%s, %s)",
            collection_id,
            naive_to_utc(begin_time).isoformat("T") if begin_time else "-",
            naive_to_utc(end_time).isoformat("T") if end_time else "-",
        )

        query = collection.products.order_by('begin_time')
        if end_time:
            query = query.filter(begin_time__lte=naive_to_utc(end_time))
        if begin_time:
            query = query.filter(
                end_time__gte=naive_to_utc(begin_time),
                begin_time__gte=(begin_time - collection.max_product_duration),
            )

        result = self._collect_observatories(query, dataset_id, base_datasets)

        if output['mime_type'] == "text/csv":
            return self._csv_output(result, output)
        if output['mime_type'] == "application/json":
            return self._json_output(result, output)

        raise InvalidOutputDefError(
            'output',
            "Unexpected output format %r requested!" % output['mime_type']
        )

    @classmethod
    def _collect_observatories(cls, query, dataset_id, base_datasets):

        re_filter = re.compile("^%s([^:]+)$" % (
            "%s:" % dataset_id if dataset_id else ""
        ))

        result = {}
        for datasets in query.values_list("datasets", flat=True):
            for key, record in datasets.items():
                if key in base_datasets:
                    continue
                match = re_filter.match(key)
                if not match:
                    continue
                code = match.groups()[0]
                begin_time, end_time = record['beginTime'], record['endTime']
                begin_time_min, end_time_max = (
                    result.get(code) or (begin_time, end_time)
                )
                result[code] = (
                    min(begin_time_min, begin_time),
                    max(end_time_max, end_time),
                )
        return result

    @classmethod
    def _csv_output(cls, data, output):
        output_fobj = StringIO(newline="\r\n")
        print("site,startTime,endTime", file=output_fobj)
        for code in sorted(data):
            begin_time, end_time = data[code]
            print("%s,%s,%s" % (code, begin_time, end_time), file=output_fobj)
        return CDFileWrapper(output_fobj, **output)

    @classmethod
    def _json_output(cls, data, output):

        def _get_obs_info(code):
            begin_time, end_time = data[code]
            return {
                'name': code,
                'timeExtent': {
                    'start': begin_time,
                    'end': end_time,
                },
            }

        return CDObject([
            _get_obs_info(code) for code in sorted(data)
        ], format=FormatJSON(), **output)
