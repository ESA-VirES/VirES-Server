#-------------------------------------------------------------------------------
#
# WPS process fetching information about the provided product collections.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
# pylint: disable=unused-argument

import re
from io import StringIO
from django.db.models import Count, Min, Max
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, FormatText, FormatJSON, CDFileWrapper, CDObject,
    RequestParameter,
)
from eoxserver.services.ows.wps.exceptions import InvalidOutputDefError
from vires.models import ProductCollection
from vires.util import unique
from vires.time_util import format_datetime
from vires.access_util import get_vires_permissions
from vires.processes.base import WPSProcess


RE_CSL_DEMIMITER = re.compile(r"\s*,\s*")


class GetCollectionInfo(WPSProcess):
    """ Process information about the available products collections.
    """
    identifier = "vires:get_collection_info"
    title = "Get get information about the available product collections."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("permissions", RequestParameter(get_vires_permissions)),
        ("collection_ids", LiteralData(
            "collection", str, optional=True, default=None,
            title="Optional comma separated list of collection identifiers."
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

    def execute(self, permissions, collection_ids, output, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)

        collection_ids = self._parse_collection_ids(collection_ids)
        collections = self._get_collections(collection_ids, permissions)

        access_logger.info(
            "request: collection_ids: %s, ",
            "<all>" if collection_ids is None else
            "(%s)" % ", ".join(collection_ids)
        )

        if output['mime_type'] == "text/csv":
            return self._csv_output(collections, output)
        if output['mime_type'] == "application/json":
            return self._json_output(collections, output)

        raise InvalidOutputDefError(
            'output',
            "Unexpected output format %r requested!" % output['mime_type']
        )

    @staticmethod
    def _parse_collection_ids(collection_ids):
        if collection_ids is None:
            return None
        collection_ids = collection_ids.strip()
        if not collection_ids:
            return []
        return list(unique(RE_CSL_DEMIMITER.split(collection_ids)))

    @staticmethod
    def _get_collections(collection_ids, permisisons):

        collections = ProductCollection.select_permitted(permisisons).values(
            'identifier', 'type__identifier', 'metadata'
        ).annotate(
            product_count=Count('products'),
            begin_time=Min('products__begin_time'),
            end_time=Max('products__end_time'),
        ).order_by('identifier')

        if collection_ids is not None:
            collections = collections.filter(identifier__in=collection_ids)

        return collections

    @classmethod
    def _csv_output(cls, collections, output):
        output_fobj = StringIO(newline="\r\n")
        print(
            "collectionId,productType,productCount,startTime,endTime",
            file=output_fobj
        )
        for collection in collections:
            print("%s,%s,%d,%s,%s" % (
                collection['identifier'],
                collection['type__identifier'],
                collection['product_count'],
                format_datetime(collection['begin_time']) or "",
                format_datetime(collection['end_time']) or "",
            ), file=output_fobj)
        return CDFileWrapper(output_fobj, **output)

    @classmethod
    def _json_output(cls, collections, output):

        def _get_collection_info(collection):
            time_extent = {} if collection['product_count'] == 0 else {
                'timeExtent': {
                    'start': format_datetime(collection['begin_time']),
                    'end': format_datetime(collection['end_time']),
                },
            }
            return {
                'name': collection['identifier'],
                'productType': collection['type__identifier'],
                'productCount': collection['product_count'],
                **time_extent,
            }

        return CDObject([
            _get_collection_info(collection) for collection in collections
        ], format=FormatJSON(), **output)
