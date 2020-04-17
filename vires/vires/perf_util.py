#
# Performance measurement utilities.
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
# pylint: disable=too-few-public-methods,no-self-use

import sys
import logging
from .time_util import Timer

class ElapsedTimePrintBase():
    """ Print elapsed time - base class """
    format = "%s %.3gs"
    def __init__(self, message=""):
        self.timer = Timer()
        self.message = message

    def write(self, message):
        """ Print the message with the elapsed time appended. """
        raise NotImplementedError

    def __enter__(self):
        self.timer.reset()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.write(self.message)


class ElapsedTimePrint(ElapsedTimePrintBase):
    """ Print elapsed time."""

    def __init__(self, message="", output=sys.stdout):
        super().__init__(message)
        self.output = output

    def write(self, message):
        """ Print the message with the elapsed time appended. """
        print(self.format % (message, self.timer()), file=self.output)


class ElapsedTimeLogger(ElapsedTimePrintBase):
    """ Elapsed time logger. """

    def __init__(self, message="", logger=None, level=logging.INFO):
        super().__init__(message)
        self.logger = logger or logging.getLogger(__name__)
        self.level = level

    def write(self, message):
        """ Log the message with the elapsed time appended. """
        self.logger.log(self.level, self.format, message, self.timer())
