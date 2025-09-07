from django.urls import path

from accounts.views import LoginView

app_name = "accounts"

urlpatterns = [
    path("", LoginView.as_view(), name="index"),
]
