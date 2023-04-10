#-------------------------------------------------------------------------------
#
# Cached magnetic models management API
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

from vires.magnetic_models import ModelInputParser
from vires.time_util import mjd2000_to_datetime, datetime_to_mjd2000


def parse_source_model(model_expression):
    """ Parse model expression and get the canonical model expression"""
    parser = ModelInputParser()
    parser.parse_model_expression(model_expression)
    if len(parser.source_models) == 0:
        raise ValueError(
            f"The model expression {model_expression!r} defines a model "
            "composed of multiple source models."
        )
    if len(parser.source_models) == 0:
        raise ValueError(
            f"The model expression {model_expression!r} does not define "
            "any source model."
        )

    return list(parser.source_models.values())[0]


def extract_model_sources_and_time_ranges_mjd2000(model, start, end):
    """ Extract model sources and time-ranges within the given MJD2000 time
    interval.
    """
    for sources in model.extract_sources(start, end):
        for name, (source_start, source_end) in zip(*sources):
            yield name, max(start, source_start), min(end, source_end)


def extract_model_sources_datetime(model, start, end):
    """ Extract model sources within the given datetime.datetime time interval.

    This function extracts only the source names without the time intervals.
    """
    start = datetime_to_mjd2000(start)
    end = datetime_to_mjd2000(end)
    for sources in model.extract_sources(start, end):
        yield from sources.names
