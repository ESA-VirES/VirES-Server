#-------------------------------------------------------------------------------
#
# Process Utilities - get applicable time limit based on the requested sampling
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

from datetime import timedelta
from eoxserver.core.util.timetools import parse_duration


DEFAULT_SAMPLING = parse_duration("PT1S")
MAX_LIMIT = timedelta(days=999999999)


def get_time_limit(sources, requested_sampling, selection_limit):
    """ Get time-selection limit adapted to the requested data sampling. """

    if sources:
        sampling = min([
            parse_duration(value) if value else DEFAULT_SAMPLING
            for value in (
                collection_list[0].metadata.get('nominalSampling')
                for collection_list in sources.values()
            )
        ])
    else:
        sampling = DEFAULT_SAMPLING

    if requested_sampling is not None and sampling > requested_sampling:
        sampling = requested_sampling

    # ignore sampling below the default 1 sec
    if sampling < DEFAULT_SAMPLING:
        sampling = DEFAULT_SAMPLING

    return timedelta(seconds=min(
        MAX_LIMIT.total_seconds(),
        selection_limit.total_seconds() * sampling.total_seconds()
    ))
