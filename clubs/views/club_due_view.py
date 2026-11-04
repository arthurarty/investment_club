from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from clubs.forms.club_financials_forms import (
    FinancialYearContributionForm,
)
from clubs.models import (
    Club,
    FinancialYearContribution,
)
from clubs.views.utils import is_club_admin_or_creator


class ClubDueListView(LoginRequiredMixin, View):
    """
    View to display a list of all the dues applicable to
    all members of a club.
    """

    def get(self, request, club_id: int, financial_year_id: int):
        """
        Handle GET requests to display the list of clubs.
        """
        club = Club.objects.get(id=club_id)
        is_club_admin = is_club_admin_or_creator(request, club)
        is_member = club.members.filter(user=request.user).exists()
        if not is_club_admin and not is_member:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
        financial_year = club.financial_years.get(id=financial_year_id)
        dues = FinancialYearContribution.objects.filter(
            financial_year=financial_year
        ).order_by("due_period")
        context = {
            "dues": dues,
            "financial_year": financial_year,
            "is_club_admin": is_club_admin,
            "club": club,
            "financial_contribution_form": FinancialYearContributionForm(),
        }
        return render(request, "clubs/financial_year_dues.html", context)
