#-------------------------------------------------------------------------------
#
# Testing utilities.
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

from unittest import TestCase, main
from matplotlib.colors import Colormap
from vires.colormaps import get_colormap

class TestColormaps(TestCase):

    COLORMAPS = [
        "autumn",
        "blackbody",
        "blackwhite",
        "bluered",
        "bone",
        "cool",
        "coolwarm",
        "copper",
        "diverging_1",
        "diverging_2",
        "earth",
        "electric",
        "greens",
        "greys",
        "hot",
        "hsv",
        "inferno",
        "jet",
        "magma",
        "picnic",
        "plasma",
        "portland",
        "rainbow",
        "rdbu",
        "redblue",
        "spring",
        "summer",
        "twilight",
        "twilight_shifted",
        "viridis",
        "winter",
        "yignbu",
        "yiorrd",
        "ylgnbu",
        "ylorrd",
    ]

    def test_get_colormap(self):
        for name in self.COLORMAPS:
            try:
                self.assertTrue(
                    isinstance(get_colormap(name), Colormap)
                )
            except:
                print "Test failed for colormap %r!" % name
                raise

    def test_get_colormap_invalid(self):
        with self.assertRaises(ValueError):
            get_colormap("-invalid-")


if __name__ == "__main__":
    main()
