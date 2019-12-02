#-------------------------------------------------------------------------------
#
# Products management - fast de-registration
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
# pylint: disable=missing-docstring,broad-except

from os.path import exists
from django.core.management.base import BaseCommand
from eoxserver.backends.access import connect
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.management.commands import cache_session
from vires.models import ProductCollection


class Command(CommandOutputMixIn, BaseCommand):
    help = "De-register all products from the selected collections."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("identifier", nargs="*")
        parser.add_argument(
            "--invalid-only", dest="remove_invalid",
            action="store_true", default=False,
            help=(
                "Remove only invalid product (product which are registered "
                "but referring to an non-existent file."
            )
        )

    @cache_session
    def handle(self, *args, **kwargs):
        collection_ids = kwargs['identifier']
        remove_invalid = kwargs['remove_invalid']

        counter = Counter()

        for collection_id in collection_ids:
            counter.increment()

            collection = get_collection(collection_id)
            if collection is None:
                self.print_err(
                    "The product collection '%s' does not exist!"
                    % collection_id
                )
                counter.increment_failed()
                continue

            try:
                counter.increment_removed(self._purge_collection(
                    collection, remove_invalid
                ))
            except Exception as error:
                self.print_traceback(error, kwargs)
                self.print_err(
                    "Purging of collection '%s' failed! Reason: %s"
                    % (collection_id, error)
                )
                counter.increment_failed()
            else:
                counter.increment_success()

        counter.print_report(lambda msg: self.print_msg(msg, 1))

    @nested_commit_on_success
    def _purge_collection(self, collection, remove_invalid):
        count = 0
        for product in list_collection(collection):
            if remove_invalid and is_valid_product(product):
                continue
            delete_product(product)
            self.print_msg("%s de-registered" % product.identifier)
            count += 1
        return count


class Counter(object):

    def __init__(self):
        self._total = 0
        self._removed = 0
        self._failed = 0
        self._success = 0

    def increment(self, count=1):
        self._total += count

    def increment_removed(self, count=1):
        self._removed += count

    def increment_failed(self, count=1):
        self._failed += count

    def increment_success(self, count=1):
        self._success += count

    def print_report(self, print_fcn):
        if self._removed > 0:
            print_fcn("%d product(s) de-registered." % self._removed)
        else:
            print_fcn("No product de-registered.")

        if self._success > 0:
            print_fcn(
                "%d of %s collection(s) purged."
                % (self._success, self._total)
            )

        if self._failed > 0:
            print_fcn(
                "Failed to purge %d of %d collections(s)."
                % (self._failed, self._total)
            )

        if self._total == 0:
            print_fcn("No collection purged.")


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


def list_collection(collection):
    """ List all products in a collection. """
    return (
        item.cast() for item in collection.eo_objects.all() if item.iscoverage
    )


def is_valid_product(product):
    """ Check if product is valid or not. """
    return exists(connect(product.data_items.all()[0]))


def delete_product(product):
    """ Delete product object. """
    product.delete()
