#-------------------------------------------------------------------------------
#
# views
#
# Authors: Martin Paces <martin.paces@eox.at>
#
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

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.messages import INFO, ERROR, add_message
from .decorators import redirect_unauthenticated
from .forms import UserProfileForm
from .utils import get_user_permissions
from .settings import PERMISSIONS

USER_PROFILE_TEMPLATE = 'vires_oauth/index.html'


def test_view(request):
    response = "\n".join([
        "\n".join("%s: %s" % (key, value) for key, value in request.META.items()),
        "\n".join("%s: %s" % (key, value) for key, value in request.headers.items()),
    ])
    return HttpResponse(response, 'text/plain', 200)


@redirect_unauthenticated
def update_user_profile_view(request):
    form = UserProfileForm(request.user, request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save_profile(request.user)
            add_message(request, INFO, "Profile updated.")
            return redirect('account_update_profile')
        add_message(request, ERROR, "Profile update failed.")
    return render(request, USER_PROFILE_TEMPLATE, {
        'permissions': [
            (code, PERMISSIONS.get(code, code))
            for code in get_user_permissions(request.user)
        ],
        'form': form,
    })
