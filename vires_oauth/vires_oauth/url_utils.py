#-------------------------------------------------------------------------------
#
#  URL utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

from django.urls.resolvers import URLResolver, URLPattern


def decorate_views(decorator, items):
    """ Decorate views from URL patterns. """
    for item in items:
        item.callback = decorator(item.callback)


def name_filter(*names):
    """ Name filter predicate. """
    names = set(names)
    def _name_filter(item):
        return item.name in names
    return _name_filter


def filter_urls(items, predicate):
    """ Filter URL patterns by the given predicate. """
    for item in items:
        if predicate(item):
            yield item


def iter_ulr_patterns(item):
    """ Recursively iterate URL resolvers. """

    def _iterate(items):
        for item in items:
            yield from iter_ulr_patterns(item)

    if isinstance(item, URLPattern):
        yield item

    elif isinstance(item, URLResolver):
        yield from _iterate(item.url_patterns)

    elif isinstance(item, list):
        yield from _iterate(item)
    else:
        raise TypeError(f"Unexpected input type! {type(item)}")
