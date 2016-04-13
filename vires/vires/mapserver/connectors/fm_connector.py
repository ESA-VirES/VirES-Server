#-------------------------------------------------------------------------------
#
# Forward Model WMS connector
#
# Project: VirES
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2014 EOX IT Services GmbH
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
# pylint: disable=missing-docstring,no-self-use,too-many-locals,unused-argument

from os.path import join
from uuid import uuid4
import logging
from django.contrib.gis import geos
from eoxserver.core import Component, implements
from eoxserver.core.util.perftools import log_duration
from eoxserver.contrib import vsi, gdal
from eoxserver.resources.coverages import models
from eoxserver.services.subset import Trim, Slice
from eoxserver.services.mapserver.interfaces import ConnectorInterface
from vires.forward_models.util import get_forward_model_providers

#TODO: Fix the logging.
logger = logging.getLogger("eoxserver")

class ForwardModelConnector(Component):
    """ Connects a CDF file.
    """
    implements(ConnectorInterface)

    def supports(self, data_items):
        return (
            len(data_items) == 1 and
            data_items[0].semantic == "coefficients"
        )

    def connect(self, coverage, data_items, layer, options):
        data_item = data_items[0]
        model_provider = self.get_model_provider(data_item.format)

        # parse options
        time = self.check_time(
            options.get("time"), model_provider.time_validity
        )
        elevation = options.get("elevation") or 0
        band = self.get_band(coverage, options.get("bands", ()))
        size_x, size_y = options["width"], options["height"]
        #FIXME: Does 'options.get("subsets")' always return the right object?
        bbox = self.get_bbox(options.get("subsets"))
        coeff_min, coeff_max = self.parse_coeff_range(
            options["dimensions"].get("coeff")
        )
        range_min, range_max = self.parse_data_range(
            band, options["dimensions"].get("range")
        )

        with log_duration("model evaluation", logger):
            # fast Cubic Spline model interpolation
            pixel_array = model_provider.evaluate_int(
                data_item, band.identifier, bbox, size_x, size_y, elevation,
                time, coeff_min, coeff_max
            )
            # scale pixel values
            scale_factor = 255.0 / (range_max - range_min)
            pixel_array = scale_factor * (pixel_array - range_min)

        # finalize the layer data
        path = join("/vsimem", uuid4().hex)
        driver = gdal.GetDriverByName("GTiff")
        dataset = driver.Create(path, size_x, size_y, 1, gdal.GDT_Byte)
        dataset.SetGeoTransform((
            bbox[0], (bbox[2] - bbox[0]) / float(size_x), 0.0,
            bbox[3], 0.0, (bbox[1] - bbox[3]) / float(size_y)
        ))
        dataset.GetRasterBand(1).WriteArray(pixel_array)
        layer.data = path

        logger.info("Created tempfile %s", layer.data)

    def disconnect(self, coverage, data_items, layer, options):
        logger.info("Removing tempfile %s", layer.data)
        vsi.remove(layer.data)

    def get_model_provider(self, identifier):
        try:
            return get_forward_model_providers()[identifier]
        except IndexError:
            raise Exception("No model provider '%s' found!" % identifier)

    def check_time(self, time, validity):
        if isinstance(time, Trim):
            _time = (time.high - time.low) / 2 + time.low
        elif isinstance(time, Slice):
            _time = time.value
        else:
            if validity[0] == validity[1]:
                _time = validity[0]
                # static model and not time is required
            else:
                raise Exception("Missing the mandatory 'time' parameter!")

        # time exceeding the validity range is set to the closest valid time
        if _time < validity[0]:
            _time = validity[0]
        if _time > validity[1]:
            _time = validity[1]
        return _time

    def get_band(self, coverage, bands):
        if len(bands) < 1:
            return coverage.range_type[0]
        try:
            return coverage.range_type.bands.get(identifier=bands[0])
        except models.Band.DoesNotExist:
            raise Exception("Invalid band '%s' specified." % bands[0])

    def get_bbox(self, subsets):
        bbox = subsets.xy_bbox
        if subsets.srid != 4326:
            bbox = geos.Polygon.from_bbox(bbox).transform(4326).extent
        return bbox

    def parse_coeff_range(self, coeff_range):
        if coeff_range:
            try:
                cmin, cmax = [
                    (int(v) if v else None)
                    for v in coeff_range[0].split(",")
                ]
            except ValueError:
                raise Exception("Invalid coefficient range provided.")
        else:
            cmin, cmax = None, None
        return cmin, cmax

    def parse_data_range(self, band, data_range):
        if data_range:
            try:
                rmin, rmax = [
                    float(v) for v in data_range[0].split(",")
                ]
            except ValueError:
                raise Exception("Invalid data range provided.")
        else:
            rmin, rmax = band.allowed_values
        return rmin, rmax
