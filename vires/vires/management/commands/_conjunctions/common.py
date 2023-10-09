#-------------------------------------------------------------------------------
#
# Conjunction table management - common subroutines
#
# Authors: Martin Paces martin.paces@eox.at
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
#pylint: disable=missing-docstring,too-few-public-methods

from vires.management.api.conjunctions import (
    Counter as BaseCounter, get_spacecrafts_tuple
)
from vires.data.vires_settings import ORBIT_CONJUNCTION_FILE
from vires.util import unique


def pair_collections(collections):

    def _pair_collections(collections):
        tail = sorted(collections, key=lambda c: c.identifier)
        while tail:
            first, tail = tail[0], tail[1:]
            for second in tail:
                if is_valid_spacecraft_pair(first, second):
                    yield first, second

    yield from unique(_pair_collections(collections))


def is_valid_spacecraft_pair(collection1, collection2):
    return (
        get_spacecrafts_tuple(collection1, collection2)
        in ORBIT_CONJUNCTION_FILE
    )


class Counter(BaseCounter):

    def __init__(self):
        super().__init__()
        self.failed = 0

    def print_report(self, print_fcn):
        if self.processed > 0:
            print_fcn(f"{self.processed} of {self.total} product(s) processed.")

        if self.skipped > 0:
            print_fcn(f"{self.skipped} of {self.total} product(s) skipped.")

        if self.failed > 0:
            print_fcn(f"Failed to process {self.failed} of {self.total} product(s).")

        if self.removed > 0:
            print_fcn(f"{self.removed} old product(s) removed from lookup tables.")

        if self.total == 0:
            print_fcn("No product processed.")
