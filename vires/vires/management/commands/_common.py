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
from logging import (
    getLogger, DEBUG, INFO, WARNING, ERROR,
    Formatter, StreamHandler,
)
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date, parse_datetime
from eoxserver.core.util.timetools import parse_duration
from vires.time_util import naive_to_utc


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


def time_spec(value):
    """ CLI time specification parser. """
    date_ = parse_date(value)
    if date_ is not None:
        return naive_to_utc(datetime.combine(date_, time()))
    datetime_ = parse_datetime(value)
    if datetime_ is not None:
        return naive_to_utc(datetime_)
    try:
        return naive_to_utc(datetime.utcnow() - abs(parse_duration(value)))
    except ValueError:
        pass
    raise ValueError("Invalid time specification '%s'." % value)


class ConsoleOutput():

    def info(self, message, *args):
        self.print_message("INFO", message, *args)

    def warning(self, message, *args):
        self.print_message("WARNING", message, *args)

    def error(self, message, *args):
        self.print_message("ERROR", message, *args)

    def print_message(self, label, message, *args):
        print("%s: %s" % (label, message % args), file=sys.stderr)


class Subcommand(ConsoleOutput):
    """ Base subcommand class """
    def __init__(self, logger=None):
        self.logger = logger
        self.log = False

    def add_arguments(self, parser):
        """ Add CLI arguments. """
        raise NotImplementedError

    def handle(self, **kwargs):
        """ Handle subcommand. """
        raise NotImplementedError


class Supercommand(ConsoleOutput, BaseCommand):
    """ Base class for Django command with subcommands. """

    commands = {}

    def add_arguments(self, parser):
        super().add_arguments(parser)

        subparsers = parser.add_subparsers(
            dest="command", metavar="<command>", #required=True,
        )

        for name, command in self.commands.items():
            subparser = subparsers.add_parser(name, help=command.help)
            subparser.description = getattr(command, "description", command.help)
            if hasattr(command, "formatter_class"):
                subparser.formatter_class = command.formatter_class
            command.add_arguments(subparser)

        # .add_subparsers() in Python < 3.7 does not support required parameter
        # and the attribute has to be set as an object property.
        subparsers.required = True

    def handle(self, *arg, **kwargs):
        self.set_stream_handler(kwargs['verbosity'])
        return self.commands[kwargs.pop('command')].handle(**kwargs)

    def set_stream_handler(self, verbosity):
        """ Set command stream handler for the given verbosity level. """
        if verbosity == 0:
            self._add_stream_handler(getLogger('vires'), WARNING)
        elif verbosity == 1:
            self._add_stream_handler(getLogger('vires'), INFO)
        elif verbosity == 2:
            self._add_stream_handler(getLogger('vires'), DEBUG)
        elif verbosity == 3:
            self._add_stream_handler(getLogger(), DEBUG)

    @staticmethod
    def _add_stream_handler(logger, level=DEBUG):
        """ Add stream handler to the given logger. """
        formatter = Formatter('%(levelname)s: %(message)s')
        handler = StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(min(level, logger.level))
