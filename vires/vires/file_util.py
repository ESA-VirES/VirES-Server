#-------------------------------------------------------------------------------
#
# various file utilities
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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

from errno import ENOENT
from os.path import getmtime


class FileChangeMonitor(object):
    """ File change monitor keeps track of the files' last modification times
    and can be queried if a file has been modified or not.
    """
    NO_FILE_MTIME = -float('inf')

    def __init__(self):
        self._mtimes = {}

    def changed(self, *filenames):
        """ Return True if any of the queried files has changed. """
        # Note: A list is used to make sure self.changed() is called for each
        #       filename. Lazy evaluation is not desired here.
        return any([self._changed(filename) for filename in filenames])

    def _changed(self, filename):
        """ Return True if the queried file has changed. """
        last_mtime = self._mtimes.get(filename)

        try:
            mtime = getmtime(filename)
        except OSError as error:
            if error.errno != ENOENT:
                raise
            mtime = self.NO_FILE_MTIME

        if last_mtime == mtime:
            return False

        self._mtimes[filename] = mtime
        return True
