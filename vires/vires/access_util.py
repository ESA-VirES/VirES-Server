#-------------------------------------------------------------------------------
#
#  Access logging Utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2017 EOX IT Services GmbH
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

from logging import LoggerAdapter


class AccessLoggerAdapter(LoggerAdapter):
    """ Logger adapter adding extra fields required by the access logger. """

    def __init__(self, logger, username=None, remote_addr=None, **kwargs):
        super().__init__(logger, {
            "remote_addr": remote_addr if remote_addr else "-",
            "username": username if username else "-",
        })


def get_remote_addr(request):
    """ Extract remote address from the Django HttpRequest """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.partition(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_user(request):
    """ Extract authenticated user from the Django HttpRequest
    or return None for unauthenticated user.
    """
    user = request.user
    return user if user and user.is_authenticated else None


def get_username(request):
    """ Extract username of the authenticated user from the Django HttpRequest
    or return None for unauthenticated user.
    """
    user = get_user(request)
    return user.username if user else None


def get_vires_permissions(request):
    """ Extract vires permissions of the authenticated user from the
    Django HttpRequest or return None for unauthenticated user.
    """
    user = get_user(request)
    return getattr(user, 'vires_permissions', None) if user else None
