from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls

from accounts.views import LoginView, logout_view

app_name = "accounts"

urlpatterns = [
    path("", LoginView.as_view(), name="index"),
    path("2fa/", include(tf_urls)),
    path("logout/", logout_view, name="logout"),
]
