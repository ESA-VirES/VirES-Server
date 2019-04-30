#-------------------------------------------------------------------------------
#
# data upload view
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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
# pylint: disable=unused-import, unused-argument, unused-variable

import re
import json
import hashlib
from os import makedirs
from os.path import join, exists, isdir
from logging import getLogger
from shutil import rmtree
from glob import glob
from uuid import uuid4
from numpy import argmax, argmin
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from ..time_util import datetime, naive_to_utc
from ..cdf_util import cdf_open, CDF_EPOCH_TYPE, CDF_DOUBLE_TYPE, CDFError
from ..models import CustomDataset
from .exceptions import HttpError
from .decorators import (
    set_extra_kwargs,
    handle_error,
    allow_methods,
    allow_content_types,
    allow_content_length,
    reject_content,
)

RE_FILENAME = re.compile(r"^\w[\w.-]{0,254}$")
MAX_FILE_SIZE = 256 * 1024 * 1024 # 256 MiB size limit
MAX_PAYLOAD_SIZE = MAX_FILE_SIZE + 64 * 1024
EXTRA_KWASGS = {
    "logger": getLogger(__name__),
}


def get_upload_dir():
    """ Get upload directory. """
    return settings.VIRES_UPLOAD_DIR


@set_extra_kwargs(**EXTRA_KWASGS)
@handle_error
@allow_methods(["GET", "POST"])
def custom_data_collection(request, **kwargs):
    """ Custom data collection view. """
    if request.method == "GET":
        return list_collection(request, **kwargs)
    elif request.method == "POST":
        return post_item(request, **kwargs)
    raise HttpError(405, "Method not allowed")


@set_extra_kwargs(**EXTRA_KWASGS)
@handle_error
@allow_methods(["GET", "DELETE"])
def custom_data_item(request, identifier, **kwargs):
    """ Custom data item view. """
    if request.method == "GET":
        return get_item(request, identifier, **kwargs)
    elif request.method == "DELETE":
        return delete_item(request, identifier, **kwargs)
    raise HttpError(405, "Method not allowed")


def model_to_infodict(obj, user=None):
    """ Convert DB object to a info dictionary. """
    return {
        "identifier": obj.identifier,
        "owner": obj.owner.username if obj.owner else None,
        "created": obj.created.isoformat("T"),
        "start": obj.start.isoformat("T"),
        "end": obj.end.isoformat("T"),
        "filename": obj.filename,
        "size": obj.size,
        "content_type": obj.content_type,
        "checksum": obj.checksum,
        "info": json.loads(obj.info) if obj.info else None,
    }


class InvalidDataFormatError(Exception):
    """ Invalid data format error. """
    pass


def check_input_file(path):
    """ File format check. """
    mandatory_fields = [
        ('Timestamp', CDF_EPOCH_TYPE, 1),
        ('Latitude', CDF_DOUBLE_TYPE, 1),
        ('Longitude', CDF_DOUBLE_TYPE, 1),
    ]

    try:
        with cdf_open(path) as cdf:
            fields = {
                field: {
                    'shape': cdf[field].shape,
                    'cdf_type': int(cdf[field].type()),
                }
                for field in cdf
            }
    except CDFError as error:
        raise InvalidDataFormatError(str(error))

    for name, type_, ndim in mandatory_fields:
        field = fields.get(name)
        if not field:
            raise InvalidDataFormatError("Missing mandatory %s field!" % name)

        if field['cdf_type'] != int(type_):
            raise InvalidDataFormatError("Invalid type of %s field!" % name)

        if len(field['shape']) != ndim:
            raise InvalidDataFormatError("Invalid dimension of %s field!" % name)

    size = fields['Timestamp']['shape'][0]

    if size == 0:
        raise InvalidDataFormatError("Empty dataset!")

    for name, field in fields.items():
        shape = field['shape']
        if len(shape) < 1 or shape[0] != size:
            raise InvalidDataFormatError("Invalid dimension of %s field!" % name)

    with cdf_open(path) as cdf:
        times = cdf.raw_var('Timestamp')[...]
        start = naive_to_utc(cdf['Timestamp'][argmin(times)])
        end = naive_to_utc(cdf['Timestamp'][argmax(times)])

    return "application/x-cdf", start, end, fields


