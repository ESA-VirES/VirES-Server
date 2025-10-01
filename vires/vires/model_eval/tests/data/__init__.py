#-------------------------------------------------------------------------------
#
# Input test data
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

from os.path import join, dirname

_DIRNAME = dirname(__file__)

INPUT_CDF_CDF_EPOCH = join(_DIRNAME, "input_cdf_epoch.cdf")

INPUT_JSON_ISO_TIME = join(_DIRNAME, "input_iso_time.json")
INPUT_JSON_MJD2000 = join(_DIRNAME, "input_mjd2000.json")
INPUT_JSON_CDF_EPOCH = join(_DIRNAME, "input_cdf_epoch.json")

INPUT_MSGPK_ISO_TIME = join(_DIRNAME, "input_iso_time.msgpack")
INPUT_MSGPK_MJD2000 = join(_DIRNAME, "input_mjd2000.msgpack")
INPUT_MSGPK_CDF_EPOCH = join(_DIRNAME, "input_cdf_epoch.msgpack")

INPUT_CSV_ISO_TIME = join(_DIRNAME, "input_iso_time.csv")
INPUT_CSV_MJD2000 = join(_DIRNAME, "input_mjd2000.csv")
INPUT_CSV_CDF_EPOCH = join(_DIRNAME, "input_cdf_epoch.csv")
