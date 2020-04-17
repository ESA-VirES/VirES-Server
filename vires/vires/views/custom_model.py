#-------------------------------------------------------------------------------
#
# model upload view
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
from django.conf import settings
from django.http import HttpResponse
from eoxmagmod import load_model_shc, decimal_year_to_mjd2000
from ..time_util import (
    datetime, naive_to_utc, mjd2000_to_datetime, format_datetime,
)
from ..models import CustomModel
from ..locked_file_access import log_append
from ..readers import InvalidFileFormat
from .exceptions import HttpError400, HttpError404, HttpError405, HttpError413
from .decorators import (
    set_extra_kwargs, handle_error, allow_methods,
    allow_content_length, reject_content,
)

MIN_MJD2000 = decimal_year_to_mjd2000(1.0)
MAX_MJD2000 = decimal_year_to_mjd2000(4000.0)

RE_FILENAME = re.compile(r"^\w[\w.-]{0,254}$")
MAX_FILE_SIZE = 16 * 1024 * 1024 # 16 MiB size limit
MAX_PAYLOAD_SIZE = MAX_FILE_SIZE + 64 * 1024
EXTRA_KWASGS = {
    "logger": getLogger(__name__),
}
LOG_FILENAME = "change.log"


def get_upload_dir():
    """ Get upload directory. """
    return join(settings.VIRES_UPLOAD_DIR, "custom_model")


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
def custom_model(request, identifier=None, **kwargs):
    """ Custom model view. """
    if identifier:
        return custom_model_item(request, identifier, **kwargs)
    return custom_model_collection(request, **kwargs)


@allow_methods(["GET", "POST"])
def custom_model_collection(request, **kwargs):
    """ Custom model collection view. """
    if request.method == "GET":
        return list_collection(request, **kwargs)
    if request.method == "POST":
        return post_item(request, **kwargs)
    raise HttpError405


@allow_methods(["GET", "DELETE"])
def custom_model_item(request, identifier, **kwargs):
    """ Custom model item view. """
    if request.method == "GET":
        return get_item(request, identifier, **kwargs)
    if request.method == "DELETE":
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
    def _mjd2000_to_utc(mjd2000):
        return naive_to_utc(mjd2000_to_datetime(
            max(MIN_MJD2000, min(MAX_MJD2000, mjd2000))
        ))

    try:
        with open(path) as file_:
            shc_model = load_model_shc(file_)
    except Exception as error:
        raise InvalidFileFormat('Not a valid SHC file!')

    parameters = {
        "min_degree": shc_model.min_degree,
        "max_degree": shc_model.degree,
    }

    start, end = (_mjd2000_to_utc(mjd2000) for mjd2000 in shc_model.validity)

    return "text/x-shc", start, end, parameters


@reject_content
def list_collection(request, **kwargs):
    """ List custom model collection. """
    owner = request.user if request.user.is_authenticated else None
    data = json.dumps([
        model_to_infodict(model) for model in _get_models(owner)
    ])
    return HttpResponse(data, "application/json")


@reject_content
def get_item(request, identifier, **kwargs):
    """ Get info about the custom model."""
    owner = request.user if request.user.is_authenticated else None
    model = _get_model(owner, identifier)
    data = json.dumps(model_to_infodict(model))
    return HttpResponse(data, "application/json")


@allow_content_length(MAX_PAYLOAD_SIZE)
def post_item(request, **kwargs):
    """ Post custom model. """
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
    owner = request.user if request.user.is_authenticated else None
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
            content_type, start, end, parameters = check_input_file(filename)
        except InvalidFileFormat as error:
            raise HttpError400(str(error))

        model = CustomModel()
        model.owner = owner
        model.created = timestamp
        model.start = start
        model.end = end
        model.identifier = identifier
        model.filename = basename
        model.location = filename
        model.size = size
        model.content_type = content_type
        model.checksum = md5.hexdigest()
        model.info = json.dumps(parameters)

        data = json.dumps(model_to_infodict(model))

        with open(join(upload_dir, "info.json"), "wb") as file_:
            file_.write(data)

        log_change("CREATED", identifier, timestamp)

        model.save()

    except:
        rmtree(upload_dir, ignore_errors=True)
        raise

    _log_change(kwargs["logger"], "uploaded", owner, model)

    _delete_items(owner, kwargs["logger"], number_of_preserved=1)

    return HttpResponse(data, "application/json")


@reject_content
def delete_item(request, identifier, **kwargs):
    """ Delete custom model."""
    owner = request.user if request.user.is_authenticated else None
    model = _get_model(owner, identifier)

    _delete_item(owner, model, kwargs["logger"])

    return HttpResponse(status=204)


def _delete_items(owner, logger, number_of_preserved=0):
    """ Batch model removal. """
    for model in _get_models(owner)[number_of_preserved:]:
        _delete_item(owner, model, logger)


def _delete_item(owner, model, logger):
    """ Low level item removal. """
    model.delete()

    upload_dir = join(get_upload_dir(), model.identifier)
    if isdir(upload_dir):
        rmtree(upload_dir, ignore_errors=True)

    log_change("REMOVED", model.identifier)

    _log_change(logger, "removed", owner, model)


def _get_models(owner):
    return CustomModel.objects.filter(owner=owner).order_by("-created")


def _get_model(owner, identifier):
    try:
        return CustomModel.objects.get(owner=owner, identifier=identifier)
    except CustomModel.DoesNotExist:
        raise HttpError404


def _log_change(logger, action, owner, model):
    logger.info(
        "%s: custom model %s[%dB, %s] %s by %s",
        model.identifier, model.filename, model.size,
        model.content_type, action,
        owner.username if owner else "<anonymous-user>",
    )
