#-------------------------------------------------------------------------------
#
# Product source classes.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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
# pylint: disable=too-few-public-methods,too-many-instance-attributes

from collections import namedtuple
from itertools import chain
from datetime import timedelta
from vires.util import cached_property, unique
from vires.models import Product, ProductCollection


TD_ZERO = timedelta(minutes=0)


class Record(namedtuple("Record", ["index", "start", "end", "data"])):
    """ Product record class. """

    def set_start(self, new_start):
        """ Get new record object with replaced start time. """
        return self.__class__(self.index, new_start, self.end, self.data)

    def set_end(self, new_end):
        """ Get new record object with replaced end time. """
        return self.__class__(self.index, self.start, new_end, self.data)


class SwarmDefaultParameters:
    """ Default SWARM product parameters. """
    TIME_VARIABLE = "Timestamp"
    TIME_TOLERANCE = timedelta(microseconds=0) # time selection buffer
    TIME_OVERLAP = timedelta(seconds=60) # time interpolation buffer
    TIME_GAP_THRESHOLD = timedelta(seconds=30) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=0.5)
    VARIABLE_INTERPOLATION_KINDS = {}


class MagLRParameters(SwarmDefaultParameters):
    """ MAGx_LR_1B parameters """
    VARIABLE_INTERPOLATION_KINDS = {
        "B_NEC": "linear",
        "F": "linear",
    }


class AuxImf2Parameters(SwarmDefaultParameters):
    """ AUX_IMF_2_ parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=61) # time selection buffer
    TIME_OVERLAP = timedelta(hours=2) # time interpolation buffer
    TIME_GAP_THRESHOLD = timedelta(minutes=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=60)
    VARIABLE_INTERPOLATION_KINDS = {
        "F10_INDEX": "zero",
        "IMF_BY_GSM": "zero",
        "IMF_BZ_GSM": "zero",
        "IMF_V": "zero",
    }


class GfzKpParameters(SwarmDefaultParameters):
    """ GFZ_KP parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=181) # time selection buffer
    TIME_OVERLAP = timedelta(hours=6) # time interpolation buffer
    TIME_GAP_THRESHOLD = timedelta(minutes=181) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=180)
    VARIABLE_INTERPOLATION_KINDS = {
        "Kp": "zero",
        "ap": "zero",
    }


