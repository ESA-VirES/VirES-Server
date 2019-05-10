#-------------------------------------------------------------------------------
#
# locked file access
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

from fcntl import flock, LOCK_EX, LOCK_NB
from errno import EAGAIN
from time import sleep

class FileIsLocked(Exception):
    """ Locked file exception. """
    pass


def open_locked(filename, mode="r", **kwargs):
    """ Open file with locking using flock(2). """

    fobj = open(filename, mode, **kwargs)
    try:
        # Acquire an exclusive lock for the open file.
        flock(fobj, LOCK_EX|LOCK_NB)
    except IOError as exc:
        fobj.close()
        if exc.errno == EAGAIN:
            raise FileIsLocked("%s is locked!" % filename)
        raise
    except:
        fobj.close()
        raise
    return fobj


def log_append(filename, line, n_atempts=10, sleep_time=0.001):
    """ Append line of text to a log file with an exclusive log. """
    line = "%s\n" % line

    def _append():
        with open_locked(filename, "a") as file_:
            file_.write(line)

    for atempt in xrange(n_atempts):
        try:
            _append()
        except FileIsLocked:
            if atempt < n_atempts:
                sleep(sleep_time)
                continue
            raise
        else:
            break
