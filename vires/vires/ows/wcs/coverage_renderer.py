#-------------------------------------------------------------------------------
# $Id$
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

import logging
from uuid import uuid4
#from cStringIO import StringIO
import csv
from itertools import izip
try:
    # available in Python 2.7+
    from collections import OrderedDict
except ImportError:
    from django.utils.datastructures import SortedDict as OrderedDict


from spacepy import pycdf
from eoxserver.core import implements, Component
from eoxserver.backends.access import connect
from eoxserver.services.ows.version import Version
from eoxserver.services.ows.wcs.interfaces import WCSCoverageRendererInterface
from eoxserver.services.exceptions import (
    InvalidSubsettingException, RenderException
)
from eoxserver.services.result import ResultFile
from eoxserver.services.subset import Trim

from vires import models
from vires.util import get_total_seconds


logger = logging.getLogger(__name__)


class ProductRenderer(Component):
    """ A coverage renderer for VirES Products and Product Collections.
    """

    implements(WCSCoverageRendererInterface)

    versions = (Version(2, 0),)
    handles = (models.Product, models.ProductCollection)

    def supports(self, params):
        return issubclass(params.coverage.real_type, self.handles)

    def render(self, params):
        coverage = params.coverage.cast()
        frmt = params.format

        # get subset
        subset = self._apply_subsets(coverage, params.subsets)

        output_data = self._read_data(coverage, subset, params.rangesubset)

        result = self._encode_data(coverage, output_data, frmt)

        # TODO: coverage description if "multipart"
        return [result]

    def _apply_subsets(self, coverage, subsets):
        if len(subsets) > 1:
            raise InvalidSubsettingException(
                "Too many subsets supplied"
            )

        elif len(subsets):
            subset = subsets[0]

            if not isinstance(subset, Trim):
                raise InvalidSubsettingException(
                    "Invalid subsetting method: only trims are allowed"
                )

            if subset.is_temporal:
                # TODO: translate temporal subset to indices
                begin_time, end_time = coverage.time_extent
                if subset.low < begin_time or subset.high > end_time:
                    raise InvalidSubsettingException(
                        "Temporal subset does not match coverage temporal "
                        "extent."
                    )

                # TODO: implement
                resolution = get_total_seconds(coverage.resolution_time)
                low = get_total_seconds(subset.low - begin_time) / resolution
                high = get_total_seconds(subset.high - begin_time) / resolution

                subset = Trim("x", low, high)
                logger.debug("Calculated subset %s" % subset)

            else:
                if subset.low < 0 or subset.high > coverage.size_x:
                    raise InvalidSubsettingException(
                        "Subset size does not match coverage size."
                    )

        else:
            subset = Trim("x", 0, coverage.size_x)

        return subset

    def _read_data(self, coverage, subset, rangesubset):
        range_type = coverage.range_type

        # Open file
        filename = connect(coverage.data_items.all()[0])

        ds = pycdf.CDF(filename)
        output_data = OrderedDict()

        # Read data
        for band in range_type:
            if not rangesubset or band.identifier in rangesubset:
                data = ds[band.identifier][int(subset.low):int(subset.high)]
                output_data[band.identifier] = data

        return output_data

    def _encode_data(self, coverage, output_data, frmt):
        # Encode data
        if frmt == "text/csv":
            output_filename = "/tmp/%s.csv" % uuid4().hex
            with open(output_filename, "w+") as f:
                #f = StringIO()
                writer = csv.writer(f)
                writer.writerow(output_data.keys())
                for row in izip(*output_data.values()):
                    writer.writerow(map(translate, row))

            return ResultFile(
                output_filename, "text/csv", "%s.csv" % coverage.identifier,
                coverage.identifier
            )

        elif not frmt or frmt in ("application/cdf", "application/x-cdf"):
            #encoder = CDFEncoder(params.rangesubset)
            output_filename = "/tmp/%s.cdf" % uuid4().hex
            output_ds = pycdf.CDF(output_filename, '')

            for name, data in output_data.items():
                output_ds[name] = data

            output_ds.save()
            output_ds.close()

            return ResultFile(
                output_filename, "application/cdf",
                "%s.cdf" % coverage.identifier, coverage.identifier
            )

        else:
            raise RenderException("Invalid format '%s'" % frmt, "format")


def translate(arr):
    try:
        if arr.ndim == 1:
            return "{%s}" % ";".join(map(str, arr))
    except:
        pass

    return arr
