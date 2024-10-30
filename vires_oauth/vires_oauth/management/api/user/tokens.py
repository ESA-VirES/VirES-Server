#-------------------------------------------------------------------------------
#
# Revoke all active user tokens
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2024 EOX IT Services GmbH
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

from django.db import transaction
from oauth2_provider.models import (
    get_refresh_token_model,
    get_id_token_model,
    get_access_token_model,
)


@transaction.atomic
def revoke_tokens(user, logger):
    """ Revoke all tokens belonging to the given user. """

    selection = {"user": user}

    for token in get_refresh_token_model().objects.filter(**selection):
        if not token.revoked:
            token.revoke()

    for token in get_id_token_model().objects.filter(**selection):
        token.revoke()

    for token in get_access_token_model().objects.filter(**selection):
        token.revoke()

    logger.info("user %s tokens revoked", user.username)


@transaction.atomic
def remove_tokens(user, logger):
    """ Delete all tokens belonging to the given user. """

    selection = {"user": user}

    for token in get_refresh_token_model().objects.filter(**selection):
        if not token.revoked:
            token.revoke()
        token.delete()

    for token in get_id_token_model().objects.filter(**selection):
        token.delete()

    for token in get_access_token_model().objects.filter(**selection):
        token.delete()

    logger.info("user %s tokens removed", user.username)
