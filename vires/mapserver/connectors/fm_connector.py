#-------------------------------------------------------------------------------
# $Id$
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
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

from os.path import join
from uuid import uuid4
import logging

from django.contrib.gis import geos
from eoxserver.core import Component, implements, ExtensionPoint
from eoxserver.core.util.perftools import log_duration
from eoxserver.contrib import vsi, gdal
from eoxserver.backends.access import connect
from eoxserver.resources.coverages import models
from eoxserver.services.subset import Trim, Slice
from eoxserver.services.mapserver.interfaces import ConnectorInterface

from vires.interfaces import ForwardModelProviderInterface


logger = logging.getLogger("eoxserver")


class ForwardModelConnector(Component):
    """ Connects a CDF file.
    """

    implements(ConnectorInterface)

    model_providers = ExtensionPoint(ForwardModelProviderInterface)

    def supports(self, data_items):
        return (
            len(data_items) == 1 and
            data_items[0].semantic == "coefficients"
        )

    def connect(self, coverage, data_items, layer, options):
        """
        """

        data_item = data_items[0]
        for model_provider in self.model_providers:
            if model_provider.identifier == data_item.format:
                break
        else:
            raise Exception(
                "No model provider '%s' available." % data_item.format
            )

        time = options.get("time")
        if isinstance(time, Trim):
            time = (time.high - time.low) / 2 + time.low
        elif isinstance(time, Slice):
            time = time.value
        else:
            raise Exception("Missing 'time' parameter.")

        elevation = options.get("elevation") or 0
        subsets = options.get("subsets")
        bands = options.get("bands", ())
        try:
            bandname = bands[0]
            band = coverage.range_type.bands.get(identifier=bandname)
        except models.Band.DoesNotExist:
            raise Exception("Invalid band '%s' specified." % bandname)
        except IndexError:
            band = coverage.range_type[0]

        size_x, size_y = options["width"], options["height"]

        bbox = subsets.xy_bbox
        if subsets.srid != 4326:
            bbox = geos.Polygon.from_bbox(bbox).transform(4326).extent

        with log_duration("model evaluation", logger):

            coeff_min, coeff_max = (None, None)
            coeff_range = options["dimensions"].get("coeff")
            if coeff_range:
                try:
                    coeff_min, coeff_max = map(float, coeff_range[0].split(","))
                except:
                    raise Exception("Invalid coefficient range provided.")

            array = model_provider.evaluate(
                data_item, band.identifier, bbox, size_x, size_y, elevation,
                time, coeff_min, coeff_max
            )

            range_min, range_max = band.allowed_values
            data_range = options["dimensions"].get("range")
            if data_range:
                try:
                    range_min, range_max = map(float, data_range[0].split(","))
                except:
                    raise Exception("Invalid data range provided.")

            array = (array - range_min) / (range_max - range_min) * 255



        path = join("/vsimem", uuid4().hex)
        #path = "/tmp/fm_output.tif"
        driver = gdal.GetDriverByName("GTiff")
        ds = driver.Create(path, size_x, size_y, 1, gdal.GDT_Byte)

        gt = (
            bbox[0],
            float(bbox[2] - bbox[0]) / size_x,
            0,
            bbox[3],
            0,
            -float(bbox[3] - bbox[1]) / size_y
        )

        ds.SetGeoTransform(gt)

        band = ds.GetRasterBand(1)
        band.WriteArray(array)
        layer.data = path

        logger.info("Created tempfile %s" % layer.data)

    def disconnect(self, coverage, data_items, layer, options):
        """
        """

        logger.info("Removing tempfile %s" % layer.data)

        vsi.remove(layer.data)
