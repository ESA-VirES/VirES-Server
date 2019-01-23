#-------------------------------------------------------------------------------
#
# Process utilities - PNG output
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
from matplotlib.cm import ScalarMappable
from numpy import array, isnan
from numpy.ma import masked_where
#from osgeo import gdal; gdal.UseExceptions() #pylint: disable=multiple-statements
from eoxserver.contrib import gdal


def data_to_png(filename, data, norm, cmap=None, ignore_alpha=None):
    """ Convert 2-D array of scalar values to PNG image.
    The data are normalised by means of the provided normaliser (see,
    e.g., http://matplotlib.org/users/colormapnorms.html.
    If provided colour map is used to colour the values. Unless explicitly
    requested the alpha channel of the colour-map is ignored.
    """
    mask = isnan(data)
    if ignore_alpha is None:
        ignore_alpha = not mask.any()
    data = masked_where(mask, data)
    if cmap:
        colors = ScalarMappable(norm, cmap).to_rgba(data, bytes=True)
        if ignore_alpha:
            colors = colors[:, :, :3]
    else:
        colors = norm(data)
        colors[colors < 0.0] = 0.0
        colors[colors > 1.0] = 1.0
        colors = array(255.0 * colors, dtype='uint8')
    array_to_png(filename, colors)


def array_to_png(filename, data):
    """ Convert an array to a PNG. """
    height, width = data.shape[:2]
    nbands = 1 if len(data.shape) == 2 else data.shape[2]
    mem_driver = gdal.GetDriverByName('MEM')
    png_driver = gdal.GetDriverByName('PNG')
    mem_ds = mem_driver.Create('', width, height, nbands, gdal.GDT_Byte)
    if len(data.shape) == 2:
        mem_ds.GetRasterBand(1).WriteArray(data)
    else:
        for idx in xrange(nbands):
            mem_ds.GetRasterBand(idx + 1).WriteArray(data[:, :, idx])
    png_driver.CreateCopy(filename, mem_ds, 0)
