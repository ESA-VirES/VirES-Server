#-------------------------------------------------------------------------------
#
# Cached product management command.
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
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from eoxserver.resources.coverages.management.commands import CommandOutputMixIn
from vires.aux import update_kp, update_dst
from vires.orbit_counter import update_orbit_counter_file
from vires.model_mma import update_mma_sha_2f
from vires.cached_products import (
    copy_file, update_cached_product, simple_cached_product_updater,
    InvalidSourcesError,
)


class Command(CommandOutputMixIn, BaseCommand):
    help = """ Update a cached singleton product. """
    option_list = BaseCommand.option_list

    def add_arguments(self, parser):
        parser.add_argument(
            "product_type", help="Product type",
            choices=list(sorted(CACHED_PRODUCTS)),
        )
        parser.add_argument(
            "source", nargs="+", help="Source filename or URL."
        )

    def handle(self, product_type, source, **kwargs):
        product_info = CACHED_PRODUCTS[product_type]
        try:
            update_cached_product(
                sources=source,
                destination=product_info["filename"],
                updater=product_info.get("updater", copy_file),
                tmp_extension=product_info.get("tmp_extension"),
                logger=getLogger(__name__)
            )
        except InvalidSourcesError as exc:
            raise CommandError(str(exc))


# load the default cached products
CACHED_PRODUCTS = {
    product_type: {"filename": filename}
    for product_type, filename
    in getattr(settings, "VIRES_CACHED_PRODUCTS", {}).iteritems()
}

# custom cached products
if "MMA_SHA_2F" in CACHED_PRODUCTS:
    CACHED_PRODUCTS["MMA_SHA_2F"].update({
        "updater": update_mma_sha_2f,
        "tmp_extension": ".tmp.cdf",
    })

CACHED_PRODUCTS.update({
    "AUXAORBCNT": {
        "filename": settings.VIRES_ORBIT_COUNTER_DB['A'],
        "label": "Swarm A orbit counter",
        "updater": simple_cached_product_updater(update_orbit_counter_file),
        "tmp_extension": ".tmp.cdf",
    },
    "AUXBORBCNT": {
        "filename": settings.VIRES_ORBIT_COUNTER_DB['B'],
        "label": "Swarm B orbit counter",
        "updater": simple_cached_product_updater(update_orbit_counter_file),
        "tmp_extension": ".tmp.cdf",
    },
    "AUXCORBCNT": {
        "filename": settings.VIRES_ORBIT_COUNTER_DB['C'],
        "label": "Swarm C orbit counter",
        "updater": simple_cached_product_updater(update_orbit_counter_file),
        "tmp_extension": ".tmp.cdf",
    },
    "GFZ_AUX_DST": {
        "filename": settings.VIRES_AUX_DB_DST,
        "label": 'Dst-index',
        "updater": simple_cached_product_updater(update_dst),
        "tmp_extension": ".tmp.cdf",
    },
    "GFZ_AUX_KP": {
        "filename": settings.VIRES_AUX_DB_KP,
        "label": 'Kp-index',
        "updater": simple_cached_product_updater(update_kp),
        "tmp_extension": ".tmp.cdf",
    },
})
