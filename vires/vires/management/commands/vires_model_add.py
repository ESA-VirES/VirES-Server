#-------------------------------------------------------------------------------
#
# Forward models management - Add one or more models.
#
# Project: VirES
# Authors: Martin Paces <martin.paces@eox.at>
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
# pylint: disable=missing-docstring

from optparse import make_option
from datetime import datetime
from django.core.management.base import CommandError, BaseCommand
from django.contrib.gis import geos
from eoxserver.backends.models import DataItem
from eoxserver.resources.coverages import models
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.models import ForwardModel
from vires.forward_models.util import get_forward_model_providers
from vires.time_util import naive_to_utc

# NOTE: Because of the EOxServer core limitation we cannot serve
#       WMS model views outside of the model time validity range.
#       Therefore we register two models, one with the original name
#       and true validity range and the second with an extended validity
#       range allowing WMS rendering outside of the validity period.
#       The second model has '_view' prefix in its identifier.

class Command(CommandOutputMixIn, BaseCommand):
    args = "<identifier> [<identifier> ...]"

    @property
    def help(self):
        return (
            "Register one or more forward models using the given forward "
            "model providers' names as the coverage identifiers.\n"
            "Following models are available:\n\t%s" % (
                ", ".join(list(get_forward_model_providers()))
            )
        )

    option_list = BaseCommand.option_list + (
        make_option(
            "-r", "--range-type", dest="range_type_name",
            default="MagneticModel",
            help=(
                "Optional name of the model range type. "
                "Defaults to 'MagneticModel'."
            )
        ),
    )

    def handle(self, *args, **kwargs):
        range_type_name = kwargs["range_type_name"]
        try:
            range_type = models.RangeType.objects.get(name=range_type_name)
        except models.RangeType.DoesNotExist:
            raise CommandError(
                "Invalid range type name '%s'!" % range_type_name
            )

        success_count = 0  # success counter - counts finished syncs
        providers = get_forward_model_providers()
        for identifier in args:
            provider = providers.get(identifier)
            if not provider:
                self.print_err(
                    "Invalid forward model provider name '%s'! "
                    "This model cannot be registered!" % identifier
                )
                continue

            self.print_msg(
                "Registering model %s [%s] ... " % (identifier, identifier)
            )
            try:
                register_forward_model(identifier, provider, range_type)
            except Exception as exc:
                self.print_traceback(exc, kwargs)
                self.print_err(
                    "Registration of model '%s' failed! Reason: %s" % (
                        identifier, exc,
                    )
                )
                continue

            success_count += 1

        count = len(args)
        error_count = count - success_count
        if error_count > 0:
            self.print_msg("Failed to register %d models." % error_count, 1)
        if success_count > 0:
            self.print_msg(
                "Successfully registered %d of %s models." %
                (success_count, count), 1
            )
        else:
            self.print_msg("No model registered.")


@nested_commit_on_success
def register_forward_model(identifier, provider, range_type):
    """ Register a new forward model. """
    # first 'true' validity model
    _register_forward_model(identifier, provider, range_type)
    # second 'view' (extended range) model
    _register_forward_model(
        identifier + "_view", provider, range_type,
        (naive_to_utc(datetime(1, 1, 1)), naive_to_utc(datetime(4000, 1, 1)))
    )


@nested_commit_on_success
def _register_forward_model(identifier, provider, range_type, validity=None):
    """ Register exactly one new forward model. """
    begin_time, end_time = validity or provider.time_validity

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

    data_item = DataItem(
        dataset=forward_model, semantic="coefficients",
        location="none", format=provider.identifier
    )
    data_item.full_clean()
    data_item.save()
