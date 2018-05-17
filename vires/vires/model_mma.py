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

from os.path import basename
from numpy import concatenate
from .cdf_util import cdf_open

MMA_SHA_2F_MAX_ALLOWED_TIME_GAP = 7200000 # ms (2 hours)
MMA_SHA_2F_TIME_VARIABLE = "t_qs"
MMA_SHA_2F_VARIABLES = ["t_qs", "qs_geo", "t_gh", "gh_geo"]


def filter_mma_sha_2f(sources):
    """ Filter and sort the input MMA_SHA_2F products. """
    return filter_and_sort_sources(
        sources, MMA_SHA_2F_TIME_VARIABLE, MMA_SHA_2F_MAX_ALLOWED_TIME_GAP
    )


def update_mma_sha_2f(sources, destination):
    """ Update cached MMA_SHA_2F product. """
    sources = filter_mma_sha_2f(sources)
    models = list(_load_models(sources, MMA_SHA_2F_VARIABLES))
    create_merged_mma_sha_2f(destination, sources, models)


def create_merged_mma_sha_2f(destination, sources, models):
    """ Create blank MMA_SHA_2F product file.
    """
    def _create_empty_mma_sha_2f(cdf_dst, cdf_src):
        _copy_attributes(cdf_dst, cdf_src)
        cdf_dst.attrs["TITLE"] = "Merged " + str(cdf_src.attrs["TITLE"])
        _set_variable(
            cdf_dst, cdf_src, "t_qs", _merge_variable(models, "t_qs", axis=1)
        )
        _copy_variable(cdf_dst, cdf_src, "nm_qs")
        _set_variable(
            cdf_dst, cdf_src, "qs_geo", _merge_variable(models, "qs_geo", axis=1)
        )
        _set_variable(
            cdf_dst, cdf_src, "t_gh", _merge_variable(models, "t_gh", axis=1)
        )
        _copy_variable(cdf_dst, cdf_src, "nm_gh")
        _set_variable(
            cdf_dst, cdf_src, "gh_geo", _merge_variable(models, "gh_geo", axis=1)
        )

    with cdf_open(destination, "w") as cdf_dst:
        with cdf_open(sources[-1], "r") as cdf_src:
            _create_empty_mma_sha_2f(cdf_dst, cdf_src)
        set_sources(cdf_dst, sources)


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


def set_sources(cdf_dst, sources):
    """ Set attribute containing list of source files. """
    cdf_dst.attrs["SOURCES"] = [basename(source) for source in sources]


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
