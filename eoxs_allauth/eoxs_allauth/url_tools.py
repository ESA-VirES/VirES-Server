#-------------------------------------------------------------------------------
#
#  Set of tools helping to handle URL resolvers.
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
# pylint: disable=missing-docstring

from types import ModuleType
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver

def decorate_pattern(pattern, decorator, pattern_filter=None):
    """ Generator decorating a URL pattern's callback by the given decorator if
    matched by the optional pattern_filter. If no filter provided the callback
    is decorated. The new or the same unchanged pattern is returned.
    The filter is a simple function receiving a pattern object and returning
    True or False.
    """
    if pattern_filter is None or pattern_filter(pattern):
        pattern = RegexURLPattern(
            pattern.regex.pattern,
            decorator(pattern.callback),
            pattern.default_args,
            pattern.name
        )
    return pattern


def decorate_resolver(resolver, decorator, pattern_filter=None):
    """ Generator decorating a URL pattern resolver's callback by the given
    decorator if matched by the optional pattern_filter.
    If no filter provided then all callbacks are decorated.
    New resolver instance is returned.
    The filter is a simple function receiving a pattern object and returning
    True or False.
    """
    return RegexURLResolver(
        resolver.regex.pattern,
        decorate(resolver.url_patterns, decorator, pattern_filter),
        resolver.default_kwargs,
        resolver.app_name,
        resolver.namespace
    )


def decorate(url_patterns, decorator, pattern_filter=None):
    """ Decorate the callbacks of the URL patterns with the provided
    decorator. The decorator can be applied to selected patterns matched by the
    optional pattern filter.
    The filter is a simple function receiving a pattern object and returning
    True or False.
    """
    def _decorate(pattern):
        """ Decorate one pattern """
        if isinstance(pattern, RegexURLPattern):
            return decorate_pattern(pattern, decorator, pattern_filter)
        elif isinstance(pattern, RegexURLResolver):
            return decorate_resolver(pattern, decorator, pattern_filter)
        else:
            raise ValueError("Unexpected pattern type %r!" % pattern)

    return [_decorate(pattern) for pattern in url_patterns]


def decorate_include(include, decorator, pattern_filter=None):
    """ Decorate the callbacks of the included URL pattern definition with
    the provided decorator. The decorator can be applied to selected patterns
    matched by the optional pattern filter.
    The filter is a simple function receiving a pattern object and returning
    True or False.
    """
    url_patterns, namespace, app_name = include
    if isinstance(url_patterns, ModuleType):
        url_patterns = url_patterns.urlpatterns
    return (
        decorate(url_patterns, decorator, pattern_filter), namespace, app_name
    )
