#-------------------------------------------------------------------------------
#
# VirES HAPI output data formats
#
# https://github.com/hapi-server/data-specification/blob/master/hapi-3.0.0/HAPI-data-access-spec-3.0.0.md
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2021 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,unused-argument,too-few-public-methods

import os
import json
from io import TextIOWrapper, BytesIO, StringIO
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from ..formats.csv import arrays_to_csv
from ..formats.binary import cast_array_to_allowed_hapi_types, arrays_to_binary
from ..formats.json import arrays_to_json_fragment
from .common import HapiResponse

DEFAULT_DATA_RESPONSE_FORMAT = "csv"
DATA_RESPONSE_FORMATS = {}


def _register_format(handler):
    DATA_RESPONSE_FORMATS[handler.format] = handler


def get_data_formatter(format_):
    return DATA_RESPONSE_FORMATS[format_]


def parse_format(format_):
    if not format_:
        format_ = DEFAULT_DATA_RESPONSE_FORMAT
    if format_ not in DATA_RESPONSE_FORMATS:
        raise ValueError(f"Invalid data format {format_}!")
    return format_


def get_available_formats():
    return list(DATA_RESPONSE_FORMATS)


class HapiDataResponse():
    """ Base HAPI data response. """
    format = None
    header_prefix = None
    response_opts = None

    def __new__(cls, datasets, header=None):
        buffer_ = BytesIO()
        cls._write_response(buffer_, datasets, header)
        return HttpResponse(buffer_.getvalue(), **cls.response_opts)

    @classmethod
    def _write_response(cls, binary_file, datasets, header):
        raise NotImplementedError

    @classmethod
    def _write_data_header(cls, text_file, header):
        lines = StringIO(json.dumps(
            cls._get_json_response(header), cls=DjangoJSONEncoder, indent=2
        ))
        for line in lines:
            if cls.header_prefix:
                text_file.write(cls.header_prefix)
            text_file.write(line)
        text_file.write("\n")

    @classmethod
    def _get_json_response(cls, content):
        return {
            "HAPI": HapiResponse.VERSION,
            "status": HapiResponse.generate_status(
                *HapiResponse.STATUS_CODES[1200]
            ),
            "format": cls.format,
            **content,
        }


class CsvDataResponse(HapiDataResponse):
    """ CSV data response. """
    format = "csv"
    header_prefix = "#"
    response_opts = {
        "content_type": "text/csv",
        "charset": "utf-8",
    }

    @classmethod
    def _write_response(cls, binary_file, datasets, header):
        text_file = TextIOWrapper(binary_file, encoding="UTF-8", newline="\r\n")
        if header:
            cls._write_data_header(text_file, header)
        for dataset in datasets:
            arrays_to_csv(text_file, dataset.values())
        text_file.detach()

_register_format(CsvDataResponse)


class BinaryDataResponse(HapiDataResponse):
    """ Binary HAPI data response. """
    format = "binary"
    header_prefix = "#"
    response_opts = {
        "content_type": "application/octet-stream",
    }

    @classmethod
    def _write_response(cls, binary_file, datasets, header):
        if header:
            text_file = TextIOWrapper(binary_file, encoding="ascii", newline="\r\n")
            cls._write_data_header(text_file, header)
            text_file.detach()
        for dataset in datasets:
            arrays_to_binary(binary_file, cast_array_to_allowed_hapi_types(dataset.values()))

_register_format(BinaryDataResponse)


class XBinaryDataResponse(HapiDataResponse):
    """ Custom extended binary format HAPI response. """
    format = "x_binary"
    header_prefix = "#"
    response_opts = {
        "content_type": "application/octet-stream",
    }

    @classmethod
    def _write_response(cls, binary_file, datasets, header):
        if header:
            text_file = TextIOWrapper(binary_file, encoding="ascii", newline="\r\n")
            cls._write_data_header(text_file, header)
            text_file.detach()
        for dataset in datasets:
            arrays_to_binary(binary_file, dataset.values())

_register_format(XBinaryDataResponse)


class JsonDataResponse(HapiDataResponse):
    """ JSON HAPI data response. """
    format = "json"
    response_opts = {
        "content_type": "application/json",
    }

    @classmethod
    def _write_response(cls, binary_file, datasets, header):
        if not header:
            header = {}
        header["data"] = []
        text_file = TextIOWrapper(binary_file, encoding="ascii", newline="\r\n")
        cls._write_data_header(text_file, header)
        text_file.detach()

        # inject data records into the empty data list
        tail = cls._seek_backwards(binary_file, b"]")

        text_file = TextIOWrapper(binary_file, encoding="ascii", newline="\r\n")
        record_count = 0
        for dataset in datasets:
            record_count += dataset.length
            arrays_to_json_fragment(
                text_file, dataset.values(), prefix="\n", suffix=","
            )
        text_file.detach()

        if record_count > 0: # remove trailing comma if needed
            cls._seek_backwards(binary_file, b",")

        binary_file.write(tail)

    @classmethod
    def _seek_backwards(cls, file, searched):
        size = len(searched)
        position = file.seek(-size, os.SEEK_CUR)
        char = file.read(size)
        while position and char != searched:
            position = file.seek(-size - 1, os.SEEK_CUR)
            char = file.read(size)
        position = file.seek(-size, os.SEEK_CUR)
        tail = file.read()
        file.seek(position, os.SEEK_SET)
        return tail

_register_format(JsonDataResponse)
