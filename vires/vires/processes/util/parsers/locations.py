#-------------------------------------------------------------------------------
#
#  Process Utilities - locations input parsers
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

from io import StringIO
from numpy import array
from eoxmagmod import EARTH_RADIUS
from eoxserver.services.ows.wps.parameters import AllowedRange
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError


EARTH_RADIUS_M = EARTH_RADIUS * 1e3 # mean Earth radius in meters


def _get_checking_parser(parse, allowed_values):
    """ Get parser function checking for allowed values. """
    def _parse(value):
        return allowed_values.verify(parse(value))
    return _parse


LOCATION_TYPE_DEFINITIONS = {
    'Latitude': _get_checking_parser(float, AllowedRange(-90., +90.)),
    'Longitude': _get_checking_parser(float, AllowedRange(-180., +180.)),
    'Radius': _get_checking_parser(
        float, AllowedRange(0.9*EARTH_RADIUS_M, 2.0*EARTH_RADIUS_M)
    ),
}


def parse_locations(input_id, mime_type, data):
    """ Parse locations. """
    try:
        return _parse_locations(mime_type, data)
    except ValueError as error:
        raise InvalidInputValueError(input_id, str(error))


def _parse_locations(mime_type, data):

    if mime_type == "text/csv":
        records = _parse_csv(
            StringIO(data),
            LOCATION_TYPE_DEFINITIONS,
            LOCATION_TYPE_DEFINITIONS,
        )
    else:
        raise ValueError("Unexpected mime type '%s'!" % mime_type)

    locations = []
    for location in records:
        locations.append((
            location['Latitude'],
            location['Longitude'],
            location['Radius'],
        ))

    return array(locations)


def _parse_csv(file, types, required_fields=None, delimiter=','):

    required_fields = set(required_fields or ())

    def _read_lines(lines):
        for line in lines:
            line = line.strip()
            if line:
                yield [
                    field.strip() for field in line.split(delimiter)
                ]

    lines = enumerate(_read_lines(file), 1)

    try:
        lineno, fields = next(lines)
    except StopIteration:
        return

    for missing_field in required_fields.difference(fields):
        raise ValueError(f"Missing required CSV field '{missing_field}'!")

    try:
        for lineno, values in lines:
            if len(fields) != len(values):
                raise ValueError("Wrong number of CSV fields!")
            yield {
                field: types.get(field, str)(value)
                for field, value in zip(fields, values)
            }
    except ValueError as error:
        raise ValueError(f"CSV input line #{lineno}: {error}")
