#-------------------------------------------------------------------------------
#
# Forward models management - Remove one or more models.
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
from eoxserver.resources.coverages.management.commands import (
    CommandOutputMixIn, nested_commit_on_success
)
from vires.models import ForwardModel

@nested_commit_on_success
def deregister_forward_model(identifier):
    """ De-register forward model. """
    forward_model = ForwardModel.objects.get(identifier=identifier).cast()
    forward_model.delete()


class Command(CommandOutputMixIn, BaseCommand):
    help = "De-register one or more forward models."
    args = "<identifier> [<identifier> ...]"
    option_list = BaseCommand.option_list + (
        make_option(
            "-a", "--all", dest="remove_all",
            action="store_true", default=False,
            help="Use this flag to remove all registered models."
        ),
    )

    @nested_commit_on_success
    def handle(self, *args, **kwargs):

        if kwargs.get("remove_all"):
            identifiers = [
                item.identifier for item in ForwardModel.objects.all()
            ]
        else:
            identifiers = args
            if not identifiers:
                raise CommandError(
                    "Missing the mandatory model identifier(s)."
                )

        success_count = 0  # success counter - counts finished syncs
        for identifier in identifiers:
            self.print_msg("De-registering model %s ... " % identifier)
            try:
                deregister_forward_model(identifier)
            except Exception as exc:
                self.print_traceback(exc, kwargs)
                self.print_err(
                    "De-registration of model '%s' failed! Reason: %s" % (
                        identifier, exc,
                    )
                )
                continue
            success_count += 1

        count = len(identifiers)
        error_count = count - success_count
        if error_count > 0:
            self.print_msg("Failed to de-register %d models." % error_count, 1)
        if success_count > 0:
            self.print_msg(
                "Successfully de-registered %d of %s models." %
                (success_count, count), 1
            )
        else:
            self.print_msg("No model de-registered.")

