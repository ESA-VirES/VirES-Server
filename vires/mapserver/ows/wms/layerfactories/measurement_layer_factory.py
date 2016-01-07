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


import os.path

from django.conf import settings

from eoxserver.core.util.iteratortools import pairwise_iterative
from eoxserver.contrib import mapserver as ms
from eoxserver.resources.coverages import crss
from eoxserver.services.mapserver.wms.layerfactories.base import (
    AbstractLayerFactory
)

from vires import models


class MeasurementLayerFactory(AbstractLayerFactory):
    handles = (models.Product, models.ProductCollection)
    suffixes = ("_measurement",)

    def generate(self, eo_object, group_layer, suffix, options):
        # don't generate any layers, but add the footprint as feature to the
        # group layer

        if group_layer:
            layer = group_layer
        else:
            layer = self._create_point_layer(
                eo_object.identifier + "_measurement"
            )
            self._apply_style(layer, 30000, 60000)

        # set the actual band
        layer.metadata.set("eoxs_band", options.get("bands", ("F",))[0])

        #shape = ms.shapeObj.fromWKT(eo_object.footprint.wkt)
        #shape.initValues(1)
        #shape.setValue(0, eo_object.identifier)
        #layer.addFeature(shape)
        coverage = eo_object.cast()
        data_items = coverage.data_items.filter(format="CDF")
        yield layer, data_items

    def generate_group(self, name):
        layer = self._create_point_layer(name)

        self._apply_style(layer, 20000, 50000)

        ## Dummy feature, or else empty groups will produce errors
        #shape = ms.shapeObj()
        #shape.initValues(1)
        #shape.setValue(0, "dummy")
        #layer.addFeature(shape)

        return layer

    def _create_point_layer(self, name):
        layer = ms.layerObj()
        layer.name = name
        layer.type = ms.MS_LAYER_POINT

        srid = 4326
        layer.setProjection(crss.asProj4Str(srid))
        layer.setMetaData("ows_srs", crss.asShortCode(srid))
        layer.setMetaData("wms_srs", crss.asShortCode(srid))

        layer.dump = True

        layer.header = os.path.join(settings.PROJECT_DIR, "conf", "outline_template_header.html")
        layer.template = os.path.join(settings.PROJECT_DIR, "conf", "outline_template_dataset.html")
        layer.footer = os.path.join(settings.PROJECT_DIR, "conf", "outline_template_footer.html")

        layer.setMetaData("gml_include_items", "all")
        layer.setMetaData("wms_include_items", "all")

        layer.addProcessing("ITEMS=value")

        layer.offsite = ms.colorObj(0, 0, 0)

        return layer

    def _apply_style(self, layer, minvalue, maxvalue):
        # trying to apply a rainbow scale effect. Does not seem to work, since
        # only the last appended style is used.
        cls = ms.classObj()
        colors = (
            ms.colorObj(127, 0, 127),  # lila
            ms.colorObj(0, 0, 255),    # blue
            ms.colorObj(0, 255, 255),  # light blue
            ms.colorObj(255, 255, 0),  # yellow
            ms.colorObj(255, 127, 0),  # orange
            ms.colorObj(255, 0, 0),    # red
        )

        step = (maxvalue - minvalue) / (len(colors) - 1)

        for i, (startcolor, endcolor) in enumerate(pairwise_iterative(colors)):
            style = ms.styleObj()
            style.mincolor = startcolor
            style.maxcolor = endcolor

            style.minvalue = minvalue + i * step
            style.maxvalue = minvalue + (i + 1) * step

            style.minsize = 0
            style.maxsize = 10 - i

            style.rangeitem = "value"
            style.setBinding(ms.MS_STYLE_BINDING_SIZE, "value")
            style.symbol = 1
            cls.insertStyle(style)

        cls.group = "rainbow"
        layer.insertClass(cls)
        layer.classgroup = "rainbow"
