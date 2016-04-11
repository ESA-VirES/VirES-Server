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
from django.core.management.base import CommandError, BaseCommand
from eoxserver.resources.coverages import models
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn,
)
from vires.management.commands.vires_add_forward_model import (
    register_forward_model
)
from vires.forward_models.util import get_forward_model_providers


class Command(CommandOutputMixIn, BaseCommand):

    @property
    def help(self):
        return (
            "Register one or more forward models using the given forward "
            "model providers' names as the coverage identifiers.\n"
            "Following models are available:\n\t%s" % (
                ", ".join(list(get_forward_model_providers()))
            )
        )
    args = "<identifier> [<identifier> ...]"

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
