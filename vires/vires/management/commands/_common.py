#-------------------------------------------------------------------------------
#
# Common utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring

import sys
from logging import INFO, WARNING, ERROR

_LABEL2LOGLEVEL = {
    "INFO": INFO,
    "WARNING": WARNING,
    "ERROR": ERROR,
}


JSON_OPTS = {
    'sort_keys': False,
    'indent': 2,
    'separators': (',', ': '),
}


def datetime_to_string(dtobj):
    return dtobj if dtobj is None else dtobj.isoformat('T')


class ConsoleOutput():
    logger = None

    @classmethod
    def info(cls, message, *args, **kwargs):
        cls.print_message("INFO", message, *args, **kwargs)

    @classmethod
    def warning(cls, message, *args, **kwargs):
        cls.print_message("WARNING", message, *args, **kwargs)

    @classmethod
    def error(cls, message, *args, **kwargs):
        cls.print_message("ERROR", message, *args, **kwargs)

    @classmethod
    def print_message(cls, label, message, *args, **kwargs):
        print("%s: %s" % (label, message % args), file=sys.stderr)
        if kwargs.get('log') and cls.logger:
            cls.logger.log(_LABEL2LOGLEVEL[label], message, *args)
