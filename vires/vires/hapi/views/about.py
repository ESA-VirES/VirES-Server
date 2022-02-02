#-------------------------------------------------------------------------------
#
# VirES HAPI - about view
#
# https://github.com/hapi-server/data-specification/blob/master/hapi-3.0.0/HAPI-data-access-spec-3.0.0.md
#
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

from django.conf import settings
from vires.views.decorators import allow_methods, reject_content
from .common import HapiResponse, catch_error, allowed_parameters

HAPI_ABOUT_DEFAULTS = {
    "id": "VirES",
    "title": "VirES for Swarm",
    "contact": "n/a",
}

HAPI_ABOUT = {}


@catch_error
@allow_methods(['GET'])
@reject_content
@allowed_parameters()
def about(request):
    if not HAPI_ABOUT:
        HAPI_ABOUT.update(_generate_about_payload(
            getattr(settings, "HAPI_ABOUT", {})
        ))
    return HapiResponse(HAPI_ABOUT)


def _generate_about_payload(extra_settings):
    return {
        **HAPI_ABOUT_DEFAULTS,
        **{
            key: extra_settings[key]
            for key in [
                "id",
                "title",
                "description",
                "contact",
                "contactID",
                "citation",
            ] if extra_settings.get(key)
        },
    }
