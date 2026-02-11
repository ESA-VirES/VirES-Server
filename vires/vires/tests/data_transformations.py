#-------------------------------------------------------------------------------
#
#  Data transformations - tests
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
# pylint: disable=missing-function-docstring

import numpy
import numpy.random
import numpy.testing
from unittest import TestCase, main
from vires.data_transformations import (
    TRANSFORMATION_REGISTER,
    parse_transformation_spec,
    DataTransformation,
    ComposedTransform,
    Index,
    Broadcast,
    Ravel,
)

class _TransformTestBase:
    transform_class = None
    produced_variable = None
    required_variables = None

    def _create(self):
        raise NotImplementedError

    def test_produced_variable(self):
        self.assertEqual(
            self._create().produced_variable, self.produced_variable
        )

    def test_class(self):
        self.assertIsInstance(self._create(), self.transform_class)

    def test_required_variables(self):
        self.assertEqual(
            self._create().required_variables, self.required_variables
        )


class TestIndexRavelTransform(_TransformTestBase, TestCase):
    transform_class = ComposedTransform
    produced_variable = "A"
    required_variables = ["B"]

    def _create(self):
        return parse_transformation_spec("A",[
            {"op": "index", "args": ["B", [1, 2, 3, 4], "uint8"]},
            {"op": "ravel"},
        ])

    def test_trasform_success(self):
        src = numpy.random.random(5)
        dst = numpy.ravel(
            numpy.broadcast_to(
                numpy.reshape(
                    numpy.arange(1, 5, dtype="uint8"), (1, 4)
                ), (5, 4)
            ), order="C"
        )
        result = self._create()({"B": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)


class TestIndexTransform(_TransformTestBase, TestCase):
    transform_class = Index
    produced_variable = "A"
    required_variables = ["B"]

    def _create(self):
        return parse_transformation_spec("A",[
            {"op": "index", "args": ["B", [1, 2, 3, 4], "uint8"]},
        ])

    def test_trasform_success(self):
        src = numpy.random.random(5)
        dst = numpy.broadcast_to(
            numpy.reshape(
                numpy.arange(1, 5, dtype="uint8"), (1, 4)
            ), (5, 4)
        )
        result = self._create()({"B": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)


class TestBroadcastRavelTransform(_TransformTestBase, TestCase):
    transform_class = ComposedTransform
    produced_variable = "A"
    required_variables = ["A"]

    def _create(self):
        return parse_transformation_spec("A",[
            {"op": "broadcast", "args": [[4]]},
            {"op": "ravel"},
        ])

    def test_trasform_success(self):
        src = numpy.random.random(5)
        dst = numpy.ravel(
            numpy.broadcast_to(numpy.reshape(src, (5, 1)), (5, 4))
        )
        result = self._create()({"A": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)


class TestBroadcastTransform(_TransformTestBase, TestCase):
    transform_class = Broadcast
    produced_variable = "A"
    required_variables = ["A"]

    def _create(self):
        return parse_transformation_spec("A",[
            {"op": "broadcast", "args": [[4]]},
        ])

    def test_trasform_success(self):
        src = numpy.random.random(5)
        dst = numpy.broadcast_to(numpy.reshape(src, (5, 1)), (5, 4))
        result = self._create()({"A": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)


class TestRavelTransform(_TransformTestBase, TestCase):
    transform_class = Ravel
    produced_variable = "A"
    required_variables = ["A"]

    def _create(self):
        return parse_transformation_spec("A",[
            {"op": "ravel"},
        ])

    def test_trasform_success_1d(self):
        dst = numpy.arange(5)
        src = dst
        result = self._create()({"A": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)

    def test_trasform_success_2d(self):
        dst = numpy.arange(20)
        src = dst.reshape((5, 4), order="C")
        result = self._create()({"A": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)

    def test_trasform_success_3d(self):
        dst = numpy.arange(60)
        src = dst.reshape((5, 4, 3), order="C")
        result = self._create()({"A": src})
        numpy.testing.assert_equal(result, dst)
        self.assertEqual(result.dtype, dst.dtype)


if __name__ == "__main__":
    main()
