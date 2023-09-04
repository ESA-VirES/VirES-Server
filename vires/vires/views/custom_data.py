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
#pylint: disable=unused-argument,too-many-locals

import re
import json
import hashlib
from os import makedirs, remove
from os.path import join, isdir, basename
from logging import getLogger
from shutil import rmtree
from uuid import uuid4
from numpy import argmax, argmin, datetime64, asarray
from django.conf import settings
from django.http import HttpResponse
from ..time_util import datetime, naive_to_utc, format_datetime, Timer
from ..cdf_util import (
    is_cdf_file, cdf_open, convert_cdf_raw_times, CDFError,
    CDF_EPOCH_TYPE, CDF_EPOCH16_TYPE, CDF_TIME_TT2000_TYPE, CDF_DOUBLE_TYPE,
    CDF_REAL8_TYPE, CDF_TYPE_TO_LABEL, LABEL_TO_CDF_TYPE, CDF_TYPE_TO_DTYPE,
)
from ..cdf_write_util import (
    cdf_add_variable, cdf_assert_backward_compatible_dtype
)
from ..models import CustomDataset
from ..locked_file_access import log_append
from ..readers import (
    InvalidFileFormat, read_csv_data, reduce_int_type, sanitize_custom_data,
)
from .exceptions import HttpError400, HttpError404, HttpError405, HttpError413
from .decorators import (
    set_extra_kwargs, handle_error, allow_methods,
    allow_content_type, allow_content_length, reject_content,
)

DAYS2MS = 1000 * 60 * 60 * 24
DATETIME64_MS_2000 = datetime64("2000-01-01", "ms")

RE_FILENAME = re.compile(r"^\w[\w.-]{0,254}$")
MAX_FILE_SIZE = 256 * 1024 * 1024 # 256 MiB size limit
MAX_POST_PAYLOAD_SIZE = MAX_FILE_SIZE + 64 * 1024
MAX_UPDATE_PAYLOAD_SIZE = 64 * 1024
EXTRA_KWASGS = {
    "logger": getLogger(__name__),
}
CHANGE_LOG_FILENAME = "change.log"

EXCLUDED_FIELDS = {'Spacecraft'}
MANDATORY_FIELDS = [
    ("Timestamp", (CDF_EPOCH_TYPE,), ()),
    ("Latitude", (CDF_DOUBLE_TYPE, CDF_REAL8_TYPE), ()),
    ("Longitude", (CDF_DOUBLE_TYPE, CDF_REAL8_TYPE), ()),
]
EXPECTED_FIELDS = [
    ("Radius", (CDF_DOUBLE_TYPE, CDF_REAL8_TYPE), ()),
    ("F", (CDF_DOUBLE_TYPE, CDF_REAL8_TYPE), ()),
    ("B_NEC", (CDF_DOUBLE_TYPE, CDF_REAL8_TYPE), (3,)),
]


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
    if request.method == "POST":
        return post_item(request, **kwargs)
    raise HttpError405


@allow_methods(["GET", "PUT", "PATCH", "DELETE"])
def custom_data_item(request, identifier, **kwargs):
    """ Custom data item view. """
    if request.method == "GET":
        return get_item(request, identifier, **kwargs)
    if request.method in ("PUT", "PATCH"):
        return update_item(request, identifier, **kwargs)
    if request.method == "DELETE":
        return delete_item(request, identifier, **kwargs)
    raise HttpError405


def model_to_infodict(obj):
    """ Convert DB object to a info dictionary. """
    info = sanitize_info(json.loads(obj.info)) if obj.info else {}
    info.update({
        "identifier": obj.identifier,
        "owner": obj.owner.username if obj.owner else None,
        "is_valid": obj.is_valid,
        "created": format_datetime(obj.created),
        "start": format_datetime(obj.start),
        "end": format_datetime(obj.end),
        "filename": obj.filename,
        "data_file": basename(obj.location),
        "size": obj.size,
        "content_type": obj.content_type,
        "checksum": obj.checksum,
    })
    return info


