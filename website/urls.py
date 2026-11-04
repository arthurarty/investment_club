from django.urls import path

from website.views import LandingView

app_name = "website"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
]
