#-------------------------------------------------------------------------------
#
# Process Utilities - collections input parser
#
# Authors: Martin Paces <martin.paces@eox.at>
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
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from ..time_series import ProductTimeSeries, CustomDatasetTimeSeries


def parse_collections(input_id, source, permissions,
                      custom_dataset=None, user=None):
    """ Parse input collections definitions. """
    result = {}

    if not isinstance(source, dict):
        raise InvalidInputValueError(
            input_id, "JSON object expected!"
        )

    for label, collection_ids in source.items():
        try:
            result[label] = _parse_collection_ids(
                collection_ids, custom_dataset, permissions
            )
        except (ValueError, TypeError) as error:
            raise InvalidInputValueError("label %r: %s" % (label, str(error)))

    master_ptype = None
    for label, collections in result.items():
        if collections == custom_dataset:
            continue

        # master (first collection) must be always defined
        if len(collections) < 1:
            raise InvalidInputValueError(
                input_id, "Collection list must have at least one item!"
                " (label: %r)" % label
            )
        # master (first collection) must be always of the same product type
        collection, dataset_id = collections[0]
        if master_ptype is None:
            master_dataset = (collection.type.identifier, dataset_id)
        else:
            if master_dataset != (collection.type.identifier, dataset_id):
                raise InvalidInputValueError(
                    input_id, "Master collection product type mismatch!"
                    " (label: %r; )" % label
                )

        # slaves are optional
        # slaves' order does not matter

        # collect slave product-types
        slave_datasets = set()

        # for one label multiple collections of the same range-type not allowed
        for collection, dataset_id in collections[1:]:
            dataset = (collection.type.identifier, dataset_id)
            if dataset == master_dataset or dataset in slave_datasets:
                raise InvalidInputValueError(
                    input_id, "Multiple collections of the same type "
                    "are not allowed! (label: %r; )" % label
                )
            slave_datasets.add(dataset)

    # convert collections to product time-series
    return {
        label: (
            [
                CustomDatasetTimeSeries(user)
            ] if collections == custom_dataset else [
                ProductTimeSeries(collection, dataset_id)
                for collection, dataset_id in collections
            ]
        ) for label, collections in result.items()
    }


def _parse_collection_ids(ids, custom_dataset, permissions):

    if not isinstance(ids, (list, tuple)):
        raise TypeError("Invalid list of collection identifiers! %r" % ids)

    collection_dataset_ids = []
    for id_ in ids:
        if not isinstance(id_, str):
            raise TypeError("Invalid collection identifier %r!" % id_)
        collection_id, separator, dataset_id = id_.partition(':')
        if not separator:
            dataset_id = None
        collection_dataset_ids.append((collection_id, dataset_id))

    available_collections = {
        collection.identifier: collection for collection
        in ProductCollection.select_permitted(permissions).filter(
            identifier__in=set(cid for cid, _ in collection_dataset_ids)
        )
    }

    collections = []
    for collection_id, dataset_id in collection_dataset_ids:

        if collection_id == custom_dataset:
            if dataset_id:
                raise ValueError(
                    "Custom dataset does not allow dataset identifier "
                    "specification!"
                )
            return custom_dataset

        collection = available_collections.get(collection_id)
        if not collection:
            raise ValueError("Invalid collection identifier %r!" % collection_id)

        dataset_id = collection.type.get_dataset_id(dataset_id)
        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not collection.type.is_valid_dataset_id(dataset_id):
            raise ValueError("Invalid dataset identifier %r!" % dataset_id)

        collections.append((collection, dataset_id))

    return collections
