#-------------------------------------------------------------------------------
#
# VirES for Swarm application specific settings
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2024 EOX IT Services GmbH
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

from datetime import timedelta

SWARM_MISSION = "Swarm"

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
    "FAST_AUXAODBGEO": "SW_FAST_AUXAODBGEO.cdf",
    "FAST_AUXBODBGEO": "SW_FAST_AUXBODBGEO.cdf",
    "FAST_AUXCODBGEO": "SW_FAST_AUXCODBGEO.cdf",
    "FAST_AUXAODBMAG": "SW_FAST_AUXAODBMAG.cdf",
    "FAST_AUXBODBMAG": "SW_FAST_AUXBODBMAG.cdf",
    "FAST_AUXCODBMAG": "SW_FAST_AUXCODBMAG.cdf",
    "GR1_ORBCNT": "GR1_ORBCNT.cdf",
    "GR2_ORBCNT": "GR2_ORBCNT.cdf",
    "GF1_ORBCNT": "GF1_ORBCNT.cdf",
    "GF2_ORBCNT": "GF2_ORBCNT.cdf",
    "GO_ORBCNT": "GO_ORBCNT.cdf",
    "CH_ORBCNT": "CH_ORBCNT.cdf",
    "CS2_ORBCNT": "CS2_ORBCNT.cdf",
    "GR1_ODBGEO": "GR1_ODBGEO.cdf",
    "GR2_ODBGEO": "GR2_ODBGEO.cdf",
    "GF1_ODBGEO": "GF1_ODBGEO.cdf",
    "GF2_ODBGEO": "GF2_ODBGEO.cdf",
    "GO_ODBGEO": "GO_ODBGEO.cdf",
    "CH_ODBGEO": "CH_ODBGEO.cdf",
    "CS2_ODBGEO": "CS2_ODBGEO.cdf",
    "GR1_ODBMAG": "GR1_ODBMAG.cdf",
    "GR2_ODBMAG": "GR2_ODBMAG.cdf",
    "GF1_ODBMAG": "GF1_ODBMAG.cdf",
    "GF2_ODBMAG": "GF2_ODBMAG.cdf",
    "GO_ODBMAG": "GO_ODBMAG.cdf",
    "CH_ODBMAG": "CH_ODBMAG.cdf",
    "CS2_ODBMAG": "CS2_ODBMAG.cdf",
    "CNJ_SWA_SWB": "CNJ_SWA_SWB.cdf",
    "CNJ_FAST_SWA_SWB": "CNJ_FAST_SWA_SWB.cdf",
}

SPACECRAFTS = [
    ("Swarm", "A"),
    ("Swarm", "B"),
    ("Swarm", "C"),
    ("GRACE", "1"),
    ("GRACE", "2"),
    ("GRACE-FO", "1"),
    ("GRACE-FO", "2"),
    ("CryoSat-2", None),
    ("GOCE", None),
    ("CHAMP", None),
]

MISSION_TO_FILE_PREFIX = {
    "Swarm": "AUX{spacecraft}",
    "GRACE": "GR{spacecraft}_",
    "GRACE-FO": "GF{spacecraft}_",
    "CryoSat-2": "CS2_",
    "GOCE": "GO_",
    "CHAMP": "CH_",
}

ORBIT_COUNTER_FILE = {}
ORBIT_DIRECTION_GEO_FILE = {}
ORBIT_DIRECTION_MAG_FILE = {}

grade = None
for mission, spacecraft in SPACECRAFTS:
    prefix = MISSION_TO_FILE_PREFIX[mission].format(spacecraft=spacecraft)
    ORBIT_COUNTER_FILE[(mission, spacecraft)] = CACHED_PRODUCT_FILE[f"{prefix}ORBCNT"]
    ORBIT_DIRECTION_GEO_FILE[(mission, spacecraft, grade)] = CACHED_PRODUCT_FILE[f"{prefix}ODBGEO"]
    ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft, grade)] = CACHED_PRODUCT_FILE[f"{prefix}ODBMAG"]

grade = "FAST"
mission = "Swarm"
for spacecraft in ["A", "B", "C"]:
    prefix = MISSION_TO_FILE_PREFIX[mission].format(spacecraft=spacecraft)
    ORBIT_DIRECTION_GEO_FILE[(mission, spacecraft, grade)] = CACHED_PRODUCT_FILE[f"{grade}_{prefix}ODBGEO"]
    ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft, grade)] = CACHED_PRODUCT_FILE[f"{grade}_{prefix}ODBMAG"]

del mission, spacecraft, prefix, grade

ORBIT_CONJUNCTION_FILE = {
    (("Swarm", "A", None), ("Swarm", "B", None)): CACHED_PRODUCT_FILE["CNJ_SWA_SWB"],
    (("Swarm", "A", "FAST"), ("Swarm", "B", "FAST")): CACHED_PRODUCT_FILE["CNJ_FAST_SWA_SWB"],
}

ORBIT_CONJUNCTION_GRADES = {
    (("Swarm", "A"), ("Swarm", "B")): (None, "FAST")
}

SPACECRAFTS = list(ORBIT_COUNTER_FILE)


# thresholds used by the orbit direction extraction

OD_THRESHOLDS_DEFAULT = {
    "max_product_gap": timedelta(seconds=15.5),
    "min_product_gap": timedelta(seconds=0.5),
    "nominal_sampling": timedelta(seconds=1),
    "gap_threshold": timedelta(seconds=15),
}

OD_THRESHOLDS = {
    ("GOCE", None): {
        "max_product_gap": timedelta(seconds=72),
        "min_product_gap": timedelta(seconds=8),
        "nominal_sampling": timedelta(seconds=16),
        "gap_threshold": timedelta(seconds=64),
    },
}
