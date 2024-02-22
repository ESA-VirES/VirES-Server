#-------------------------------------------------------------------------------
#
# Orbit direction - merging data from multiple sources
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

from collections import namedtuple
from numpy import inf


def resolve_overlaps(sources):
    """ Resolve non-overlapping segments of contiguous orbit direction data
    from multiple sources.
    The input is a list of lists (one for each source) of contiguous segments.
    The segments from different sources are expected to overlap but segments
    from the same source are not.
    The positions of the sources define the order in which the segments overlap
    (later sources fill gaps in the earlier ones).
    """
    return list(_extract_trimmed_data(_merge_segments(
        _SortedSegmentBuffer(_generate_segments(sources))
    )))


def _generate_segments(sources):
    for level, source in enumerate(sources):
        for item in source:
            yield _Segment(level, item.start, item.end, item)


def _extract_trimmed_data(segments):
    for segment in segments:
        yield segment.get_trimmed_data()


def _merge_segments(segments):
    """ Resolve segments overlaps. Segments are read from a segment iterator
    of segments sorted by the start time and trimmed to yield a sequence
    of non-overlapping segments.
    """
    try:
        current = next(segments)
    except StopIteration:
        return

    for next_ in segments:

        if current.end < next_.start: # no overlap, gap between segments
            yield current.trim_end(inf)
            current = next_

        elif current.end == next_.start: # no overlap, adjacent segments
            yield current.trim_end(next_.start)
            current = next_

        elif next_.level < current.level: # next overlaps current
            if current.start < next_.start: # current is ahead of next
                yield current.trim_end(next_.start)
            if current.end > next_.end: # current tails next
                segments.push(current.trim_start(next_.end))
            current = next_

        elif next_.end > current.end: # overlapped next tails current
            segments.push(next_.trim_start(current.end))

    yield current.trim_end(inf)


class _Segment(namedtuple("Segment", ["level", "start", "end", "data"])):
    """ Segment helper structure holding the segment level, time bounds and
    the actual data payload.
    """

    @property
    def is_valid(self):
        """ True is segment is valid. """
        return self.start <= self.end

    def trim_start(self, new_start):
        """ Return copy of the segment with replaced start value. """
        return self.__class__(self.level, new_start, self.end, self.data)

    def trim_end(self, new_end):
        """ Return copy of the segment with replaced end value. """
        return self.__class__(self.level, self.start, new_end, self.data)

    def get_trimmed_data(self):
        """ Return data trimmed by the current bounds. """
        return self.data.trim(self.start, self.end)


class _SortedSegmentBuffer:
    """ Segment buffer acting as an iterator yielding segments sorted
    by the start time.
    New segments can be added while during the iteration via the push method.
    The new segment is inserted preserving the ordering of the segments.
    """

    @staticmethod
    def _sort_segments(segments):
        return sorted(segments, key=lambda s: (s.start, s.level), reverse=True)

    def __init__(self, segments):
        self.segments = self._sort_segments(segments)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self.segments.pop()
        except IndexError:
            raise StopIteration from None

    def push(self, segment):
        """ Push a new segment into the buffer. """
        self.segments = self._sort_segments([segment, *self.segments])
