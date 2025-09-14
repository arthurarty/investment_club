from django.urls import path

from clubs.views import ClubsView

app_name = "clubs"

urlpatterns = [
    path("", ClubsView.as_view(), name="index"),
]
