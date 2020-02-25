#-------------------------------------------------------------------------------
#
# Product registration
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
# pylint: disable=missing-docstring, too-many-locals, too-many-branches
# pylint: disable=too-many-arguments, broad-except

import sys
from os.path import abspath, basename, splitext
from traceback import print_exc
from django.db import transaction
from django.core.management.base import CommandError
from vires.swarm import SwarmProductMetadataReader
from vires.models import Product, ProductCollection
from vires.orbit_direction_update import DataIntegrityError
from vires.cdf_util import cdf_open
from .._common import Subcommand
from .._orbit_direction.common import (
    update_orbit_direction_tables, sync_orbit_direction_tables,
)


class RegisterProductSubcommand(Subcommand):
    name = "register"
    help = (
        "Register one or more products to a collection. "
        "The already registered or duplicated (different versions "
        "of the same product registered simultaneously) products "
        "are detected resolved."
    )

    def add_arguments(self, parser):
        parser.add_argument("product-file", nargs="*")
        parser.add_argument(
            "-f", "--file", dest="input_file", default=None,
            help=(
                "Optional file from which the inputs are read rather "
                "than form the command line arguments. Use dash to read "
                "filenames from standard input."
            )
        )
        parser.add_argument(
            "-c", "--collection", "--product-collection",
            dest="collection_id", required=True, help=(
                "Mandatory name of the product collection the product(s) "
                "should be placed in."
            )
        )
        parser.add_argument(
            "--conflict", dest="conflict", choices=("IGNORE", "REPLACE"),
            default="IGNORE", help=(
                "Define how to resolve conflict when the product is already "
                "registered. By default the registration is skipped and the "
                "the new product is IGNORED. An alternative is to REPLACE "
                "the old product, i.e., to de-register the old one and "
                "register the new one). In case of the REPLACE the collection "
                "links are NOT preserved."
            )
        )
        parser.add_argument(
            "--overlap", dest="overlap", choices=("IGNORE", "REPLACE"),
            default="REPLACE", help=(
                "Define how to resolve registered overlapping products."
                "The default REPLACE option causes the overlapping "
                "products to be de-registered to prevent duplicated data."
                "Alternatively, the overlapping data can be IGNORED. "
            )
        )

    def handle(self, **kwargs):
        data_files = kwargs["product-file"]
        ignore_registered = kwargs["conflict"] == "IGNORE"
        ignore_overlaps = kwargs["overlap"] == "IGNORE"
        collection_id = kwargs["collection_id"]

        collection = get_collection(collection_id)

        if collection is None:
            raise CommandError(
                "The product collection '%s' does not exist!" % collection_id
            )

        counter = Counter()

        for data_file in read_products(kwargs["input_file"], data_files):
            product_id = get_product_id(data_file)

            try:
                removed, inserted, updated = self._register_product(
                    collection, product_id, data_file, ignore_registered,
                    ignore_overlaps,
                )
            except Exception as error:
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Registration of '%s' failed! Reason: %s",
                    product_id, error
                )
                counter.increment_failed()
            else:
                counter.increment_removed(len(removed))
                if updated:
                    counter.increment_updated()
                elif inserted:
                    counter.increment_inserted()
                else:
                    counter.increment_skipped()
            finally:
                counter.increment()

        counter.print_report(lambda msg: print(msg, file=sys.stderr))

    @transaction.atomic
    def _register_product(self, collection, product_id, data_file,
                          ignore_registered, ignore_overlaps):
        removed, inserted, updated = [], [], []
        metadata = read_metadata(data_file)

        products = find_time_overlaps(
            collection, metadata["begin_time"], metadata["end_time"]
        )
        old_product = None
        for product in products:
            if product.identifier == product_id:
                old_product = product
            else:
                if ignore_overlaps and product.identifier != product_id:
                    self.info("%s ignored", product.identifier)
                else:
                    delete_product(product)
                    self.info(
                        "%s in %s deregistered",
                        product.identifier, collection.identifier
                    )
                    removed.append(product.identifier)

        if not old_product:
            product = register_product(collection, product_id, data_file, metadata)
            self.info("%s in %s registered", product_id, collection.identifier)
            inserted.append(product_id)
        elif not ignore_registered:
            product = update_product(old_product, data_file, metadata)
            self.info("%s in %s updated", product_id, collection.identifier)
            updated.append(product_id)
        else:
            product = None
            self.info("%s in %s ignored", product_id, collection.identifier)

        if old_product and collection.metadata.get("calculateOrbitDirection"):
            try:
                update_orbit_direction_tables(product)
            except DataIntegrityError:
                self.warning(
                    "Synchronizing orbit direction lookup tables ..."
                )
                sync_orbit_direction_tables(collection)

        return removed, inserted, updated


class Counter():

    def __init__(self):
        self._total = 0
        self._inserted = 0
        self._updated = 0
        self._removed = 0
        self._skipped = 0
        self._failed = 0

    def increment(self, count=1):
        self._total += count

    def increment_inserted(self, count=1):
        self._inserted += count

    def increment_updated(self, count=1):
        self._updated += count

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

        if self._updated > 0:
            print_fcn(
                "%d of %d product(s) updated."
                % (self._updated, self._total)
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
    with cdf_open(data_file) as cdf:
        return SwarmProductMetadataReader.read(cdf)


def read_products(filename, args):
    """ Get products iterator. """

    def _read_lines(lines):
        for line in lines:
            line = line.partition("#")[0] # strip comments
            line = line.strip() # strip white-space padding
            if line: # empty lines ignored
                yield line

    if filename is None:
        return iter(args)

    if filename == "-":
        return _read_lines(sys.stdin)

    with open(filename) as file_:
        return _read_lines(file_)


def get_collection(identifier):
    """ Get collection for the given collection identifier.
    Return None if no collection matched.
    """
    try:
        return ProductCollection.objects.select_related('type').get(
            identifier=identifier
        )
    except ProductCollection.DoesNotExist:
        return None


def get_product_id(data_file):
    """ Get the product identifier. """
    return splitext(basename(data_file))[0]


def find_product(collection, product_id):
    """ Return True if the product is already registered. """
    try:
        return collection.products.get(identifier=product_id)
    except Product.DoesNotExist:
        return None


def find_time_overlaps(collection, begin_time, end_time):
    """ Lookup products with the same temporal overlap."""
    return collection.products.filter(
        begin_time__lte=end_time, end_time__gte=begin_time
    )


def register_product(collection, identifier, data_file, metadata):
    """ Register product. """
    return update_product(
        Product(identifier=identifier, collection=collection),
        data_file, metadata
    )


def update_product(product, data_file, metadata):
    """ Update and save product. """
    product.begin_time = metadata['begin_time']
    product.end_time = metadata['end_time']
    product.datasets = {
        name: {"location": abspath(data_file)}
        for name in product.collection.type.definition['datasets']
    }
    product.save()
    return product


def delete_product(product):
    """ Delete product object. """
    product.delete()