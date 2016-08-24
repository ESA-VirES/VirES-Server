#-------------------------------------------------------------------------------
#
#  Spherical Harmonic Expansion models WMS rendering
#
# Project: VirES
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
# pylint: disable=missing-docstring,no-self-use,unused-argument,too-few-public-methods

from eoxserver.core.util.iteratortools import pairwise_iterative
from eoxserver.contrib import mapserver as ms
from eoxserver.services.mapserver.wms.layerfactories.base import (
    BaseCoverageLayerFactory
)
from vires import models

class ForwardModelLayerFactory(BaseCoverageLayerFactory):
    handles = (models.ForwardModel,)
    suffixes = (None,)
    requires_connection = True

    def generate(self, eo_object, group_layer, suffix, options):
        forward_model = eo_object.cast()
        extent = forward_model.extent
        data_items = forward_model.data_items.filter(semantic="coefficients")
        #range_type = forward_model.range_type
        #offsite = self.offsite_color_from_range_type(range_type)
        #options = self.get_render_options(coverage)
        layer = self._create_layer(
            forward_model, forward_model.identifier, extent
        )

        ran = [float(s) for s in options['dimensions']['range'][0].split(',')] 
        interval = (ran[1]-ran[0])/40
        layer.type = ms.MS_LAYER_LINE
        layer.setConnectionType(ms.MS_RASTER + 4, "")  # CONTOUR
        #self.set_render_options(layer, offsite, options)
        layer.tileitem = None
        #layer.units = ms.MS_PIXELS
        layer.status = ms.MS_DEFAULT
        layer.setProcessing("BANDS=1")
        layer.setProcessing("CONTOUR_ITEM=elevation")
        layer.setProcessing("CONTOUR_INTERVAL=%s"%interval)
        layer.labelitem = "elevation"

        self._apply_styles(layer, ran[0], ran[1])
        yield layer, data_items

    def _apply_styles(self, layer, minvalue, maxvalue):

        def create_linear_style(name, layer, colors, minvalue, maxvalue):
            step = (maxvalue - minvalue) / float(len(colors) - 1)
            for i, (color_a, color_b) in enumerate(pairwise_iterative(colors)):
                cls = ms.classObj()
                cls.setExpression("([elevation] >= %s AND [elevation] < %s)"%((minvalue + i * step),(minvalue + (i + 1) * step)))
                cls.group = name

                style = ms.styleObj()
                style.width = 2
                style.mincolor = color_a
                style.maxcolor = color_b
                style.minvalue = minvalue + i * step
                style.maxvalue = minvalue + (i + 1) * step
                style.rangeitem = "elevation"

                label = ms.labelObj()
                label.color = ms.colorObj(255, 255, 255)
                label.outlinecolor = ms.colorObj(0, 0, 0)
                label.position = ms.MS_AUTO
                label.buffer = 10
                label.anglemode = ms.MS_FOLLOW
                label.partials = ms.MS_FALSE
                label.setText("(tostring([elevation],'%.2f'))")

                cls.addLabel(label)

                cls.insertStyle(style)
                layer.insertClass(cls)

        def create_style(name, layer, colors, minvalue, maxvalue):
            interval = (maxvalue - minvalue)
            for item in pairwise_iterative(colors):
                cls = ms.classObj()
                cls.group = name
                (color_a, perc_a), (color_b, perc_b) = item
                cls.setExpression("([elevation] >= %s AND [elevation] < %s)"%((minvalue + perc_a * interval),(minvalue + perc_b * interval)))

                style = ms.styleObj()
                style.width = 2
                style.mincolor = color_a
                style.maxcolor = color_b
                style.minvalue = minvalue + perc_a * interval
                style.maxvalue = minvalue + perc_b * interval
                style.rangeitem = "elevation"

                label = ms.labelObj()
                label.color = ms.colorObj(255, 255, 255)
                cls.addLabel(label)

                cls.insertStyle(style)
                layer.insertClass(cls)

        create_linear_style("blackwhite", layer, (
            ms.colorObj(0, 0, 0),
            ms.colorObj(255, 255, 255),
        ), minvalue, maxvalue)

        create_linear_style("coolwarm", layer, (
            ms.colorObj(255, 0, 0),
            ms.colorObj(255, 255, 255),
            ms.colorObj(0, 0, 255),
        ), minvalue, maxvalue)

        create_linear_style("rainbow", layer, (
            ms.colorObj(150, 0, 90),
            ms.colorObj(0, 0, 200),
            ms.colorObj(0, 25, 255),
            ms.colorObj(0, 152, 255),
            ms.colorObj(44, 255, 150),
            ms.colorObj(151, 255, 0),
            ms.colorObj(255, 234, 0),
            ms.colorObj(255, 111, 0),
            ms.colorObj(255, 0, 0),
        ), minvalue, maxvalue)

        create_linear_style("jet", layer, (
            ms.colorObj(0, 0, 144),
            ms.colorObj(0, 15, 255),
            ms.colorObj(0, 144, 255),
            ms.colorObj(15, 255, 238),
            ms.colorObj(144, 255, 112),
            ms.colorObj(255, 238, 0),
            ms.colorObj(255, 112, 0),
            ms.colorObj(238, 0, 0),
            ms.colorObj(127, 0, 0),
        ), minvalue, maxvalue)

        create_style("custom2", layer, (
            (ms.colorObj(0, 0, 0), 0.0),
            (ms.colorObj(3, 10, 255), 0.000000000001),
            (ms.colorObj(32, 74, 255), 0.1),
            (ms.colorObj(60, 138, 255), 0.2),
            (ms.colorObj(119, 196, 255), 0.3333),
            (ms.colorObj(240, 255, 255), 0.4666),
            (ms.colorObj(240, 255, 255), 0.5333),
            (ms.colorObj(242, 255, 127), 0.6666),
            (ms.colorObj(255, 255, 0), 0.8),
            (ms.colorObj(255, 131, 30), 0.9),
            (ms.colorObj(255, 8, 61), 0.999999999999),
            (ms.colorObj(255, 0, 255), 1.0),
        ), minvalue, maxvalue)

        create_linear_style("custom1", layer, (
            ms.colorObj(64, 0, 64),
            ms.colorObj(59, 0, 77),
            ms.colorObj(54, 0, 91),
            ms.colorObj(50, 0, 104),
            ms.colorObj(45, 0, 118),
            ms.colorObj(41, 0, 132),
            ms.colorObj(36, 0, 145),
            ms.colorObj(32, 0, 159),
            ms.colorObj(27, 0, 173),
            ms.colorObj(22, 0, 186),
            ms.colorObj(18, 0, 200),
            ms.colorObj(13, 0, 214),
            ms.colorObj(9, 0, 227),
            ms.colorObj(4, 0, 241),
            ms.colorObj(0, 0, 255),
            ms.colorObj(2, 23, 255),
            ms.colorObj(4, 46, 255),
            ms.colorObj(6, 69, 255),
            ms.colorObj(9, 92, 255),
            ms.colorObj(11, 115, 255),
            ms.colorObj(13, 139, 255),
            ms.colorObj(16, 162, 255),
            ms.colorObj(18, 185, 255),
            ms.colorObj(20, 208, 255),
            ms.colorObj(23, 231, 255),
            ms.colorObj(25, 255, 255),
            ms.colorObj(63, 255, 255),
            ms.colorObj(102, 255, 255),
            ms.colorObj(140, 255, 255),
            ms.colorObj(178, 255, 255),
            ms.colorObj(216, 255, 255),
            ms.colorObj(255, 255, 255),
            ms.colorObj(255, 255, 212),
            ms.colorObj(255, 255, 170),
            ms.colorObj(255, 255, 127),
            ms.colorObj(255, 255, 84),
            ms.colorObj(255, 255, 42),
            ms.colorObj(255, 255, 0),
            ms.colorObj(255, 237, 0),
            ms.colorObj(255, 221, 0),
            ms.colorObj(255, 204, 0),
            ms.colorObj(255, 186, 0),
            ms.colorObj(255, 170, 0),
            ms.colorObj(255, 153, 0),
            ms.colorObj(255, 135, 0),
            ms.colorObj(255, 119, 0),
            ms.colorObj(255, 102, 0),
            ms.colorObj(255, 84, 0),
            ms.colorObj(255, 68, 0),
            ms.colorObj(255, 51, 0),
            ms.colorObj(255, 33, 0),
            ms.colorObj(255, 17, 0),
            ms.colorObj(255, 0, 0),
            ms.colorObj(255, 0, 23),
            ms.colorObj(255, 0, 46),
            ms.colorObj(255, 0, 69),
            ms.colorObj(255, 0, 92),
            ms.colorObj(255, 0, 115),
            ms.colorObj(255, 0, 139),
            ms.colorObj(255, 0, 162),
            ms.colorObj(255, 0, 185),
            ms.colorObj(255, 0, 208),
            ms.colorObj(255, 0, 231),
            ms.colorObj(255, 0, 255),
        ), minvalue, maxvalue)
