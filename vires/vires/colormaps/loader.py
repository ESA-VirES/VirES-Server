#-------------------------------------------------------------------------------
#
# colormap loader
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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

from matplotlib.colors import LinearSegmentedColormap


def load_colormap(filename):
    """ Load colormap from a .CM file. """
    with open(filename) as fin:
        return parse_colormap(fin)


def parse_colormap(lines):
    """ Parse colormap file. """
    name, scale = next(lines).split()
    scale = 1.0/float(scale)

    reds, greens, blues = [], [], []
    for line in lines:
        position, red, green, blue = [float(v) for v in line.split()]
        red *= scale
        green *= scale
        blue *= scale
        reds.append((position, red, red))
        greens.append((position, green, green))
        blues.append((position, blue, blue))

    return name, LinearSegmentedColormap(
        name, {'red': reds, 'green': greens, 'blue': blues}
    )
