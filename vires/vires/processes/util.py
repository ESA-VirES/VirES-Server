#-------------------------------------------------------------------------------
#
# Process utilities
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
from collections import OrderedDict
from numpy import array
#from osgeo import gdal; gdal.UseExceptions()
from eoxserver.contrib import gdal
from matplotlib.cm import ScalarMappable
from eoxmagmod import read_model_shc
from vires.util import get_color_scale, get_model
from eoxserver.services.ows.wps.exceptions import InvalidInputValueError

def parse_style(input_id, style):
    """ Parse style value and return the corresponding colour-map object. """
    if style is None:
        return None
    try:
        return get_color_scale(style)
    except ValueError:
        raise InvalidInputValueError(
            input_id, "Invalid style identifier %r!" % style
        )


def parse_model(input_id, model_id, shc, shc_input_id="shc"):
    """ Parse model identifier and returns the corresponding model."""
    if model_id == "Custom_Model":
        try:
            model = read_model_shc(shc)
        except ValueError:
            raise InvalidInputValueError(
                shc_input_id, "Failed to parse the custom model coefficients."
            )
    else:
        model = get_model(model_id)
        if model is None:
            raise InvalidInputValueError(
                input_id, "Invalid model identifier %r!" % model_id
            )
    return model


def parse_models(input_id, model_ids, shc, shc_input_id="shc"):
    """ Parse model identifiers and returns an ordered dictionary
    the corresponding models.
    """
    models = OrderedDict()
    if model_ids.strip():
        for model_id in (id_.strip() for id_ in model_ids.split(",")):
            models[model_id] = parse_model(
                input_id, model_id, shc, shc_input_id
            )
    return models


def parse_filters(input_id, filter_string):
    """ Parse filters' string. """
    try:
        filter_ = {}
        if filter_string.strip():
            for item in filter_string.split(";"):
                name, bounds = item.split(":")
                name = name.strip()
                if not name:
                    raise ValueError("Invalid empty filter name!")
                lower, upper = [float(v) for v in bounds.split(",")]
                filter_[name] = (lower, upper)
    except ValueError as exc:
        raise InvalidInputValueError(input_id, exc)
    return filter_


def data_to_png(filename, data, norm, cmap=None, ignore_alpha=True):
    """ Convert 2-D array of scalar values to PNG image.
    The data are normalised by means of the provided normaliser (see,
    e.g., http://matplotlib.org/users/colormapnorms.html.
    If provided colour map is used to colour the values. Unless explicitly
    requested the alpha channel of the colour-map is ignored.
    """
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
