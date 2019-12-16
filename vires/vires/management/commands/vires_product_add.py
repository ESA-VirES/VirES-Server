#-------------------------------------------------------------------------------
#
# Products management - fast registration
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring, too-many-locals, too-many-branches
# pylint: disable=too-many-arguments, broad-except

import sys
from os.path import basename
from django.core.management.base import CommandError, BaseCommand
from eoxserver.core import env
from eoxserver.backends.models import Storage, Package, DataItem
from eoxserver.backends.component import BackendComponent
from eoxserver.resources.coverages.models import RangeType
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.models import Product, ProductCollection
from vires.management.commands import cache_session
from vires.management.commands.vires_dataset_register import (
    VirESMetadataReader
)
from vires.management.commands.vires_update_orbit_directions import (
    RE_MAG_LR_PRODUCT, update_orbit_direction_tables,
    sync_orbit_direction_tables,
)
from vires.orbit_direction_update import DataIntegrityError
from vires.cdf_util import cdf_open


class Command(CommandOutputMixIn, BaseCommand):

    help = (
        "Register one or more products to a collection. "
        "This is a high-level convenience command with a minimal set of "
        "parameters which registers multiple products, links them to "
        "a collection, resolves already registered and duplicated "
        "products (different versions of the same product registered "
        "simultaneously)."
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "-f", "--file", dest="input_file", default=None,
            help=(
                "Optional file from which the inputs are read rather "
                "than form the command line arguments. Use dash to read "
                "filenames from standard input."
            )
        )
        parser.add_argument(
            "-r", "--range-type", dest="range_type_name", default=None,
            help=(
                "Optional name of the model range type. "
                "If not provided the range of the collection is used."
            )
        )
        parser.add_argument(
            "-c", "--collection", dest="collection_id", required=True,
            help=(
                "Mandatory name of the collection the product(s) should be "
                "linked to."
            )
        )
        parser.add_argument(
            "--conflict", dest="conflict", choices=("IGNORE", "REPLACE"),
            default="IGNORE", help=(
                "Define how to resolve conflict when the product is already "
                "registered. By default the registration is skipped and the "
                "the passed product is IGNORED. An alternative is to REPLACE "
                "the old product, i.e., to de-register the old one and "
                "register the new one). In case of the REPLACE the collection "
                "links are NOT preserved."
            )
        )
        parser.add_argument(
            "--overlap", dest="overlap", choices=("IGNORE", "REPLACE"),
            default="REPLACE", help=(
                "Define how to resolve registered overlapping products."
                "By default, the REPLACE option causes the overlapping "
                "products to be de-registered to prevent duplicated data."
                "Alternatively, the duplicated data can be IGNORED. "
            )
        )

    @cache_session
    def handle(self, *args, **kwargs):

        identifiers = kwargs["identifier"]
        ignore_registered = kwargs["conflict"] == "IGNORE"
        ignore_overlaps = kwargs["overlap"] == "IGNORE"

        range_type = get_range_type(kwargs["range_type_name"])
        collection_id = kwargs["collection_id"]
        collection = get_collection(collection_id)

        if collection is None:
            if range_type:
                self.print_wrn(
                    "The product collection '%s' does not exist! A new "
                    "collection will be created ..." % collection_id
                )
                collection = collection_create(collection_id, range_type)
            else:
                raise CommandError(
                    "The product collection '%s' does not exist! "
                    "A range type must be specified to create a new one."
                    % collection_id
                )

        counter = Counter()

        id_suffix = get_product_id_suffix(collection)

        for data_file in read_products(kwargs["input_file"], identifiers):

            product_id = get_product_id(data_file) + id_suffix

            try:
                removed, inserted = self._register_product(
                    collection, product_id, data_file, ignore_registered,
                    ignore_overlaps,
                )
            except Exception as error:
                self.print_traceback(error, kwargs)
                self.print_err(
                    "Registration of '%s' failed! Reason: %s"
                    % (product_id, error)
                )
                counter.increment_failed()
            else:
                counter.increment_removed(len(removed))
                if inserted:
                    counter.increment_inserted()
                else:
                    counter.increment_skipped()
            finally:
                counter.increment()

        counter.print_report(lambda msg: self.print_msg(msg, 1))


    @nested_commit_on_success
    def _register_product(self, collection, product_id, data_file,
                          ignore_registered, ignore_overlaps):
        removed, inserted = [], []
        metadata = read_metadata(data_file)

        is_in_collection = False

        products = find_time_overlaps(
            collection, metadata["begin_time"], metadata["end_time"]
        )
        for product in products:
            if product.identifier == product_id and ignore_registered:
                is_in_collection = True
            else:
                if ignore_overlaps and product.identifier != product_id:
                    self.print_msg("%s ignored" % product.identifier)
                else:
                    delete_product(product)
                    self.print_msg("%s de-registered" % product.identifier)
                    removed.append(product.identifier)

        if not is_in_collection:
            # The product may be registered but not inserted in the collection.
            product = find_product(product_id)

            if product and not ignore_registered:
                delete_product(product)
                self.print_msg("%s de-registered" % product.identifier)
                removed.append(product.identifier)
                product = None

            if not product:
                product = register_product(
                    collection.range_type, product_id, data_file, metadata
                )

                # update orbit direction tables
                if RE_MAG_LR_PRODUCT.match(product_id):
                    try:
                        update_orbit_direction_tables(collection, product)
                    except DataIntegrityError:
                        self.print_wrn(
                            "Synchronizing orbit direction lookup tables ..."
                        )
                        sync_orbit_direction_tables(collection)

                collection.insert(product)
                self.print_msg(
                    "%s registered and inserted in %s"
                    % (product.identifier, collection.identifier)
                )
                inserted.append(product_id)
            else:
                collection.insert(product)
                self.print_msg(
                    "%s inserted in %s"
                    % (product.identifier, collection.identifier)
                )

        return removed, inserted


