from django.urls import path

from clubs.views.club_views import ClubDetailView, ClubsListView
from clubs.views.member_views import MemberLookUpView

app_name = "clubs"

urlpatterns = [
    path("", ClubsListView.as_view(), name="index"),
    path("<int:club_id>/", ClubDetailView.as_view(), name="detail"),
    path("member-lookup/", MemberLookUpView.as_view(), name="member-lookup"),
]
