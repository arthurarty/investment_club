from django.urls import path

from clubs.views.club_financial_view import (
    ClubFinancialYearCreateView,
    ClubFinancialYearDetailView,
    FinancialTransactionCreateView,
    FinancialYearDueCreateView,
)
from clubs.views.club_reports_view import FinancialReportView
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
    path(
        "<int:club_id>/financial-year/",
        ClubFinancialYearCreateView.as_view(),
        name="financial-year",
    ),
    path(
        "<int:club_id>/financial-year/<int:financial_year_id>/",
        ClubFinancialYearDetailView.as_view(),
        name="financial-year-detail",
    ),
    path(
        "<int:club_id>/financial-year/<int:financial_year_id>/due/",
        FinancialYearDueCreateView.as_view(),
        name="financial-year-due",
    ),
    path(
        "<int:club_id>/financial-year/<int:financial_year_id>/transaction/",
        FinancialTransactionCreateView.as_view(),
        name="financial-transaction",
    ),
    path(
        "<int:club_id>/financial-year/<int:financial_year_id>/reports/",
        FinancialReportView.as_view(),
        name="financial-reports",
    ),
]
