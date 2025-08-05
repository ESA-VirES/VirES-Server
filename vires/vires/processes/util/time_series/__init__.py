#-------------------------------------------------------------------------------
#
#  Time Series - data sources
#
# Authors: Martin Paces <martin.paces@eox.at>
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

from vires.models import ProductCollection
from .base import TimeSeries
from .product_source import (
    product_source_factory,
    SingleCollectionProductSource,
    MultiCollectionProductSource,
)
from .product import ProductTimeSeries
from .custom_data import CustomDatasetTimeSeries
from .indices import IndexKp10, IndexDst, IndexDDst, IndexF107
from .orbit_counter import OrbitCounter
from .orbit_direction import OrbitDirection, QDOrbitDirection
from .cached_model import CachedModelExtraction, ModelInterpolation


def get_product_time_series(identifier):
    """ Convenience function creating product time series for the given
    product collection identifier.
    """
    return ProductTimeSeries(SingleCollectionProductSource(
        ProductCollection.objects.get(identifier=identifier)
    ))
