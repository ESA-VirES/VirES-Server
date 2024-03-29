#-------------------------------------------------------------------------------
#
# Update orbit tables from MAGx_LR products - common subroutines
#
# Authors: Martin Paces martin.paces@eox.at
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
#pylint: disable=missing-docstring,too-few-public-methods

from vires.management.api.orbit_direction import Counter as BaseCounter


class Counter(BaseCounter):

    def __init__(self):
        super().__init__()
        self.failed = 0

    def print_report(self, print_fcn):
        if self.processed > 0:
            print_fcn(
                "%d of %d product(s) processed."
                % (self.processed, self.total)
            )

        if self.skipped > 0:
            print_fcn(
                "%d of %d product(s) skipped."
                % (self.skipped, self.total)
            )

        if self.failed > 0:
            print_fcn(
                "Failed to process %d of %d product(s)."
                % (self.failed, self.total)
            )

        if self.removed > 0:
            print_fcn(
                "%d old product(s) removed from lookup tables." % self.removed
            )

        if self.total == 0:
            print_fcn("No file processed.")
