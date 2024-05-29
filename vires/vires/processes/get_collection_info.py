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
RE_ID = re.compile("[a-zA-Z0-9_-]{0,128}")


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
        ("type_ids", LiteralData(
            "type", str, optional=True, default=None,
            title="Optional comma separated list of product type identifiers."
        )),
        ("mission_ids", LiteralData(
            "mission", str, optional=True, default=None,
            title="Optional comma separated list of mission identifiers."
        )),
        ("spacecraft_ids", LiteralData(
            "spacecraft", str, optional=True, default=None,
            title="Optional comma separated list of spacecraft identifiers."
        )),
        ("grade_id", LiteralData(
            "grade", str, optional=True, default=None,
            title="Optional grade identifier."
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

    def execute(self, permissions, collection_ids, type_ids,
                mission_ids, spacecraft_ids, grade_id,
                output, **kwargs):
        """ Execute process """
        access_logger = self.get_access_logger(**kwargs)

        collection_ids = self._parse_ids(collection_ids)
        type_ids = self._parse_ids(type_ids)
        mission_ids = self._parse_ids(mission_ids)
        spacecraft_ids = self._parse_ids(spacecraft_ids)
        grade_id = self._parse_id(grade_id)

        collections = self._get_collections(permissions,
            collection_ids=collection_ids,
            type_ids=type_ids,
            mission_ids=mission_ids,
            spacecraft_ids=spacecraft_ids,
            grade_id=grade_id,
        )

        access_logger.info(
            "request: "
            "collection_ids: %s, "
            "type_ids: %s, "
            "mission_ids: %s, "
            "spacecraft_ids: %s, "
            "grade_id: %s",
            self._format_ids(collection_ids),
            self._format_ids(type_ids),
            self._format_ids(mission_ids),
            self._format_ids(spacecraft_ids),
            self._format_id(grade_id),
        )

        if output['mime_type'] == "text/csv":
            return self._csv_output(collections, output)
        if output['mime_type'] == "application/json":
            return self._json_output(collections, output)

        raise InvalidOutputDefError(
            'output', f"Unexpected output format {output['mime_type']} requested!"
        )

    @staticmethod
    def _format_ids(ids):
        return "<all>" if ids is None else "(%s)" % ", ".join(ids)

    @staticmethod
    def _format_id(id_):
        return "<any>" if id_ is None else ("<none>" if not id_ else id_)

    @staticmethod
    def _format_nominal_sampling(data):
        if not data:
            return ""
        if isinstance(data, dict):
            return " ".join(f"{dataset}:{value}" for dataset, value in data.items())
        return str(data)

    @staticmethod
    def _parse_ids(ids):
        if ids is None:
            return None
        ids = ids.strip()
        if not ids:
            return []
        return list(unique(
            id_ for id_ in RE_CSL_DEMIMITER.split(ids) if RE_ID.match(id_)
        ))

    @staticmethod
    def _parse_id(id_):
        if id_ is not None:
            id_ = id_.strip()
            if RE_ID.match(id_):
                return id_
        return None

    @staticmethod
    def _get_collections(permissions, collection_ids, type_ids, mission_ids,
                         spacecraft_ids, grade_id):

        collections = ProductCollection.select_permitted(permissions).values(
            'identifier', 'type__identifier', 'metadata',
            'spacecraft__mission', 'spacecraft__spacecraft', 'grade',
        ).annotate(
            product_count=Count('products'),
            begin_time=Min('products__begin_time'),
            end_time=Max('products__end_time'),
            last_update=Max('products__updated'),
        ).order_by('identifier')

        if collection_ids is not None:
            collections = collections.filter(identifier__in=collection_ids)

        if type_ids is not None:
            collections = collections.filter(type__identifier__in=type_ids)

        if mission_ids is not None:
            collections = collections.filter(spacecraft__mission__in=mission_ids)

        if spacecraft_ids is not None:
            collections = collections.filter(spacecraft__spacecraft__in=spacecraft_ids)

        if grade_id is not None:
            collections = collections.filter(grade=(grade_id or None))

        return collections

    @classmethod
    def _csv_output(cls, collections, output):
        output_fobj = StringIO(newline="\r\n")
        print(
            "collectionId,productType,productCount,startTime,endTime,"
            "lastUpdate,nominalSampling",
            file=output_fobj
        )
        for collection in collections:
            print("%s,%s,%d,%s,%s,%s,%s" % (
                collection['identifier'],
                collection['type__identifier'],
                collection['product_count'],
                format_datetime(collection['begin_time']) or "",
                format_datetime(collection['end_time']) or "",
                format_datetime(collection['last_update']) or "",
                cls._format_nominal_sampling(collection['metadata'].get('nominalSampling')),
            ), file=output_fobj)
        return CDFileWrapper(output_fobj, **output)

    @classmethod
    def _json_output(cls, collections, output):

        extra_keys = [
            'spacecraft__mission', 'spacecraft__spacecraft', 'grade',
        ]
        key_mapping = {
            'spacecraft__mission': 'mission',
            'spacecraft__spacecraft': 'spacecraft',

        }

        def _get_collection_info(collection):
            time_extent = {} if collection['product_count'] == 0 else {
                'timeExtent': {
                    'start': format_datetime(collection['begin_time']),
                    'end': format_datetime(collection['end_time']),
                },
            }

            extra_metadata = {}
            for key in extra_keys:
                if collection[key]:
                    extra_metadata[key_mapping.get(key, key)] = collection[key]

            nominal_sampling = collection['metadata'].get('nominalSampling')
            if nominal_sampling:
                extra_metadata['nominalSampling'] = nominal_sampling

            if collection['product_count'] > 0:
                extra_metadata['lastUpdate'] = format_datetime(collection['last_update'])

            return {
                'name': collection['identifier'],
                **extra_metadata,
                'productType': collection['type__identifier'],
                'productCount': collection['product_count'],
                **time_extent,
            }

        return CDObject([
            _get_collection_info(collection) for collection in collections
        ], format=FormatJSON(), **output)
