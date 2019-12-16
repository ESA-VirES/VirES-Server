#-------------------------------------------------------------------------------
#
#  Magnetic model rendering
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
# pylint: disable=too-many-arguments,too-many-locals,missing-docstring

from os import remove
from os.path import join, exists
from uuid import uuid4
from math import pi, ceil
from matplotlib.colors import Normalize
from numpy import cos, meshgrid, empty, linspace, tile
from scipy.interpolate import RectBivariateSpline
from eoxserver.services.ows.wps.parameters import CDFile
from eoxmagmod import (
    vnorm, convert, vincdecnorm,
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
    decimal_year_to_mjd2000,
)
from vires.config import SystemConfigReader
from .png_output import data_to_png
from .f107 import get_f107_value


DEG2RAD = pi / 180.0

DEFAULT_GRID_STEP = (8, 8) # interpolation grid sampling in pixels
MIN_MJD2000 = decimal_year_to_mjd2000(1.0)
MAX_MJD2000 = decimal_year_to_mjd2000(4000.0)


def diff_row(array):
    """ Differentiate 2D array columns along the row."""
    diff = empty(array.shape)
    # inner rows
    diff[:, 1:-1, ...] = 0.5 * (array[:, 2:, ...] - array[:, :-2, ...])
    # border rows
    diff[:, 0, ...] = array[:, 1, ...] - array[:, 0, ...]
    diff[:, -1, ...] = array[:, -1, ...] - array[:, -2, ...]
    return diff


def dist_ew(coord_gdt):
    """ East-West sample distances. """
    # first column Geocentric spherical coordinates in degrees
    col_coord_sph = convert(
        coord_gdt[:, 0, :], GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL
    )
    # convert spherical latitudes to radians
    col_coord_sph[:, 0] *= DEG2RAD
    # longitude differences in radians
    diff_lon = DEG2RAD * (coord_gdt[0, 1, 1] - coord_gdt[0, 0, 1])
    # distance between samples
    dist = diff_lon * col_coord_sph[:, 2] * cos(col_coord_sph[:, 0])
    return tile(dist.reshape(dist.size, 1), (1, coord_gdt.shape[0]))


# field evaluators
EVAL_VARIABLE = {
    # magnetic field intensity
    "F": lambda f, c: vnorm(f),
    # intensity of the ground tangential magnetic field component
    "H": lambda f, c: vnorm(f[..., 0:2]),
    # easting magnetic field component
    "X": lambda f, c: f[..., 0],
    # northing magnetic field component
    "Y": lambda f, c: f[..., 1],
    # down-pointing magnetic field component
    "Z": lambda f, c: f[..., 2],
    # magnetic field inclination
    "I": lambda f, c: vincdecnorm(f)[0],
    # magnetic field inclination
    "D": lambda f, c: vincdecnorm(f)[1],
    # easting magnetic field component derivative
    # along the easting coordinate
    "X_EW": lambda f, c: diff_row(f[..., 0]) / dist_ew(c),
    # northing magnetic field component derivative
    # along the easting coordinate
    "Y_EW": lambda f, c: diff_row(f[..., 1]) / dist_ew(c),
    # northing magnetic field component derivative
    # along the down-pointing radial coordinate
    "Z_EW": lambda f, c: diff_row(f[..., 2]) / dist_ew(c),
}
ALLOWED_VARIABLES = set(EVAL_VARIABLE)


def eval_model(model, variable, mjd2000, bbox, srid, elevation, size, **_):
    """ Render WMS model view. """
    assert srid == 4326
    size_x, size_y = size
    min_x, min_y, max_x, max_y = bbox

    hd_x = (0.5 / max(1, size_x)) * (max_x - min_x)
    hd_y = (0.5 / max(1, size_y)) * (min_y - max_y)
    lons, lats = meshgrid(
        linspace(min_x + hd_x, max_x - hd_x, size_x, endpoint=True),
        linspace(max_y + hd_y, min_y - hd_y, size_y, endpoint=True)
    )

    # Geodetic coordinates with elevation above the WGS84 ellipsoid.
    coord_gdt = empty((size_y, size_x, 3))
    coord_gdt[:, :, 0] = lats
    coord_gdt[:, :, 1] = lons
    coord_gdt[:, :, 2] = elevation

    field_components = model.model.eval(
        mjd2000, coord_gdt, GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
        scale=[1, 1, -1],
        **get_extra_model_parameters(mjd2000, model.model.parameters)
    )

    try:
        return EVAL_VARIABLE[variable](field_components, coord_gdt)
    except KeyError:
        raise ValueError("Invalid variable '%s'." % variable)


