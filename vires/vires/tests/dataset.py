#-------------------------------------------------------------------------------
#
#  Testing dataset class.
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2016-2025 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,too-few-public-methods

from unittest import main, TestCase
from numpy.random import random, randint
from numpy import concatenate, arange, array, nan
from vires.tests import ArrayMixIn
from vires.dataset import Dataset
from vires.cdf_util import CDF_DOUBLE_TYPE

N = 100
M = 4
N_SUBSET = 10
DATA_A = random(N)
DATA_B = random((N, M))
DATA_C = random(N)
DATA_D = random((N, M))

DATA_ZERO_SCALAR = random(0)
DATA_ZERO_VECTOR = random((0, M))

DATA_X = array([1.0, 3.0, 4.0, 5.0])
DATA_Y = array([1.0, 3.0, 1.0, 2.0])
DATA_Y_SLOPE = array([2.0, 0.0, 0.0, 1.0])
DATA_Z = array([[1.0, 2.0], [3.0, 1.0], [1.0, 3.0], [2.0, 1.0]])
DATA_Z_SLOPE = array([[2.0, -1.0], [0.0, 0.0], [0.0, 0.0], [1.0, -2.0]])

DATA_X_INTERPOLATED = array([
    -0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75,
    3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25,
])

TEST_ATTRIB = {
    "TEST_ATTRIBUTE": "TEST_ATTRIBUTE_VALUE"
}


class FilterStub():
    """ Test filter stub. """

    def __init__(self, required_variables):
        self.required_variables = required_variables

    @staticmethod
    def filter(dataset, index):
        if index is None:
            index = arange(dataset.length)
        return index[:(len(index) >> 1)]


