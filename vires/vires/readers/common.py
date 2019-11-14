#-------------------------------------------------------------------------------
#
# common reader utilities
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

from numpy import array, stack, dtype, iinfo, datetime64

DAYS2MS = 1000 * 60 * 60 * 24
DATETIME64_MS_2000 = datetime64("2000-01-01", "ms")

_INT_TYPES = set([
    dtype("int8"), dtype("int16"), dtype("int32"), dtype("int64"),
    dtype("uint8"), dtype("uint16"), dtype("uint32"), dtype("uint64"),
])


def reduce_int_type(data, force_signed=False, force_unsigned=False):
    """ Reduce integer type to a maximum necessary bit-depth. """

    def _is_within(type_, vmin, vmax):
        info = iinfo(type_)
        return vmin >= info.min and vmax <= info.max

    if data.dtype in _INT_TYPES:
        vmin, vmax = data.min(), data.max()

        if (vmin >= 0 or force_unsigned) and not force_signed: # unsigned
            types = [dtype("uint8"), dtype("uint16"), dtype("uint32")]
        else: # signed
            types = [dtype("int8"), dtype("int16"), dtype("int32")]

        for type_ in types:
            if _is_within(type_, vmin, vmax):
                return data.astype(type_)

    return data


def sanitize_custom_data(data):
    """ Sanitize input custom data. """
    # translate field names to their proper forms
    special_fields = {field.lower(): field for field in [
        "Timestamp", "MJD2000", "Latitude", "Longitude", "Radius",
        "F", "B_NEC", "B_N", "B_E", "B_C",
    ]}

    data = {
        special_fields.get(field, field): values
        for field, values in data.items()
    }

    # calculate time-stamp from MJD2000
    if "Timestamp" not in data and "MJD2000" in data:
        data["Timestamp"] = DATETIME64_MS_2000 + array(
            DAYS2MS * data["MJD2000"], "timedelta64[ms]"
        )

    # join B_NEC components
    if "B_NEC" not in data and "B_N" in data and "B_E" in data and "B_C" in data:
        data["B_NEC"] = stack((data["B_N"], data["B_E"], data["B_C"]), axis=1)
        del data["B_N"]
        del data["B_E"]
        del data["B_C"]

    return data
