from django.urls import path

from website.views import LandingView, robots_txt

app_name = "website"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("robots.txt", robots_txt, name="robots_txt"),
]