class TestDataset(ArrayMixIn, TestCase):

    def test_get_slope_variable(self):
        variable_name = "VARIABLE"
        self.assertEqual(
            Dataset.get_slope_variable(variable_name),
            Dataset.SLOPE_VARIABLE_TEMPLATE.format(name=variable_name)
        )

    def test_epmty(self):
        """Test empty dataset."""
        dataset = Dataset()
        self.assertEqual(set(dataset), set([]))
        self.assertEqual(len(dataset), 0)
        self.assertEqual(dataset.length, 0)
        self.assertTrue(dataset.is_empty)

    def test_zero_size(self):
        """Test non-empty dataset with zero-length arrays."""
        dataset = Dataset()
        self.assertEqual(len(dataset), 0)
        self.assertEqual(dataset.length, 0)
        self.assertTrue(dataset.is_empty)

        dataset.set('A', DATA_ZERO_SCALAR)
        dataset.set('B', DATA_ZERO_VECTOR, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        with self.assertRaises(ValueError):
            dataset.set('C', DATA_C)

        self.assertEqual(set(dataset), set(['A', 'B']))
        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, 0)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_set(self):
        """Test Dataset.set() method."""
        dataset = Dataset()
        dataset.set('A', DATA_A)
        dataset.set('B', DATA_B, CDF_DOUBLE_TYPE)
        dataset.set('C', DATA_C, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset.set('D', DATA_D, cdf_attr=TEST_ATTRIB)
        with self.assertRaises(ValueError):
            dataset.set('E', DATA_ZERO_SCALAR)

        str(dataset)

        self.assertEqual(len(dataset), 4)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B', 'C', 'D']))

        self.assertAllEqual(dataset['A'], DATA_A)
        self.assertAllEqual(dataset['B'], DATA_B)
        self.assertAllEqual(dataset['C'], DATA_C)
        self.assertAllEqual(dataset['D'], DATA_D)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('D'), None)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), None)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('D'), TEST_ATTRIB)

    def test_update(self):
        """Test Dataset.update() method."""
        dataset_a = Dataset()
        dataset_a.set('A', DATA_A, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_a.set('B', DATA_D)

        dataset_b = Dataset()
        dataset_a.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_a.set('C', DATA_C, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        dataset_zero_size = Dataset()
        dataset_zero_size.set('B', DATA_ZERO_SCALAR)
        dataset_zero_size.set('C', DATA_ZERO_VECTOR)

        dataset = Dataset()
        dataset.update(dataset_a)
        dataset.update(dataset_b)
        dataset.update(Dataset())
        with self.assertRaises(ValueError):
            dataset.update(dataset_zero_size)

        self.assertEqual(len(dataset), 3)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B', 'C']))

        self.assertAllEqual(dataset['A'], DATA_A)
        self.assertAllEqual(dataset['B'], DATA_B)
        self.assertAllEqual(dataset['C'], DATA_C)

        self.assertEqual(dataset.cdf_type.get('A'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)

    def test_merge(self):
        """Test Dataset.merge() method, including name translation."""

        dataset_a = Dataset()
        dataset_a.set('X', DATA_A, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_a.set('Y', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        variable_mapping = {"X": "A", "Y": "B"}

        dataset_b = Dataset()
        dataset_b.set('B', DATA_D)
        dataset_b.set('C', DATA_C, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        dataset_zero_size = Dataset()
        dataset_zero_size.set('B', DATA_ZERO_SCALAR)
        dataset_zero_size.set('C', DATA_ZERO_VECTOR)

        dataset = Dataset()
        dataset.merge(dataset_a, variable_mapping)
        dataset.merge(dataset_b)
        dataset.merge(Dataset())
        with self.assertRaises(ValueError):
            dataset.merge(dataset_zero_size)

        self.assertEqual(len(dataset), 3)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B', 'C']))

        self.assertAllEqual(dataset['A'], DATA_A)
        self.assertAllEqual(dataset['B'], DATA_B)
        self.assertAllEqual(dataset['C'], DATA_C)

        self.assertEqual(dataset.cdf_type.get('A'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)

    def test_append(self):
        """Test Dataset.append() method."""
        dataset_a = Dataset()
        dataset_a.set('A', DATA_A, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_a.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        dataset_b = Dataset()
        dataset_b.set('A', DATA_C)
        dataset_b.set('B', DATA_D)

        dataset_key_missmatch = Dataset()
        dataset_key_missmatch.set('C', DATA_C)
        dataset_key_missmatch.set('B', DATA_D)

        dataset_zero_size = Dataset()
        dataset_zero_size.set('A', DATA_ZERO_SCALAR)
        dataset_zero_size.set('B', DATA_ZERO_VECTOR)

        dataset = Dataset()
        dataset.append(dataset_a)
        dataset.append(dataset_b)
        dataset.append(dataset_zero_size)
        dataset.append(Dataset())

        with self.assertRaises(ValueError):
            dataset.append(dataset_key_missmatch)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, 2*N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], concatenate((DATA_A, DATA_C), axis=0))
        self.assertAllEqual(dataset['B'], concatenate((DATA_B, DATA_D), axis=0))

        self.assertEqual(dataset.cdf_type.get('A'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_extract(self):
        """Test Dataset.extract() method."""
        dataset_source = Dataset()
        dataset_source.set('A', DATA_A)
        dataset_source.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set('C', DATA_C, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set('D', DATA_D)

        dataset = dataset_source.extract(['B', 'D', 'G'])

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['B', 'D']))

        self.assertAllEqual(dataset['B'], DATA_B)
        self.assertAllEqual(dataset['D'], DATA_D)

        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('D'), None)

        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('D'), None)

    def test_subset(self):
        """Test Dataset.subset() method."""
        dataset_source = Dataset()
        dataset_source.set('A', DATA_A)
        dataset_source.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        index = randint(N, size=N_SUBSET)

        dataset = dataset_source.subset(index)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, N_SUBSET)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], DATA_A[index])
        self.assertAllEqual(dataset['B'], DATA_B[index])

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_subset_empty(self):
        """Test Dataset.subset() method for an empty dataset."""
        dataset_source = Dataset()
        index = randint(N, size=N_SUBSET)
        dataset = dataset_source.subset(index)
        self.assertEqual(len(dataset), 0)

    def test_subset_zero_size(self):
        """Test Dataset.subset() method for a non-empty dataset
        with zero length arrays.
        """
        dataset_zero_size = Dataset()
        dataset_zero_size.set('A', DATA_ZERO_SCALAR)
        dataset_zero_size.set('B', DATA_ZERO_VECTOR, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        index = arange(0)

        dataset = dataset_zero_size.subset(index)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, 0)
        self.assertTrue(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], DATA_ZERO_SCALAR)
        self.assertAllEqual(dataset['B'], DATA_ZERO_VECTOR)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_subset_without_index(self):
        """Test Dataset.subset() method with index set to None. """
        dataset_source = Dataset()
        dataset_source.set('A', DATA_A)
        dataset_source.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        dataset = dataset_source.subset(None)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], DATA_A)
        self.assertAllEqual(dataset['B'], DATA_B)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_subset_without_index_no_copy(self):
        """Test Dataset.subset() method with index set to None and no-copy. """
        dataset_source = Dataset()
        dataset_source.set('A', DATA_A)
        dataset_source.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        dataset = dataset_source.subset(None, always_copy=False)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, N)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], DATA_A)
        self.assertAllEqual(dataset['B'], DATA_B)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_filter(self):
        """Test Dataset.filter() method."""
        dataset_source = Dataset()
        dataset_source.set('A', DATA_A)
        dataset_source.set('B', DATA_B, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set('C', DATA_C, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set('D', DATA_D)

        filters = [
            FilterStub(('A', 'B')),
            FilterStub(('C', 'D')),
            FilterStub(('E', 'F')),
        ]

        dataset, remaining = dataset_source.filter(filters)

        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].required_variables, ('E', 'F'))

        self.assertEqual(len(dataset), 4)
        self.assertEqual(dataset.length, N >> 2)
        self.assertFalse(dataset.is_empty)
        self.assertEqual(set(dataset), set(['A', 'B', 'C', 'D']))

        self.assertAllEqual(dataset['A'], DATA_A[:(N >> 2)])
        self.assertAllEqual(dataset['B'], DATA_B[:(N >> 2)])
        self.assertAllEqual(dataset['C'], DATA_C[:(N >> 2)])
        self.assertAllEqual(dataset['D'], DATA_D[:(N >> 2)])

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('D'), None)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('D'), None)


    def test_filter_zero_size(self):
        """Test Dataset.filter() for an non-empty array
        with zero length arrays.
        """
        dataset_zero_size = Dataset()
        dataset_zero_size.set('A', DATA_ZERO_SCALAR)
        dataset_zero_size.set('B', DATA_ZERO_VECTOR, CDF_DOUBLE_TYPE, TEST_ATTRIB)

        filters = [FilterStub(('A', 'B'))]

        dataset, remaining = dataset_zero_size.filter(filters)

        self.assertEqual(len(remaining), 0)

        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset.length, 0)
        self.assertTrue(dataset.is_empty)

        self.assertEqual(set(dataset), set(['A', 'B']))

        self.assertAllEqual(dataset['A'], DATA_ZERO_SCALAR)
        self.assertAllEqual(dataset['B'], DATA_ZERO_VECTOR)

        self.assertEqual(dataset.cdf_type.get('A'), None)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)

    def test_interpolate(self):
        """ Test Dataset.interpolate() method. """
        dataset_source = Dataset()
        dataset_source.set("T", DATA_X)
        dataset_source.set("A", DATA_Y)
        dataset_source.set("B", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("C", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("D", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("E", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("F", DATA_Y)
        dataset_source.set("_d_F_dt", DATA_Y_SLOPE)
        dataset_source.set("K", DATA_Z)
        dataset_source.set("L", DATA_Z)
        dataset_source.set("M", DATA_Z)
        dataset_source.set("N", DATA_Z)
        dataset_source.set("O", DATA_Z)
        dataset_source.set("P", DATA_Z)
        dataset_source.set("_d_P_dt", DATA_Z_SLOPE)

        data_x = array([
            -0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75,
            3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25,
        ])

        # no kinds given - only selected variables
        dataset = dataset_source.interpolate(data_x, "T", variables=['A', 'K'])

        self.assertEqual(set(dataset), set(['A', 'K']))

        self.assertAllEqual(dataset['A'], array([
            nan, nan, nan, 1.0, 1.0, 3.0, 3.0,
            3.0, 1.0, 1.0, 2.0, nan, nan, nan,
        ]))

        self.assertAllEqual(dataset['K'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0],
            [3.0, 1.0], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0], [1.0, 3.0],
            [2.0, 1.0], [nan, nan], [nan, nan], [nan, nan],
        ]))

        # with kind specification - all variables
        kinds = {
            "B": "nearest",
            "C": "previous",
            "D": "linear",
            "E": "cubic", # fallback to linear
            "F": "cubic",
            "L": "nearest",
            "M": "zero",
            "N": "linear",
            "O": "cubic", # fallback to linear
            "P": "cubic",
        }

        dataset = dataset_source.interpolate(data_x, "T", kinds=kinds)

        # auxiliary slopes are not to be interpolated
        assert "_d_F_dt" not in dataset
        assert "_d_P_dt" not in dataset

        self.assertEqual(dataset.length, len(data_x))
        self.assertFalse(dataset.is_empty)

        self.assertAllEqual(dataset['A'], array([
            nan, nan, nan, 1.0, 1.0, 3.0, 3.0,
            3.0, 1.0, 1.0, 2.0, nan, nan, nan,
        ]))
        self.assertAllEqual(dataset['B'], array([
            nan, nan, nan, 1.0, 1.0, 3.0, 3.0,
            3.0, 1.0, 1.0, 2.0, nan, nan, nan,
        ]))
        self.assertAllEqual(dataset['C'], array([
            nan, nan, nan, 1.0, 1.0, 1.0, 1.0,
            3.0, 3.0, 1.0, 1.0, nan, nan, nan,
        ]))
        self.assertAllEqual(dataset['D'], array([
            nan, nan, nan, 1.25, 1.75, 2.25, 2.75,
            2.5 , 1.5 , 1.25, 1.75, nan,  nan, nan,
        ]))
        self.assertAllEqual(dataset['E'], array([
            nan, nan, nan, 1.25, 1.75, 2.25, 2.75,
            2.5 , 1.5 , 1.25, 1.75, nan,  nan, nan,
        ]))
        self.assertAllEqual(dataset['F'], array([
            nan, nan, nan, 1.46875, 2.21875, 2.71875, 2.96875,
            2.6875, 1.3125, 1.109375, 1.703125, nan, nan, nan
        ]))

        self.assertAllEqual(dataset['K'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0],
            [3.0, 1.0], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0], [1.0, 3.0],
            [2.0, 1.0], [nan, nan], [nan, nan], [nan, nan],
        ]))

        self.assertAllEqual(dataset['L'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0],
            [3.0, 1.0], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0], [1.0, 3.0],
            [2.0, 1.0], [nan, nan], [nan, nan], [nan, nan],
        ]))

        self.assertAllEqual(dataset['M'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0],
            [1.0, 2.0], [1.0, 2.0], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0],
            [1.0, 3.0], [nan, nan], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['N'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.25, 1.875], [1.75, 1.625],
            [2.25, 1.375], [2.75, 1.125], [2.5, 1.5], [1.5, 2.5],
            [1.25, 2.5], [1.75, 1.5], [nan, nan], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['O'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.25, 1.875], [1.75, 1.625],
            [2.25, 1.375], [2.75, 1.125], [2.5, 1.5], [1.5, 2.5],
            [1.25, 2.5], [1.75, 1.5], [nan, nan], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['P'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.46875, 1.765625], [2.21875, 1.390625],
            [2.71875, 1.140625], [2.96875, 1.015625], [2.6875, 1.3125], [1.3125, 2.6875],
            [1.109375, 2.78125], [1.703125, 1.59375], [nan, nan], [nan, nan], [nan, nan],
        ]))

        self.assertEqual(dataset.cdf_type.get('A'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)


    def test_interpolate_advanced(self):
        """ Test Dataset.interpolate() method with gap detection
        and neg boohooed
        """
        dataset_source = Dataset()
        dataset_source.set("T", DATA_X)
        dataset_source.set("A", DATA_Y)
        dataset_source.set("B", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("C", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("D", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("E", DATA_Y, CDF_DOUBLE_TYPE, TEST_ATTRIB)
        dataset_source.set("F", DATA_Y)
        dataset_source.set("_d_F_dt", DATA_Y_SLOPE)
        dataset_source.set("K", DATA_Z)
        dataset_source.set("L", DATA_Z)
        dataset_source.set("M", DATA_Z)
        dataset_source.set("N", DATA_Z)
        dataset_source.set("O", DATA_Z)
        dataset_source.set("P", DATA_Z)
        dataset_source.set("_d_P_dt", DATA_Z_SLOPE)

        data_x = array([
            -0.25, 0.25, 0.75, 1.25, 1.75, 2.25, 2.75,
            3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25,
        ])

        kinds = {
            "B": "nearest",
            "C": "previous",
            "D": "linear",
            "E": "cubic", # fallback to linear
            "F": "cubic",
            "L": "nearest",
            "M": "zero",
            "N": "linear",
            "O": "cubic", # fallback to linear
            "P": "cubic",
        }

        dataset = dataset_source.interpolate(
            data_x, "T", kinds=kinds,
            gap_threshold=1.0, segment_neighbourhood=0.5,
        )

        # auxiliary slopes are not to be interpolated
        assert "_d_F_dt" not in dataset
        assert "_d_P_dt" not in dataset

        self.assertEqual(dataset.length, len(data_x))
        self.assertFalse(dataset.is_empty)

        self.assertAllEqual(dataset['A'], array([
            nan, nan, 1.0, 1.0, nan, nan, 3.0,
            3.0, 1.0, 1.0, 2.0, 2.0, nan, nan,
        ]))
        self.assertAllEqual(dataset['B'], array([
            nan, nan, 1.0, 1.0, nan, nan, 3.0,
            3.0, 1.0, 1.0, 2.0, 2.0, nan, nan,
        ]))
        self.assertAllEqual(dataset['C'], array([
            nan, nan, nan, 1.0, nan, nan, nan,
            3.0, 3.0, 1.0, 1.0, 2.0, nan, nan,
        ]))
        self.assertAllEqual(dataset['D'], array([
            nan, nan, nan, nan, nan, nan, 3.5,
            2.5, 1.5, 1.25, 1.75, 2.25, nan, nan,
        ]))
        self.assertAllEqual(dataset['E'], array([
            nan, nan, nan, nan, nan, nan, 3.5,
            2.5, 1.5, 1.25, 1.75, 2.25, nan, nan,
        ]))
        self.assertAllEqual(dataset['F'], array([
            nan, nan, nan, nan, nan, nan, 2.5625,
            2.6875, 1.3125, 1.109375, 1.703125, 2.171875, nan, nan
        ]))

        self.assertAllEqual(dataset['K'], array([
            [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0], [nan, nan],
            [nan, nan], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0], [1.0, 3.0],
            [2.0, 1.0], [2.0, 1.0], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['L'], array([
            [nan, nan], [nan, nan], [1.0, 2.0], [1.0, 2.0], [nan, nan],
            [nan, nan], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0], [1.0, 3.0],
            [2.0, 1.0], [2.0, 1.0], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['M'], array([
            [nan, nan], [nan, nan], [nan, nan], [1.0, 2.0], [nan, nan],
            [nan, nan], [nan, nan], [3.0, 1.0], [3.0, 1.0], [1.0, 3.0],
            [1.0, 3.0], [2.0, 1.0], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['N'], array([
            [nan, nan], [nan, nan], [nan, nan], [nan, nan], [nan, nan],
            [nan, nan], [3.5, 0.5], [2.5, 1.5], [1.5, 2.5], [1.25, 2.5],
            [1.75, 1.5], [2.25, 0.5], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['O'], array([
            [nan, nan], [nan, nan], [nan, nan], [nan, nan], [nan, nan],
            [nan, nan], [3.5, 0.5], [2.5, 1.5], [1.5, 2.5], [1.25, 2.5],
            [1.75, 1.5], [2.25, 0.5], [nan, nan], [nan, nan],
        ]))
        self.assertAllEqual(dataset['P'], array([
            [nan, nan], [nan, nan], [nan, nan], [nan, nan], [nan, nan],
            [nan, nan], [2.5625, 1.4375], [2.6875, 1.3125], [1.3125, 2.6875], [1.109375, 2.78125],
            [1.703125, 1.59375], [2.171875, 0.65625], [nan, nan], [nan, nan],
        ]))

        self.assertEqual(dataset.cdf_type.get('A'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('B'), CDF_DOUBLE_TYPE)
        self.assertEqual(dataset.cdf_type.get('C'), CDF_DOUBLE_TYPE)

        self.assertEqual(dataset.cdf_attr.get('A'), None)
        self.assertEqual(dataset.cdf_attr.get('B'), TEST_ATTRIB)
        self.assertEqual(dataset.cdf_attr.get('C'), TEST_ATTRIB)


if __name__ == "__main__":
    main()
