#-------------------------------------------------------------------------------
#
# Dump info about cached products in JSON format
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2020 EOX IT Services GmbH
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
#pylint: disable=missing-docstring

import sys
import json
from os.path import getmtime
from datetime import datetime
from vires.util import unique, include
from vires.cdf_util import cdf_open, CDFError
from vires.cache_util import cache_path
from vires.time_util import naive_to_utc
from vires.data.vires_settings import (
    SPACECRAFTS, AUX_DB_DST, AUX_DB_KP, CACHED_PRODUCT_FILE,
)
from .._common import Subcommand, JSON_OPTS, datetime_to_string


class DumpCachedProductSubcommand(Subcommand):
    name = "dump"
    help = """ Dump cached product info in JSON format. """

    def add_arguments(self, parser):
        parser.add_argument(
            "product_type", nargs="*", help="Product type",
            #choices=list(sorted(CACHED_PRODUCTS)),
        )
        parser.add_argument(
            "-f", "--file-name", dest="file", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        product_types = kwargs['product_type']

        if not product_types:
            product_types = list(CACHED_PRODUCTS)

        data = [
            serialize_cache_item(name, **CACHED_PRODUCTS[name])
            for name in include(unique(product_types), CACHED_PRODUCTS)
        ]

        filename = kwargs["file"]
        with (sys.stdout if filename == "-" else open(filename, "w")) as file_:
            json.dump(data, file_, **JSON_OPTS)


def serialize_cache_item(identifier, filename, info_reader):
    info = info_reader(filename)
    return {
        "identifier": identifier,
        "updated": info['updated'],
        "location": filename,
        "sources": info['sources'],
    }


def read_info_file(filename):

    try:
        last_modified = naive_to_utc(
            datetime.utcfromtimestamp(getmtime(filename))
        )
    except FileNotFoundError:
        last_modified = None

    try:
        with open("%s.source" % filename) as file_:
            sources = [line.strip() for line in file_]
    except FileNotFoundError:
        sources = []

    return {
        "updated": datetime_to_string(last_modified),
        "sources": sources,
    }


def read_info_cdf(filename):
    try:
        with cdf_open(filename) as cdf:
            last_modified = cdf.attrs['CREATED'][0]
            if 'SOURCES' in cdf.attrs:
                sources = list(cdf.attrs['SOURCES'])
            if 'SOURCE' in cdf.attrs:
                sources = list(cdf.attrs['SOURCE'])
    except CDFError:
        last_modified = None
        sources = []

    return {
        "updated": last_modified,
        "sources": sources,
    }


def configure_cached_product(product_type, **kwargs):
    """ Cached product configuration. """
    if product_type in CACHED_PRODUCTS:
        CACHED_PRODUCTS[product_type].update(kwargs)


CACHED_PRODUCTS = {
    product_type: {
        "filename": cache_path(filename),
        "info_reader": read_info_file,
    }
    for product_type, filename in CACHED_PRODUCT_FILE.items()
}

configure_cached_product("MMA_CHAOS6", info_reader=read_info_cdf)
configure_cached_product("MMA_SHA_2C", info_reader=read_info_cdf)
configure_cached_product("MMA_SHA_2F", info_reader=read_info_cdf)
configure_cached_product("AUX_F10_2_", info_reader=read_info_cdf)

for spacecraft in SPACECRAFTS:
    configure_cached_product("AUX%sORBCNT" % spacecraft, info_reader=read_info_cdf)
    #configure_cached_product("AUX%sODBGEO" % spacecraft, info_reader=read_info_cdf)
    #configure_cached_product("AUX%sODBMAG" % spacecraft, info_reader=read_info_cdf)

CACHED_PRODUCTS.update({
    "GFZ_AUX_DST": {
        "filename": cache_path(AUX_DB_DST),
        "info_reader": read_info_cdf,
    },
    "GFZ_AUX_KP": {
        "filename": cache_path(AUX_DB_KP),
        "info_reader": read_info_cdf,
    },
})
