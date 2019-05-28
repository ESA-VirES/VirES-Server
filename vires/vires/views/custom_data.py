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

import re
import json
import hashlib
from os import makedirs
from os.path import join, isdir
from logging import getLogger
from shutil import rmtree
from uuid import uuid4
from numpy import argmax, argmin
from django.conf import settings
from django.http import HttpResponse
from ..time_util import datetime, naive_to_utc, format_datetime
from ..cdf_util import cdf_open, CDF_EPOCH_TYPE, CDF_DOUBLE_TYPE, CDFError
from ..models import CustomDataset
from ..locked_file_access import log_append
from .exceptions import (
    InvalidFileFormat, HttpError400, HttpError404, HttpError405, HttpError413,
)
from .decorators import (
    set_extra_kwargs, handle_error, allow_methods,
    allow_content_length, reject_content,
)

RE_FILENAME = re.compile(r"^\w[\w.-]{0,254}$")
MAX_FILE_SIZE = 256 * 1024 * 1024 # 256 MiB size limit
MAX_PAYLOAD_SIZE = MAX_FILE_SIZE + 64 * 1024
EXTRA_KWASGS = {
    "logger": getLogger(__name__),
}
LOG_FILENAME = "change.log"


def get_upload_dir():
    """ Get upload directory. """
    return join(settings.VIRES_UPLOAD_DIR, "custom_data")


def log_change(change, identifier, timestamp=None):
    """ Log change to a change log. """
    filename = join(get_upload_dir(), LOG_FILENAME)

    if timestamp is None:
        timestamp = naive_to_utc(datetime.utcnow())

    log_append(filename, "%s %s %s" % (
        format_datetime(timestamp), identifier, change
    ))


@set_extra_kwargs(**EXTRA_KWASGS)
@handle_error
def custom_data(request, identifier=None, **kwargs):
    """ Custom data view. """
    if identifier:
        return custom_data_item(request, identifier, **kwargs)
    return custom_data_collection(request, **kwargs)


@allow_methods(["GET", "POST"])
def custom_data_collection(request, **kwargs):
    """ Custom data collection view. """
    if request.method == "GET":
        return list_collection(request, **kwargs)
    elif request.method == "POST":
        return post_item(request, **kwargs)
    raise HttpError405


@allow_methods(["GET", "DELETE"])
def custom_data_item(request, identifier, **kwargs):
    """ Custom data item view. """
    if request.method == "GET":
        return get_item(request, identifier, **kwargs)
    elif request.method == "DELETE":
        return delete_item(request, identifier, **kwargs)
    raise HttpError405


def model_to_infodict(obj):
    """ Convert DB object to a info dictionary. """
    return {
        "identifier": obj.identifier,
        "owner": obj.owner.username if obj.owner else None,
        "created": format_datetime(obj.created),
        "start": format_datetime(obj.start),
        "end": format_datetime(obj.end),
        "filename": obj.filename,
        "size": obj.size,
        "content_type": obj.content_type,
        "checksum": obj.checksum,
        "info": json.loads(obj.info) if obj.info else None,
    }


