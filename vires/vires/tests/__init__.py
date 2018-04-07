#-------------------------------------------------------------------------------
#
# Unit tests.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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

from numpy import asarray
from numpy.testing import assert_equal, assert_allclose


class ArrayMixIn(object):
    """ Mix-in class adding handy array assertions. """
    # pylint: disable=invalid-name

    @staticmethod
    def assertAllTrue(arr):
        if not asarray(arr).all():
            raise AssertionError("Not all array elements are True!")

    @staticmethod
    def assertAllEqual(arr0, arr1):
        arr0 = asarray(arr0)
        arr1 = asarray(arr1)

        if arr0.shape != arr1.shape:
            raise AssertionError(
                "Array shape mismatch! %s != %s" % (arr0.shape, arr1.shape)
            )

        try:
            assert_equal(arr0, arr1)
        except AssertionError as exc:
            raise AssertionError("Not all array elements are equal!\n%s" % exc)


    @staticmethod
    def assertAllAlmostEqual(arr0, arr1, delta=1e-7):
        arr0 = asarray(arr0)
        arr1 = asarray(arr1)

        if arr0.shape != arr1.shape:
            raise AssertionError(
                "Array shape mismatch! %s != %s" % (arr0.shape, arr1.shape)
            )

        try:
            assert_allclose(arr0, arr1, atol=delta)
        except AssertionError as exc:
            raise AssertionError(
                "Not all array elements are almost equal!\n%s" % exc
            )
