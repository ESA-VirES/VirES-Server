#-------------------------------------------------------------------------------
#
# Synchronize conjunctions table.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
#pylint: disable=missing-docstring

import sys
from vires.models import ProductCollection
from vires.management.api.conjunctions import sync_conjunctions_table
from .._common import Subcommand
from .common import Counter, pair_collections


class SyncConjunctionsSubcommand(Subcommand):
    name = "sync"
    help = (
        " Synchronize content of the conjunction table with the content "
        " of the orbit collections. "
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "collection-identifier", nargs="*",
            help=(
                "Optional identifiers of the source orbit collections "
                "to re-build the conjunctions table."
            )
        )

    def handle(self, **kwargs):
        query = ProductCollection.objects.order_by('identifier')
        query = query.filter(metadata__calculateConjunctions=True)

        collection_ids = kwargs['collection-identifier']
        if collection_ids:
            query = query.filter(identifier__in=collection_ids)

        counter = Counter()
        self.log = True
        for collection1, collection2 in pair_collections(query):
            sync_conjunctions_table(
                collection1, collection2, logger=self, counter=counter
            )
        self.log = False
        counter.print_report(self.info)
        sys.exit(counter.failed)
