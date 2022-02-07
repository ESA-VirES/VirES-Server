#-------------------------------------------------------------------------------
#
# Magnetic models - model factory classes
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

from io import TextIOWrapper
from zipfile import ZipFile
from ..util import cached_property
from ..file_util import FileChangeMonitor
from ..model_shc import get_filenames_from_zip_archive


class BaseModelFactory():
    """ Base model factory class.

    The model factory class provides unified model loading and hides
    the messy model file handling (__call__() method).

    The model factory class also tracks last modification time of the model
    files and indicates whether the source model files have been updated
    and the model needs to be reloaded (model_changed flag).
    """

    def __init__(self):
        self._tracker = FileChangeMonitor()

    def __call__(self):
        """ Create new model instance. """
        raise NotImplementedError

    @property
    def model_changed(self):
        """ Check if the model files changed. """
        return self._tracker.changed(*self.files)

    @cached_property
    def files(self):
        """ Get list of files required by this model. """
        raise NotImplementedError


class ModelFactory(BaseModelFactory):
    """ Simple file-based model factory class. """

    def __init__(self, loader, model_files):
        super().__init__()
        self.loader = loader
        self.model_files = model_files

    @cached_property
    def files(self):
        return [model_file.filename for model_file in self.model_files]

    def __call__(self):
        """ Create new model instance. """
        return self.loader(*self.files)

    @property
    def sources(self):
        """ Load model sources. """
        return [model_file.sources for model_file in self.model_files]


class ZippedModelFactory(BaseModelFactory):
    """ Model factory handling model files stored in a ZIP archive. """

    def __init__(self, loader, zip_file):
        super().__init__()
        self.loader = loader
        self.zip_file = zip_file

    @cached_property
    def files(self):
        return [self.zip_file.filename]

    def __call__(self):
        """ Create new model instance. """

        with ZipFile(self.zip_file.filename) as archive:
            file_objects = []
            try:
                for filename in get_filenames_from_zip_archive(archive):
                    file_objects.append(archive.open(filename))

                return self.loader(*[
                    TextIOWrapper(file_object, encoding="UTF-8")
                    for file_object in file_objects
                ])

            finally:
                for file_object in file_objects:
                    file_object.close()

    @property
    def sources(self):
        """ Load model sources. """
        return [self.zip_file.sources]
