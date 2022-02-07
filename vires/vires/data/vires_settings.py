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

DEFAULT_MISSION = "Swarm"

AUX_DB_DST = "aux_dst.cdf"
AUX_DB_KP = "aux_kp.cdf"
AUX_IMF_2__COLLECTION = "SW_OPER_AUX_IMF_2_"
CACHED_PRODUCT_FILE = {
    "AUX_F10_2_": "SW_OPER_AUX_F10_2_.cdf",
    "MCO_SHA_2C": "SW_OPER_MCO_SHA_2C.shc",
    "MCO_SHA_2D": "SW_OPER_MCO_SHA_2D.shc",
    "MCO_SHA_2F": "SW_OPER_MCO_SHA_2F.shc",
    "MCO_SHA_2X": "SW_OPER_MCO_SHA_2X.zip",
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
    "GR1_ORBCNT": "GR1_ORBCNT.cdf",
    "GR2_ORBCNT": "GR2_ORBCNT.cdf",
    "GF1_ORBCNT": "GF1_ORBCNT.cdf",
    "GF2_ORBCNT": "GF2_ORBCNT.cdf",
    "CS2_ORBCNT": "CS2_ORBCNT.cdf",
    "GR1_ODBGEO": "GR1_ODBGEO.cdf",
    "GR2_ODBGEO": "GR2_ODBGEO.cdf",
    "GF1_ODBGEO": "GF1_ODBGEO.cdf",
    "GF2_ODBGEO": "GF2_ODBGEO.cdf",
    "CS2_ODBGEO": "CS2_ODBGEO.cdf",
    "GR1_ODBMAG": "GR1_ODBMAG.cdf",
    "GR2_ODBMAG": "GR2_ODBMAG.cdf",
    "GF1_ODBMAG": "GF1_ODBMAG.cdf",
    "GF2_ODBMAG": "GF2_ODBMAG.cdf",
    "CS2_ODBMAG": "CS2_ODBMAG.cdf",
    "CNJ_SWA_SWB": "CNJ_SWA_SWB.cdf",
}
ORBIT_COUNTER_FILE = {
    ("Swarm", "A"): CACHED_PRODUCT_FILE["AUXAORBCNT"],
    ("Swarm", "B"): CACHED_PRODUCT_FILE["AUXBORBCNT"],
    ("Swarm", "C"): CACHED_PRODUCT_FILE["AUXCORBCNT"],
    ("GRACE", "1"): CACHED_PRODUCT_FILE["GR1_ORBCNT"],
    ("GRACE", "2"): CACHED_PRODUCT_FILE["GR2_ORBCNT"],
    ("GRACE-FO", "1"): CACHED_PRODUCT_FILE["GF1_ORBCNT"],
    ("GRACE-FO", "2"): CACHED_PRODUCT_FILE["GF2_ORBCNT"],
    ("CryoSat-2", None): CACHED_PRODUCT_FILE["CS2_ORBCNT"],
}
ORBIT_DIRECTION_GEO_FILE = {
    ("Swarm", "A"): CACHED_PRODUCT_FILE["AUXAODBGEO"],
    ("Swarm", "B"): CACHED_PRODUCT_FILE["AUXBODBGEO"],
    ("Swarm", "C"): CACHED_PRODUCT_FILE["AUXCODBGEO"],
    ("GRACE", "1"): CACHED_PRODUCT_FILE["GR1_ODBGEO"],
    ("GRACE", "2"): CACHED_PRODUCT_FILE["GR2_ODBGEO"],
    ("GRACE-FO", "1"): CACHED_PRODUCT_FILE["GF1_ODBGEO"],
    ("GRACE-FO", "2"): CACHED_PRODUCT_FILE["GF2_ODBGEO"],
    ("CryoSat-2", None): CACHED_PRODUCT_FILE["CS2_ODBGEO"],
}
ORBIT_DIRECTION_MAG_FILE = {
    ("Swarm", "A"): CACHED_PRODUCT_FILE["AUXAODBMAG"],
    ("Swarm", "B"): CACHED_PRODUCT_FILE["AUXBODBMAG"],
    ("Swarm", "C"): CACHED_PRODUCT_FILE["AUXCODBMAG"],
    ("GRACE", "1"): CACHED_PRODUCT_FILE["GR1_ODBMAG"],
    ("GRACE", "2"): CACHED_PRODUCT_FILE["GR2_ODBMAG"],
    ("GRACE-FO", "1"): CACHED_PRODUCT_FILE["GF1_ODBMAG"],
    ("GRACE-FO", "2"): CACHED_PRODUCT_FILE["GF2_ODBMAG"],
    ("CryoSat-2", None): CACHED_PRODUCT_FILE["CS2_ODBMAG"],
}
ORBIT_CONJUNCTION_FILE = {
    (("Swarm", "A"), ("Swarm", "B")): CACHED_PRODUCT_FILE["CNJ_SWA_SWB"],
}

SPACECRAFTS = list(ORBIT_COUNTER_FILE)
