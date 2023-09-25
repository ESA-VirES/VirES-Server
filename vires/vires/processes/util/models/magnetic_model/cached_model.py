#-------------------------------------------------------------------------------
#
# Data Source - cached model - filling missing data
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
# pylint: disable=too-many-locals

from logging import getLogger, LoggerAdapter
from numpy import isnan, count_nonzero
from vires.util import cached_property, LazyString
from vires.dataset import Dataset
from ..base import Model


class CachedModelGapFill(Model):
    """ Special model filling gaps in the extracted cached model values. """

    class _LoggerAdapter(LoggerAdapter):
        def process(self, msg, kwargs):
            model_name = self.extra["model_name"]
            return f"{model_name}: cached_model: {msg}", kwargs

    @cached_property
    def variables(self):
        return [self.target_variable]

    @cached_property
    def required_variables(self):
        return [self.source_variable, *self.model.required_variables]

    def __init__(self, model, logger=None, varmap=None):
        del varmap

        super().__init__()

        self.source_variable = f"__cached__B_NEC_{model.name}"
        self.target_variable = f"B_NEC_{model.name}"
        self.model = model

        self.logger = self._LoggerAdapter(logger or getLogger(__name__), {
            "model_name": model.name,
        })

    def eval(self, dataset, variables=None, **kwargs):

        output_ds = Dataset()

        if variables is not None and self.source_variable not in variables:
            return output_ds

        data, cdf_type, attrs = (
            dataset[self.source_variable],
            dataset.cdf_type.get(self.source_variable),
            dataset.cdf_attr.get(self.source_variable),
        )
        gap_mask = isnan(data[:, 0])

        self.logger.debug(
            "Filling missing %s model values.",
            LazyString(lambda: f"{count_nonzero(gap_mask)} of {gap_mask.size}")
        )

        if gap_mask.any():
            data = data.copy()
            subset_ds = dataset.extract(self.model.required_variables).subset(gap_mask)
            result_ds = self.model.eval(subset_ds, [self.target_variable])
            data[gap_mask, ...] = result_ds[self.target_variable]

            # record source models
            self.product_set.update(self.model.product_set)

        output_ds.set(self.target_variable, data, cdf_type, attrs)

        return output_ds
