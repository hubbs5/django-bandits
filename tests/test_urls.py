# tests/test_urls.py

from django.urls import path
from django.http import HttpResponse


def dummy_view(request):
    return HttpResponse("Dummy View")


urlpatterns = [
    path("some_path/", dummy_view, name="dummy_view"),
    path("accounts/signup/", dummy_view, name="signup"),
]