def check_input_file(path):
    """ File format check. """
    excluded_fields = {'Spacecraft'}
    mandatory_fields = [
        ("Timestamp", CDF_EPOCH_TYPE, 1),
        ("Latitude", CDF_DOUBLE_TYPE, 1),
        ("Longitude", CDF_DOUBLE_TYPE, 1),
    ]

    try:
        with cdf_open(path) as cdf:
            fields = {
                field: {
                    "shape": cdf[field].shape,
                    "cdf_type": int(cdf[field].type()),
                }
                for field in cdf
            }
    except CDFError as error:
        raise InvalidFileFormat(str(error))

    for name, type_, ndim in mandatory_fields:
        field = fields.get(name)
        if not field:
            raise InvalidFileFormat("Missing mandatory %s field!" % name)

        if field["cdf_type"] != int(type_):
            raise InvalidFileFormat("Invalid type of %s field!" % name)

        if len(field["shape"]) != ndim:
            raise InvalidFileFormat("Invalid dimension of %s field!" % name)

    size = fields["Timestamp"]["shape"][0]

    if size == 0:
        raise InvalidFileFormat("Empty dataset!")

    for name, field in fields.items():
        shape = field["shape"]
        if name in excluded_fields:
            del fields[name]
        elif len(shape) < 1 or shape[0] != size:
            del fields[name] # ignore fields with wrong dimension

    with cdf_open(path) as cdf:
        times = cdf.raw_var("Timestamp")[...]
        start = naive_to_utc(cdf["Timestamp"][argmin(times)])
        end = naive_to_utc(cdf["Timestamp"][argmax(times)])

    return "application/x-cdf", start, end, fields


@reject_content
def list_collection(request, **kwargs):
    """ List custom data collection. """
    owner = request.user if request.user.is_authenticated() else None
    data = json.dumps([
        model_to_infodict(dataset) for dataset in _get_models(owner)
    ])
    return HttpResponse(data, "application/json")


@reject_content
def get_item(request, identifier, **kwargs):
    """ Get info about the custom data."""
    owner = request.user if request.user.is_authenticated() else None
    dataset = _get_model(owner, identifier)
    data = json.dumps(model_to_infodict(dataset))
    return HttpResponse(data, "application/json")


@allow_content_length(MAX_PAYLOAD_SIZE)
def post_item(request, **kwargs):
    """ Post custom data. """
    # parse request
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        raise HttpError400("Invalid file upload request!")

    if uploaded_file.size > MAX_FILE_SIZE:
        raise HttpError413("Uploaded file too large!")

    if not RE_FILENAME.match(uploaded_file.name):
        raise HttpError400("Invalid filename!")

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
        except InvalidFileFormat as error:
            raise HttpError400(str(error))

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
        dataset.info = json.dumps(fields)

        data = json.dumps(model_to_infodict(dataset))

        with open(join(upload_dir, "info.json"), "wb") as file_:
            file_.write(data)

        log_change("CREATED", identifier, timestamp)

        dataset.save()

    except:
        rmtree(upload_dir, ignore_errors=True)
        raise

    _log_change(kwargs["logger"], "uploaded", owner, dataset)

    _delete_items(owner, kwargs["logger"], number_of_preserved=1)

    return HttpResponse(data, "application/json")


@reject_content
def delete_item(request, identifier, **kwargs):
    """ Delete custom data."""
    owner = request.user if request.user.is_authenticated() else None
    dataset = _get_model(owner, identifier)
    _delete_item(owner, dataset, kwargs["logger"])

    return HttpResponse(status=204)


def _delete_items(owner, logger, number_of_preserved=0):
    """ Batch dataset removal. """
    for dataset in _get_models(owner)[number_of_preserved:]:
        _delete_item(owner, dataset, logger)


def _delete_item(owner, dataset, logger):
    """ Low level item removal. """
    dataset.delete()

    upload_dir = join(get_upload_dir(), dataset.identifier)
    if isdir(upload_dir):
        rmtree(upload_dir, ignore_errors=True)

    log_change("REMOVED", dataset.identifier)

    _log_change(logger, "removed", owner, dataset)


def _get_models(owner):
    return CustomDataset.objects.filter(owner=owner).order_by("-created")


def _get_model(owner, identifier):
    try:
        return CustomDataset.objects.get(owner=owner, identifier=identifier)
    except CustomDataset.DoesNotExist:
        raise HttpError404


def _log_change(logger, action, owner, dataset):
    logger.info(
        "%s: custom file %s[%dB, %s] %s by %s",
        dataset.identifier, dataset.filename, dataset.size,
        dataset.content_type, action,
        owner.username if owner else "<anonymous-user>",
    )
