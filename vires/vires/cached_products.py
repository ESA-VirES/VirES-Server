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
from os.path import exists, basename, splitext
from shutil import copyfileobj
from contextlib import closing
from urllib2 import urlopen
from logging import getLogger

# URL time-out in seconds
URL_TIMEOUT = 25


class InvalidSourcesError(ValueError):
    """ Exception raised in case of invalid number of updater sources. """
    pass


def update_cached_product(sources, destination, updater, filter_=None,
                          tmp_extension=None, logger=None):
    """ Update cached file from the given source using the provided
    updater subroutine.
    The optional label can contain the name of the updated product.

    NOTE: When the cached product is stored as CDF then change the default
    tmp_extension '.tmp' to '.tmp.cdf'.
    """
    logger = logger or getLogger(__name__)

    if filter_:
        sources = filter_(sources)

    logger.info("Updating %s from %s", destination, ", ".join(
        source if source != '-' else '<standard input>'
        for source in sources
    ))

    temporary_file = destination + (tmp_extension or ".tmp")
    remove_if_exists(temporary_file)

    try:
        updater(sources, temporary_file)
        rename(temporary_file, destination)
    except Exception as exc:
        logger.error("Failed to update %s! %s", destination, exc)
        remove_if_exists(temporary_file)
        raise


def simple_cached_product_updater(updater):
    """ Decorator for a simple cached product updater consuming single source
    file.
    """
    def _simple_cached_product_updater_(sources, destination):
        if len(sources) > 1:
            raise InvalidSourcesError(
                "Too many sources! Only one source file expected."
            )
        updater(sources[0], destination)
    return _simple_cached_product_updater_


@simple_cached_product_updater
def copy_file(source, destination):
    """ Read content from the source file and copy it to the destination
    path without modification.
    """
    source_info_file = splitext(destination)[0] + '.source'
    source_id = splitext(basename(source))[0]

    with open(source, "rb") as file_in:
        with open(destination, "wb") as file_out:
            copyfileobj(file_in, file_out, 1024*1024)

    with open(source_info_file, "wb") as file_out:
        file_out.write(source_id)


def open_source(source):
    """ Open the source for reading and return a context-manger-enabled file
    object.
    """
    if is_url(source):
        return closing(urlopen(source, timeout=URL_TIMEOUT))
    elif source == '-':
        return stdin
    return open(source, "rb")


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
