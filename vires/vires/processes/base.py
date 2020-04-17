#-------------------------------------------------------------------------------
#
# Base VirES WPS process class
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

from logging import getLogger
from eoxserver.services.ows.wps.parameters import RequestParameter
from vires.util import cached_property
from vires.access_util import AccessLoggerAdapter, get_username, get_remote_addr


class WPSProcess():
    """ Process retrieving registered Swarm data based on collection, time
    interval and additional optional parameters.
    This precess is designed to be used by the web-client.
    """

    inputs = [
        ("username", RequestParameter(get_username)),
        ("remote_addr", RequestParameter(get_remote_addr)),
    ]

    def get_access_logger(self, *args, **kwargs):
        """ Get access logger wrapped by the AccessLoggerAdapter """
        return AccessLoggerAdapter(self._access_logger, *args, **kwargs)

    @cached_property
    def _access_logger(self):
        """ Get raw access logger. """
        return getLogger(
            "access.wps.%s" % self.__class__.__module__.split(".")[-1]
        )

    @cached_property
    def logger(self):
        """ Get an ordinary logger. """
        return getLogger(
            "vires.processes.%s" % self.__class__.__module__.split(".")[-1]
        )
