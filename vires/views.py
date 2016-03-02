from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from allauth.account.forms import LoginForm, SignupForm
from eoxserver.services.views import ows

def workspace(request):

    # TODO: check if request.metho is set to "POST"
    # if yes then login or signup user then do redirect or whatever
    return render(request, "vires/workspace.html", {
        "login_form": LoginForm(),
        "signup_form": SignupForm()
    })


@login_required
def wrapped_ows(request):
    return ows(request)
