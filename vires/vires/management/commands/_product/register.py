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
# pylint: disable=missing-docstring, too-few-public-methods, broad-except

import sys
from traceback import print_exc
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import CommandError
from vires.management.api.product import (
    register_product, get_product_id, read_product_metadata,
    execute_post_registration_actions,
)
from vires.management.api.product_collection import get_product_collection
from .._common import Subcommand


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
            "--update", "--re-register", dest="ignore_registered",
            action="store_false", default=True, help=(
                "Update product record when the product is already registered.  "
                "By default, the registration is skipped."
            )
        )
        parser.add_argument(
            "--ignore-overlaps", action="store_true", default=False, help=(
                "Ignore time-overlapping products. "
                "By default, the registration de-registers existing products "
                "overlapping time extent of the new product."
            )
        )
        parser.add_argument(
            "--skip-post-registration-actions", dest="skip_post_reg_actions",
            action="store_true", default=False, help=(
                "Register product without executing any post-registration "
                "actions. Do not use unless you know what you doing!"
            )
        )


    def handle(self, **kwargs):
        data_files = kwargs["product-file"]
        update_existing = not kwargs["ignore_registered"]
        resolve_time_overlaps = not kwargs["ignore_overlaps"]
        collection_id = kwargs["collection_id"]
        skip_post_reg_actions = kwargs["skip_post_reg_actions"]

        try:
            collection = get_product_collection(collection_id)
        except ObjectDoesNotExist:
            raise CommandError(
                "The product collection %s does not exist!" % collection_id
            )

        counter = Counter()

        for data_file in read_products(kwargs["input_file"], data_files):
            product_id = get_product_id(data_file)
            try:
                result = register_product(
                    collection, data_file, metadata={
                        "identifier": product_id,
                        **read_product_metadata(data_file, collection.type),
                    },
                    update_existing=update_existing,
                    resolve_time_overlaps=resolve_time_overlaps,
                    logger=self.logger
                )
            except Exception as error:
                if kwargs.get('traceback'):
                    print_exc(file=sys.stderr)
                self.error(
                    "Registration of %s/%s failed! Reason: %s",
                    collection.identifier, product_id, error
                )
                collection.refresh_from_db()
                counter.failed += 1
                result = None

            else:
                counter.removed += len(result.deregistered)
                if result.inserted:
                    counter.inserted += 1
                elif result.updated:
                    counter.updated += 1
                else:
                    counter.skipped += 1
            finally:
                counter.total += 1

            if (
                not skip_post_reg_actions and
                result and (result.inserted or result.updated)
            ):
                execute_post_registration_actions(
                    result.product, logger=self.logger
                )

        counter.print_report(lambda msg: print(msg, file=sys.stderr))

        sys.exit(counter.failed > 0)


class Counter():

    def __init__(self):
        self.total = 0
        self.inserted = 0
        self.updated = 0
        self.removed = 0
        self.skipped = 0
        self.failed = 0

    def print_report(self, print_fcn):
        if self.inserted > 0 or self.total == 0:
            print_fcn(
                "%d of %d product(s) registered."
                % (self.inserted, self.total)
            )

        if self.updated > 0:
            print_fcn(
                "%d of %d product(s) updated."
                % (self.updated, self.total)
            )

        if self.skipped > 0:
            print_fcn(
                "%d of %d product(s) skipped."
                % (self.skipped, self.total)
            )

        if self.removed > 0:
            print_fcn("%d overlapping product(s) de-registered." % self.removed)

        if self.failed > 0:
            print_fcn(
                "Failed to register %d of %d product(s)."
                % (self.failed, self.total)
            )


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
