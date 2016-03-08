#-------------------------------------------------------------------------------
#
# Project: EOxServer - django-allauth integration.
# Authors: Daniel Santillan <daniel.santillan@eox.at>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2016 EOX IT Services GmbH
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

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.account.forms import LoginForm, SignupForm
from eoxserver.services.views import ows

if hasattr(settings, 'EOXS_ALLAUTH_WORKSPACE_TEMPLATE'):
    WORKSPACE_TEMPLATE = settings.EOXS_ALLAUTH_WORKSPACE_TEMPLATE
else:
    WORKSPACE_TEMPLATE = "eoxs_allauth/workspace.html"

def workspace(request):
    """ EOxServer/allauth workspace.
    Note that the work space is used as the actual landing page.
    """
    # TODO: check if request.method is set to "POST"
    # if yes then login or signup user then do redirect or whatever
    return render(request, WORKSPACE_TEMPLATE, {
        "login_form": LoginForm(),
        "signup_form": SignupForm()
    })

@login_required
def wrapped_ows(request):
    """ EOxServer/allauth wrapper of the ows endpoint. """
    return ows(request)
