#-------------------------------------------------------------------------------
#
# common color-maps
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

from os.path import join
from glob import glob
from matplotlib import cm as matplotlib_colormaps
import vires.contrib.colormaps as contrib_colormaps
from .loader import load_colormap

__all__ = ['COLORMAPS', 'get_colormap']

COLORMAPS = {}
COLORMAPS.update(
    (name.lower(), colormap) for name, colormap
    in matplotlib_colormaps.cmap_d.items()
)
COLORMAPS.update(contrib_colormaps.cmaps)
COLORMAPS.update(
    load_colormap(filename) for filename in glob(join(__path__[0], "*.cm"))
)


def get_colormap(name):
    """ Get colormap. """
    colormap = COLORMAPS.get(name.lower())
    if colormap is None:
        raise ValueError("Invalid colormap %s!" % name)
    return colormap
