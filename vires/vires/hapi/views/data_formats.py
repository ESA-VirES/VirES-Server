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

import json
from logging import getLogger
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, StreamingHttpResponse
from ..formats.csv import arrays_to_csv
from ..formats.binary import arrays_to_hapi_binary, arrays_to_x_binary
from ..formats.json import arrays_to_json_fragment
from .common import HapiResponse, LOGGER_NAME

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
    header_prefix = ""
    response_opts = {}

    @classmethod
    def _collect_stats(cls, datasets, logger):
        """ Collect some info about the response and log it. """
        variables = None
        count = 0
        for dataset in datasets:
            count += dataset.length
            if not variables:
                variables = list(dataset)
            yield dataset
        if logger:
            logger.info(
                "response: count: %d samples, format: %s, mime-type: %s, "
                "parameters: (%s)",
                count, cls.format, cls.response_opts.get('content_type'),
                ", ".join(variables or ())
            )


    @classmethod
    def _generate_response(cls, datasets, header=None):
        raise NotImplementedError

    # streamed response
    def __new__(cls, request, datasets, header=None, **kwargs):
        #return cls._get_http_response(request, datasets, header, **kwargs)
        return cls._get_streaming_http_response(request, datasets, header, **kwargs)

    @classmethod
    def _get_http_response(cls, request, datasets, header=None, logger=None, **kwargs):
        del request
        return HttpResponse(
            cls._generate_response(cls._collect_stats(datasets, logger), header),
            **cls.response_opts
        )

    @classmethod
    def _get_streaming_http_response(cls, request, datasets, header=None, logger=None, **kwargs):

        def _handle_errors(chunks):
            try:
                yield from chunks
            except GeneratorExit:
                # streaming stopped before consuming all chunks - do nothing
                raise
            except:
                getLogger(LOGGER_NAME).error(
                    "An error occurred while streaming HAPI data response! %s",
                    request.get_full_path_info(),
                    exc_info=True
                )
                raise

        return StreamingHttpResponse(
            _handle_errors(
                cls._generate_response(
                    cls._collect_stats(datasets, logger), header
                ),
            ),
            **cls.response_opts
        )

    @classmethod
    def _get_data_header(cls, header):

        def _get_lines():
            lines = json.dumps(
                cls._get_json_response(header), cls=DjangoJSONEncoder, indent=2
            ).split("\n")
            for line in lines:
                yield f"{cls.header_prefix}{line}\r\n".encode("ASCII")

        return b"".join(_get_lines())

    @classmethod
    def _get_json_response(cls, content):
        return {
            "HAPI": HapiResponse.VERSION,
            "status": HapiResponse.generate_status(1200, "OK"),
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
    def _generate_response(cls, datasets, header=None):
        if header:
            yield cls._get_data_header(header)
        for dataset in datasets:
            yield arrays_to_csv(dataset.values())

_register_format(CsvDataResponse)


class JsonDataResponse(HapiDataResponse):
    """ JSON HAPI data response. """
    format = "json"
    response_opts = {
        "content_type": "application/json",
    }

    @classmethod
    def _generate_response(cls, datasets, header=None):
        body = cls._get_data_header({**(header or {}), "data": []})
        # insert records into the empty data array
        chunk, tail = cls._seek_backwards_and_split(body, b"]")
        record_count = 0
        for dataset in datasets:
            yield chunk
            record_count += dataset.length
            chunk = arrays_to_json_fragment(dataset.values())
        # remove trailing comma and close the JSON body
        if record_count > 0:
            chunk = chunk[:-1]
        yield chunk
        yield tail

    @classmethod
    def _seek_backwards_and_split(cls, buffer_, searched):
        idx = buffer_.rfind(searched)
        if idx < 0:
            idx = len(buffer_)
        return buffer_[:idx], buffer_[idx:]

_register_format(JsonDataResponse)


class BinaryDataResponse(HapiDataResponse):
    """ Binary HAPI data response. """
    format = "binary"
    header_prefix = "#"
    response_opts = {
        "content_type": "application/octet-stream",
    }

    @classmethod
    def _generate_response(cls, datasets, header=None):
        if header:
            yield cls._get_data_header(header)
        for dataset in datasets:
            yield arrays_to_hapi_binary(dataset.values())

_register_format(BinaryDataResponse)


class XBinaryDataResponse(HapiDataResponse):
    """ Custom extended binary format HAPI response. """
    format = "x_binary"
    header_prefix = "#"
    response_opts = {
        "content_type": "application/octet-stream",
    }

    @classmethod
    def _generate_response(cls, datasets, header=None):
        if header:
            yield cls._get_data_header(header)
        for dataset in datasets:
            yield arrays_to_x_binary(dataset.values())

_register_format(XBinaryDataResponse)
