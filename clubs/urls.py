from django.urls import path

from clubs.views.club_views import ClubDetailView, ClubsListView
from clubs.views.member_views import ClubMemberView, MemberLookUpView

app_name = "clubs"

urlpatterns = [
    path("", ClubsListView.as_view(), name="index"),
    path("<int:club_id>/", ClubDetailView.as_view(), name="detail"),
    path(
        "<int:club_id>/member-lookup/", MemberLookUpView.as_view(), name="member-lookup"
    ),
    path("<int:club_id>/club-member/", ClubMemberView.as_view(), name="club-member"),
]
