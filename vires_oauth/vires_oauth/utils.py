#-------------------------------------------------------------------------------
#
#  Various utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring

from logging import LoggerAdapter
from django.utils.http import is_safe_url


def for_sender(classname):
    """ Decorator filtering signals by the sender. """
    def _for_sender(receiver_function):
        def _for_sender_wrapper(sender, *args, **kwargs):
            if issubclass(sender, classname):
                receiver_function(sender, *args, **kwargs)
        return _for_sender_wrapper
    return _for_sender


def strip_blanks(func):
    """ Decorator removing blank fields from the serialized objects """
    def _strip_blanks_(*args, **kwargs):
        return {
            key: value
            for key, value in func(*args, **kwargs).items()
            if value not in (None, "")
        }
    return _strip_blanks_



def decorate(decorators, function):
    """ Decorate `function` with one or more decorators. `decorators` can be
    a single decorator or an iterable of decorators.
    """
    if hasattr(decorators, '__iter__'):
        decorators = reversed(decorators)
    else:
        decorators = [decorators]
    for decorator in decorators:
        function = decorator(function)
    return function


def get_next_redirect_url(request, redirect_field='next', allowed_hosts=None):
    """ Get safe redirect URL from the request. """
    redirect_url = (
        request.POST.get(redirect_field) or request.GET.get(redirect_field)
    )
    if is_safe_url(redirect_url, allowed_hosts=allowed_hosts):
        return redirect_url
    return None


def get_remote_addr(request):
    """ Extract remote address from a request. """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.partition(',')[0]
    return request.META.get('REMOTE_ADDR')


class AccessLoggerAdapter(LoggerAdapter):
    """ Logger adapter adding extra fields required by the access logger. """

    def __init__(self, logger, request, user=None):
        user = user or request.user
        super().__init__(logger, {
            "remote_addr": get_remote_addr(request) if request else "-",
            "username": "-" if user.is_anonymous else user.username,
        })
