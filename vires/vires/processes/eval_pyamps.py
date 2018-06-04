#-------------------------------------------------------------------------------
#
# Average magnetic field and polar current system evaluation
#
# Project: VirES
# Authors: Mikael Toresen <mikael.toresen@eox.at>
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
# pylint: disable=missing-docstring,too-many-arguments,too-many-locals
# pylint: disable=unused-argument,no-self-use,too-few-public-methods

from os import remove
from os.path import join, exists
from uuid import uuid4
from datetime import datetime
from matplotlib.colors import Normalize
from numpy import (
    array, full_like, full, linspace, concatenate,
    sqrt, nan, abs as np_abs, meshgrid, nanmin, nanmax
)
from pyamps import AMPS, get_B_space
from eoxmagmod import (
    convert, eval_mlt, eval_qdlatlon,
    GEODETIC_ABOVE_WGS84, GEOCENTRIC_SPHERICAL,
)
from django.conf import settings
from eoxserver.services.ows.wps.parameters import (
    BoundingBox, BoundingBoxData, ComplexData, CDFile,
    FormatBinaryRaw, FormatBinaryBase64,
    LiteralData, AllowedRange
)
from vires.processes.base import WPSProcess
from vires.config import SystemConfigReader
from vires.dataset import Dataset
from vires.perf_util import ElapsedTimeLogger
from vires.processes.util import (
    parse_style, data_to_png, ProductTimeSeries,
    SunPosition, SubSolarPoint, MagneticDipole, DipoleTiltAngle,
)
from vires.cdf_util import (
    datetime_to_cdf_rawtime,
    CDF_EPOCH_TYPE,
)
from vires.time_util import (
    naive_to_utc,
    datetime_mean,
    datetime_to_decimal_year,
    datetime_to_mjd2000,
)

