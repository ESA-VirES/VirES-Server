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
# pylint: disable=too-many-locals

from itertools import chain
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from ..time_series.product_source import MultiCollectionProductSource
from ..time_series import ProductTimeSeries, CustomDatasetTimeSeries


def parse_collections(input_id, source, permissions,
                      custom_dataset=None, user=None):
    """ Parse input collections definitions. """
    result = {}

    if not isinstance(source, dict):
        raise InvalidInputValueError(
            input_id, "JSON object expected!"
        )

    for label, collection_dataset_ids in source.items():
        try:
            result[label] = _parse_datasets(
                collection_dataset_ids, custom_dataset, permissions
            )
        except (ValueError, TypeError) as error:
            raise InvalidInputValueError(f"label {label}: {error}") from None

    master_type = None
    for label, datasets in result.items():

        if datasets == custom_dataset:
            continue

        # master (first collection) must be always defined
        if len(datasets) < 1:
            raise InvalidInputValueError(
                input_id,
                f"Collection list must have at least one item! (label: {label})"
            )

        # master (first collection) must be always of the same product type
        collections, dataset_id = datasets[0]
        if master_type is None:
            master_type = (collections[0].type.identifier, dataset_id)
        else:
            if master_type != (collections[0].type.identifier, dataset_id):
                raise InvalidInputValueError(
                    input_id,
                    "Master collection product type mismatch! "
                    f"(label: {label})"
                )

        # slaves are optional
        # slaves' order does not matter

        # collect slave product-types
        slave_types = set()

        # for one label multiple datasets of the same product type are not allowed
        for collections, dataset_id in datasets[1:]:
            slave_type = (collections[0].type.identifier, dataset_id)
            if slave_type == master_type or slave_type in slave_types:
                raise InvalidInputValueError(
                    input_id,
                    "Multiple collections of the same type are not allowed! "
                    f"(label: {label})"
                )
            slave_types.add(slave_type)

    # convert collections to product time-series
    return {
        label: (
            [
                CustomDatasetTimeSeries(user)
            ] if datasets == custom_dataset else [
                ProductTimeSeries(MultiCollectionProductSource(*args))
                for args in datasets
            ]
        ) for label, datasets in result.items()
    }


def _parse_datasets(ids, custom_dataset, permissions,
                    dataset_separator=":", collection_separator="+"):

    if not isinstance(ids, (list, tuple)):
        raise TypeError(f"Invalid list of collection identifiers! {ids!r}")

    collection_dataset_ids = []
    for id_ in ids:
        if not isinstance(id_, str):
            raise TypeError(f"Invalid collection identifier '{id_}'!")
        collection_ids, separator, dataset_id = id_.partition(dataset_separator)
        if not separator:
            dataset_id = None
        collection_ids = collection_ids.split(collection_separator)
        collection_dataset_ids.append((collection_ids, dataset_id))

    available_collections = {
        collection.identifier: collection for collection in (
            ProductCollection
                .select_permitted(permissions)
                .select_related("type", "spacecraft")
                .filter(identifier__in=set(chain.from_iterable(
                    ids for ids, _ in collection_dataset_ids
                )))
        )
    }

    datasets = []

    for collection_ids, dataset_id in collection_dataset_ids:

        if len(collection_ids) == 1 and collection_ids[0] == custom_dataset:
            if dataset_id:
                raise ValueError(
                    "Custom dataset does not allow dataset identifier "
                    "specification!"
                )
            return custom_dataset

        try:
            collections = [
                available_collections[collection_id]
                for collection_id in collection_ids
            ]
        except KeyError as collection_id:
            raise ValueError(
                f"Invalid collection identifier '{collection_id}'!"
            ) from None

        collection0 = collections[0]

        for collection in collections[1:]:
            if collection.type != collection0.type:
                raise ValueError(
                    "Collection type mismatch! "
                    f"{collection0.identifier}({collection0.type.identifier} "
                    f"vs. {collection.identifier}({collection.type.identifier}"
                ) from None

        dataset_id = collection0.type.get_dataset_id(dataset_id)
        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not collection0.type.is_valid_dataset_id(dataset_id):
            raise ValueError(f"Invalid dataset identifier '{dataset_id}'!")

        datasets.append((collections, dataset_id))

    return datasets
