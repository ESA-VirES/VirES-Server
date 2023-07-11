#-------------------------------------------------------------------------------
#
# Cached magnetic models management API - common subroutines
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2023 EOX IT Services GmbH
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

from os import makedirs, remove, rename
from os.path import join, basename, isdir
from shutil import copyfile
from glob import iglob
from django.conf import settings


def get_temp_cache_file(cache_file):
    """ Get temporary cache filename. """
    return f"{cache_file}.tmp.cdf"


def get_model_cache_read_only_flag():
    """ Extract the cache read-only boolean flag from settings. """
    return getattr(settings, "VIRES_MODEL_CACHE_READ_ONLY", False)


def get_model_cache_root_directory():
    """ Extract the cache root directory from settings. """
    return getattr(settings, "VIRES_MODEL_CACHE_DIR")


def get_collection_model_cache_directory(collection_id):
    """ Get collection directory path for the given collection name. """
    return join(
        get_model_cache_root_directory(), "magnetic_models", collection_id
    )


def get_product_model_cache_file(root_path, product_id):
    """ Get product file path for the given collection name. """
    return join(root_path, f"{product_id}.cdf")


def list_cache_files(cache_dir_path, extension=".cdf"):
    """ List cache file base-names. """
    subset = slice(None, -len(extension) if extension else None)
    for item in iglob(join(cache_dir_path, f"*{extension}")):
        if not item.endswith(".cdf.tmp.cdf"):
            yield basename(item[subset])


def select_products(collection, product_filter=None):
    """ Product selection. """
    products = collection.products
    if product_filter is not None:
        products = product_filter(products)
    return products.all()


def select_models(collection, model_names=None):
    """ Model selection. """
    models = collection.cached_magnetic_models
    if model_names is not None:
        models = models.filter(name__in=model_names)
    return list(models.all())


def init_directory(path, logger):
    """ Initialize cache directory. """
    if not isdir(path):
        logger.info("Creating cache directory %s", path)
        makedirs(path)


def remove_file(filename):
    """ Remove file. """
    try:
        remove(filename)
    except FileNotFoundError:
        return False
    return True


def copy_file(src_filename, dst_filename):
    """ Copy file. """
    copyfile(src_filename, dst_filename)


def rename_file(src_filename, dst_filename):
    """ Rename file. """
    rename(src_filename, dst_filename)
