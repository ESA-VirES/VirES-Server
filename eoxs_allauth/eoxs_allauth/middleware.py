#-------------------------------------------------------------------------------
#
#  Auxiliary middle-ware classes
#
# Project: EOxServer - django-allauth integration.
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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
# pylint: disable=missing-docstring, no-self-use, unused-argument

from logging import getLogger, INFO, WARNING

LOGGER = getLogger("eoxs_allauth.access")


class AccessLoggingMiddleware(object):
    """ Middleware that logs access to the service.

    This middleware makes use of the view attributes to decide the logging
    level of the authenticated and non-authenticated requests.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        """ Access logging. """
        if request.user.is_authenticated():
            type_, level = "A", getattr(view_func, 'log_level_auth', INFO)
        else:
            type_, level = "N", getattr(view_func, 'log_level_unauth', INFO)
        LOGGER.log(level, "%s %s %s", type_, request.method, request.path)

    def process_response(self, request, response):
        """ Log response status. """
        # Warn in case of an error.
        level = WARNING if response.status_code >= 400 else INFO
        LOGGER.log(
            level, "R %s %s %s %s ", request.method, request.path,
            response.status_code, response.reason_phrase,
        )
        return response
