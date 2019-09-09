#-------------------------------------------------------------------------------
#
# client state view
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

import json
from logging import getLogger
from uuid import uuid4
from django.http import HttpResponse
from ..time_util import datetime, naive_to_utc, format_datetime
from ..models import ClientState
from .exceptions import HttpError400, HttpError404, HttpError405, HttpError413
from .decorators import (
    set_extra_kwargs, handle_error, allow_methods, allow_content_type,
    allow_content_length, reject_content,
)

MAX_PAYLOAD_SIZE = 64 * 1024 # 64kB
EXTRA_KWASGS = {
    "logger": getLogger(__name__),
}


@set_extra_kwargs(**EXTRA_KWASGS)
@handle_error
def client_state(request, identifier=None, **kwargs):
    """ Custom data view. """
    if identifier:
        return client_state_item(request, identifier, **kwargs)
    return client_state_collection(request, **kwargs)


@allow_methods(["GET", "POST"])
def client_state_collection(request, **kwargs):
    """ Custom data collection view. """
    if request.method == "GET":
        return list_collection(request, **kwargs)
    elif request.method == "POST":
        return post_item(request, **kwargs)
    raise HttpError405


@allow_methods(["GET", "PATCH", "DELETE"])
def client_state_item(request, identifier, **kwargs):
    """ Custom data item view. """
    if request.method == "GET":
        return get_item(request, identifier, **kwargs)
    if request.method == "PATCH":
        return update_item(request, identifier, **kwargs)
    elif request.method == "DELETE":
        return delete_item(request, identifier, **kwargs)
    raise HttpError405


def model_to_infodict(obj, include_state=True):
    """ Convert DB object to a info dictionary. """
    data = {
        "identifier": obj.identifier,
        "owner": obj.owner.username if obj.owner else None,
        "created": format_datetime(obj.created),
        "updated": format_datetime(obj.updated),
        "name": obj.name,
        "description":  obj.description,
    }
    if include_state:
        data["state"] = json.loads(obj.state)
    return data


@reject_content
def list_collection(request, **kwargs):
    """ List client state collection. """
    owner = request.user if request.user.is_authenticated() else None
    data = json.dumps([
        model_to_infodict(state) for state in  _get_models(owner)
    ])
    return HttpResponse(data, "application/json")


@reject_content
def get_item(request, identifier, **kwargs):
    """ Get info about the client state."""
    owner = request.user if request.user.is_authenticated() else None
    state = _get_model(owner, identifier)
    data = json.dumps(model_to_infodict(state))
    return HttpResponse(data, "application/json")


@allow_content_length(MAX_PAYLOAD_SIZE)
@allow_content_type("application/json")
def post_item(request, **kwargs):
    """ Post client state. """
    # metadata
    owner = request.user if request.user.is_authenticated() else None
    timestamp = naive_to_utc(datetime.utcnow())
    identifier = str(uuid4()) # create a new random identifier

    # parse payload
    if len(request.body) > MAX_PAYLOAD_SIZE:
        raise HttpError413

    input_ = _parse_request(request.body)

    state = ClientState()
    state.owner = owner
    state.identifier = identifier
    state.created = timestamp
    state.updated = timestamp
    state.name = input_.get("name", format_datetime(timestamp))
    state.description = input_.get("description")
    state.state = json.dumps(input_["state"])
    data = json.dumps(model_to_infodict(state))
    state.save()

    _log_change(kwargs["logger"], "saved", owner, state)

    return HttpResponse(data, "application/json")


@reject_content
def delete_item(request, identifier, **kwargs):
    """ Delete client state."""
    owner = request.user if request.user.is_authenticated() else None
    state = _get_model(owner, identifier)
    state.delete()

    _log_change(kwargs["logger"], "deleted", owner, state)

    return HttpResponse(status=204)


@allow_content_length(MAX_PAYLOAD_SIZE)
@allow_content_type("application/json")
def update_item(request, identifier, **kwargs):
    """ Post client state. """
    # metadata
    owner = request.user if request.user.is_authenticated() else None
    state = _get_model(owner, identifier)
    input_ = _parse_request(request.body)

    if input_.get("name") is not None:
        state.name = input_["name"]

    if input_.get("description") is not None:
        state.description = input_["description"]

    if input_.get("state") is not None:
        state.state = json.dumps(input_["state"])

    data = json.dumps(model_to_infodict(state))
    state.save()

    _log_change(kwargs["logger"], "updated", owner, state)

    return HttpResponse(data, "application/json")


def _parse_request(data):
    try:
        return json.loads(data)
    except ValueError as error:
        raise HttpError400(str(error))


def _get_models(owner):
    return ClientState.objects.filter(owner=owner).order_by("-created")


def _get_model(owner, identifier):
    try:
        return ClientState.objects.get(owner=owner, identifier=identifier)
    except ClientState.DoesNotExist:
        raise HttpError404


def _log_change(logger, action, owner, state):
    logger.info(
        "%s: client state %s %s by %s",
        state.identifier, state.name, action,
        owner.username if owner else "<anonymous-user>",
    )