class WdcDstParameters(SwarmDefaultParameters):
    """ WDC_DST parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(minutes=61) # time selection buffer
    TIME_OVERLAP = timedelta(hours=2) # time interpolation buffer
    TIME_GAP_THRESHOLD = timedelta(minutes=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(minutes=60)
    VARIABLE_INTERPOLATION_KINDS = {
        "Dst": "linear",
        "dDst": "zero",
    }


class OmniHr1MinParameters(SwarmDefaultParameters):
    """ OMNI HR 1min parameters """
    INTERPOLATION_KIND = "zero"
    TIME_TOLERANCE = timedelta(0) # time selection buffer
    TIME_OVERLAP = timedelta(minutes=120) # time interpolation buffer
    TIME_GAP_THRESHOLD = timedelta(seconds=61) # gap time threshold
    TIME_SEGMENT_NEIGHBOURHOOD = timedelta(seconds=60)
    VARIABLE_INTERPOLATION_KINDS = {
        "IMF_BY_GSM": "linear",
        "IMF_BZ_GSM": "linear",
        "IMF_V": "linear",
        "IMF_Vx": "linear",
        "IMF_Vy": "linear",
        "IMF_Vz": "linear",
    }


DEFAULT_PRODUCT_TYPE_PARAMETERS = SwarmDefaultParameters #pylint: disable=invalid-name
PRODUCT_TYPE_PARAMETERS = {
    "SW_MAGx_LR_1B": MagLRParameters,
    "SW_AUX_IMF_2_": AuxImf2Parameters,
    "OMNI_HR_1min": OmniHr1MinParameters,
    "GFZ_KP": GfzKpParameters,
    "WDC_DST": WdcDstParameters,
}


def product_source_factory(collections, dataset_id=None):
    """ Product source factory function. """
    if len(collections) == 1:
        return SingleCollectionProductSource(collections[0], dataset_id)
    return MultiCollectionProductSource(collections, dataset_id)


class ProductSource:
    """ Base product source. """
    # cutting start of the product
    time_precision = timedelta(microseconds=1000) # 1ms precision

    @staticmethod
    def _get_id(base_id, dataset_id, default_dataset_id):
        if dataset_id == default_dataset_id:
            return base_id
        return f"{base_id}:{dataset_id}"

    @staticmethod
    def _get_collection(collection_name):
        try:
            return ProductCollection.objects.get(identifier=collection_name)
        except ProductCollection.DoesNotExist:
            raise RuntimeError(
                f"Non-existent product collection {collection_name}!"
            ) from None

    @staticmethod
    def _get_variable_mapping(dataset_definition):
        return {
            variable: source
            for variable, source in (
                (variable, type_info.get("source"))
                for variable, type_info in dataset_definition.items()
            ) if source
        }

    @staticmethod
    def _time_subset_qs(collection, start, stop, time_tolerance=TD_ZERO):
        """ Django query set selecting product within the given time interval.
        """
        selection = {}

        if start is not None:
            _start = start - time_tolerance
            selection["end_time__gte"] = _start
            selection["begin_time__gte"] = _start - collection.max_product_duration

        if stop is not None:
            _stop = stop + time_tolerance
            selection["begin_time__lt"] = _stop

        return Product.objects.prefetch_related("collection__type").filter(
            collection=collection, **selection
        )

    @staticmethod
    def _product_qs(collection):
        """ Queryset selecting all products. """
        return Product.objects.filter(
            collection=collection,
        )

    @cached_property
    def metadata(self):
        """ Get collection metadata. """
        raise NotImplementedError

    @cached_property
    def dataset_definition(self):
        """ Get list of available variables """
        raise NotImplementedError

    def count_products(self, start, end, time_tolerance=TD_ZERO):
        """ Count products overlapping the given time interval.
        """
        raise NotImplementedError

    def iter_products(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield applicable products and their time subset to be
        extracted.
        """
        raise NotImplementedError

    def iter_ids(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield product ids and time intervals.
        """
        raise NotImplementedError

    def get_sample_product(self):
        """ Get one sample product from a collection or None if empty """
        raise NotImplementedError

    collections = None
    identifier = None
    collection_id = None
    datased_id = None
    type_id = None
    params = None
    translate_fw = None


class SingleCollectionProductSource(ProductSource):
    """ Single collection product source class. """

    @cached_property
    def metadata(self):
        """ Get collection metadata. """
        collection, = self.collections
        return {
            **collection.metadata,
            **collection.spacecraft_dict,
            "nominalSampling": collection.get_nominal_sampling(self.dataset_id),
            "grade": collection.grade,
        }

    @cached_property
    def dataset_definition(self):
        """ Get dictionary of available variables """
        return self.type.get_dataset_definition(self.dataset_id)

    def __init__(self, collection, dataset_id=None):

        if isinstance(collection, str):
            collection = self._get_collection(collection)

        dataset_id = collection.type.get_dataset_id(dataset_id)
        default_dataset_id = collection.type.default_dataset_id

        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not collection.type.is_valid_dataset_id(dataset_id):
            raise ValueError(f"Invalid dataset identifier {dataset_id!r}!")

        self.collections = (collection,)
        self.type = collection.type

        self.identifier = self._get_id(
            collection.identifier, dataset_id, default_dataset_id
        )
        self.collection_id = collection.identifier
        self.dataset_id = dataset_id
        self.type_id = collection.type.identifier

        self.params = PRODUCT_TYPE_PARAMETERS.get(
            self._get_id(
                collection.type.identifier,
                collection.type.get_base_dataset_id(dataset_id),
                default_dataset_id,
            ),
            DEFAULT_PRODUCT_TYPE_PARAMETERS,
        )

        # mapping from VirES to product variable names
        self.translate_fw = self._get_variable_mapping(self.dataset_definition)

    def count_products(self, start, end, time_tolerance=TD_ZERO):
        """ Count products overlapping the given time interval.
        """
        collection, = self.collections
        return self._time_subset_qs(collection, start, end, time_tolerance).count()


    def iter_products(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield applicable products and their time subset to be
        extracted.
        """
        collection, = self.collections
        time_precision = self.time_precision
        _Record = namedtuple("Record", ["start", "end", "data"])

        def _read_products(source):
            for product in source:
                yield _Record(
                    product.begin_time,
                    product.end_time + time_precision,
                    product
                )

        return self._select_products(
            _read_products(
                self._time_subset_qs(collection, start, end, time_tolerance)
                    .order_by("begin_time")
            )
        )

    def iter_ids(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield product ids and time intervals.
        """
        collection, = self.collections
        time_precision = self.time_precision
        _Record = namedtuple("Record", ["start", "end", "data"])

        def _read_products(source):
            for start, end, id_ in source:
                yield _Record(start, end + time_precision, id_)

        return self._select_products(
            _read_products(
                self._time_subset_qs(collection, start, end, time_tolerance)
                    .order_by("begin_time")
                    .values_list("begin_time", "end_time", "identifier")
            )
        )

    def get_sample_product(self):
        """ Get one sample product from a collection or None if empty """
        collection, = self.collections
        try:
            return self._product_qs(collection).order_by("begin_time")[0]
        except IndexError:
            return None

    @staticmethod
    def _select_products(sources):

        last_record = next(sources, None)
        if not last_record:
            return

        for record in sources:
            result = Record(0, *last_record)
            if last_record.end > record.start: # clip the last product
                result = result.set_end(record.start)
            yield result
            last_record = record

        yield Record(0, *last_record)


class MultiCollectionProductSource(ProductSource):
    """ Multi-collection product source class.

    Gaps in temporal coverage are filled from the next-in-line collections.
    """

    @cached_property
    def metadata(self):
        """ Get collection metadata. """
        # merge selected metadata

        grade = "+".join(unique(
            collection.grade or "" for collection in self.collections
        ))

        def _join(values):
            return "+".join(unique(value for value in values if value)) or None

        subtractable_collections = {
            key: _join(
                (collection.metadata.get("subtractableCollections") or {}).get(key)
                for collection in self.collections
            )
            for key in chain.from_iterable(
                collection.metadata.get("subtractableCollections") or {}
                for collection in self.collections
            )
        }

        collection = self.collections[0]
        return {
            **collection.metadata,
            **collection.spacecraft_dict,
            "nominalSampling": collection.get_nominal_sampling(self.dataset_id),
            "subtractableCollections": subtractable_collections,
            "grade": grade,
        }

    @cached_property
    def dataset_definition(self):
        """ Get dictionary of available variables """
        return self.type.get_dataset_definition(self.dataset_id)

    def __init__(self, collections, dataset_id=None):

        # check number of the passed collections
        if len(collections) < 2:
            raise ValueError("At least two distinct collections must be given!")

        if len(collections) > 256:
            raise ValueError("Maximum number of collections exceeded!")

        # convert collection ids to collection objects
        collections = [
            (
                self._get_collection(collection)
                if isinstance(collection, str) else collection
            ) for collection in collections
        ]

        #check that the collections are unique
        if len(set(collections)) < len(collections):
            raise ValueError("Combined collections are not unique!")

        #check that all collections are of the same type
        type_ = collections[0].type
        for collection in collections[1:]:
            if collection.type != type_:
                raise ValueError("Combined collections must be all of the same type!")

        dataset_id = type_.get_dataset_id(dataset_id)
        default_dataset_id = type_.default_dataset_id

        if dataset_id is None:
            raise ValueError("Missing mandatory dataset identifier!")

        if not type_.is_valid_dataset_id(dataset_id):
            raise ValueError(f"Invalid dataset identifier {dataset_id!r}!")

        self.collections = collections
        self.type = type_

        self.collection_id = "+".join(
            collection.identifier for collection in collections
        )
        self.dataset_id = dataset_id
        self.type_id = type_.identifier

        self.identifier = self._get_id(
            self.collection_id, dataset_id, default_dataset_id
        )

        self.params = PRODUCT_TYPE_PARAMETERS.get(
            self._get_id(
                type_.identifier,
                type_.get_base_dataset_id(dataset_id),
                default_dataset_id,
            ),
            DEFAULT_PRODUCT_TYPE_PARAMETERS,
        )

        # mapping from VirES to product variable names
        self.translate_fw = self._get_variable_mapping(self.dataset_definition)

    def count_products(self, start, end, time_tolerance=TD_ZERO):
        """ Count products overlapping the given time interval.
        """
        time_precision = self.time_precision
        _Record = namedtuple("Record", ["start", "end", "data"])

        def _read_products(source):
            for start, end, data in source:
                yield _Record(start, end + time_precision, data)

        return sum(1 for _ in self._select_products([
            _read_products(
                self._time_subset_qs(collection, start, end, time_tolerance)
                    .order_by("begin_time")
                    .values_list("begin_time", "end_time", "id")
            )
            for collection in self.collections
        ]))

    def iter_products(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield applicable products and their time subset to be
        extracted.
        """
        time_precision = self.time_precision
        _Record = namedtuple("Record", ["start", "end", "data"])

        def _read_products(source):
            for product in source:
                yield _Record(
                    product.begin_time,
                    product.end_time + time_precision,
                    product
                )

        return self._select_products([
            _read_products(
                self._time_subset_qs(
                    collection, start, end, time_tolerance
                ).order_by("begin_time")
            )
            for collection in self.collections
        ])

    def iter_ids(self, start, end, time_tolerance=TD_ZERO):
        """ Iterate over products overlapping the given time interval.
        Resolve temporal overlays of the products to prevent duplicate time
        coverage and yield product ids and time intervals.
        """
        time_precision = self.time_precision
        _Record = namedtuple("Record", ["start", "end", "data"])

        def _read_products(source):
            for start, end, id_ in source:
                yield _Record(start, end + time_precision, id_)

        return self._select_products([
            _read_products(
                self._time_subset_qs(collection, start, end, time_tolerance)
                    .order_by("begin_time")
                    .values_list("begin_time", "end_time", "identifier")
            )
            for collection in self.collections
        ])

    def get_sample_product(self):
        """ Get one sample product from a collection or None if empty """
        for collection in self.collections:
            try:
                return self._product_qs(collection).order_by("begin_time")[0]
            except IndexError:
                pass
        return None

    @staticmethod
    def _select_products(product_sources):

        class _ProductIterator:
            """ Iterator holding head product. """

            def __bool__(self):
                return self.head is not None

            def __init__(self, sequence):
                self.head = None
                self.iterator = iter(sequence)
                self.pull_next()

            def pull_next(self):
                """ Pull next product from the iterator and set it as head. """
                self.head = next(self.iterator, None)

        class _ProductSelector:
            """ Helper class holding the product iterators, selecting and
            clipping the applicable products.
            """

            def __bool__(self):
                return self.head is not None

            def __init__(self, sequences):
                self.head = None
                self.product_iterators = [
                    (index, _ProductIterator(sequence))
                    for index, sequence in enumerate(sequences)
                ]
                self.remove_empty()
                self.pull_next()

            def pull_next(self):
                """ Pull next product from the iterators and set it as head. """
                head_iterator, head = None, None

                for index, product_iterator in self.product_iterators:
                    if not head or product_iterator.head.start < head.start:
                        head_iterator = product_iterator
                        head = Record(index, *product_iterator.head)

                if not head:
                    self.head = None
                    return

                self.head = head
                head_iterator.pull_next()
                self.remove_empty()

            def remove_empty(self):
                """ Remove empty iterators. """
                self.product_iterators = [
                    (index, iterator)
                    for index, iterator in self.product_iterators if iterator
                ]

            def __iter__(self):
                if not self:
                    return
                last_record = self.head
                self.pull_next()
                while self:
                    record = self.head
                    if last_record.end <= record.start: # no time overlap
                        yield last_record
                        last_record = record
                    elif record.index <= last_record.index: # clip the last product
                        yield last_record.set_end(record.start)
                        last_record = record
                    elif last_record.end < record.end: # clip the new product
                        yield last_record
                        last_record = record.set_start(last_record.end)
                    self.pull_next()
                yield last_record

        return _ProductSelector(product_sources)