class Counter(object):

    def __init__(self):
        self._total = 0
        self._inserted = 0
        self._removed = 0
        self._skipped = 0
        self._failed = 0

    def increment(self, count=1):
        self._total += count

    def increment_inserted(self, count=1):
        self._inserted += count

    def increment_removed(self, count=1):
        self._removed += count

    def increment_skipped(self, count=1):
        self._skipped += count

    def increment_failed(self, count=1):
        self._failed += count

    def print_report(self, print_fcn):
        if self._inserted > 0:
            print_fcn(
                "%d of %d product(s) registered."
                % (self._inserted, self._total)
            )

        if self._skipped > 0:
            print_fcn(
                "%d of %d product(s) skipped."
                % (self._skipped, self._total)
            )

        if self._removed > 0:
            print_fcn("%d product(s) de-registered." % self._removed)


        if self._failed > 0:
            print_fcn(
                "Failed to register %d of %d product(s)."
                % (self._failed, self._total)
            )

        if self._total == 0:
            print_fcn("No action performed.")


def read_metadata(data_file):
    """ Read metadata from product. """
    with cdf_open(data_file) as dataset:
        metadata = VirESMetadataReader.read(dataset)
    return metadata


def read_products(filename, args):
    """ Get products iterator. """

    def _read_lines(lines):
        for line in lines:
            line = line.partition("#")[0] # strip comments
            line = line.strip() # strip white-space padding
            if line: # empty lines ignored
                yield line

    if filename is None:
        products = iter(args)
    elif filename == "-":
        products = _read_lines(sys.stdin)
    else:
        with open(filename) as file_:
            products = _read_lines(file_)

    return products


def get_collection(collection_id):
    """ Get collection for the given collection identifier.
    Return None if no collection matched.
    """
    try:
        return ProductCollection.objects.get(
            identifier=collection_id
        )
    except ProductCollection.DoesNotExist:
        return None


def get_range_type(range_type_name):
    """ Get range type for the given collection name.
    When no range-type is given returns None.
    """
    if range_type_name:
        try:
            range_type = RangeType.objects.get(name=range_type_name)
        except RangeType.DoesNotExist:
            raise CommandError(
                "Invalid range type name '%s'!" % range_type_name
            )
    else:
        range_type = None
    return range_type


def get_product_id(data_file):
    """ Get the product identifier derived from the data filename. """
    return basename(data_file).partition(".")[0]


def get_product_id_suffix(collection):
    """ Get product identifier suffix derived from the product type
    (range-type name)
    """
    return "".join(collection.range_type.name.partition(":")[1:])


def collection_create(identifier, range_type):
    """ Create a new product collection. """
    collection = ProductCollection()
    collection.identifier = identifier
    collection.range_type = range_type
    collection.srid = 4326
    collection.min_x = -180
    collection.min_y = -90
    collection.max_x = 180
    collection.max_y = 90
    collection.size_x = 0
    collection.size_y = 1
    collection.full_clean()
    collection.save()
    return collection


def find_product(product_id):
    """ Return True if the product is already registered. """
    try:
        item = Product.objects.get(identifier=product_id)
    except Product.DoesNotExist:
        return None
    return item.cast() if item.iscoverage else None


def find_time_overlaps(collection, begin_time, end_time):
    """ Lookup products with the same temporal overlap."""
    return (
        item.cast() for item in collection.eo_objects.filter(
            begin_time__lte=end_time, end_time__gte=begin_time
        ) if item.iscoverage
    )


def register_product(range_type, product_id, data_file, metadata):
    """ Register product. """
    semantic = ["bands[1:%d]" % len(range_type)]
    data_format = metadata.pop("format", None)

    product = Product()
    product.identifier = product_id
    product.visible = False
    product.range_type = range_type
    product.srid = 4326
    product.extent = (-180, -90, 180, 90)
    for key, value in metadata.iteritems():
        setattr(product, key, value)

    product.full_clean()
    product.save()

    storage, package, format_, location = _get_location_chain([data_file])
    format_ = data_format
    data_item = DataItem(
        location=location, format=format_ or "", semantic=semantic,
        storage=storage, package=package,
    )
    data_item.dataset = product
    data_item.full_clean()
    data_item.save()

    return product


def delete_product(product):
    """ Delete product object. """
    product.delete()


def _get_location_chain(items):
    component = BackendComponent(env)
    storage = None
    package = None

    storage_type, url = _split_location(items[0])
    if storage_type:
        storage_component = component.get_storage_component(storage_type)
    else:
        storage_component = None

    if storage_component:
        storage, _ = Storage.objects.get_or_create(
            url=url, storage_type=storage_type
        )

    # packages
    for item in items[1 if storage else 0:-1]:
        type_or_format, location = _split_location(item)
        package_component = component.get_package_component(type_or_format)
        if package_component:
            package, _ = Package.objects.get_or_create(
                location=location, format=format,
                storage=storage, package=package
            )
            storage = None  # override here
        else:
            raise Exception(
                "Could not find package component for format '%s'"
                % type_or_format
            )

    format_, location = _split_location(items[-1])
    return storage, package, format_, location


def _split_location(item):
    """ Splits string as follows: <format>:<location> where format can be
        None.
    """
    idx = item.find(":")
    return (None, item) if idx == -1 else (item[:idx], item[idx + 1:])
