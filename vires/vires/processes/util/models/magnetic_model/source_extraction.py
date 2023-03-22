#-------------------------------------------------------------------------------
#
# Data Source - common source extraction
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
#pylint: disable=too-few-public-methods

from numpy import searchsorted


class ExtractSourcesMixIn:
    """ Mix-in class defining the extract sources method. """

    def extract_sources(self, start, end):
        """ Extract a subset of sources matched my the given time interval. """
        validity_start, validity_end = self.validity
        start = max(start, validity_start)
        end = min(end, validity_end)

        product_set = set()

        if start > end:
            return product_set # not overlap

        for source_list, ranges in self.sources:
            if source_list:
                idx_start = max(0, searchsorted(ranges[:, 1], start, "left"))
                idx_stop = searchsorted(ranges[:, 0], end, "right")
                product_set.update(source_list[idx_start:idx_stop])

        return product_set
