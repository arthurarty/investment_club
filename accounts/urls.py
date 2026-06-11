from django.urls import path

from accounts.views import LoginView, UserCreationView, logout_view

app_name = "accounts"

urlpatterns = [
    path("", LoginView.as_view(), name="index"),
    path("logout/", logout_view, name="logout"),
    path("users/", UserCreationView.as_view(), name="user-creation"),
]
