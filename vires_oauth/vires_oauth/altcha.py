#-------------------------------------------------------------------------------
#
#  Altcha challenge integration
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
# pylint: disable=missing-docstring

#
# ALTCHA Configuration
#
# The following configuration options are set in the settings.ALTCHA dictionary:
#
#   ENABLED            bool  Enables/disables ALTCHA captcha. Default False.
#   ALGORITHM          str   Challenge algorithm. See ALTCHA documentation.
#   MAX_NUMBER         int   Challenge maximum number. See ALTCHA documentation.
#   SALT_LENGTH        int   Length of the salt string. See ALTCHA documentation.
#   INCLUDE_MAXNUMBER  int   Flag controlling whether MAX_NUMBER is included
#                            in the challenge payload or not. Default False.
#   EXPIRE_SECONDS     int   Challenge expiration time in seconds. Default no
#                            expiration.
#   HMAC_KEY           str   HMAC secret key, defaults to settings.SECRET_KEY.
#                            See ALTCHA documentation.
#

from datetime import timedelta
from django.conf import settings
import altcha
from .time_utils import now
from .models import Challenge


def is_altcha_enabled():
    """ Return true if the Altcha challenge is enabled. """
    altcha_settings = _get_altcha_settings()
    return altcha_settings.get("ENABLED") or False


def create_altcha_challenge(**options):
    """ Create Altcha challenge. """
    return _create_altcha_challenge(
        **_get_altcha_challenge_options(**options)
    )

def altcha_challange_to_dict(challenge):
    """ Convert Altcha challenge to a dictionary. """
    return challenge.to_dict()


def encode_raw_solved_altcha_challange(payload):
    """ Encode raw solved Altcha challenge. """
    return payload.to_base64()


def parse_raw_solved_altcha_challenge(payload):
    """ Parse raw solved Altcha challenge. """
    return altcha.Payload.from_base64(payload)


def verify_solved_altcha_challenge(payload):
    """ Verify solved alpha challenge. """

    if not _check_challenge(payload.challenge.signature):
        return False

    _burn_challenge(payload.challenge.signature)

    result = altcha.verify_solution(
        payload, **_get_hmac_options(_get_altcha_settings()),
    )

    return result.verified


def solve_altcha_challenge(challenge, timeout=90.0):
    solution = altcha.solve_challenge(challenge, timeout=timeout)
    if solution is None:
        raise RuntimeError("Challenge not solved in time!")
    return altcha.Payload(challenge, solution)


def test_altcha_challenge(**options):
    """ Run simple test of the Altcha challenge workflow. """

    challenge = create_altcha_challenge(**options)
    assert isinstance(challenge, altcha.Challenge)

    solution = solve_altcha_challenge(challenge)
    assert isinstance(solution, altcha.Payload)

    if not verify_solved_altcha_challenge(solution):
        raise AssertionError("Failed to verify the solved challenge!")

    if verify_solved_altcha_challenge(solution):
        raise AssertionError("Failed to mark the challenge as used!")


def _get_altcha_settings():
    return getattr(settings, "ALTCHA", None) or {}


def _get_hmac_options(altcha_settings):
    options = {
        "hmac_secret": altcha_settings.get("HMAC_SECRET") or settings.SECRET_KEY,
        "hmac_key_secret": altcha_settings.get("HMAC_KEY_SECRET"),
    }
    if hmac_algorithm := altcha_settings.get("HMAC_ALGORITHM"):
        options["hmac_algorithm"] = hmac_algorithm
    return options


def _get_altcha_challenge_options(**options):
    """ Get Altcha challenge options from Django settings. """
    altcha_settings = _get_altcha_settings()
    expiration_period = altcha_settings.get("EXPIRE_SECONDS", -1)

    return {
        "algorithm": altcha_settings.get("ALGORITHM"),
        "cost": altcha_settings.get("COST"),
        "counter": altcha_settings.get("COUNTER"),
        "memory_cost": altcha_settings.get("MEMORY_COST"),
        "parallelism": altcha_settings.get("PARALLELISM"),
        "expires_at": (
            now() + timedelta(seconds=expiration_period)
            if expiration_period >= 0 else None
        ),
        **_get_hmac_options(altcha_settings),
        **options,
    }


def _create_altcha_challenge(**options):
    challenge = altcha.create_challenge(**options)
    _save_challenge(
        challenge=challenge.signature,
        expires=options.get("expires_at"),
    )
    return challenge


def _save_challenge(challenge, expires=None):
    """ Save challenge to DB. """
    Challenge(challenge=challenge, expires=expires).save()


def _check_challenge(challenge):
    """ Check DB if challenge is valid. """
    try:
        return Challenge.objects.get(challenge=challenge).is_valid
    except Challenge.DoesNotExist:
        return False


def _burn_challenge(challenge):
    """ Label the DB saved challenge as used. """
    try:
        obj = Challenge.objects.get(challenge=challenge)
        obj.used = True
        obj.save()
    except Challenge.DoesNotExist:
        pass
