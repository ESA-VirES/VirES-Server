#-------------------------------------------------------------------------------
#
# Forward models management - Add one model with arbitrary identifier.
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
# pylint: disable=missing-docstring, too-few-public-methods

from optparse import make_option

from django.core.management.base import CommandError, BaseCommand
from django.contrib.gis import geos
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from eoxserver.resources.coverages import models
from eoxserver.backends import models as backends

from vires.models import ForwardModel
from vires.forward_models.util import get_forward_model_providers

@nested_commit_on_success
def register_forward_model(identifier, provider, range_type):
    """ Register new forward mode. """
    begin_time, end_time = provider.time_validity

    forward_model = ForwardModel()
    forward_model.visible = True
    forward_model.identifier = identifier
    forward_model.range_type = range_type
    forward_model.srid = 4326
    forward_model.min_x = -180
    forward_model.min_y = -90
    forward_model.max_x = 180
    forward_model.max_y = 90
    forward_model.size_x = 1
    forward_model.size_y = 1
    forward_model.begin_time = begin_time
    forward_model.end_time = end_time
    forward_model.footprint = geos.MultiPolygon(
        geos.Polygon.from_bbox((-180, -90, 180, 90))
    )
    forward_model.full_clean()
    forward_model.save()

    data_item = backends.DataItem(
        dataset=forward_model, semantic="coefficients",
        location="none", format=provider.identifier
    )
    data_item.full_clean()
    data_item.save()


class Command(CommandOutputMixIn, BaseCommand):
    @property
    def option_list(self):
        provider_names = list(get_forward_model_providers())
        return BaseCommand.option_list + (
            make_option(
                "-i", "--identifier", "--coverage-id",
                dest="identifier", action="store", default=None,
                help="Mandatory forward model identifier."
            ),
            make_option(
                "-r", "--range-type", dest="range_type_name",
                default="MagneticModel",
                help=(
                    "Optional name of the model range type. "
                    "Defaults to 'MagneticModel'."
                )
            ),
            make_option(
                "-m", "--model", dest="provider_name", choices=provider_names,
                help=(
                    "Mandatory forward model provider name. The allowed values "
                    "are: %s" % ", ".join(provider_names)
                )
            )
        )

    help = "Register one forward model with a custom coverage identifier."

    def handle(self, *args, **kwargs):
        identifier = kwargs["identifier"]
        range_type_name = kwargs["range_type_name"]
        provider_name = kwargs["provider_name"]

        if not identifier:
            raise CommandError("Missing the mandatory model identifier!")

        if not provider_name:
            raise CommandError(
                "Missing the mandatory forward model provider name!"
            )

        try:
            range_type = models.RangeType.objects.get(name=range_type_name)
        except models.RangeType.DoesNotExist:
            raise CommandError(
                "Invalid range type name '%s'!" % range_type_name
            )

        try:
            provider = get_forward_model_providers()[provider_name]
        except IndexError:
            raise CommandError(
                "Invalid forward model provider name '%s'!" % provider_name
            )

        self.print_msg(
            "Registering model %s [%s] ... " % (identifier, provider.identifier)
        )
        register_forward_model(identifier, provider, range_type)