class EvalAMPS(WPSProcess):
    """ Calculate current and magnetic field of AMPS model on a grid"""
    identifier = "eval_amps"
    title = "Evaluate AMPS model"
    metadata = {}
    profiles = ["vires"]

    REFRE = 6371.2 # Reference radius used in geomagnetic modeling

    EVAL_MAG_VARIABLE = {
        # amps magnetic field intensity
        "F": lambda b: sqrt((b**2).sum(axis=0)),
        # amps eastward magnetic field component
        "X": lambda b: b[0],
        # amps northward magnetic field component
        "Y": lambda b: b[1],
        # amps down-pointing magnetic field component
        "Z": lambda b: -b[2], # opposite sign, up-vector in amps, down(center) in vires
    }
    EVAL_CURR_VARIABLE = {
        "Ju": # amps upward current
            lambda m, c: AMPS.get_upward_current(m, *c),
        "Psi": # amps divergence-free current function
            lambda m, c: AMPS.get_divergence_free_current_function(m, *c),
        "j_X": # amps eastward component of the horizontal current
            lambda m, c: AMPS.get_total_current(m, *c)[0].reshape(c[0].shape),
        "j_Y": # amps northward component of the horizontal current
            lambda m, c: AMPS.get_total_current(m, *c)[1].reshape(c[0].shape),
    }

    inputs = [
        ("bbox", BoundingBoxData(
            "bbox", crss=None, optional=True, title="Area of interest",
            abstract="Optional area of interest encoded ",
            default=BoundingBox(((-90., -180.), (+90., +180.))),
        )),
        ("width", LiteralData(
            "width", int, optional=False, title="Image width in pixels.",
            allowed_values=AllowedRange(1, 1024, dtype=int), default=256,
        )),
        ("height", LiteralData(
            "height", int, optional=False, title="Image height in pixels.",
            allowed_values=AllowedRange(1, 1024, dtype=int), default=128,
        )),
        ("begin_time", LiteralData(
            "begin_time", datetime, optional=False,
            abstract="Start of the time interval",
        )),
        ("end_time", LiteralData(
            "end_time", datetime, optional=False,
            abstract="End of the time interval",
        )),
        ("variable", LiteralData(
            "variable", str, optional=True, default="F",
            abstract="Variable to be evaluated.",
            allowed_values=list(EVAL_MAG_VARIABLE.keys())+list(EVAL_CURR_VARIABLE.keys()),
        )),
        ("elevation", LiteralData(
            "elevation", float, optional=True, uoms=(("km", 1.0), ("m", 1e-3)),
            default=0.0, allowed_values=AllowedRange(-1., 1000., dtype=float),
            abstract="Height above WGS84 ellipsoid used to evaluate the model.",
        )),
        ("range_min", LiteralData(
            "range_min", float, optional=True, default=None,
            abstract="Minimum displayed value."
        )),
        ("range_max", LiteralData(
            "range_max", float, optional=True, default=None,
            abstract="Maximum displayed value."
        )),
        ("style", LiteralData(
            "style", str, optional=True, default="jet",
            abstract="The name of the colour-map applied to the result.",

        )),
    ]

    outputs = [
        ("output", ComplexData(
            "output", title="The output image.", formats=(
                FormatBinaryBase64("image/png"),
                FormatBinaryRaw("image/png"),
            )
        )),
        ("style_range", LiteralData(
            "style_range", str, title="Style and value range.",
            abstract="Colour-map name and range of values of the result."
        )),
    ]

    def model_parameters(self, time):
        dataset = Dataset()

        dataset.set('Timestamp', array([datetime_to_cdf_rawtime(
            time, CDF_EPOCH_TYPE
        )]), CDF_EPOCH_TYPE)
        dataset.set('Longitude', array([0.0]))
        dataset.set('Latitude', array([0.0]))
        dataset.set('Radius', array([0.0]))

        product_aux_imf2 = ProductTimeSeries(settings.VIRES_AUX_IMF_2__COLLECTION)
        model_sun = SunPosition()
        model_subsol = SubSolarPoint()
        model_dipole = MagneticDipole()
        model_tilt_angle = DipoleTiltAngle()

        # get AUX_IMF2_ variables
        dataset.update(
            product_aux_imf2.interpolate(dataset['Timestamp'], [
                "IMF_V", "IMF_BY_GSM", "IMF_BZ_GSM", "F10_INDEX",
            ])
        )
        # get sun position needed by the tilt angle
        dataset.update(
            model_sun.eval(dataset, ["SunDeclination", "SunHourAngle"])
        )
        # get earth-sun vector
        dataset.update(model_subsol.eval(dataset, ["SunVector"]))
        # get dipole axis vector
        dataset.update(model_dipole.eval(dataset, ["DipoleAxisVector"]))
        # get tilt angle
        dataset.update(model_tilt_angle.eval(dataset, ["DipoleTiltAngle"]))
        # extract scalars from the dataset
        amps_parameters = (dataset[key][0] for key in [
            "IMF_V", "IMF_BY_GSM", "IMF_BZ_GSM", "F10_INDEX", "DipoleTiltAngle"
        ])
        return amps_parameters

    def gcoor2qdlatmlt(self, lats, lons, elev, dtime):
        gcoor = convert(
            concatenate((
                lats.reshape(-1, 1),
                lons.reshape(-1, 1),
                elev.reshape(-1, 1),
            ), axis=1),
            GEODETIC_ABOVE_WGS84,
            GEOCENTRIC_SPHERICAL,
        )
        qdlats, qdlons = eval_qdlatlon(
            gcoor[:, 0],
            gcoor[:, 1],
            gcoor[:, 2],
            full_like(gcoor[:, 0], fill_value=datetime_to_decimal_year(dtime)),
        )
        mlts = eval_mlt(
            qdlons,
            full_like(qdlons, fill_value=datetime_to_mjd2000(dtime)),
        )

        qdlats = qdlats.reshape(lats.shape)
        mlts = mlts.reshape(lats.shape)
        return qdlats, mlts

    def execute(self, variable, begin_time, end_time, elevation,
                range_max, range_min, bbox, width, height, style,
                output):
        # get configurations
        conf_sys = SystemConfigReader()

        # parse styles
        color_map = parse_style("style", style)

        # fix the time-zone of the naive date-time
        begin_time = naive_to_utc(begin_time)
        end_time = naive_to_utc(end_time)
        mean_dt = datetime_mean(begin_time, end_time)

        self.access_logger.info(
            "request: toi: (%s, %s), aoi: %s, elevation: %g, "
            "variable: %s, "
            "image-size: (%d, %d), mime-type: %s",
            begin_time.isoformat("T"), end_time.isoformat("T"),
            bbox[0] + bbox[1], elevation, variable,
            width, height, output['mime_type'],
        )

        imf_v, imf_by, imf_bz, f107, tilt = self.model_parameters(mean_dt)


        (y_min, x_min), (y_max, x_max) = bbox
        hd_x = (0.5 / width) * (x_max - x_min)
        hd_y = (0.5 / height) * (y_min - y_max)
        lons, lats = meshgrid(
            linspace(x_min + hd_x, x_max - hd_x, width, endpoint=True),
            linspace(y_max + hd_y, y_min - hd_y, height, endpoint=True)
        )
        elevations = full_like(lons, fill_value=elevation)

        with ElapsedTimeLogger("pyamps.%s %dx%dpx %s evaluated in" % (
            variable, width, height, bbox[0] + bbox[1],
        ), self.logger):
            if variable in self.EVAL_CURR_VARIABLE:
                qdlats, mlts = self.gcoor2qdlatmlt(lats, lons, elevations, mean_dt)
                try:
                    model = AMPS(
                        v=imf_v, By=imf_by, Bz=imf_bz,
                        tilt=tilt, f107=f107,
                        height=elevation,
                        resolution=0, dr=90,
                    )
                except IndexError:
                    self.logger.debug(
                        "Cannot evaluate model at IMF_V: %s, "
                        "IMF_BY_GSM: %s, IMF_BZ_GSM: %s, "
                        "F10_INDEX: %s, DipoleTiltAngle: %s",
                        imf_v, imf_by, imf_bz, f107, tilt
                    )
                    pixel_array = full((height, width), nan)
                else:
                    eval_func = self.EVAL_CURR_VARIABLE[variable]
                    pixel_array = eval_func(model, [qdlats, mlts])
                    if variable == "Ju":
                        pixel_array[np_abs(qdlats) < 45] = nan
            elif variable in self.EVAL_MAG_VARIABLE:
                b_nec = array(
                    get_B_space(
                        glat=lats.flatten(),
                        glon=lons.flatten(),
                        height=elevations.flatten(),
                        time=full(lons.size, mean_dt, dtype=object),
                        v=full(lons.size, imf_v),
                        By=full(lons.size, imf_by),
                        Bz=full(lons.size, imf_bz),
                        tilt=full(lons.size, tilt),
                        f107=full(lons.size, f107),
                        epoch=datetime_to_decimal_year(mean_dt),
                    )
                ).reshape(3, height, width)
                pixel_array = self.EVAL_MAG_VARIABLE[variable](b_nec)

        range_min = nanmin(pixel_array) if range_min is None else range_min
        range_max = nanmax(pixel_array) if range_max is None else range_max
        if range_max < range_min:
            range_max, range_min = range_min, range_max
        self.logger.debug("output data range: %s", (range_min, range_max))
        data_norm = Normalize(range_min, range_max)

        # the output image
        temp_basename = uuid4().hex
        temp_filename = join(conf_sys.path_temp, temp_basename + ".png")

        try:
            data_to_png(temp_filename, pixel_array, data_norm, color_map)
            result = CDFile(temp_filename, **output)
        except Exception:
            if exists(temp_filename):
                remove(temp_filename)
            raise

        return {
            "output": result,
            "style_range": "%s,%s,%s"%(style, range_min, range_max),
        }
