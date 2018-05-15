#-------------------------------------------------------------------------------
#
# Cached product management utilities.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
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

from sys import stdin
from os import rename, remove
from os.path import exists
from shutil import copyfileobj
from contextlib import closing
from urllib2 import urlopen

# URL time-out in seconds
URL_TIMEOUT = 25


def update_cached_product(source, destination, updater, label=None,
                          tmp_extension=None):
    """ Update cached file from the given source using the provided
    updater subroutine.
    The optional label can contain the name of the updated product.

    NOTE: When the cached product is stored as CDF then change the default
    tmp_extension '.tmp' to '.tmp.cdf'.
    """
    print "Updating %s from %s" % (
        label or destination, source if source != '-' else '<standard input>'
    )

    temporary_file = destination + (tmp_extension or ".tmp")
    remove_if_exists(temporary_file)

    try:
        if is_url(source):
            with closing(urlopen(source, timeout=URL_TIMEOUT)) as fin:
                updater(fin, temporary_file)
        elif source == '-':
            updater(stdin, temporary_file)
        else:
            with open(source) as fin:
                updater(fin, temporary_file)
        rename(temporary_file, destination)
    except Exception:
        remove_if_exists(temporary_file)
        raise


def remove_if_exists(filename):
    """ Remove file if it exists. """
    if exists(filename):
        remove(filename)


def is_url(source):
    """ Return true if the source is a URL. """
    return (
        source.startswith("https://") or
        source.startswith("http://") or
        source.startswith("ftp://")
    )


def copy_file(file_in, destination):
    """ Read content from the input file object and copy it to the destination
    path without modification.
    """
    with file(destination, "wb") as file_out:
        copyfileobj(file_in, file_out, 1024*1024)
