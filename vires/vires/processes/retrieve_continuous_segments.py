#-------------------------------------------------------------------------------
#
# WPS process fetching intervals of continuous segments of product data
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

import csv
from datetime import datetime
from eoxserver.services.ows.wps.parameters import (
    LiteralData, ComplexData, CDTextBuffer, FormatText
)
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError
from vires.models import ProductCollection
from vires.cache_util import cache_path
from vires.time_util import naive_to_utc, format_datetime, parse_duration
from vires.cdf_util import cdf_rawtime_to_datetime, timedelta_to_cdf_rawtime
from vires.processes.base import WPSProcess
from vires.processes.util.time_series import ProductTimeSeries, QDOrbitDirection
from vires.data.vires_settings import ORBIT_DIRECTION_MAG_FILE, DEFAULT_MISSION

ALLOWED_COLLECTIONS = ["SW_AEJxLPL_2F", "SW_AEJxLPS_2F"]
TIME_VARIABLE = "Timestamp"


def get_spacecraft_time_series(mission, spacecraft):
    """ Get spacecraft specific time-series. """
    return [
        QDOrbitDirection(
            ":".join(["QDOrbitDirection", mission, spacecraft]),
            cache_path(ORBIT_DIRECTION_MAG_FILE[(mission, spacecraft)])
        ),
    ]


class RetrieveContinuousSegments(WPSProcess):
    """ Process listing continuous segments of data. """
    identifier = "retrieve_continuous_segments"
    title = "Retrieve list of continuous segments of data."
    metadata = {}
    profiles = ["vires"]

    inputs = WPSProcess.inputs + [
        ("collection_id", LiteralData(
            'collection', str, optional=False,
            title="Collection identifier",
            abstract="Collection identifier",
        )),
        ("begin_time", LiteralData(
            'begin_time', datetime, optional=False, title="Begin time",
            abstract="Start of the selection time interval",
        )),
        ("end_time", LiteralData(
            'end_time', datetime, optional=False, title="End time",
            abstract="End of the selection time interval",
        )),
    ]

    outputs = [
        ("output", ComplexData(
            'times', title="Output data",
            formats=(FormatText('text/csv'), FormatText('text/plain'))
        )),
    ]

    def execute(self, collection_id, begin_time, end_time, output, **kwargs):
        """ Execute process. """
        access_logger = self.get_access_logger(**kwargs)

        try:
            time_series = ProductTimeSeries(
                ProductCollection.objects
                .select_related('type', 'spacecraft')
                .filter(type__identifier__in=ALLOWED_COLLECTIONS)
                .get(identifier=collection_id)
            )
        except ProductCollection.DoesNotExist:
            raise InvalidInputValueError(
                "collection_id",
                "Invalid collection identifier %r!" % collection_id
            ) from None

        access_logger.info(
            "request: collection: %s, toi: (%s, %s)",
            collection_id,
            format_datetime(naive_to_utc(begin_time)) if begin_time else "-",
            format_datetime(naive_to_utc(end_time)) if end_time else "-",
        )

        return _write_csv(
            CDTextBuffer(),
            _generate_pairs(time_series, begin_time, end_time)
        )


def _write_csv(output, records):
    output = CDTextBuffer()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["starttime", "endtime", "bbox", "identifier"])

    envelope = "(-90,-180,90,180)"

    for start, end, id_ in records:
        writer.writerow([
            format_datetime(naive_to_utc(start)),
            format_datetime(naive_to_utc(end)),
            envelope, id_
        ])

    return output


def _generate_pairs(time_series, begin_time, end_time):
    metadata = _Metadata(time_series.collection)
    secondary_time_series = get_spacecraft_time_series(
        metadata.mission, metadata.spacecraft,
    )
    variables = [TIME_VARIABLE] + list(metadata.split_by)

    for dataset in time_series.subset(begin_time, end_time, variables):
        if dataset.is_empty:
            continue

        cdf_type = dataset.cdf_type[TIME_VARIABLE]
        times = dataset[TIME_VARIABLE]
        mask = _get_time_split_mask(times, metadata.time_threshold, cdf_type)

        for item in secondary_time_series:
            dataset.merge(
                item.interpolate(times, variables, {}, cdf_type)
            )

        for variable, threshold in metadata.split_by.items():
            mask |= _get_split_mask(dataset[variable], threshold)

        for start, end in _generate_time_intervals(times, mask.nonzero()[0]):
            yield _output(start, end, dataset, cdf_type)


class _Metadata():
    def __init__(self, collection):
        metadata =collection.metadata
        self.mission, self.spacecraft = collection.spacecraft_tuple
        self.split_by = metadata.get('splitBy', {})
        self.time_threshold = parse_duration(
            metadata['nominalSampling']
        )


def _output(start_time, end_time, dataset, cdf_type):
    return (
        cdf_rawtime_to_datetime(start_time, cdf_type),
        cdf_rawtime_to_datetime(end_time, cdf_type),
        dataset.source
    )


def _get_split_mask(values, threshold):
    return abs(values[1:] - values[:-1]) > threshold


def _get_time_split_mask(times, time_threshold, cdf_type):
    threshold = timedelta_to_cdf_rawtime(time_threshold, cdf_type)
    return times[1:] - times[:-1] > threshold


def _generate_time_intervals(times, breaks):
    time_start = times[0]
    for idx in breaks:
        time_end = times[idx]
        yield time_start, time_end
        time_start = times[idx + 1]
    time_end = times[-1]
    yield time_start, time_end
