#-------------------------------------------------------------------------------
#
# MMA products handling
#
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from os.path import basename, splitext
from numpy import concatenate, array, empty
from .cdf_util import cdf_open, CDF_EPOCH_TYPE


MMA_SHA_2F_MAX_ALLOWED_TIME_GAP = 7200000 # ms (2 hours)
MMA_SHA_2F_TIME_VARIABLE = "t_qs"
MMA_SHA_2F_VARIABLES = [
    "t_qs", "qs_geo",
    "t_gh", "gh_geo",
]

MMA_SHA_2C_MAX_ALLOWED_TIME_GAP = 7200000 # ms (2 hours)
MMA_SHA_2C_TIME_VARIABLE = "t_qs_1"
MMA_SHA_2C_VARIABLES = [
    "t_qs_1", "qs_1",
    "t_qs_2", "qs_2",
    "t_gh_1", "gh_1",
    "t_gh_2", "gh_2",
]


def filter_mma_sha_2f(sources):
    """ Filter and sort the input MMA_SHA_2F products. """
    return filter_and_sort_sources(
        sources, MMA_SHA_2F_TIME_VARIABLE, MMA_SHA_2F_MAX_ALLOWED_TIME_GAP
    )


def filter_mma_sha_2c(sources):
    """ Filter and sort the input MMA_SHA_2C products. """
    return filter_and_sort_sources(
        sources, MMA_SHA_2C_TIME_VARIABLE, MMA_SHA_2C_MAX_ALLOWED_TIME_GAP
    )


def merge_mma_sha_2f(sources, destination):
    """ Merge inputs and update the cached MMA_SHA_2F product. """
    sources = filter_mma_sha_2f(sources)
    models = list(_load_models(sources, MMA_SHA_2F_VARIABLES))
    create_merged_mma_model(
        destination, sources, models, _merge_mma_sha_2f, MMA_SHA_2F_TIME_VARIABLE
    )


def merge_mma_sha_2c(sources, destination):
    """ Merge inputs and update the cached MMA_SHA_2C product. """
    sources = filter_mma_sha_2c(sources)
    models = list(_load_models(sources, MMA_SHA_2C_VARIABLES))
    create_merged_mma_model(
        destination, sources, models, _merge_mma_sha_2c, MMA_SHA_2C_TIME_VARIABLE
    )


def _merge_mma_sha_2f(cdf_dst, cdf_src, models):
    """ Merge MMA_SHA_2F product files. """
    _copy_attributes(cdf_dst, cdf_src)
    cdf_dst.attrs["TITLE"] = "Merged " + str(cdf_src.attrs["TITLE"])
    for variable in ["qs", "gh"]:
        time_variable = "t_" + variable
        _set_variable(
            cdf_dst, cdf_src, time_variable,
            _merge_variable(models, time_variable, axis=1)
        )
        _copy_variable(cdf_dst, cdf_src, "nm_" + variable)
        coeff_variable = variable + "_geo"
        _set_variable(
            cdf_dst, cdf_src, coeff_variable,
            _merge_variable(models, coeff_variable, axis=1)
        )


def _merge_mma_sha_2c(cdf_dst, cdf_src, models):
    """ Merge MMA_SHA_2C product files. """
    _copy_attributes(cdf_dst, cdf_src)
    cdf_dst.attrs["TITLE"] = "Merged " + str(cdf_src.attrs["TITLE"])
    for variable in ["qs_1", "qs_2", "gh_1", "gh_2"]:
        time_variable = "t_" + variable
        _set_variable(
            cdf_dst, cdf_src, time_variable,
            _merge_variable(models, time_variable, axis=1)
        )
        _copy_variable(cdf_dst, cdf_src, "nm_" + variable)
        _set_variable(
            cdf_dst, cdf_src, variable,
            _merge_variable(models, variable, axis=1)
        )


def create_merged_mma_model(destination, sources, models, merge_models,
                            time_variable):
    """ Create merged MMA model.
    """
    with cdf_open(destination, "w") as cdf_dst:
        set_sources(cdf_dst, sources)
        set_source_time_ranges(cdf_dst, sources, time_variable)
        with cdf_open(sources[-1], "r") as cdf_src:
            merge_models(cdf_dst, cdf_src, models)


def filter_and_sort_sources(sources, time_variable, max_gap):
    """ Sort sources by validity and filter adjacent consecutive products. """

    def _sortable_sources(sources):
        for source in sources:
            start, stop = _read_validity(source, time_variable)
            yield start, stop, source

    def _filter_sources(sources):
        start_last, stop_last, source = sources.next()
        yield start_last, stop_last, source
        for start, stop, source in sources:
            if stop >= start_last:
                continue
            elif start_last - stop <= max_gap:
                yield start, stop, source
                start_last, stop_last = start, stop
            else:
                break

    sorted_sources = sorted(_sortable_sources(sources), reverse=True)
    filtered_sources = list(_filter_sources(iter(sorted_sources)))
    return [source for _, _, source in reversed(filtered_sources)]


def filename2id(filename):
    """ Turn product filename into an identifier. """
    return splitext(basename(filename))[0]


def set_sources(cdf, sources):
    """ Set attribute containing list of source files. """
    cdf.attrs["SOURCES"] = [filename2id(source) for source in sources]


def set_source_time_ranges(cdf, sources, time_variable):
    """ Set attribute containing list of source time-ranges. """
    source_validities = array([
        _read_validity(source, time_variable) for source in sources
    ])
    # Note that because of the linear interpolation between two
    # consecutive models the 'validities' of two consecutive
    # models overlap.
    overlaped_validities = empty(source_validities.shape)
    overlaped_validities[0, 0] = source_validities[0, 0]
    overlaped_validities[-1, 1] = source_validities[-1, 1]
    overlaped_validities[1:, 0] = source_validities[:-1, 1]
    overlaped_validities[:-1, 1] = source_validities[1:, 0]

    cdf.attrs.new("SOURCE_TIME_RANGES")
    attr = cdf.attrs["SOURCE_TIME_RANGES"]
    for item in overlaped_validities:
        attr.new(data=item, type=CDF_EPOCH_TYPE)


def _read_validity(source, time_variable):
    with cdf_open(source, "r") as cdf_src:
        time = cdf_src.raw_var(time_variable)[...].squeeze()
        return time[0], time[-1]


def _load_models(sources, variables):
    def _load_model(cdf_src, variables):
        return {
            variable: cdf_src.raw_var(variable)[...] for variable in variables
        }

    for source in sources:
        with cdf_open(source, "r") as cdf_src:
            yield _load_model(cdf_src, variables)


def _merge_variable(models, variable, axis=0):
    return concatenate([model[variable] for model in models], axis=axis)


def _set_variable(cdf_dst, cdf_src, variable, data):
    raw_var = cdf_src.raw_var(variable)
    cdf_dst.new(variable, data, raw_var.type())
    cdf_dst[variable].attrs.update(raw_var.attrs)


def _copy_variable(cdf_dst, cdf_src, variable):
    raw_var = cdf_src.raw_var(variable)
    cdf_dst.new(variable, raw_var[...], raw_var.type())
    cdf_dst[variable].attrs.update(raw_var.attrs)


def _copy_attributes(cdf_dst, cdf_src):
    cdf_dst.attrs.update(cdf_src.attrs)
