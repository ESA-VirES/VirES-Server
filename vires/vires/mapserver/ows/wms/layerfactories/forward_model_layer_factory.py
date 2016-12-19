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

        layer = self._create_layer(
            forward_model, forward_model.identifier, extent
        )

        ran = [float(s) for s in options['dimensions']['range'][0].split(',')]

        if group_layer=="magma":
            return

        if 'contours' in options['dimensions']:
            contours = int(options['dimensions']['contours'][0])
        else:
            contours = 0

        if contours:
            interval = (ran[1]-ran[0])/40
            layer.type = ms.MS_LAYER_LINE
            layer.setConnectionType(ms.MS_RASTER + 4, "")  # CONTOUR
            layer.tileitem = None
            layer.status = ms.MS_DEFAULT
            layer.setProcessing("BANDS=1")
            layer.setProcessing("CONTOUR_ITEM=elevation")
            layer.setProcessing("CONTOUR_INTERVAL=%s"%interval)
            layer.labelitem = "elevation"

        self._apply_styles(layer, ran[0], ran[1], contours)
        yield layer, data_items

    def _apply_styles(self, layer, minvalue, maxvalue, contours):

        def create_linear_style(name, layer, colors, minvalue, maxvalue, contours):
            if contours:
                create_contours_linear_style(name, layer, colors, minvalue, maxvalue)
            else:
                create_base_linear_style(name, layer, colors, minvalue, maxvalue)

        def create_style(name, layer, colors, minvalue, maxvalue, contours):
            if contours:
                create_contours_style(name, layer, colors, minvalue, maxvalue)
            else:
                create_base_style(name, layer, colors, minvalue, maxvalue)

        def create_base_linear_style(name, layer, colors, minvalue, maxvalue):
            
            step = (maxvalue - minvalue) / float(len(colors) - 1)
            # Create style for values below range
            cls = ms.classObj()
            cls.setExpression("([pixel] <= %s)"%(minvalue))
            cls.group = name
            style = ms.styleObj()
            style.color = colors[0]
            cls.insertStyle(style)
            layer.insertClass(cls)

            # Create style for values above range
            cls = ms.classObj()
            cls.setExpression("([pixel] > %s)"%(maxvalue))
            cls.group = name
            style = ms.styleObj()
            style.color = colors[-1]
            cls.insertStyle(style)
            layer.insertClass(cls)

            for i, (color_a, color_b) in enumerate(pairwise_iterative(colors)):
                cls = ms.classObj()
                cls.setExpression("([pixel] >= %s AND [pixel] < %s)"%((minvalue + i * step),(minvalue + (i + 1) * step)))
                cls.group = name

                style = ms.styleObj()
                style.mincolor = color_a
                style.maxcolor = color_b
                style.minvalue = minvalue + i * step
                style.maxvalue = minvalue + (i + 1) * step
                style.rangeitem = ""
                cls.insertStyle(style)
                layer.insertClass(cls)

        def create_base_style(name, layer, colors, minvalue, maxvalue):

            # Create style for values below range
            cls = ms.classObj()
            cls.setExpression("([pixel] <= %s)"%(minvalue))
            cls.group = name
            style = ms.styleObj()
            style.color = colors[0][0]
            cls.insertStyle(style)
            layer.insertClass(cls)

            # Create style for values above range
            cls = ms.classObj()
            cls.setExpression("([pixel] > %s)"%(maxvalue))
            cls.group = name
            style = ms.styleObj()
            style.color = colors[-1][0]
            cls.insertStyle(style)
            layer.insertClass(cls)
            
            interval = (maxvalue - minvalue)
            for item in pairwise_iterative(colors):
                cls = ms.classObj()
                cls.group = name
                (color_a, perc_a), (color_b, perc_b) = item
                cls.setExpression("([pixel] >= %s AND [pixel] < %s)"%((minvalue + perc_a * interval),(minvalue + perc_b * interval)))

                style = ms.styleObj()
                style.mincolor = color_a
                style.maxcolor = color_b
                style.minvalue = minvalue + perc_a * interval
                style.maxvalue = minvalue + perc_b * interval
                style.rangeitem = ""
                cls.insertStyle(style)
                layer.insertClass(cls)

        def create_contours_linear_style(name, layer, colors, minvalue, maxvalue):

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
                if step<0.1:
                    label.setText("(tostring([elevation],'%.4f'))")
                elif step<1:
                    label.setText("(tostring([elevation],'%.2f'))")
                else:
                    label.setText("(tostring([elevation],'%g'))")
                cls.addLabel(label)

                cls.insertStyle(style)
                layer.insertClass(cls)

        def create_contours_style(name, layer, colors, minvalue, maxvalue):

            interval = (maxvalue - minvalue)
            step = (maxvalue - minvalue) / float(len(colors) - 1)
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
                label.outlinecolor = ms.colorObj(0, 0, 0)
                label.position = ms.MS_AUTO
                label.buffer = 10
                label.anglemode = ms.MS_FOLLOW
                label.partials = ms.MS_FALSE
                if step<0.1:
                    label.setText("(tostring([elevation],'%.4f'))")
                elif step<1:
                    label.setText("(tostring([elevation],'%.2f'))")
                else:
                    label.setText("(tostring([elevation],'%g'))")
                cls.addLabel(label)

                cls.insertStyle(style)
                layer.insertClass(cls)

        create_linear_style("blackwhite", layer, (
            ms.colorObj(0, 0, 0),
            ms.colorObj(255, 255, 255),
        ), minvalue, maxvalue, contours)

        create_linear_style("coolwarm", layer, (
            ms.colorObj(255, 0, 0),
            ms.colorObj(255, 255, 255),
            ms.colorObj(0, 0, 255),
        ), minvalue, maxvalue, contours)

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
        ), minvalue, maxvalue, contours)

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
        ), minvalue, maxvalue, contours)

        create_style("diverging_2", layer, (
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
        ), minvalue, maxvalue, contours)

        create_linear_style("diverging_1", layer, (
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
        ), minvalue, maxvalue, contours)

        create_linear_style("viridis", layer, (
            ms.colorObj(68,1,84),
            ms.colorObj(68,2,86),
            ms.colorObj(69,4,87),
            ms.colorObj(69,5,89),
            ms.colorObj(70,7,90),
            ms.colorObj(70,8,92),
            ms.colorObj(70,10,93),
            ms.colorObj(70,11,94),
            ms.colorObj(71,13,96),
            ms.colorObj(71,14,97),
            ms.colorObj(71,16,99),
            ms.colorObj(71,17,100),
            ms.colorObj(71,19,101),
            ms.colorObj(72,20,103),
            ms.colorObj(72,22,104),
            ms.colorObj(72,23,105),
            ms.colorObj(72,24,106),
            ms.colorObj(72,26,108),
            ms.colorObj(72,27,109),
            ms.colorObj(72,28,110),
            ms.colorObj(72,29,111),
            ms.colorObj(72,31,112),
            ms.colorObj(72,32,113),
            ms.colorObj(72,33,115),
            ms.colorObj(72,35,116),
            ms.colorObj(72,36,117),
            ms.colorObj(72,37,118),
            ms.colorObj(72,38,119),
            ms.colorObj(72,40,120),
            ms.colorObj(72,41,121),
            ms.colorObj(71,42,122),
            ms.colorObj(71,44,122),
            ms.colorObj(71,45,123),
            ms.colorObj(71,46,124),
            ms.colorObj(71,47,125),
            ms.colorObj(70,48,126),
            ms.colorObj(70,50,126),
            ms.colorObj(70,51,127),
            ms.colorObj(70,52,128),
            ms.colorObj(69,53,129),
            ms.colorObj(69,55,129),
            ms.colorObj(69,56,130),
            ms.colorObj(68,57,131),
            ms.colorObj(68,58,131),
            ms.colorObj(68,59,132),
            ms.colorObj(67,61,132),
            ms.colorObj(67,62,133),
            ms.colorObj(66,63,133),
            ms.colorObj(66,64,134),
            ms.colorObj(66,65,134),
            ms.colorObj(65,66,135),
            ms.colorObj(65,68,135),
            ms.colorObj(64,69,136),
            ms.colorObj(64,70,136),
            ms.colorObj(63,71,136),
            ms.colorObj(63,72,137),
            ms.colorObj(62,73,137),
            ms.colorObj(62,74,137),
            ms.colorObj(62,76,138),
            ms.colorObj(61,77,138),
            ms.colorObj(61,78,138),
            ms.colorObj(60,79,138),
            ms.colorObj(60,80,139),
            ms.colorObj(59,81,139),
            ms.colorObj(59,82,139),
            ms.colorObj(58,83,139),
            ms.colorObj(58,84,140),
            ms.colorObj(57,85,140),
            ms.colorObj(57,86,140),
            ms.colorObj(56,88,140),
            ms.colorObj(56,89,140),
            ms.colorObj(55,90,140),
            ms.colorObj(55,91,141),
            ms.colorObj(54,92,141),
            ms.colorObj(54,93,141),
            ms.colorObj(53,94,141),
            ms.colorObj(53,95,141),
            ms.colorObj(52,96,141),
            ms.colorObj(52,97,141),
            ms.colorObj(51,98,141),
            ms.colorObj(51,99,141),
            ms.colorObj(50,100,142),
            ms.colorObj(50,101,142),
            ms.colorObj(49,102,142),
            ms.colorObj(49,103,142),
            ms.colorObj(49,104,142),
            ms.colorObj(48,105,142),
            ms.colorObj(48,106,142),
            ms.colorObj(47,107,142),
            ms.colorObj(47,108,142),
            ms.colorObj(46,109,142),
            ms.colorObj(46,110,142),
            ms.colorObj(46,111,142),
            ms.colorObj(45,112,142),
            ms.colorObj(45,113,142),
            ms.colorObj(44,113,142),
            ms.colorObj(44,114,142),
            ms.colorObj(44,115,142),
            ms.colorObj(43,116,142),
            ms.colorObj(43,117,142),
            ms.colorObj(42,118,142),
            ms.colorObj(42,119,142),
            ms.colorObj(42,120,142),
            ms.colorObj(41,121,142),
            ms.colorObj(41,122,142),
            ms.colorObj(41,123,142),
            ms.colorObj(40,124,142),
            ms.colorObj(40,125,142),
            ms.colorObj(39,126,142),
            ms.colorObj(39,127,142),
            ms.colorObj(39,128,142),
            ms.colorObj(38,129,142),
            ms.colorObj(38,130,142),
            ms.colorObj(38,130,142),
            ms.colorObj(37,131,142),
            ms.colorObj(37,132,142),
            ms.colorObj(37,133,142),
            ms.colorObj(36,134,142),
            ms.colorObj(36,135,142),
            ms.colorObj(35,136,142),
            ms.colorObj(35,137,142),
            ms.colorObj(35,138,141),
            ms.colorObj(34,139,141),
            ms.colorObj(34,140,141),
            ms.colorObj(34,141,141),
            ms.colorObj(33,142,141),
            ms.colorObj(33,143,141),
            ms.colorObj(33,144,141),
            ms.colorObj(33,145,140),
            ms.colorObj(32,146,140),
            ms.colorObj(32,146,140),
            ms.colorObj(32,147,140),
            ms.colorObj(31,148,140),
            ms.colorObj(31,149,139),
            ms.colorObj(31,150,139),
            ms.colorObj(31,151,139),
            ms.colorObj(31,152,139),
            ms.colorObj(31,153,138),
            ms.colorObj(31,154,138),
            ms.colorObj(30,155,138),
            ms.colorObj(30,156,137),
            ms.colorObj(30,157,137),
            ms.colorObj(31,158,137),
            ms.colorObj(31,159,136),
            ms.colorObj(31,160,136),
            ms.colorObj(31,161,136),
            ms.colorObj(31,161,135),
            ms.colorObj(31,162,135),
            ms.colorObj(32,163,134),
            ms.colorObj(32,164,134),
            ms.colorObj(33,165,133),
            ms.colorObj(33,166,133),
            ms.colorObj(34,167,133),
            ms.colorObj(34,168,132),
            ms.colorObj(35,169,131),
            ms.colorObj(36,170,131),
            ms.colorObj(37,171,130),
            ms.colorObj(37,172,130),
            ms.colorObj(38,173,129),
            ms.colorObj(39,173,129),
            ms.colorObj(40,174,128),
            ms.colorObj(41,175,127),
            ms.colorObj(42,176,127),
            ms.colorObj(44,177,126),
            ms.colorObj(45,178,125),
            ms.colorObj(46,179,124),
            ms.colorObj(47,180,124),
            ms.colorObj(49,181,123),
            ms.colorObj(50,182,122),
            ms.colorObj(52,182,121),
            ms.colorObj(53,183,121),
            ms.colorObj(55,184,120),
            ms.colorObj(56,185,119),
            ms.colorObj(58,186,118),
            ms.colorObj(59,187,117),
            ms.colorObj(61,188,116),
            ms.colorObj(63,188,115),
            ms.colorObj(64,189,114),
            ms.colorObj(66,190,113),
            ms.colorObj(68,191,112),
            ms.colorObj(70,192,111),
            ms.colorObj(72,193,110),
            ms.colorObj(74,193,109),
            ms.colorObj(76,194,108),
            ms.colorObj(78,195,107),
            ms.colorObj(80,196,106),
            ms.colorObj(82,197,105),
            ms.colorObj(84,197,104),
            ms.colorObj(86,198,103),
            ms.colorObj(88,199,101),
            ms.colorObj(90,200,100),
            ms.colorObj(92,200,99),
            ms.colorObj(94,201,98),
            ms.colorObj(96,202,96),
            ms.colorObj(99,203,95),
            ms.colorObj(101,203,94),
            ms.colorObj(103,204,92),
            ms.colorObj(105,205,91),
            ms.colorObj(108,205,90),
            ms.colorObj(110,206,88),
            ms.colorObj(112,207,87),
            ms.colorObj(115,208,86),
            ms.colorObj(117,208,84),
            ms.colorObj(119,209,83),
            ms.colorObj(122,209,81),
            ms.colorObj(124,210,80),
            ms.colorObj(127,211,78),
            ms.colorObj(129,211,77),
            ms.colorObj(132,212,75),
            ms.colorObj(134,213,73),
            ms.colorObj(137,213,72),
            ms.colorObj(139,214,70),
            ms.colorObj(142,214,69),
            ms.colorObj(144,215,67),
            ms.colorObj(147,215,65),
            ms.colorObj(149,216,64),
            ms.colorObj(152,216,62),
            ms.colorObj(155,217,60),
            ms.colorObj(157,217,59),
            ms.colorObj(160,218,57),
            ms.colorObj(162,218,55),
            ms.colorObj(165,219,54),
            ms.colorObj(168,219,52),
            ms.colorObj(170,220,50),
            ms.colorObj(173,220,48),
            ms.colorObj(176,221,47),
            ms.colorObj(178,221,45),
            ms.colorObj(181,222,43),
            ms.colorObj(184,222,41),
            ms.colorObj(186,222,40),
            ms.colorObj(189,223,38),
            ms.colorObj(192,223,37),
            ms.colorObj(194,223,35),
            ms.colorObj(197,224,33),
            ms.colorObj(200,224,32),
            ms.colorObj(202,225,31),
            ms.colorObj(205,225,29),
            ms.colorObj(208,225,28),
            ms.colorObj(210,226,27),
            ms.colorObj(213,226,26),
            ms.colorObj(216,226,25),
            ms.colorObj(218,227,25),
            ms.colorObj(221,227,24),
            ms.colorObj(223,227,24),
            ms.colorObj(226,228,24),
            ms.colorObj(229,228,25),
            ms.colorObj(231,228,25),
            ms.colorObj(234,229,26),
            ms.colorObj(236,229,27),
            ms.colorObj(239,229,28),
            ms.colorObj(241,229,29),
            ms.colorObj(244,230,30),
            ms.colorObj(246,230,32),
            ms.colorObj(248,230,33),
            ms.colorObj(251,231,35),
            ms.colorObj(253,231,37),
        ), minvalue, maxvalue, contours)
        
        create_linear_style("inferno", layer, (
            ms.colorObj(0,0,4),
            ms.colorObj(1,0,5),
            ms.colorObj(1,1,6),
            ms.colorObj(1,1,8),
            ms.colorObj(2,1,10),
            ms.colorObj(2,2,12),
            ms.colorObj(2,2,14),
            ms.colorObj(3,2,16),
            ms.colorObj(4,3,18),
            ms.colorObj(4,3,20),
            ms.colorObj(5,4,23),
            ms.colorObj(6,4,25),
            ms.colorObj(7,5,27),
            ms.colorObj(8,5,29),
            ms.colorObj(9,6,31),
            ms.colorObj(10,7,34),
            ms.colorObj(11,7,36),
            ms.colorObj(12,8,38),
            ms.colorObj(13,8,41),
            ms.colorObj(14,9,43),
            ms.colorObj(16,9,45),
            ms.colorObj(17,10,48),
            ms.colorObj(18,10,50),
            ms.colorObj(20,11,52),
            ms.colorObj(21,11,55),
            ms.colorObj(22,11,57),
            ms.colorObj(24,12,60),
            ms.colorObj(25,12,62),
            ms.colorObj(27,12,65),
            ms.colorObj(28,12,67),
            ms.colorObj(30,12,69),
            ms.colorObj(31,12,72),
            ms.colorObj(33,12,74),
            ms.colorObj(35,12,76),
            ms.colorObj(36,12,79),
            ms.colorObj(38,12,81),
            ms.colorObj(40,11,83),
            ms.colorObj(41,11,85),
            ms.colorObj(43,11,87),
            ms.colorObj(45,11,89),
            ms.colorObj(47,10,91),
            ms.colorObj(49,10,92),
            ms.colorObj(50,10,94),
            ms.colorObj(52,10,95),
            ms.colorObj(54,9,97),
            ms.colorObj(56,9,98),
            ms.colorObj(57,9,99),
            ms.colorObj(59,9,100),
            ms.colorObj(61,9,101),
            ms.colorObj(62,9,102),
            ms.colorObj(64,10,103),
            ms.colorObj(66,10,104),
            ms.colorObj(68,10,104),
            ms.colorObj(69,10,105),
            ms.colorObj(71,11,106),
            ms.colorObj(73,11,106),
            ms.colorObj(74,12,107),
            ms.colorObj(76,12,107),
            ms.colorObj(77,13,108),
            ms.colorObj(79,13,108),
            ms.colorObj(81,14,108),
            ms.colorObj(82,14,109),
            ms.colorObj(84,15,109),
            ms.colorObj(85,15,109),
            ms.colorObj(87,16,110),
            ms.colorObj(89,16,110),
            ms.colorObj(90,17,110),
            ms.colorObj(92,18,110),
            ms.colorObj(93,18,110),
            ms.colorObj(95,19,110),
            ms.colorObj(97,19,110),
            ms.colorObj(98,20,110),
            ms.colorObj(100,21,110),
            ms.colorObj(101,21,110),
            ms.colorObj(103,22,110),
            ms.colorObj(105,22,110),
            ms.colorObj(106,23,110),
            ms.colorObj(108,24,110),
            ms.colorObj(109,24,110),
            ms.colorObj(111,25,110),
            ms.colorObj(113,25,110),
            ms.colorObj(114,26,110),
            ms.colorObj(116,26,110),
            ms.colorObj(117,27,110),
            ms.colorObj(119,28,109),
            ms.colorObj(120,28,109),
            ms.colorObj(122,29,109),
            ms.colorObj(124,29,109),
            ms.colorObj(125,30,109),
            ms.colorObj(127,30,108),
            ms.colorObj(128,31,108),
            ms.colorObj(130,32,108),
            ms.colorObj(132,32,107),
            ms.colorObj(133,33,107),
            ms.colorObj(135,33,107),
            ms.colorObj(136,34,106),
            ms.colorObj(138,34,106),
            ms.colorObj(140,35,105),
            ms.colorObj(141,35,105),
            ms.colorObj(143,36,105),
            ms.colorObj(144,37,104),
            ms.colorObj(146,37,104),
            ms.colorObj(147,38,103),
            ms.colorObj(149,38,103),
            ms.colorObj(151,39,102),
            ms.colorObj(152,39,102),
            ms.colorObj(154,40,101),
            ms.colorObj(155,41,100),
            ms.colorObj(157,41,100),
            ms.colorObj(159,42,99),
            ms.colorObj(160,42,99),
            ms.colorObj(162,43,98),
            ms.colorObj(163,44,97),
            ms.colorObj(165,44,96),
            ms.colorObj(166,45,96),
            ms.colorObj(168,46,95),
            ms.colorObj(169,46,94),
            ms.colorObj(171,47,94),
            ms.colorObj(173,48,93),
            ms.colorObj(174,48,92),
            ms.colorObj(176,49,91),
            ms.colorObj(177,50,90),
            ms.colorObj(179,50,90),
            ms.colorObj(180,51,89),
            ms.colorObj(182,52,88),
            ms.colorObj(183,53,87),
            ms.colorObj(185,53,86),
            ms.colorObj(186,54,85),
            ms.colorObj(188,55,84),
            ms.colorObj(189,56,83),
            ms.colorObj(191,57,82),
            ms.colorObj(192,58,81),
            ms.colorObj(193,58,80),
            ms.colorObj(195,59,79),
            ms.colorObj(196,60,78),
            ms.colorObj(198,61,77),
            ms.colorObj(199,62,76),
            ms.colorObj(200,63,75),
            ms.colorObj(202,64,74),
            ms.colorObj(203,65,73),
            ms.colorObj(204,66,72),
            ms.colorObj(206,67,71),
            ms.colorObj(207,68,70),
            ms.colorObj(208,69,69),
            ms.colorObj(210,70,68),
            ms.colorObj(211,71,67),
            ms.colorObj(212,72,66),
            ms.colorObj(213,74,65),
            ms.colorObj(215,75,63),
            ms.colorObj(216,76,62),
            ms.colorObj(217,77,61),
            ms.colorObj(218,78,60),
            ms.colorObj(219,80,59),
            ms.colorObj(221,81,58),
            ms.colorObj(222,82,56),
            ms.colorObj(223,83,55),
            ms.colorObj(224,85,54),
            ms.colorObj(225,86,53),
            ms.colorObj(226,87,52),
            ms.colorObj(227,89,51),
            ms.colorObj(228,90,49),
            ms.colorObj(229,92,48),
            ms.colorObj(230,93,47),
            ms.colorObj(231,94,46),
            ms.colorObj(232,96,45),
            ms.colorObj(233,97,43),
            ms.colorObj(234,99,42),
            ms.colorObj(235,100,41),
            ms.colorObj(235,102,40),
            ms.colorObj(236,103,38),
            ms.colorObj(237,105,37),
            ms.colorObj(238,106,36),
            ms.colorObj(239,108,35),
            ms.colorObj(239,110,33),
            ms.colorObj(240,111,32),
            ms.colorObj(241,113,31),
            ms.colorObj(241,115,29),
            ms.colorObj(242,116,28),
            ms.colorObj(243,118,27),
            ms.colorObj(243,120,25),
            ms.colorObj(244,121,24),
            ms.colorObj(245,123,23),
            ms.colorObj(245,125,21),
            ms.colorObj(246,126,20),
            ms.colorObj(246,128,19),
            ms.colorObj(247,130,18),
            ms.colorObj(247,132,16),
            ms.colorObj(248,133,15),
            ms.colorObj(248,135,14),
            ms.colorObj(248,137,12),
            ms.colorObj(249,139,11),
            ms.colorObj(249,140,10),
            ms.colorObj(249,142,9),
            ms.colorObj(250,144,8),
            ms.colorObj(250,146,7),
            ms.colorObj(250,148,7),
            ms.colorObj(251,150,6),
            ms.colorObj(251,151,6),
            ms.colorObj(251,153,6),
            ms.colorObj(251,155,6),
            ms.colorObj(251,157,7),
            ms.colorObj(252,159,7),
            ms.colorObj(252,161,8),
            ms.colorObj(252,163,9),
            ms.colorObj(252,165,10),
            ms.colorObj(252,166,12),
            ms.colorObj(252,168,13),
            ms.colorObj(252,170,15),
            ms.colorObj(252,172,17),
            ms.colorObj(252,174,18),
            ms.colorObj(252,176,20),
            ms.colorObj(252,178,22),
            ms.colorObj(252,180,24),
            ms.colorObj(251,182,26),
            ms.colorObj(251,184,29),
            ms.colorObj(251,186,31),
            ms.colorObj(251,188,33),
            ms.colorObj(251,190,35),
            ms.colorObj(250,192,38),
            ms.colorObj(250,194,40),
            ms.colorObj(250,196,42),
            ms.colorObj(250,198,45),
            ms.colorObj(249,199,47),
            ms.colorObj(249,201,50),
            ms.colorObj(249,203,53),
            ms.colorObj(248,205,55),
            ms.colorObj(248,207,58),
            ms.colorObj(247,209,61),
            ms.colorObj(247,211,64),
            ms.colorObj(246,213,67),
            ms.colorObj(246,215,70),
            ms.colorObj(245,217,73),
            ms.colorObj(245,219,76),
            ms.colorObj(244,221,79),
            ms.colorObj(244,223,83),
            ms.colorObj(244,225,86),
            ms.colorObj(243,227,90),
            ms.colorObj(243,229,93),
            ms.colorObj(242,230,97),
            ms.colorObj(242,232,101),
            ms.colorObj(242,234,105),
            ms.colorObj(241,236,109),
            ms.colorObj(241,237,113),
            ms.colorObj(241,239,117),
            ms.colorObj(241,241,121),
            ms.colorObj(242,242,125),
            ms.colorObj(242,244,130),
            ms.colorObj(243,245,134),
            ms.colorObj(243,246,138),
            ms.colorObj(244,248,142),
            ms.colorObj(245,249,146),
            ms.colorObj(246,250,150),
            ms.colorObj(248,251,154),
            ms.colorObj(249,252,157),
            ms.colorObj(250,253,161),
            ms.colorObj(252,255,164),
        ), minvalue, maxvalue, contours)
    
        create_style("hsv", layer, (
            (ms.colorObj(255,0,0), 0.0),
            (ms.colorObj(253,255,2), 0.169),
            (ms.colorObj(247,255,2), 0.173),
            (ms.colorObj(0,252,4), 0.337),
            (ms.colorObj(0,252,10), 0.341),
            (ms.colorObj(1,249,255), 0.506),
            (ms.colorObj(2,0,253), 0.671),
            (ms.colorObj(8,0,253), 0.675),
            (ms.colorObj(255,0,251), 0.839),
            (ms.colorObj(255,0,245), 0.843),
            (ms.colorObj(255,0,6), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("hot", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(230,0,0), 0.3),
            (ms.colorObj(255,210,0), 0.6),
            (ms.colorObj(255,255,255), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("cool", layer, (
            (ms.colorObj(0,255,255), 0.0),
            (ms.colorObj(255,0,255), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("spring", layer, (
            (ms.colorObj(255,0,255), 0.0),
            (ms.colorObj(255,255,0), 1.0),
        ), minvalue, maxvalue, contours)
   
        create_style("summer", layer, (
            (ms.colorObj(0,128,102), 0.0),
            (ms.colorObj(255,255,102), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("autumn", layer, (
            (ms.colorObj(255,0,0), 0.0),
            (ms.colorObj(255,255,0), 1.0),
        ), minvalue, maxvalue, contours)
    
        create_style("winter", layer, (
            (ms.colorObj(0,0,255), 0.0),
            (ms.colorObj(0,255,128), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("bone", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(84,84,116), 0.376),
            (ms.colorObj(169,200,200), 0.753),
            (ms.colorObj(255,255,255), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("copper", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(255,160,102), 0.804),
            (ms.colorObj(255,199,127), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("greys", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(255,255,255), 1.0),
        ), minvalue, maxvalue, contours)

   
        create_style("yignbu", layer, (
            (ms.colorObj(8,29,88), 0.0),
            (ms.colorObj(37,52,148), 0.125),
            (ms.colorObj(34,94,168), 0.25),
            (ms.colorObj(29,145,192), 0.375),
            (ms.colorObj(65,182,196), 0.5),
            (ms.colorObj(127,205,187), 0.625),
            (ms.colorObj(199,233,180), 0.75),
            (ms.colorObj(237,248,217), 0.875),
            (ms.colorObj(255,255,217), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("greens", layer, (
            (ms.colorObj(0,68,27), 0.0),
            (ms.colorObj(0,109,44), 0.125),
            (ms.colorObj(35,139,69), 0.25),
            (ms.colorObj(65,171,93), 0.375),
            (ms.colorObj(116,196,118), 0.5),
            (ms.colorObj(161,217,155), 0.625),
            (ms.colorObj(199,233,192), 0.75),
            (ms.colorObj(229,245,224), 0.875),
            (ms.colorObj(247,252,245), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("yiorrd", layer, (
            (ms.colorObj(128,0,38), 0.0),
            (ms.colorObj(189,0,38), 0.125),
            (ms.colorObj(227,26,28), 0.25),
            (ms.colorObj(252,78,42), 0.375),
            (ms.colorObj(253,141,60), 0.5),
            (ms.colorObj(254,178,76), 0.625),
            (ms.colorObj(254,217,118), 0.75),
            (ms.colorObj(255,237,160), 0.875),
            (ms.colorObj(255,255,204), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("bluered", layer, (
            (ms.colorObj(0,0,255), 0.0),
            (ms.colorObj(255,0,0), 1.0),
        ), minvalue, maxvalue, contours)
   
        create_style("rdbu", layer, (
            (ms.colorObj(5,10,172), 0.0),
            (ms.colorObj(106,137,247), 0.35),
            (ms.colorObj(190,190,190), 0.5),
            (ms.colorObj(220,170,132), 0.6),
            (ms.colorObj(230,145,90), 0.7),
            (ms.colorObj(178,10,28), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("picnic", layer, (
            (ms.colorObj(0,0,255), 0.0),
            (ms.colorObj(51,153,255), 0.1),
            (ms.colorObj(102,204,255), 0.2),
            (ms.colorObj(153,204,255), 0.3),
            (ms.colorObj(204,204,255), 0.4),
            (ms.colorObj(255,255,255), 0.5),
            (ms.colorObj(255,204,255), 0.6),
            (ms.colorObj(255,153,255), 0.7),
            (ms.colorObj(255,102,204), 0.8),
            (ms.colorObj(255,102,102), 0.9),
            (ms.colorObj(255,0,0), 1.0),
        ), minvalue, maxvalue, contours)
  
        create_style("portland", layer, (
            (ms.colorObj(12,51,131), 0.0),
            (ms.colorObj(10,136,186), 0.25),
            (ms.colorObj(242,211,56), 0.5),
            (ms.colorObj(242,143,56), 0.75),
            (ms.colorObj(217,30,30), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("blackbody", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(230,0,0), 0.2),
            (ms.colorObj(230,210,0), 0.4),
            (ms.colorObj(255,255,255), 0.7),
            (ms.colorObj(160,200,255), 1.0),
        ), minvalue, maxvalue, contours)

        create_style("earth", layer, (
            (ms.colorObj(0,0,130), 0.0),
            (ms.colorObj(0,180,180), 0.1),
            (ms.colorObj(40,210,40), 0.2),
            (ms.colorObj(230,230,50), 0.4),
            (ms.colorObj(120,70,20), 0.6),
            (ms.colorObj(255,255,255), 1.0),
        ), minvalue, maxvalue, contours)
        
        create_style("electric", layer, (
            (ms.colorObj(0,0,0), 0.0),
            (ms.colorObj(30,0,100), 0.15),
            (ms.colorObj(120,0,100), 0.4),
            (ms.colorObj(160,90,0), 0.6),
            (ms.colorObj(230,200,0), 0.8),
            (ms.colorObj(255,250,220), 1.0),
        ), minvalue, maxvalue, contours)



        create_linear_style("magma", layer, (
            ms.colorObj(0,0,4),
            ms.colorObj(1,0,5),
            ms.colorObj(1,1,6),
            ms.colorObj(1,1,8),
            ms.colorObj(2,1,9),
            ms.colorObj(2,2,11),
            ms.colorObj(2,2,13),
            ms.colorObj(3,3,15),
            ms.colorObj(3,3,18),
            ms.colorObj(4,4,20),
            ms.colorObj(5,4,22),
            ms.colorObj(6,5,24),
            ms.colorObj(6,5,26),
            ms.colorObj(7,6,28),
            ms.colorObj(8,7,30),
            ms.colorObj(9,7,32),
            ms.colorObj(10,8,34),
            ms.colorObj(11,9,36),
            ms.colorObj(12,9,38),
            ms.colorObj(13,10,41),
            ms.colorObj(14,11,43),
            ms.colorObj(16,11,45),
            ms.colorObj(17,12,47),
            ms.colorObj(18,13,49),
            ms.colorObj(19,13,52),
            ms.colorObj(20,14,54),
            ms.colorObj(21,14,56),
            ms.colorObj(22,15,59),
            ms.colorObj(24,15,61),
            ms.colorObj(25,16,63),
            ms.colorObj(26,16,66),
            ms.colorObj(28,16,68),
            ms.colorObj(29,17,71),
            ms.colorObj(30,17,73),
            ms.colorObj(32,17,75),
            ms.colorObj(33,17,78),
            ms.colorObj(34,17,80),
            ms.colorObj(36,18,83),
            ms.colorObj(37,18,85),
            ms.colorObj(39,18,88),
            ms.colorObj(41,17,90),
            ms.colorObj(42,17,92),
            ms.colorObj(44,17,95),
            ms.colorObj(45,17,97),
            ms.colorObj(47,17,99),
            ms.colorObj(49,17,101),
            ms.colorObj(51,16,103),
            ms.colorObj(52,16,105),
            ms.colorObj(54,16,107),
            ms.colorObj(56,16,108),
            ms.colorObj(57,15,110),
            ms.colorObj(59,15,112),
            ms.colorObj(61,15,113),
            ms.colorObj(63,15,114),
            ms.colorObj(64,15,116),
            ms.colorObj(66,15,117),
            ms.colorObj(68,15,118),
            ms.colorObj(69,16,119),
            ms.colorObj(71,16,120),
            ms.colorObj(73,16,120),
            ms.colorObj(74,16,121),
            ms.colorObj(76,17,122),
            ms.colorObj(78,17,123),
            ms.colorObj(79,18,123),
            ms.colorObj(81,18,124),
            ms.colorObj(82,19,124),
            ms.colorObj(84,19,125),
            ms.colorObj(86,20,125),
            ms.colorObj(87,21,126),
            ms.colorObj(89,21,126),
            ms.colorObj(90,22,126),
            ms.colorObj(92,22,127),
            ms.colorObj(93,23,127),
            ms.colorObj(95,24,127),
            ms.colorObj(96,24,128),
            ms.colorObj(98,25,128),
            ms.colorObj(100,26,128),
            ms.colorObj(101,26,128),
            ms.colorObj(103,27,128),
            ms.colorObj(104,28,129),
            ms.colorObj(106,28,129),
            ms.colorObj(107,29,129),
            ms.colorObj(109,29,129),
            ms.colorObj(110,30,129),
            ms.colorObj(112,31,129),
            ms.colorObj(114,31,129),
            ms.colorObj(115,32,129),
            ms.colorObj(117,33,129),
            ms.colorObj(118,33,129),
            ms.colorObj(120,34,129),
            ms.colorObj(121,34,130),
            ms.colorObj(123,35,130),
            ms.colorObj(124,35,130),
            ms.colorObj(126,36,130),
            ms.colorObj(128,37,130),
            ms.colorObj(129,37,129),
            ms.colorObj(131,38,129),
            ms.colorObj(132,38,129),
            ms.colorObj(134,39,129),
            ms.colorObj(136,39,129),
            ms.colorObj(137,40,129),
            ms.colorObj(139,41,129),
            ms.colorObj(140,41,129),
            ms.colorObj(142,42,129),
            ms.colorObj(144,42,129),
            ms.colorObj(145,43,129),
            ms.colorObj(147,43,128),
            ms.colorObj(148,44,128),
            ms.colorObj(150,44,128),
            ms.colorObj(152,45,128),
            ms.colorObj(153,45,128),
            ms.colorObj(155,46,127),
            ms.colorObj(156,46,127),
            ms.colorObj(158,47,127),
            ms.colorObj(160,47,127),
            ms.colorObj(161,48,126),
            ms.colorObj(163,48,126),
            ms.colorObj(165,49,126),
            ms.colorObj(166,49,125),
            ms.colorObj(168,50,125),
            ms.colorObj(170,51,125),
            ms.colorObj(171,51,124),
            ms.colorObj(173,52,124),
            ms.colorObj(174,52,123),
            ms.colorObj(176,53,123),
            ms.colorObj(178,53,123),
            ms.colorObj(179,54,122),
            ms.colorObj(181,54,122),
            ms.colorObj(183,55,121),
            ms.colorObj(184,55,121),
            ms.colorObj(186,56,120),
            ms.colorObj(188,57,120),
            ms.colorObj(189,57,119),
            ms.colorObj(191,58,119),
            ms.colorObj(192,58,118),
            ms.colorObj(194,59,117),
            ms.colorObj(196,60,117),
            ms.colorObj(197,60,116),
            ms.colorObj(199,61,115),
            ms.colorObj(200,62,115),
            ms.colorObj(202,62,114),
            ms.colorObj(204,63,113),
            ms.colorObj(205,64,113),
            ms.colorObj(207,64,112),
            ms.colorObj(208,65,111),
            ms.colorObj(210,66,111),
            ms.colorObj(211,67,110),
            ms.colorObj(213,68,109),
            ms.colorObj(214,69,108),
            ms.colorObj(216,69,108),
            ms.colorObj(217,70,107),
            ms.colorObj(219,71,106),
            ms.colorObj(220,72,105),
            ms.colorObj(222,73,104),
            ms.colorObj(223,74,104),
            ms.colorObj(224,76,103),
            ms.colorObj(226,77,102),
            ms.colorObj(227,78,101),
            ms.colorObj(228,79,100),
            ms.colorObj(229,80,100),
            ms.colorObj(231,82,99),
            ms.colorObj(232,83,98),
            ms.colorObj(233,84,98),
            ms.colorObj(234,86,97),
            ms.colorObj(235,87,96),
            ms.colorObj(236,88,96),
            ms.colorObj(237,90,95),
            ms.colorObj(238,91,94),
            ms.colorObj(239,93,94),
            ms.colorObj(240,95,94),
            ms.colorObj(241,96,93),
            ms.colorObj(242,98,93),
            ms.colorObj(242,100,92),
            ms.colorObj(243,101,92),
            ms.colorObj(244,103,92),
            ms.colorObj(244,105,92),
            ms.colorObj(245,107,92),
            ms.colorObj(246,108,92),
            ms.colorObj(246,110,92),
            ms.colorObj(247,112,92),
            ms.colorObj(247,114,92),
            ms.colorObj(248,116,92),
            ms.colorObj(248,118,92),
            ms.colorObj(249,120,93),
            ms.colorObj(249,121,93),
            ms.colorObj(249,123,93),
            ms.colorObj(250,125,94),
            ms.colorObj(250,127,94),
            ms.colorObj(250,129,95),
            ms.colorObj(251,131,95),
            ms.colorObj(251,133,96),
            ms.colorObj(251,135,97),
            ms.colorObj(252,137,97),
            ms.colorObj(252,138,98),
            ms.colorObj(252,140,99),
            ms.colorObj(252,142,100),
            ms.colorObj(252,144,101),
            ms.colorObj(253,146,102),
            ms.colorObj(253,148,103),
            ms.colorObj(253,150,104),
            ms.colorObj(253,152,105),
            ms.colorObj(253,154,106),
            ms.colorObj(253,155,107),
            ms.colorObj(254,157,108),
            ms.colorObj(254,159,109),
            ms.colorObj(254,161,110),
            ms.colorObj(254,163,111),
            ms.colorObj(254,165,113),
            ms.colorObj(254,167,114),
            ms.colorObj(254,169,115),
            ms.colorObj(254,170,116),
            ms.colorObj(254,172,118),
            ms.colorObj(254,174,119),
            ms.colorObj(254,176,120),
            ms.colorObj(254,178,122),
            ms.colorObj(254,180,123),
            ms.colorObj(254,182,124),
            ms.colorObj(254,183,126),
            ms.colorObj(254,185,127),
            ms.colorObj(254,187,129),
            ms.colorObj(254,189,130),
            ms.colorObj(254,191,132),
            ms.colorObj(254,193,133),
            ms.colorObj(254,194,135),
            ms.colorObj(254,196,136),
            ms.colorObj(254,198,138),
            ms.colorObj(254,200,140),
            ms.colorObj(254,202,141),
            ms.colorObj(254,204,143),
            ms.colorObj(254,205,144),
            ms.colorObj(254,207,146),
            ms.colorObj(254,209,148),
            ms.colorObj(254,211,149),
            ms.colorObj(254,213,151),
            ms.colorObj(254,215,153),
            ms.colorObj(254,216,154),
            ms.colorObj(253,218,156),
            ms.colorObj(253,220,158),
            ms.colorObj(253,222,160),
            ms.colorObj(253,224,161),
            ms.colorObj(253,226,163),
            ms.colorObj(253,227,165),
            ms.colorObj(253,229,167),
            ms.colorObj(253,231,169),
            ms.colorObj(253,233,170),
            ms.colorObj(253,235,172),
            ms.colorObj(252,236,174),
            ms.colorObj(252,238,176),
            ms.colorObj(252,240,178),
            ms.colorObj(252,242,180),
            ms.colorObj(252,244,182),
            ms.colorObj(252,246,184),
            ms.colorObj(252,247,185),
            ms.colorObj(252,249,187),
            ms.colorObj(252,251,189),
            ms.colorObj(252,253,191),
        ), minvalue, maxvalue, contours)


        create_linear_style("plasma", layer, (    
            ms.colorObj(13,8,135),
            ms.colorObj(16,7,136),
            ms.colorObj(19,7,137),
            ms.colorObj(22,7,138),
            ms.colorObj(25,6,140),
            ms.colorObj(27,6,141),
            ms.colorObj(29,6,142),
            ms.colorObj(32,6,143),
            ms.colorObj(34,6,144),
            ms.colorObj(36,6,145),
            ms.colorObj(38,5,145),
            ms.colorObj(40,5,146),
            ms.colorObj(42,5,147),
            ms.colorObj(44,5,148),
            ms.colorObj(46,5,149),
            ms.colorObj(47,5,150),
            ms.colorObj(49,5,151),
            ms.colorObj(51,5,151),
            ms.colorObj(53,4,152),
            ms.colorObj(55,4,153),
            ms.colorObj(56,4,154),
            ms.colorObj(58,4,154),
            ms.colorObj(60,4,155),
            ms.colorObj(62,4,156),
            ms.colorObj(63,4,156),
            ms.colorObj(65,4,157),
            ms.colorObj(67,3,158),
            ms.colorObj(68,3,158),
            ms.colorObj(70,3,159),
            ms.colorObj(72,3,159),
            ms.colorObj(73,3,160),
            ms.colorObj(75,3,161),
            ms.colorObj(76,2,161),
            ms.colorObj(78,2,162),
            ms.colorObj(80,2,162),
            ms.colorObj(81,2,163),
            ms.colorObj(83,2,163),
            ms.colorObj(85,2,164),
            ms.colorObj(86,1,164),
            ms.colorObj(88,1,164),
            ms.colorObj(89,1,165),
            ms.colorObj(91,1,165),
            ms.colorObj(92,1,166),
            ms.colorObj(94,1,166),
            ms.colorObj(96,1,166),
            ms.colorObj(97,0,167),
            ms.colorObj(99,0,167),
            ms.colorObj(100,0,167),
            ms.colorObj(102,0,167),
            ms.colorObj(103,0,168),
            ms.colorObj(105,0,168),
            ms.colorObj(106,0,168),
            ms.colorObj(108,0,168),
            ms.colorObj(110,0,168),
            ms.colorObj(111,0,168),
            ms.colorObj(113,0,168),
            ms.colorObj(114,1,168),
            ms.colorObj(116,1,168),
            ms.colorObj(117,1,168),
            ms.colorObj(119,1,168),
            ms.colorObj(120,1,168),
            ms.colorObj(122,2,168),
            ms.colorObj(123,2,168),
            ms.colorObj(125,3,168),
            ms.colorObj(126,3,168),
            ms.colorObj(128,4,168),
            ms.colorObj(129,4,167),
            ms.colorObj(131,5,167),
            ms.colorObj(132,5,167),
            ms.colorObj(134,6,166),
            ms.colorObj(135,7,166),
            ms.colorObj(136,8,166),
            ms.colorObj(138,9,165),
            ms.colorObj(139,10,165),
            ms.colorObj(141,11,165),
            ms.colorObj(142,12,164),
            ms.colorObj(143,13,164),
            ms.colorObj(145,14,163),
            ms.colorObj(146,15,163),
            ms.colorObj(148,16,162),
            ms.colorObj(149,17,161),
            ms.colorObj(150,19,161),
            ms.colorObj(152,20,160),
            ms.colorObj(153,21,159),
            ms.colorObj(154,22,159),
            ms.colorObj(156,23,158),
            ms.colorObj(157,24,157),
            ms.colorObj(158,25,157),
            ms.colorObj(160,26,156),
            ms.colorObj(161,27,155),
            ms.colorObj(162,29,154),
            ms.colorObj(163,30,154),
            ms.colorObj(165,31,153),
            ms.colorObj(166,32,152),
            ms.colorObj(167,33,151),
            ms.colorObj(168,34,150),
            ms.colorObj(170,35,149),
            ms.colorObj(171,36,148),
            ms.colorObj(172,38,148),
            ms.colorObj(173,39,147),
            ms.colorObj(174,40,146),
            ms.colorObj(176,41,145),
            ms.colorObj(177,42,144),
            ms.colorObj(178,43,143),
            ms.colorObj(179,44,142),
            ms.colorObj(180,46,141),
            ms.colorObj(181,47,140),
            ms.colorObj(182,48,139),
            ms.colorObj(183,49,138),
            ms.colorObj(184,50,137),
            ms.colorObj(186,51,136),
            ms.colorObj(187,52,136),
            ms.colorObj(188,53,135),
            ms.colorObj(189,55,134),
            ms.colorObj(190,56,133),
            ms.colorObj(191,57,132),
            ms.colorObj(192,58,131),
            ms.colorObj(193,59,130),
            ms.colorObj(194,60,129),
            ms.colorObj(195,61,128),
            ms.colorObj(196,62,127),
            ms.colorObj(197,64,126),
            ms.colorObj(198,65,125),
            ms.colorObj(199,66,124),
            ms.colorObj(200,67,123),
            ms.colorObj(201,68,122),
            ms.colorObj(202,69,122),
            ms.colorObj(203,70,121),
            ms.colorObj(204,71,120),
            ms.colorObj(204,73,119),
            ms.colorObj(205,74,118),
            ms.colorObj(206,75,117),
            ms.colorObj(207,76,116),
            ms.colorObj(208,77,115),
            ms.colorObj(209,78,114),
            ms.colorObj(210,79,113),
            ms.colorObj(211,81,113),
            ms.colorObj(212,82,112),
            ms.colorObj(213,83,111),
            ms.colorObj(213,84,110),
            ms.colorObj(214,85,109),
            ms.colorObj(215,86,108),
            ms.colorObj(216,87,107),
            ms.colorObj(217,88,106),
            ms.colorObj(218,90,106),
            ms.colorObj(218,91,105),
            ms.colorObj(219,92,104),
            ms.colorObj(220,93,103),
            ms.colorObj(221,94,102),
            ms.colorObj(222,95,101),
            ms.colorObj(222,97,100),
            ms.colorObj(223,98,99),
            ms.colorObj(224,99,99),
            ms.colorObj(225,100,98),
            ms.colorObj(226,101,97),
            ms.colorObj(226,102,96),
            ms.colorObj(227,104,95),
            ms.colorObj(228,105,94),
            ms.colorObj(229,106,93),
            ms.colorObj(229,107,93),
            ms.colorObj(230,108,92),
            ms.colorObj(231,110,91),
            ms.colorObj(231,111,90),
            ms.colorObj(232,112,89),
            ms.colorObj(233,113,88),
            ms.colorObj(233,114,87),
            ms.colorObj(234,116,87),
            ms.colorObj(235,117,86),
            ms.colorObj(235,118,85),
            ms.colorObj(236,119,84),
            ms.colorObj(237,121,83),
            ms.colorObj(237,122,82),
            ms.colorObj(238,123,81),
            ms.colorObj(239,124,81),
            ms.colorObj(239,126,80),
            ms.colorObj(240,127,79),
            ms.colorObj(240,128,78),
            ms.colorObj(241,129,77),
            ms.colorObj(241,131,76),
            ms.colorObj(242,132,75),
            ms.colorObj(243,133,75),
            ms.colorObj(243,135,74),
            ms.colorObj(244,136,73),
            ms.colorObj(244,137,72),
            ms.colorObj(245,139,71),
            ms.colorObj(245,140,70),
            ms.colorObj(246,141,69),
            ms.colorObj(246,143,68),
            ms.colorObj(247,144,68),
            ms.colorObj(247,145,67),
            ms.colorObj(247,147,66),
            ms.colorObj(248,148,65),
            ms.colorObj(248,149,64),
            ms.colorObj(249,151,63),
            ms.colorObj(249,152,62),
            ms.colorObj(249,154,62),
            ms.colorObj(250,155,61),
            ms.colorObj(250,156,60),
            ms.colorObj(250,158,59),
            ms.colorObj(251,159,58),
            ms.colorObj(251,161,57),
            ms.colorObj(251,162,56),
            ms.colorObj(252,163,56),
            ms.colorObj(252,165,55),
            ms.colorObj(252,166,54),
            ms.colorObj(252,168,53),
            ms.colorObj(252,169,52),
            ms.colorObj(253,171,51),
            ms.colorObj(253,172,51),
            ms.colorObj(253,174,50),
            ms.colorObj(253,175,49),
            ms.colorObj(253,177,48),
            ms.colorObj(253,178,47),
            ms.colorObj(253,180,47),
            ms.colorObj(253,181,46),
            ms.colorObj(254,183,45),
            ms.colorObj(254,184,44),
            ms.colorObj(254,186,44),
            ms.colorObj(254,187,43),
            ms.colorObj(254,189,42),
            ms.colorObj(254,190,42),
            ms.colorObj(254,192,41),
            ms.colorObj(253,194,41),
            ms.colorObj(253,195,40),
            ms.colorObj(253,197,39),
            ms.colorObj(253,198,39),
            ms.colorObj(253,200,39),
            ms.colorObj(253,202,38),
            ms.colorObj(253,203,38),
            ms.colorObj(252,205,37),
            ms.colorObj(252,206,37),
            ms.colorObj(252,208,37),
            ms.colorObj(252,210,37),
            ms.colorObj(251,211,36),
            ms.colorObj(251,213,36),
            ms.colorObj(251,215,36),
            ms.colorObj(250,216,36),
            ms.colorObj(250,218,36),
            ms.colorObj(249,220,36),
            ms.colorObj(249,221,37),
            ms.colorObj(248,223,37),
            ms.colorObj(248,225,37),
            ms.colorObj(247,226,37),
            ms.colorObj(247,228,37),
            ms.colorObj(246,230,38),
            ms.colorObj(246,232,38),
            ms.colorObj(245,233,38),
            ms.colorObj(245,235,39),
            ms.colorObj(244,237,39),
            ms.colorObj(243,238,39),
            ms.colorObj(243,240,39),
            ms.colorObj(242,242,39),
            ms.colorObj(241,244,38),
            ms.colorObj(241,245,37),
            ms.colorObj(240,247,36),
            ms.colorObj(240,249,33),
        ), minvalue, maxvalue, contours)