def eval_model_int(model, variable, mjd2000, bbox, srid, elevation, size,
                   grid_step=None):
    """ Render interpolated WMS model view. """
    assert srid == 4326
    size_x, size_y = size
    min_x, min_y, max_x, max_y = bbox

    # interpolated grid
    grid_step_x, grid_step_y = grid_step or DEFAULT_GRID_STEP
    grid_size_x = max(3, int(ceil(size_x / float(grid_step_x))))
    grid_size_y = max(3, int(ceil(size_y / float(grid_step_y))))
    d_x = (max_x - min_x) / float(grid_size_x)
    d_y = (min_y - max_y) / float(grid_size_y)
    lons1_int = linspace(min_x - d_x, max_x + d_x, grid_size_x + 3, endpoint=True)
    lats1_int = linspace(max_y - d_y, min_y + d_y, grid_size_y + 3, endpoint=True)
    lats1_int = lats1_int[(lats1_int <= 90.0) & (lats1_int >= -90.0)]
    lons_int, lats_int = meshgrid(lons1_int, lats1_int)
    coord_gdt_int = empty(lons_int.shape + (3,))
    coord_gdt_int[:, :, 0] = lats_int
    coord_gdt_int[:, :, 1] = lons_int
    coord_gdt_int[:, :, 2] = elevation


    # Evaluate the magnetic field vector components
    # (northing, easting, up-pointing)
    field_components_int = model.model.eval(
        mjd2000, coord_gdt_int, GEODETIC_ABOVE_WGS84, GEODETIC_ABOVE_WGS84,
        scale=[1, 1, -1],
        **get_extra_model_parameters(mjd2000, model.model.parameters)
    )

    # interpolation pixel grid
    hd_x = (0.5 / max(1, size_x)) * (max_x - min_x)
    hd_y = (0.5 / max(1, size_y)) * (min_y - max_y)
    lons1 = linspace(min_x + hd_x, max_x - hd_x, size_x, endpoint=True)
    lats1 = linspace(max_y + hd_y, min_y - hd_y, size_y, endpoint=True)
    lons, lats = meshgrid(lons1, lats1)

    # Geodetic coordinates with elevation above the WGS84 ellipsoid.
    coord_gdt = empty((size_y, size_x, 3))
    coord_gdt[:, :, 0] = lats
    coord_gdt[:, :, 1] = lons
    coord_gdt[:, :, 2] = elevation

    # Rectangular Bivariate Cubic Spline interpolation
    field_components = empty(lons.shape + (3,))
    for idx in xrange(field_components.shape[2]):
        field_components[..., idx] = RectBivariateSpline(
            -lats1_int, lons1_int, field_components_int[..., idx],
            (-lats1_int[0], -lats1_int[-1], lons1_int[0], lons1_int[-1]),
            3, 3, 0
        )(-lats1, lons1)

    try:
        return EVAL_VARIABLE[variable](field_components, coord_gdt)
    except KeyError:
        raise Exception("Invalid variable '%s'." % variable)


def get_extra_model_parameters(mjd2000, requirements):
    """ Get additional model parameters. """
    parameters = {}
    if "f107" in requirements:
        parameters.update(get_f107_value(mjd2000))
    return parameters


def convert_to_png(data, value_range, colormap, is_transparent,
                   wps_output_def=None):
    """ Convert data array to coloured PNG image. """
    range_min, range_max = value_range
    range_min = data.min() if range_min is None else range_min
    range_max = data.max() if range_max is None else range_max
    if range_max < range_min:
        range_max, range_min = range_min, range_max

    data_norm = Normalize(range_min, range_max)

    # the output image
    conf_sys = SystemConfigReader()
    temp_basename = uuid4().hex
    temp_filename = join(conf_sys.path_temp, temp_basename + ".png")

    try:
        data_to_png(temp_filename, data, data_norm, colormap, not is_transparent)
        result = CDFile(temp_filename, **(wps_output_def or {}))
    except Exception:
        if exists(temp_filename):
            remove(temp_filename)
        raise

    return result, "image/png", (range_min, range_max)


def render_model(model, variable, mjd2000, srid, bbox, elevation, size,
                 value_range, colormap, response_format, is_transparent,
                 grid_step=None, wps_output_def=None):
    """ render WMS model view """

    if grid_step == (1, 1):
        eval_model_func = eval_model
        options = {}
    else:
        eval_model_func = eval_model_int
        options = {"grid_step": grid_step}

    data = eval_model_func(
        model=model,
        variable=variable,
        mjd2000=mjd2000,
        bbox=bbox,
        srid=srid,
        elevation=elevation,
        size=size,
        **options
    )

    assert response_format == "image/png"

    return convert_to_png(
        data, value_range, colormap, is_transparent, wps_output_def
    )
