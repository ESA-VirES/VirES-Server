#-------------------------------------------------------------------------------
#
# Parser source model class
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2023 EOX IT Services GmbH
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

from collections import namedtuple
from vires.util import cached_property
from .models import MIO_MODELS, MODEL_CACHE


class SourceMagneticModel:
    """ Source magnetic model. """
    Sources = namedtuple("Sources", ["names", "times"])

    @property
    def raw_mio_model(self):
        """ If the source model is a MIO model then get raw MIO model without
        the (1 + N*F10.7) multiplication factor or return None otherwise.
        """
        new_identifier = MIO_MODELS.get(self.identifier)

        if new_identifier is None:
            return None # not a MIO model

        return self.__class__(
            identifier=new_identifier,
            model=MODEL_CACHE.get_model(new_identifier),
            sources=self.sources,
            parameters=self.parameters,
        )

    @staticmethod
    def _get_name(identifier, parameters):
        formatted_parameters = ",".join(
            f"{key}={value}" for key, value in sorted(parameters.items())
        )
        return f"{identifier}({formatted_parameters})"

    @cached_property
    def name(self):
        """ Get composed model name. """
        return self._get_name(self.identifier, self.parameters)

    @cached_property
    def expression(self):
        """ Get model expression. """
        name = self.identifier
        if "-" in name:
            name = f"'{name}'"
        return self._get_name(name, self.parameters)

    @cached_property
    def validity(self):
        """ Get model validity. """
        return self.model.validity

    def __init__(self, identifier, model, sources=None, parameters=None):
        self.identifier = identifier
        self.model = model
        self.sources = sources or []
        self.parameters = parameters or {}

    def __str__(self):
        return f"<SourceMagneticModel: {self.expression}>"
