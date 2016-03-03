

from vires import views
from django.conf.urls import url

urlpatterns = [
    url(r'^$', views.wrapped_ows, name='ows'),
]