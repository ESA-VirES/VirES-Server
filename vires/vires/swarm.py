#-------------------------------------------------------------------------------
#
# Products management - product registration
#
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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
# pylint: disable=missing-docstring

from numpy import array, empty, isnan, floor, ceil
from django.contrib.gis.geos import Polygon, MultiPolygon
from vires.time_util import naive_to_utc


class SwarmProductMetadataReader():

    LATLON_KEYS = [
        ("Longitude", "Latitude"),
        ("longitude", "latitude"),
    ]

    TIME_KEYS = [
        "Timestamp",
        "timestamp",
        "Epoch"
    ]

    @classmethod
    def get_time_range_and_size(cls, data):
        # iterate possible time keys and try to extract the values
        for time_key in cls.TIME_KEYS:
            try:
                times = data[time_key]
            except KeyError:
                continue
            else:
                break
        else:
            raise KeyError("Temporal variable not found!")

        return (naive_to_utc(times[0]), naive_to_utc(times[-1]), times.shape[0])

    @classmethod
    def get_coords(cls, data):
        # iterate possible lat/lon keys and try to extract the values
        for lat_key, lon_key in cls.LATLON_KEYS:
            try:
                lat_data = data[lat_key][:]
                lon_data = data[lon_key][:]
            except KeyError:
                continue
            else:
                coords = empty((len(lon_data), 2))
                coords[:, 0] = lon_data
                coords[:, 1] = lat_data
                break
        else:
            # values not extracted assume global product
            coords = array([(-180.0, -90.0), (+180.0, +90.0)])

        return coords

    @classmethod
    def coords_to_bounding_box(cls, coords):
        coords = coords[~isnan(coords).any(1)]
        if coords.size:
            lon_min, lat_min = floor(coords.min(0))
            lon_max, lat_max = ceil(coords.max(0))
        else:
            lon_min, lat_min, lon_max, lat_max = -180, -90, 180, 90
        return (lon_min, lat_min, lon_max, lat_max)

    @classmethod
    def bounding_box_to_geometry(cls, bbox):
        return MultiPolygon(
            Polygon((
                (bbox[0], bbox[1]), (bbox[2], bbox[1]),
                (bbox[2], bbox[3]), (bbox[0], bbox[3]),
                (bbox[0], bbox[1]),
            ))
        )

    @classmethod
    def read(cls, data):
        # NOTE: For sake of simplicity we take geocentric (ITRF) coordinates
        #       as geodetic coordinates.
        begin_time, end_time, n_times = cls.get_time_range_and_size(data)
        coords = cls.get_coords(data)
        bbox = cls.coords_to_bounding_box(coords)
        footprint = cls.bounding_box_to_geometry(bbox)

        return {
            "format": "CDF",
            "size": (n_times, 0),
            "extent": bbox,
            "footprint": footprint,
            "begin_time": begin_time,
            "end_time": end_time,
        }
