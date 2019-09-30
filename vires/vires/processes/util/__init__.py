#-------------------------------------------------------------------------------
#
#  Process Utilities
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

from .cache import with_cache_session
from .filters import (
    Filter, ScalarRangeFilter, VectorComponentRangeFilter,
    BoundingBoxFilter,
    merge_indices,
)
from .filters_subsampling import (
    MinStepSampler, GroupingSampler, ExtraSampler,
)
from .time_series import TimeSeries
from .time_series_product import ProductTimeSeries
from .time_series_custom_data import CustomDatasetTimeSeries
from .time_series_aux import (
    IndexKp10, IndexKpFromKp10, IndexDst, IndexF107,
)
from .time_series_orbit_counter import OrbitCounter
from .time_series_orbit_direction import OrbitDirection, QDOrbitDirection
from .model import Model
from .model_magmod import (
    MagneticModelResidual, SourceMagneticModel, ComposedMagneticModel,
)
from .model_qd_mlt import QuasiDipoleCoordinates, MagneticLocalTime
from .model_sunpos import SunPosition, SubSolarPoint
from .model_dipole import MagneticDipole, DipoleTiltAngle
from .identity import Identity
from .label import Label, SpacecraftLabel
from .input_parsers import (
    parse_style, parse_collections,
    parse_model_expression, parse_model_list,
    parse_filters, parse_filters2,
    parse_variables, get_residual_variables,
)
from .png_output import data_to_png, array_to_png
from .auth import get_username, get_user
from .resolver import VariableResolver, extract_product_names
from .residuals import group_residual_variables, Sat2SatResidual
from .f107 import get_f107_value
from .model_renderer import render_model, ALLOWED_VARIABLES


# other miscellaneous utilities
def format_filters(filters):
    """ Convert filters to string. """
    return "; ".join(
        "%s: %g,%g" % (key, vmin, vmax)
        for key, (vmin, vmax) in filters.iteritems()
    )
