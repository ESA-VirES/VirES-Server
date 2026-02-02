#-------------------------------------------------------------------------------
#
#  Data transformations
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2026 EOX IT Services GmbH
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

import numpy

TRANSFORMATION_REGISTER = {}

def parse_transformation_spec(variable, spec):
    """ Parse transformation specification. """
    return ComposedTransform([
        TRANSFORMATION_REGISTER[item["op"]](
            variable, *(item.get("args") or [])
        ) for item in spec
    ])


class DataTransformation:
    """ Data transformation base class. """

    def __init__(self, produced_variable, required_variables):
        self.produced_variable = produced_variable
        self.required_variables = required_variables

    def __call__(self, data):
        """ Perform data transformation. """
        raise NotImplementedError


class SingleTransformation(DataTransformation):
    """ Single operation data transform. """

    @classmethod
    def from_spec(cls, variable, *args):
        """ Generate class instance from declared specification. """
        return cls(variable, *args)

    def __call__(self, data):
        """ Perform data transformation. """
        return self._transform(*[
            data[variable] for variable in self.required_variables
        ])

    def _transform(self, *inputs):
        """ Perform data transformation. """
        raise NotImplementedError


class ComposedTransform(DataTransformation):
    """ Composed data transform. """

    def __new__(cls, transforms):
        if len(transforms) == 1:
            return transforms[0]
        return super(ComposedTransform, cls).__new__(cls)

    def __init__(self, transforms):
        if len(transforms) == 0:
            raise ValueError("Empty list of transformation not allowed!")
        produced_variable = None
        required_variables = []
        required_variables_set = set()
        intermediate_variables_set = set()
        for transform in transforms:
            for variable in transform.required_variables:
                if (
                    variable not in required_variables_set
                    and variable not in intermediate_variables_set
                ):
                    required_variables.append(variable)
                    required_variables_set.add(variable)
            produced_variable = transform.produced_variable
            intermediate_variables_set.add(produced_variable)
        super().__init__(produced_variable, required_variables)
        self._transforms = transforms

    def __call__(self, data):
        result = None
        intermediate_data = {}
        for transform in self._transforms:
            intermediate_data[transform.produced_variable] = result = (
                transform({**data, **intermediate_data})
            )
        return result


class Index(SingleTransformation):
    """ Index variables """
    name = "index"

    def __init__(self, variable, helper_variable, index, dtype):
        super().__init__(variable, [helper_variable])
        self.index = numpy.asarray(index, dtype=dtype)

    def _transform(self, *inputs):
        data, = inputs
        index = self.index
        tmp_shape = (*((1,) * data.ndim), *index.shape)
        dst_shape = (*data.shape, *index.shape)
        return numpy.broadcast_to(numpy.reshape(index, tmp_shape), dst_shape)

TRANSFORMATION_REGISTER[Index.name] = Index.from_spec


class Broadcast(SingleTransformation):
    """ Expand data array by broadcasting. """
    name = "broadcast"

    def __init__(self, variable, record_shape):
        super().__init__(variable, [variable])
        self.record_shape = tuple(record_shape)
        self.extended_shape = (1,) * len(self.record_shape)

    def _transform(self, *inputs):
        data, = inputs
        tmp_shape = (*data.shape, *self.extended_shape)
        dst_shape = (*data.shape, *self.record_shape)
        return numpy.broadcast_to(numpy.reshape(data, tmp_shape), dst_shape)

TRANSFORMATION_REGISTER[Broadcast.name] = Broadcast.from_spec


class Ravel(SingleTransformation):
    """ Flatten multi-dimensional array. """
    name = "ravel"

    def __init__(self, variable):
        super().__init__(variable, [variable])

    def _transform(self, *inputs):
        data, = inputs
        return numpy.ravel(data, order="C")

TRANSFORMATION_REGISTER[Ravel.name] = Ravel.from_spec
