#-------------------------------------------------------------------------------
#
# Project: EOxServer <http://eoxserver.org>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#          Daniel Santillan <daniel.santillan@eox.at>
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

from os.path import dirname, join
from matplotlib.colors import LinearSegmentedColormap

import eoxmagmod as mm

# Extra models' data locations
DATA_DIR = join(dirname(__file__), 'model_data')
DATA_IGRF12 = join(DATA_DIR, 'IGRF12.shc')
DATA_SIFM = join(DATA_DIR, 'SIFM.shc')


def get_model(model_id):
    """ Get model for given identifier. """
    if model_id == "CHAOS-5-Combined":
        return (
            mm.shc.read_model_shc(mm.shc.DATA_CHAOS5_CORE) +
            mm.shc.read_model_shc(mm.shc.DATA_CHAOS5_STATIC)
        )
    if model_id == "EMM":
        return mm.emm.read_model_emm2010()
    if model_id == "IGRF":
        return mm.igrf.read_model_igrf11()
    if model_id == "IGRF12":
        return mm.shc.read_model_shc(DATA_IGRF12)
    if model_id == "SIFM":
        return mm.shc.read_model_shc(DATA_SIFM)
    if model_id == "WMM":
        return mm.read_model_wmm2010()


# TODO: Uncecessary as Python 2.6 compatibility has been dropped.
def get_total_seconds(td_obj):
    """ Get `datetime.timedelta` as total number of seconds. """
    try:
        return td_obj.total_seconds()
    except AttributeError:
        return td_obj.microseconds*1e-6 + td_obj.seconds + td_obj.days*86400


