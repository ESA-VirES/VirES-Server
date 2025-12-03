#-------------------------------------------------------------------------------
#
# Evaluation of magnetic models at user provided times and locations
# - common data
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2025 EOX IT Services GmbH
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

FORMAT_SPECIFIC_TIME_FORMAT = "format specific default"

TIME_KEY = "Timestamp"
BACKUP_TIME_KEY = f"_{TIME_KEY}"
MJD2000_KEY = "MJD2000"
LOCATION_KEYS = ("Latitude", "Longitude", "Radius")

JSON_DEFAULT_TIME_FORMAT = "ISO date-time"
CSV_DEFAULT_TIME_FORMAT = "ISO date-time"
MSGP_DEFAULT_TIME_FORMAT = "ISO date-time"
HDF_DEFAULT_TIME_FORMAT = "ISO date-time"


def get_max_data_shape(shapes):
    """ Get maximum of the given shapes. """
    def _max_shape(shape1, shape2):
        if len(shape1) > len(shape2):
            shape1, shape2 = shape2, shape1
        return (
            *(max(dim1, dim2) for dim1, dim2 in zip(shape1, shape2)),
            *shape2[len(shape1):len(shape2)],
        )
    max_shape = ()
    for shape in shapes:
        max_shape = _max_shape(max_shape, shape)
    return max_shape


def check_shape_compatibility(shape1, shape2):
    """ Check if two shapes are compatible. """
    for dim1, dim2 in zip(shape1, shape2):
        if dim1 != dim2 and min(dim1, dim2) != 1:
            return False
    return True