def sanitize_info(info):
    """ Sanitize model info dictionary. """
    if not isinstance(info, dict):
        return info

    if "fields" not in info:
        # old info version
        info = {
            "size": info["Timestamp"]["shape"][0],
            "source_fields": list(info),
            "fields": {
                name: {
                    "shape": field["shape"][1:],
                    "cdf_type": field["cdf_type"],
                    "data_type": CDF_TYPE_TO_LABEL[field["cdf_type"]],
                } for name, field in info.items()
            }
        }

    if "missing_fields" not in info:
        info["missing_fields"] = {}

    if "constant_fields" not in info:
        info["constant_fields"] = {}

    return info


@reject_content
def list_collection(request, **kwargs):
    """ List custom data collection. """
    owner = request.user if request.user.is_authenticated else None
    data = json.dumps([
        model_to_infodict(dataset) for dataset in _get_models(owner)
    ])
    return HttpResponse(data, "application/json")


@reject_content
def get_item(request, identifier, **kwargs):
    """ Get info about the custom data."""
    owner = request.user if request.user.is_authenticated else None
    dataset = _get_model(owner, identifier)
    data = json.dumps(model_to_infodict(dataset))
    return HttpResponse(data, "application/json")


@allow_content_type("multipart/form-data")
@allow_content_length(MAX_POST_PAYLOAD_SIZE)
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
    base_name = uploaded_file.name
    size = uploaded_file.size

    # create upload directory and save the uploaded file
    owner = request.user if request.user.is_authenticated else None
    upload_dir = join(get_upload_dir(), identifier)
    filename = join(upload_dir, base_name)
    makedirs(upload_dir)
    try:
        timer = Timer()

        with open(filename, "wb") as file_:
            md5 = hashlib.md5()
            for chunk in uploaded_file.chunks():
                file_.write(chunk)
                md5.update(chunk)

        # process input data and extract information
        try:
            (
                content_type, start, end, fields_info, datafile,
            ) = process_input_file(filename)
        except InvalidFileFormat as error:
            raise HttpError400(str(error))

        kwargs["logger"].info(
            "%s: %s[%dB, %s] processed in %.3gs",
            identifier, base_name, size, content_type, timer()
        )

        dataset = CustomDataset()
        dataset.is_valid = not fields_info["missing_fields"]
        dataset.owner = owner
        dataset.created = timestamp
        dataset.start = start
        dataset.end = end
        dataset.identifier = identifier
        dataset.filename = base_name
        dataset.location = datafile
        dataset.size = size
        dataset.content_type = content_type
        dataset.checksum = md5.hexdigest()
        dataset.info = json.dumps(fields_info)

        data = json.dumps(model_to_infodict(dataset))

        with open(join(upload_dir, "info.json"), "w") as file_:
            file_.write(data)

        update_change_log("CREATED", identifier, timestamp)

        dataset.save()

    except:
        rmtree(upload_dir, ignore_errors=True)
        raise

    _log_action(kwargs["logger"], "uploaded", owner, dataset)

    _delete_items(owner, kwargs["logger"], number_of_preserved=1)

    return HttpResponse(data, "application/json")


@allow_content_type("application/json")
@allow_content_length(MAX_UPDATE_PAYLOAD_SIZE)
def update_item(request, identifier, **kwargs):
    """ Update custom dataset. """
    owner = request.user if request.user.is_authenticated else None
    dataset = _get_model(owner, identifier)

    fields_info = json.loads(dataset.info)
    try:
        parsed_request = json.loads(request.body)
        fields_info = update_field_info(fields_info, parsed_request)
    except (ValueError, InvalidFileFormat):
        raise HttpError400("Invalid update request!")

    dataset.is_valid = not fields_info["missing_fields"]
    dataset.info = json.dumps(fields_info)

    data = json.dumps(model_to_infodict(dataset))

    _save_constant_variables(dataset.location, fields_info['constant_fields'])

    upload_dir = join(get_upload_dir(), identifier)
    with open(join(upload_dir, "info.json"), "w") as file_:
        file_.write(data)

    update_change_log("UPDATED", identifier)

    dataset.save()

    _log_action(kwargs["logger"], "updated", owner, dataset)

    return HttpResponse(data, "application/json")


@reject_content
def delete_item(request, identifier, **kwargs):
    """ Delete custom data."""
    owner = request.user if request.user.is_authenticated else None
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

    update_change_log("REMOVED", dataset.identifier)

    _log_action(logger, "removed", owner, dataset)