def get_color_scale(name):
    """ Get named color-map. """

    def clist_to_colormap(label, color_list, color_scale=1.0, alpha_scale=1.0):
        """ Convert list of colors to `LinearSegmentedColormap` object """
        red_list, green_list, blue_list = [], [], []

        for alpha, red, green, blue in color_list:
            alpha *= alpha_scale
            red *= color_scale
            green *= color_scale
            blue *= color_scale

            red_list.append((alpha, red, red))
            green_list.append((alpha, green, green))
            blue_list.append((alpha, blue, blue))

        return LinearSegmentedColormap(
            label, {'red': red_list, 'green': green_list, 'blue': blue_list}
        )


    if name == "blackwhite":
        return clist_to_colormap(name, [
            (0.0, 0, 0, 0),
            (1.0, 255, 255, 255),
        ], 1.0 / 255.0)

    elif name == "coolwarm":
        return clist_to_colormap(name, [
            (0.0, 255, 0, 0),
            (0.5, 255, 255, 255),
            (1.0, 0, 0, 255),
        ], 1.0 / 255.0)

    elif name == "rainbow":
        return clist_to_colormap(name, [
            (0.0, 150, 0, 90),
            (0.125, 0, 0, 200),
            (0.25, 0, 25, 255),
            (0.375, 0, 152, 255),
            (0.5, 44, 255, 150),
            (0.625, 151, 255, 0),
            (0.75, 255, 234, 0),
            (0.875, 255, 111, 0),
            (1.0, 255, 0, 0),
        ], 1.0 / 255.0)

    elif name == "custom2":
        return clist_to_colormap(name, [
            (0.0, 0, 0, 0),
            (0.000000000001, 3, 10.1796, 255),
            (0.1, 32, 74.3152, 255),
            (0.2, 60, 138.451, 255),
            (0.3333, 119.72, 196.725, 255),
            (0.4666, 240, 255, 255),
            (0.5333, 240, 255, 255),
            (0.6666, 242.25, 255, 127.5),
            (0.8, 255, 255, 0),
            (0.9, 255, 131.99, 30.5294),
            (0.999999999999, 255, 8.98008, 61.0585),
            (1.0, 255, 0, 255),
        ], 1.0 / 255.0)

    elif name == "custom1":
        return clist_to_colormap(name, [
            (0.0, 0.2510, 0, 0.2510),
            (0.01587301587, 0.2331, 0, 0.3045),
            (0.03174603174, 0.2151, 0, 0.3580),
            (0.04761904761, 0.1972, 0, 0.4115),
            (0.06349206348, 0.1793, 0, 0.4650),
            (0.07936507935, 0.1613, 0, 0.5185),
            (0.09523809522, 0.1434, 0, 0.5720),
            (0.11111111109, 0.1255, 0, 0.6255),
            (0.12698412696, 0.1076, 0, 0.6790),
            (0.14285714283, 0.0896, 0, 0.7325),
            (0.1587301587, 0.0717, 0, 0.7860),
            (0.17460317457, 0.0538, 0, 0.8395),
            (0.19047619044, 0.0359, 0, 0.8930),
            (0.20634920631, 0.0179, 0, 0.9465),
            (0.22222222218, 0, 0, 1.0000, ),
            (0.23809523805, 0.0091, 0.0909, 1.0),
            (0.25396825392, 0.0182, 0.1818, 1.0),
            (0.26984126979, 0.0273, 0.2727, 1.0),
            (0.28571428566, 0.0364, 0.3636, 1.0),
            (0.30158730153, 0.0455, 0.4545, 1.0),
            (0.3174603174, 0.0545, 0.5455, 1.0),
            (0.33333333327, 0.0636, 0.6364, 1.0),
            (0.34920634914, 0.0727, 0.7273, 1.0),
            (0.36507936501, 0.0818, 0.8182, 1.0),
            (0.38095238088, 0.0909, 0.9091, 1.0),
            (0.39682539675, 0.1000, 1.0000, 1.0),
            (0.41269841262, 0.2500, 1.0000, 1.0),
            (0.42857142849, 0.4000, 1.0000, 1.0),
            (0.44444444436, 0.5500, 1.0000, 1.0),
            (0.46031746023, 0.7000, 1.0000, 1.0),
            (0.4761904761, 0.8500, 1.0000, 1.0),
            (0.49206349197, 1.0, 1.0, 1.0000),
            (0.50793650784, 1.0, 1.0, 0.8333),
            (0.52380952371, 1.0, 1.0, 0.6667),
            (0.53968253958, 1.0, 1.0, 0.5000),
            (0.55555555545, 1.0, 1.0, 0.3333),
            (0.57142857132, 1.0, 1.0, 0.1667),
            (0.58730158719, 1.0, 1.0, 0),
            (0.60317460306, 1.0, 0.9333, 0),
            (0.61904761893, 1.0, 0.8667, 0),
            (0.6349206348, 1.0, 0.8000, 0),
            (0.65079365067, 1.0, 0.7333, 0),
            (0.66666666654, 1.0, 0.6667, 0),
            (0.68253968241, 1.0, 0.6000, 0),
            (0.69841269828, 1.0, 0.5333, 0),
            (0.71428571415, 1.0, 0.4667, 0),
            (0.73015873002, 1.0, 0.4000, 0),
            (0.74603174589, 1.0, 0.3333, 0),
            (0.76190476176, 1.0, 0.2667, 0),
            (0.77777777763, 1.0, 0.2000, 0),
            (0.7936507935, 1.0, 0.1333, 0),
            (0.80952380937, 1.0, 0.0667, 0),
            (0.82539682524, 1.0, 0, 0),
            (0.84126984111, 1.0, 0, 0.0909),
            (0.85714285698, 1.0, 0, 0.1818),
            (0.87301587285, 1.0, 0, 0.2727),
            (0.88888888872, 1.0, 0, 0.3636),
            (0.90476190459, 1.0, 0, 0.4545),
            (0.92063492046, 1.0, 0, 0.5455),
            (0.93650793633, 1.0, 0, 0.6364),
            (0.9523809522, 1.0, 0, 0.7273),
            (0.96825396807, 1.0, 0, 0.8182),
            (0.98412698394, 1.0, 0, 0.9091),
            (1.0, 1.0, 0, 1.0000),
        ])

    else:
        return name
