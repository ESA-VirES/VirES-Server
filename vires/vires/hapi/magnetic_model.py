#-------------------------------------------------------------------------------
#
# VirES HAPI - magnetic model
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
# pylint: disable=

from vires.magnetic_models import ModelInputParser
from vires.processes.util.models import SourceMagneticModel, ComposedMagneticModel

def parse_model_list(model_list):
    """ Parse list of model and return a list of named composed models and
    source models.
    """
    def _wrap_parsed_models(composed_models, source_models):
        return (
            [ComposedMagneticModel(item) for item in composed_models],
            [SourceMagneticModel(item) for item in source_models],
        )

    parser = ModelInputParser()
    try:
        parser.parse_model_list(model_list)
    except parser.ParsingError as error:
        raise ValueError(f"Invalid model list! {error}") from None

    composed_models, source_models = _wrap_parsed_models(
        parser.parsed_models, parser.source_models.values()
    )

    return composed_models, source_models
