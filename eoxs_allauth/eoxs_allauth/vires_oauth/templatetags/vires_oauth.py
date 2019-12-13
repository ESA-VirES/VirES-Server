#-------------------------------------------------------------------------------
#
# Custom Django template tags and filters
#
# Authors: Martin Paces <martin.paces@eox.at>
#-------------------------------------------------------------------------------
# Copyright (C) 2019 EOX IT Services GmbH
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

from django.template import Library
from allauth.socialaccount import app_settings
from ..provider import ViresProvider

register = Library()


VIRES_OAUTH_URL_PATHS = {
    'account_update_profile': '/',
    'account_change_password': '/accounts/password/change/',
    'account_email': '/accounts/email/',
    'socialaccount_connections': '/accounts/social/connections/',
}


@register.simple_tag
def vires_oauth_url(name):
    """ Resolve VirES OAuth server URL. """
    settings = app_settings.PROVIDERS.get(ViresProvider.id, {})
    base_url = settings['SERVER_URL'].rstrip('/')
    try:
        return '{0}{1}'.format(base_url, VIRES_OAUTH_URL_PATHS[name])
    except KeyError:
        raise ValueError("Unknown URL name '%s'!" % name)