def _get_models(owner):
    return CustomDataset.objects.filter(owner=owner).order_by("-created")


def _get_model(owner, identifier):
    try:
        return CustomDataset.objects.get(owner=owner, identifier=identifier)
    except CustomDataset.DoesNotExist:
        raise HttpError404


def _log_action(logger, action, owner, dataset):
    logger.info(
        "%s: %s[%dB, %s] %s by %s",
        dataset.identifier, dataset.filename, dataset.size,
        dataset.content_type, action,
        owner.username if owner else "<anonymous-user>",
    )


def get_upload_dir():
    """ Get upload directory. """
    return join(settings.VIRES_UPLOAD_DIR, "custom_data")


def update_change_log(change, identifier, timestamp=None):
    """ Log change to a change log. """
    filename = join(get_upload_dir(), CHANGE_LOG_FILENAME)

    if timestamp is None:
        timestamp = naive_to_utc(datetime.utcnow())

    log_append(filename, "%s %s %s" % (
        format_datetime(timestamp), identifier, change
    ))


def update_field_info(info, update):
    """ Update field info dictionary. """
    info = sanitize_info(info)

    # strip extra fields
    fields = info['fields']
    fields = {name: fields[name] for name in info['source_fields']}

    # process constant fields
    constant_fields = {
        name: _parse_input_constant_field(field)
        for name, field in update.get('constant_fields', {}).items()
        if name not in fields
    }

    for name, _, _ in MANDATORY_FIELDS:
        field = constant_fields.get(name)
        if field:
            field['required'] = True

    for name, field in constant_fields.items():
        fields[name] = field = dict(field)
        del field['value']

    info.update({
        "fields": fields,
        "missing_fields": _get_missing_fields(fields),
        "constant_fields": constant_fields,
    })

    return info


def _parse_input_constant_field(field):
    """ Parse input constant field dictionary. """
    cdf_type = (
        field.get("cdf_type") or
        LABEL_TO_CDF_TYPE.get(field.get("data_type", "CDF_DOUBLE"))
    )
    data_type = CDF_TYPE_TO_LABEL.get(cdf_type)
    if cdf_type is None or data_type is None:
        raise ValueError("Invalid field data type.")

    source_value = field.get('value')
    if source_value is None:
        raise ValueError("Missing field value!")

    try:
        parsed_value = asarray(source_value, CDF_TYPE_TO_DTYPE[cdf_type])
    except (ValueError, TypeError):
        raise ValueError("Invalid field value!")

    try:
        shape = tuple(field.get('shape', parsed_value.shape))
    except TypeError:
        raise ValueError("Invalid field shape!")

    if shape != parsed_value.shape:
        raise ValueError("Invalid field value shape!")

    return {
        "value": source_value,
        "shape": shape,
        "cdf_type": cdf_type,
        "data_type": data_type,
    }


def process_input_file(path):
    """ Process input file and extract information. """
    try:
        if is_cdf_file(path):
            format_ = "CDF"
            mime_type, cdf_file = _convert_input_cdf(path)
        else:
            format_ = "CSV"
            mime_type, cdf_file = _convert_input_csv(path)
    except InvalidFileFormat as error:
        raise InvalidFileFormat("Invalid %s file! %s" % (format_, error))

    start, end, fields_info = process_input_cdf(cdf_file)

    return mime_type, start, end, fields_info, cdf_file


