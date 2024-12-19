#-------------------------------------------------------------------------------
#
# Cached magnetic models management API - file format specific operations
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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

import json
from collections import defaultdict
from numpy import stack
from vires.cdf_util import (
    cdf_open, pycdf, cdf_rawtime_to_mjd2000,
    CDF_CHAR_TYPE, CDF_DOUBLE_TYPE, CDF_EPOCH_TYPE,
    GZIP_COMPRESSION, GZIP_COMPRESSION_LEVEL4,
)
from vires.time_util import datetime, format_datetime, naive_to_utc
from .common import remove_file


TIME_VAR = "Timestamp"
LATITUDE_VAR = "Latitude"
LONGITUDE_VAR = "Longitude"
RADIUS_VAR = "Radius"

REQUIRED_VARIABLES = [TIME_VAR, LATITUDE_VAR, LONGITUDE_VAR, RADIUS_VAR]

CDF_COMPRESSION = dict(
    compress=GZIP_COMPRESSION,
    compress_param=GZIP_COMPRESSION_LEVEL4,
)


def save_options(cdf, options):
    """ Save cache options. """
    cdf.attrs["OPTIONS"] = json.dumps(options)


def load_options(cdf):
    """ Load model options. """
    return json.loads(str(cdf.attrs["OPTIONS"]))


def read_model_cache_description(cache_file, logger):
    """ Read the description of the model cache file. """

    def _has_missing_variables(cdf):
        return bool(get_missing_variables(cdf, REQUIRED_VARIABLES))

    def _read_model_cache_description(cdf):
        models = defaultdict(set)
        for model_name, source_name in read_sources(cdf):
            models[model_name].add(source_name)
        return dict(models)

    try:
        with cdf_open(cache_file, "r") as cdf:
            return (
                _read_model_cache_description(cdf),
                _has_missing_variables(cdf),
            )
    except pycdf.CDFError as error:
        logger.debug(
            "Failed to read cache file description from %s! (%s)",
            cache_file, error
        )
    return None, True


def init_cache_file(cache_file, product_info, logger):
    """ Initialize new cache file. """
    logger.info("Creating cache file %s", cache_file)
    with cdf_open(cache_file, "w", backward_compatible=False) as cdf:
        cdf.attrs["TITLE"] = product_info.id
        cdf.attrs["COLLECTION"] = product_info.collection_id
        cdf.attrs.new("MODEL_SOURCES")
        cdf.attrs.new("SOURCE_TIME_RANGES")
        cdf.attrs["CHANGELOG"] = f"{cdf.attrs['CREATED']} file created"


def remove_cache_file(cache_file, logger):
    """ Remove an existing cache file. """
    if remove_file(cache_file):
        logger.info("Removing cache file %s", cache_file)


def read_sources(cdf):
    """ Read model sources """
    sources_attr = cdf.attrs["MODEL_SOURCES"]

    for model_source in sources_attr:
        name, _, source = model_source.partition("/")
        yield name, source


def read_sources_with_time_ranges(cdf):
    """ Read model sources with time-ranges. """
    ranges_attr = cdf.attrs["SOURCE_TIME_RANGES"]

    for (name, source), (start, end) in zip(read_sources(cdf), ranges_attr):
        yield name, source, start, end


def write_sources_with_time_ranges(cdf, sources):
    """ Write updated sources with time-ranges. """

    def _reset_attribute(name):
        del cdf.attrs[name]
        cdf.attrs.new(name)
        return cdf.attrs[name]

    sources_attr = _reset_attribute("MODEL_SOURCES")
    ranges_attr = _reset_attribute("SOURCE_TIME_RANGES")
    for idx, (name, source, start, end) in enumerate(sources):
        sources_attr.new(data=f"{name}/{source}", type=CDF_CHAR_TYPE, number=idx)
        ranges_attr.new(data=(start, end), type=CDF_EPOCH_TYPE, number=idx)


def append_log_record(cdf, message):
    """ Append new cache-file log record. """
    timestamp = format_datetime(naive_to_utc(
        datetime.utcnow().replace(microsecond=0)
    ))
    cdf.attrs["CHANGELOG"].append(f"{timestamp} {message}")


def copy_missing_variables(cdf, product_file):
    """ Copy missing common variables from the original product. """
    missing_variables = get_missing_variables(cdf, REQUIRED_VARIABLES)
    if missing_variables:
        with cdf_open(product_file) as cdf_src:
            copy_variables(cdf_src, cdf, missing_variables)


def get_missing_variables(cdf, variables):
    """ Get list of common variables not present in the checked CDF file. """
    return [
        variable for variable in variables if variable not in cdf
    ]


def copy_variables(cdf_src, cdf_dst, variables):
    """ Copy selected variables. """
    for variable in variables:
        cdf_var_src = cdf_src.raw_var(variable)
        cdf_var_dst = cdf_dst.new(
            name=variable,
            data=cdf_var_src[...],
            type=cdf_var_src.type(),
            **CDF_COMPRESSION
        )
        cdf_var_dst.attrs = cdf_var_src.attrs


def read_times_and_locations_data(cdf, time_var=TIME_VAR,
                                  latitude_var=LATITUDE_VAR,
                                  longitude_var=LONGITUDE_VAR,
                                  radius_var=RADIUS_VAR):
    """ Read times and locations from the source data file. """
    time_var = cdf.raw_var(time_var)
    return {
        "time": cdf_rawtime_to_mjd2000(time_var[...], time_var.type()),
        "location": stack((
            # Note: radius is converted from metres to kilometres
            cdf[latitude_var][...],
            cdf[longitude_var][...],
            cdf[radius_var][...] * 1e-3,
        ), axis=1),
    }


def write_model_data(cdf, model_name, b_nec):
    """ Write model data. """
    remove_model_data(cdf, model_name)

    variable_name = f"B_NEC_{model_name}"

    cdf.new(variable_name, b_nec, CDF_DOUBLE_TYPE, **CDF_COMPRESSION)

    cdf[variable_name].attrs.update({
        "DESCRIPTION": (
            "Magnetic field vector, NEC frame, calculated by "
            f"the {model_name} model."
        ),
        "UNITS": "nT",
    })


def remove_model_data(cdf, model_name):
    """ Remove model data. """

    variable_name = f"B_NEC_{model_name}"

    if variable_name in cdf:
        del cdf[variable_name]
