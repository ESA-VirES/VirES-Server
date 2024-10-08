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


import warnings
from os.path import join
from glob import glob
from matplotlib import colormaps
from vires.contrib.colormaps import colormaps as contrib_colormaps
from .loader import load_colormap

__all__ = ['get_colormap', 'list_colormaps']


BUILT_IN_COLORMAPS = set(colormaps())
COLORMAP_NAME_MAP = {name.lower(): name for name in colormaps()}

# FIXME: These colormaps are already provided by the recent matplotlib versions
#        and should be removed from VirES server ...
EXCLUDED_COLORMAPS = set([
    "magma", "inferno", "plasma", "viridis", "coolwarm", "rainbow",
    "twilight", "twilight_shifted",
])


def _register_colormaps(items):
    for name, cmap in items:
        if name in EXCLUDED_COLORMAPS:
            continue
        if name not in BUILT_IN_COLORMAPS:
            COLORMAP_NAME_MAP[name.lower()] = name
            colormaps.register(name=name, cmap=cmap, force=True)
        else:
            warnings.warn(f"Attempt to override matplotlib built-in colormap '{name}'!")

_register_colormaps(contrib_colormaps.items())
_register_colormaps(
    load_colormap(filename) for filename in glob(join(__path__[0], "*.cm"))
)


def list_colormaps():
    """ Get list of available colormaps. """
    return list(COLORMAP_NAME_MAP)


def get_colormap(name):
    """ Get colormap. """
    try:
        return colormaps[COLORMAP_NAME_MAP.get(name.lower(), name)]
    except KeyError:
        raise ValueError(f"Invalid colormap {name}!") from None
