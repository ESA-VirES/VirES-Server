#-------------------------------------------------------------------------------
#
# Cached product management API
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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

from logging import getLogger
from vires.aux_kp import update_kp
from vires.aux_dst import update_dst
from vires.aux_f107 import update_aux_f107_2_
from vires.orbit_counter import (
    update_orbit_counter_file, update_gfz_orbit_counter_file,
)
from vires.model_shc import merge_files_to_zip, filter_mco_sha_2x
from vires.model_mma import (
    merge_mma_sha_2f, filter_mma_sha_2f, merge_mma_sha_2c, filter_mma_sha_2c,
)
from vires.cache_util import cache_path
from vires.data.vires_settings import (
    SPACECRAFTS, AUX_DB_DST, AUX_DB_KP, CACHED_PRODUCT_FILE,
)
from vires.cached_products import (
    copy_file, update_cached_product as _update_cached_product,
    simple_cached_product_updater,
)


def update_cached_product(product_type, *data_files, logger=None):
    """ Update cached product.
    Options:
      product_type - string, type of the updated cached product
      data_files - one or more input files (depending on the product type)
      logger -      optional logger

    Returns:
      none
    """

    product_info = CACHED_PRODUCTS.get(product_type)
    if product_info is None:
        raise ValueError(f"Invalid cached product type {product_type}!")

    _update_cached_product(
        sources=data_files,
        destination=product_info["filename"],
        updater=product_info.get("updater", copy_file),
        filter_=product_info.get("filter"),
        tmp_extension=product_info.get("tmp_extension"),
        logger=(logger or getLogger(__name__)),
    )


def get_cached_product_configuration():
    """ Get cached product configuration. """

    # default cached products
    cached_products = {
        product_type: {"filename": cache_path(filename)}
        for product_type, filename in CACHED_PRODUCT_FILE.items()
    }

    cached_products.update({
        "GFZ_AUX_DST": {
            "filename": cache_path(AUX_DB_DST),
            "label": 'Dst-index',
            "updater": simple_cached_product_updater(update_dst),
            "tmp_extension": ".tmp.cdf",
        },
        "GFZ_AUX_KP": {
            "filename": cache_path(AUX_DB_KP),
            "label": 'Kp-index',
            "updater": simple_cached_product_updater(update_kp),
            "tmp_extension": ".tmp.cdf",
        },
    })

    def _configure_cached_product(product_type, **kwargs):
        if product_type in cached_products:
            cached_products[product_type].update(kwargs)

    # cached product specific configuration

    _configure_cached_product(
        "MCO_SHA_2X",
        updater=merge_files_to_zip,
        filter=filter_mco_sha_2x,
        tmp_extension=".tmp.zip"
    )

    _configure_cached_product(
        "MMA_CHAOS_",
        updater=merge_mma_sha_2c,
        filter=filter_mma_sha_2c,
        tmp_extension=".tmp.cdf"
    )

    _configure_cached_product(
        "MMA_SHA_2C",
        updater=merge_mma_sha_2c,
        filter=filter_mma_sha_2c,
        tmp_extension=".tmp.cdf"
    )

    _configure_cached_product(
        "MMA_SHA_2F",
        updater=merge_mma_sha_2f,
        filter=filter_mma_sha_2f,
        tmp_extension=".tmp.cdf"
    )

    _configure_cached_product(
        "AUX_F10_2_",
        updater=simple_cached_product_updater(update_aux_f107_2_),
        tmp_extension=".tmp.cdf"
    )

    for mission, spacecraft in SPACECRAFTS:

        if mission == "Swarm":
            _configure_cached_product(
                f"AUX{spacecraft}ORBCNT",
                label=f"Swarm {spacecraft} orbit counter",
                updater=simple_cached_product_updater(update_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop(f"AUX{spacecraft}ODBGEO")
            cached_products.pop(f"AUX{spacecraft}ODBMAG")
            cached_products.pop(f"FAST_AUX{spacecraft}ODBGEO")
            cached_products.pop(f"FAST_AUX{spacecraft}ODBMAG")
        elif mission == "GRACE":
            _configure_cached_product(
                f"GR{spacecraft}_ORBCNT",
                label=f"GRACE-{spacecraft} orbit counter",
                updater=simple_cached_product_updater(update_gfz_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop(f"GR{spacecraft}_ODBGEO")
            cached_products.pop(f"GR{spacecraft}_ODBMAG")
        elif mission == "GRACE-FO":
            _configure_cached_product(
                f"GF{spacecraft}_ORBCNT",
                label=f"GRACE-FO-{spacecraft} orbit counter",
                updater=simple_cached_product_updater(update_gfz_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop(f"GF{spacecraft}_ODBGEO")
            cached_products.pop(f"GF{spacecraft}_ODBMAG")
        elif mission == "CryoSat-2":
            _configure_cached_product(
                "CS2_ORBCNT",
                label="CryoSat-2 orbit counter",
                updater=simple_cached_product_updater(update_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop("CS2_ODBGEO")
            cached_products.pop("CS2_ODBMAG")
        elif mission == "GOCE":
            _configure_cached_product(
                "GO_ORBCNT",
                label="GOCE orbit counter",
                updater=simple_cached_product_updater(update_gfz_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop("GO_ODBGEO")
            cached_products.pop("GO_ODBMAG")
        elif mission == "GOCE":
            _configure_cached_product(
                "CH_ORBCNT",
                label="CHAMP orbit counter",
                updater=simple_cached_product_updater(update_gfz_orbit_counter_file),
                tmp_extension=".tmp.cdf"
            )
            cached_products.pop("CH_ODBGEO")
            cached_products.pop("CH_ODBMAG")

    return cached_products

CACHED_PRODUCTS = get_cached_product_configuration()
