from django.urls import path

from accounts.views import LoginView, logout_view

app_name = "accounts"

urlpatterns = [
    path("", LoginView.as_view(), name="index"),
    path("logout/", logout_view, name="logout"),
]