def process_input_cdf(path):
    """ Process input CDF file and extract metadata. """
    try:
        with cdf_open(path) as cdf:
            fields = {
                field: {
                    "shape": cdf[field].shape,
                    "cdf_type": int(cdf[field].type()),
                } for field in cdf
            }
    except CDFError as error:
        raise InvalidFileFormat(str(error))

    if "Timestamp" not in fields:
        raise InvalidFileFormat("Missing mandatory Timestamp field!")

    timestamp_shape = fields["Timestamp"]["shape"]
    size = timestamp_shape[0]

    if len(timestamp_shape) != 1:
        raise InvalidFileFormat("Invalid dimension of Timestamp field!")

    if size == 0:
        raise InvalidFileFormat("Empty dataset!")

    for name, field in list(fields.items()):
        shape = field["shape"]
        if name in EXCLUDED_FIELDS:
            del fields[name]
        elif len(shape) < 1 or shape[0] != size:
            del fields[name] # ignore fields with wrong dimension
        else:
            field["shape"] = shape[1:]
            field["data_type"] = CDF_TYPE_TO_LABEL[field['cdf_type']]

    with cdf_open(path) as cdf:
        times = cdf.raw_var("Timestamp")[...]
        start = naive_to_utc(cdf["Timestamp"][argmin(times)])
        end = naive_to_utc(cdf["Timestamp"][argmax(times)])

    return start, end, {
        "size": size,
        "fields": fields,
        "source_fields": list(fields),
        "missing_fields": _get_missing_fields(fields),
        "constant_fields": {},
    }


def _get_missing_fields(fields):
    missing_fields = {}

    def _check_field(name, types, shape, is_mandatory):
        types = list(map(int, types))
        field = fields.get(name)
        if not field:
            if is_mandatory:
                missing_fields[name] = {
                    "shape": shape,
                    "cdf_type": types[0],
                    "data_type": CDF_TYPE_TO_LABEL[types[0]],
                }
            return

        if field["cdf_type"] not in types:
            raise InvalidFileFormat("Invalid type of %s field!" % name)

        if len(field["shape"]) != len(shape):
            raise InvalidFileFormat("Invalid dimension of %s field!" % name)

        if tuple(field["shape"]) != shape:
            raise InvalidFileFormat("Invalid shape of %s field!" % name)


    for name, types, shape in MANDATORY_FIELDS:
        _check_field(name, types, shape, True)

    for name, types, shape in EXPECTED_FIELDS:
        _check_field(name, types, shape, False)

    return missing_fields


def _convert_input_cdf(filename):
    """ Make sure the input is in the CDF format. """
    try:
        with cdf_open(filename, 'w') as cdf:
            _convert_time_variables_to_cdf_epoch(cdf)
    except CDFError as error:
        raise InvalidFileFormat(str(error))
    return "application/x-cdf", filename


def _convert_time_variables_to_cdf_epoch(cdf):
    """ Convert CDF EPOCH16 and TT2000 variables in CDF EPOCH. """
    converted_time_types = {CDF_EPOCH16_TYPE, CDF_TIME_TT2000_TYPE}

    for variable in cdf:
        raw_var = cdf.raw_var(variable)
        if raw_var.type() not in converted_time_types:
            continue
        data = convert_cdf_raw_times(raw_var[...], raw_var.type(), CDF_EPOCH)
        attributes = raw_var.attrs
        compress, compress_param = raw_var.compress()
        del cdf[variable]
        cdf.new(
            variable, data=data, type=CDF_EPOCH_TYPE, dims=data.shape[1:],
            compress=compress, compress_param=compress_param,
        )
        cdf[variable].attrs = attributes



def _convert_input_csv(path):
    """ Convert input CSV file to CDF format. """

    data = sanitize_custom_data({
        variable: reduce_int_type(values)
        for variable, values in read_csv_data(path).items()
    })

    cdf_file = path + ".cdf"

    try:
        _save_dataset_to_cdf(cdf_file, data)
    except (CDFError, TypeError, ValueError) as error:
        raise InvalidFileFormat(str(error))

    remove(path)

    return "text/csv", cdf_file


def _save_dataset_to_cdf(filename, dataset):
    """ Save dataset to a CDF file. """
    with cdf_open(filename, "w") as cdf:
        for variable, data in dataset.items():
            cdf_assert_backward_compatible_dtype(data)
            cdf_add_variable(cdf, variable, data)


def _save_constant_variables(filename, constant_fields):
    """ Save constant fields as CDF NRV variables. """
    with cdf_open(filename, "w") as cdf:
        for name, field in constant_fields.items():
            if name in cdf:
                del cdf[name]
            cdf_type = field['cdf_type']
            value = asarray(field['value'], CDF_TYPE_TO_DTYPE[cdf_type])
            cdf.new(
                name, recVary=False, type=cdf_type, data=value, dims=value.shape
            )
