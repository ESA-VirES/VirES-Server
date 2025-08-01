#-------------------------------------------------------------------------------
#
# Dump info about cached magnetic models
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
# pylint: disable=missing-docstring

import sys
import json
from vires.models import CachedMagneticModel
from .._common import JSON_OPTS
from .common import CachedMagneticModelsSubcommand


class DumpCachedMagneticModelsSubcommand(CachedMagneticModelsSubcommand):
    name = "dump"
    help = "Dump info about cached magnetic models."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-f", "--file", dest="filename", default="-", help=(
                "Optional file-name the output is written to. "
                "By default it is written to the standard output."
            )
        )

    def handle(self, **kwargs):
        models = self.select_models(
            CachedMagneticModel.objects.order_by("collection", "name"), **kwargs
        )

        info = [dump_model_info(model) for model in models]

        filename = kwargs["filename"]
        with (sys.stdout if filename == "-" else open(filename, "w", encoding="utf-8")) as file_:
            json.dump(info, file_, **JSON_OPTS)


def dump_model_info(model):
    return {
        "name": model.name,
        "collection": model.collection.identifier,
        "expression": model.expression,
        **(model.metadata or {}),
        **(model.collection.model_options),
    }