@reject_content
def list_collection(request, **kwargs):
    """ List custom data collection. """
    owner = request.user if request.user.is_authenticated() else None
    query_set = CustomDataset.objects.filter(owner=owner).order_by('-created')
    data = json.dumps([model_to_infodict(dataset) for dataset in query_set])
    return HttpResponse(data, content_type="application/json", status=200)


@reject_content
def get_item(request, identifier, **kwargs):
    """ Get info about the custom data."""
    owner = request.user if request.user.is_authenticated() else None
    try:
        dataset = CustomDataset.objects.get(owner=owner, identifier=identifier)
    except CustomDataset.DoesNotExist:
        raise HttpError(404, "Not found!")
    data = json.dumps(model_to_infodict(dataset))
    return HttpResponse(data, content_type="application/json", status=200)


@allow_content_length(MAX_PAYLOAD_SIZE)
def post_item(request, **kwargs):
    """ Post custom data. """
    # parse request
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        raise HttpError(400, "Invalid file upload request!")

    if uploaded_file.size > MAX_FILE_SIZE:
        raise HttpError(413, "Uploaded file too large!")

    if not RE_FILENAME.match(uploaded_file.name):
        raise HttpError(400, "Invalid filename!")

    # metadata
    timestamp = naive_to_utc(datetime.utcnow())
    identifier = str(uuid4()) # create a new random identifier
    basename = uploaded_file.name
    size = uploaded_file.size

    # create upload directory and save the uploaded file
    owner = request.user if request.user.is_authenticated() else None
    upload_dir = join(get_upload_dir(), identifier)
    filename = join(upload_dir, basename)
    makedirs(upload_dir)
    try:
        with open(filename, "wb") as file_:
            md5 = hashlib.md5()
            for chunk in uploaded_file.chunks():
                file_.write(chunk)
                md5.update(chunk)

        # check the input data
        try:
            content_type, start, end, fields = check_input_file(filename)
        except InvalidDataFormatError as error:
            raise HttpError(400, str(error))

        dataset = CustomDataset()
        dataset.owner = owner
        dataset.created = timestamp
        dataset.start = start
        dataset.end = end
        dataset.identifier = identifier
        dataset.filename = basename
        dataset.location = filename
        dataset.size = size
        dataset.content_type = content_type
        dataset.checksum = md5.hexdigest()

        data = json.dumps(model_to_infodict(dataset))

        with open(join(upload_dir, "info.json"), "wb") as file_:
            file_.write(data)

        dataset.save()

    except:
        rmtree(upload_dir, ignore_errors=True)
        raise

    kwargs['logger'].info(
        "%s: custom file %s[%dB, %s] uploaded by %s",
        dataset.identifier, dataset.filename, dataset.size,
        dataset.content_type, owner.username if owner else "<anonymous-user>",
    )

    _delete_items(owner, kwargs['logger'], number_of_preserved=1)

    return HttpResponse(data, content_type="application/json", status=200)


@reject_content
def delete_item(request, identifier, **kwargs):
    """ Delete custom data."""
    owner = request.user if request.user.is_authenticated() else None
    try:
        dataset = CustomDataset.objects.get(owner=owner, identifier=identifier)
    except CustomDataset.DoesNotExist:
        raise HttpError(404, "Not found!")

    _delete_item(owner, dataset, kwargs['logger'])

    return HttpResponse(status=204)


def _delete_items(owner, logger, number_of_preserved=0):
    """ Batch dataset removal. """
    query_set = CustomDataset.objects.filter(owner=owner).order_by('-created')
    for dataset in query_set[number_of_preserved:]:
        _delete_item(owner, dataset, logger)


def _delete_item(owner, dataset, logger):
    """ Low level item removal. """
    dataset.delete()

    upload_dir = join(get_upload_dir(), dataset.identifier)
    if isdir(upload_dir):
        rmtree(upload_dir, ignore_errors=True)

    logger.info(
        "%s: custom file %s[%dB, %s] removed by %s",
        dataset.identifier, dataset.filename, dataset.size,
        dataset.content_type, owner.username if owner else "<anonymous-user>",
    )
