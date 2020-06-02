#-------------------------------------------------------------------------------
#
# VirES for Swarm application specific settings
#
# Authors: Martin Paces <martin.paces@eox.at>
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

AUX_DB_DST = "aux_dst.cdf"
AUX_DB_KP = "aux_kp.cdf"
AUX_IMF_2__COLLECTION = "SW_OPER_AUX_IMF_2_"
CACHED_PRODUCT_FILE = {
    "AUX_F10_2_": "SW_OPER_AUX_F10_2_.cdf",
    "MCO_SHA_2C": "SW_OPER_MCO_SHA_2C.shc",
    "MCO_SHA_2D": "SW_OPER_MCO_SHA_2D.shc",
    "MCO_SHA_2F": "SW_OPER_MCO_SHA_2F.shc",
    "MCO_SHA_2X": "SW_OPER_MCO_SHA_2X.shc",
    "MLI_SHA_2C": "SW_OPER_MLI_SHA_2C.shc",
    "MLI_SHA_2D": "SW_OPER_MLI_SHA_2D.shc",
    "MLI_SHA_2E": "SW_OPER_MLI_SHA_2E.shc",
    "MMA_SHA_2C": "SW_OPER_MMA_SHA_2C.cdf",
    "MMA_SHA_2F": "SW_OPER_MMA_SHA_2F.cdf",
    "MIO_SHA_2C": "SW_OPER_MIO_SHA_2C.txt",
    "MIO_SHA_2D": "SW_OPER_MIO_SHA_2D.txt",
    "MMA_CHAOS_": "SW_OPER_MMA_CHAOS_.cdf",
    "AUXAORBCNT": "SW_OPER_AUXAORBCNT.cdf",
    "AUXBORBCNT": "SW_OPER_AUXBORBCNT.cdf",
    "AUXCORBCNT": "SW_OPER_AUXCORBCNT.cdf",
    "AUXAODBGEO": "SW_VIRE_AUXAODBGEO.cdf",
    "AUXBODBGEO": "SW_VIRE_AUXBODBGEO.cdf",
    "AUXCODBGEO": "SW_VIRE_AUXCODBGEO.cdf",
    "AUXAODBMAG": "SW_VIRE_AUXAODBMAG.cdf",
    "AUXBODBMAG": "SW_VIRE_AUXBODBMAG.cdf",
    "AUXCODBMAG": "SW_VIRE_AUXCODBMAG.cdf",
}
ORBIT_COUNTER_FILE = {
    "A": CACHED_PRODUCT_FILE["AUXAORBCNT"],
    "B": CACHED_PRODUCT_FILE["AUXBORBCNT"],
    "C": CACHED_PRODUCT_FILE["AUXCORBCNT"],
}
ORBIT_DIRECTION_GEO_FILE = {
    "A": CACHED_PRODUCT_FILE["AUXAODBGEO"],
    "B": CACHED_PRODUCT_FILE["AUXBODBGEO"],
    "C": CACHED_PRODUCT_FILE["AUXCODBGEO"],
}
ORBIT_DIRECTION_MAG_FILE = {
    "A": CACHED_PRODUCT_FILE["AUXAODBMAG"],
    "B": CACHED_PRODUCT_FILE["AUXBODBMAG"],
    "C": CACHED_PRODUCT_FILE["AUXCODBMAG"],
}
SPACECRAFTS = list(ORBIT_COUNTER_FILE)
