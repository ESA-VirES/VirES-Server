#-------------------------------------------------------------------------------
#
#  Altcha challange integration
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

import datetime
from django.conf import settings
import altcha

DEFAULT_STEP = 1000000


class AltchaError(ValueError):
    """ Altcha error exception. """


def is_altcha_enabled():
    altcha_settings = _get_altcha_settings()
    return altcha_settings.get("ENABLED") or False


def create_altcha_challange(**options):
    """ Create Altcha challenge. """
    return _create_altcha_challange(
        **_get_altcha_challenge_options(**options)
    )


def verify_solved_altcha_challange(payload):
    """ Verify solved alpha challenge. """
    is_correct, error = altcha.verify_solution(
        payload, hmac_key=_get_hmac_key(), check_expires=True
    )

    if error:
        raise AltchaError(error)

    return is_correct


def solve_altcha_challange(payload, max_number=None, step=DEFAULT_STEP):

    if "maxnumber" in payload:
        max_number = payload["maxnumber"]

    def _solve():

        parameters = {
            "algorithm": payload["algorithm"],
            "challenge": payload["challenge"],
            "salt": payload["salt"],
        }

        if max_number is not None:
            parameters["max_number"] = max_number

        if max_number is not None:
            # the max_number is known - can be solved in one pass
            return altcha.solve_challenge(**parameters, start=0)

        # the max_number is not known - solving iteratively
        start, end = 0, step
        solution = None
        while not solution:
            solution = altcha.solve_challenge(
                **parameters,
                start=start,
                max_number=end,
            )
            start, end = end, end + step

        return solution

    solution = _solve()
    if solution is not None:
        solution = {**payload, "number": solution.number}

    return solution


def test_altcha_challange(**options):
    """ Run simple test of the Altcha challange workflow. """
    challange = create_altcha_challange(**options)
    solution = solve_altcha_challange(challange)
    if not verify_solved_altcha_challange(solution):
        raise AssertionError("Failed to verify the solved challenge!")


def _now():
    """ Get current date-time. """
    return datetime.datetime.now(datetime.timezone.utc)


def _get_altcha_settings():
    return getattr(settings, "ALTCHA", None) or {}


def _get_hmac_key():
    altcha_settings = _get_altcha_settings()
    return altcha_settings.get("HMAC_KEY") or settings.SECRET_KEY


def _get_altcha_challenge_options(**options):
    """ Get Altcha challenge options from Django settings. """
    altcha_settings = _get_altcha_settings()

    expiration_period = altcha_settings.get("EXPIRE_SECONDS", -1)

    return {
        "algorithm": altcha_settings.get("ALGORITHM"),
        "max_number": altcha_settings.get("MAX_NUMBER"),
        "salt_length": altcha_settings.get("SALT_LENGTH"),
        "hmac_key": _get_hmac_key(),
        "include_maxnumber": altcha_settings.get("INCLUDE_MAXNUMBER") or False,
        "expires": (
            _now() + datetime.timedelta(seconds=expiration_period)
            if expiration_period >= 0 else None
        ),
        **options,
    }


def _create_altcha_challange(include_maxnumber=False, **options):
    challenge = altcha.create_challenge(altcha.ChallengeOptions(**options))

    payload = {
        "algorithm": challenge.algorithm,
        "challenge": challenge.challenge,
        "salt": challenge.salt,
        "signature": challenge.signature,
    }

    if include_maxnumber:
        payload["maxnumber"] = challenge.maxnumber

    return payload
