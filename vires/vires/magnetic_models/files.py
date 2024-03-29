#-------------------------------------------------------------------------------
#
# Magnetic models - model file adapters
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
#pylint: disable=too-few-public-methods

from io import TextIOWrapper
from numpy import asarray
from vires.util import cached_property
from vires.cdf_util import cdf_open, cdf_rawtime_to_mjd2000, CDF_EPOCH_TYPE
from vires.cache_util import cache_path
from vires.model_shc import process_zipped_files, filename2id
from vires.data.vires_settings import CACHED_PRODUCT_FILE


class BaseModelFile():
    """ Base model file object. """

    @property
    def filename(self):
        """ Get model filename. """
        raise NotImplementedError


class ModelFileStatic(BaseModelFile):
    """ Model file with static filename. """

    def __init__(self, filename):
        self._filename = filename

    @cached_property
    def filename(self):
        return self._filename


class ModelFileCached(BaseModelFile):
    """ Model file with cache filename. """

    def __init__(self, cache_id):
        self._cache_id = cache_id

    @cached_property
    def filename(self):
        return cache_path(CACHED_PRODUCT_FILE[self._cache_id])


class BaseModelSource():
    """ Base model source class. """

    @property
    def sources(self):
        """ Get list of sources and their validity intervals. """
        raise NotImplementedError


class LiteralModelSource(BaseModelSource):
    """ Model source with single single source literal. """

    @property
    def sources(self):
        return ([self.source], asarray([self.validity]))

    @property
    def source(self):
        """ Get single source identifier. """
        raise NotImplementedError

    @property
    def validity(self):
        """ Get model validity interval. """
        raise NotImplementedError


class ModelFileWithLiteralSource(ModelFileStatic, LiteralModelSource):
    """ Model file with single literal source. """

    def __init__(self, filename, source, validity_reader):
        super().__init__(filename)
        self._source = source
        self._validity_reader = validity_reader

    @property
    def validity(self):
        return self._validity_reader(self.filename)

    @property
    def source(self):
        return self._source


class CachedModelFileWithSourceFile(ModelFileCached, LiteralModelSource):
    """ Cached model file with extra source file. """

    def __init__(self, cache_id, validity_reader):
        super().__init__(cache_id)
        self._validity_reader = validity_reader

    @property
    def validity(self):
        return self._validity_reader(self.filename)

    @property
    def source(self):
        with open(self.filename + '.source') as file_in:
            return file_in.read().strip()


class CachedZippedMultiModelFile(ModelFileCached, BaseModelSource):
    """ Cached multi-model ZIP-file container. """

    def __init__(self, cache_id, validity_reader):
        super().__init__(cache_id)
        self._validity_reader = validity_reader

    @property
    def sources(self):

        def _extract_source_and_validity(archive, filename):
            with archive.open(filename) as fin:
                return (
                    filename2id(filename),
                    self._validity_reader(TextIOWrapper(fin, encoding="UTF-8")),
                )

        result = process_zipped_files(
            self.filename, _extract_source_and_validity
        )

        return (
            [source for source, _ in result],
            asarray([validity for _, validity in result]),
        )

    @property
    def validity(self):
        """ Get model validity interval. """
        _, validities = self.sources
        return (validities[:, 0].min(), validities[:, 1].max())



class CachedComposedModelFile(ModelFileCached, BaseModelSource):
    """ Cached composed model with sources stored in the CDF file attributes. """

    def __init__(self, cache_id):
        super().__init__(cache_id)

    @property
    def sources(self):
        def _read_time_ranges(attr):
            attr._raw = True # pylint: disable=protected-access
            return cdf_rawtime_to_mjd2000(asarray(attr), CDF_EPOCH_TYPE)

        with cdf_open(self.filename) as cdf:
            sources = list(cdf.attrs["SOURCES"])
            ranges = _read_time_ranges(cdf.attrs["SOURCE_TIME_RANGES"])

        return sources, ranges
