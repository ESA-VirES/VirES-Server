#-------------------------------------------------------------------------------
#
#  Data URL parsing
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
# pylint: disable=missing-docstring

import re
import codecs
import base64

RE_WHITESPACE = re.compile(r"\s+")
RE_DATA_URL = re.compile(r"data:(?P<mediatype>[^,]*),(?P<data>.*)")


class DataUrl():
    """ Parsed Data URL class. """

    def __init__(self, data, content_type, type_parameters):
        self.data = data
        self.content_type = content_type
        self.type_parameters = type_parameters


def parse_data_url(url, encoding=None):
    match = RE_DATA_URL.match(url)
    if match is None:
        raise ValueError("Not a valid data URL!")

    content_type, parameters = _parse_media_type(match['mediatype'])
    data = match['data']
    if parameters.pop('base64', False):
        data = base64.standard_b64decode(data)
        charset = parameters.pop('charset', None)
        if charset:
            encoding = _charset_to_codec(charset)
        if encoding:
            data = data.decode(encoding)

    return DataUrl(data, content_type, parameters)


def _parse_media_type(media_type):
    mime_type, *params = RE_WHITESPACE.sub("", media_type).lower().split(';')

    param_dict = {}
    if params and params[-1] == "base64":
        param_dict["base64"] = True

    for param in params:
        key, separator, value = param.partition("=")
        if key and separator and value:
            param_dict[key] = value

    return mime_type or None, param_dict


def _charset_to_codec(charset):

    def _lookup_codec(name):
        codecs.lookup(name)
        return name

    try:
        return _lookup_codec(charset)
    except LookupError:
        pass

    try:
        return _lookup_codec(charset.replace('-', ''))
    except LookupError:
        pass

    raise ValueError("Unsupported charset!")
