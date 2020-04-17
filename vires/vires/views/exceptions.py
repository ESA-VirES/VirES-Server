#-------------------------------------------------------------------------------
#
# view exceptions
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
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

class HttpError(Exception):
    """ Simple HTTP error exception """
    def __init__(self, status, message, headers=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers or []

    def __str__(self):
        return self.message


class HttpError400(HttpError):
    """ 400 Bad Request exception. """
    def __init__(self, message=None, headers=None):
        super().__init__(400, message or "Bad request!", headers)


class HttpError404(HttpError):
    """ 404 Not Found exception. """
    def __init__(self, message=None, headers=None):
        super().__init__(404, message or "Not found!", headers)


class HttpError405(HttpError):
    """ 405 Method Not Allowed exception. """
    def __init__(self, message=None, headers=None):
        super().__init__(405, message or "Method not allowed!", headers)


class HttpError413(HttpError):
    """ 413 Payload Too Large exception. """
    def __init__(self, message=None, headers=None):
        super().__init__(413, message or "Payload too large!", headers)
