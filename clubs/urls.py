from django.urls import path

from clubs.views import ClubsListView

app_name = "clubs"

urlpatterns = [
    path("", ClubsListView.as_view(), name="index"),
]
