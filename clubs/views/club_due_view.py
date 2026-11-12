from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_financials_forms import (
    FinancialYearContributionForm,
    IndividualDueForm,
)
from clubs.models import (
    Club,
    FinancialYear,
    FinancialYearContribution,
)
from clubs.views.utils import is_club_admin_or_creator


def prepare_individual_dues_context(
    club: Club,
    financial_year: FinancialYear,
    is_club_admin: bool = True,
    individual_due_form: IndividualDueForm | None = None,
) -> dict:
    """
    Prepare context data for the individual dues view of a financial year.
    """
    individual_dues = financial_year.individual_dues.select_related(
        "club_member__user"
    ).order_by("-due_date", "-id")
    return {
        "club": club,
        "financial_year": financial_year,
        "individual_dues": individual_dues,
        "is_club_admin": is_club_admin,
        "individual_due_form": individual_due_form or IndividualDueForm(club=club),
    }


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


class ClubIndividualDueListView(LoginRequiredMixin, View):
    """
    View to list the dues that apply to individual members
    within a financial year.
    """

    def get(self, request, club_id: int, financial_year_id: int):
        """
        Handle GET requests to display the individual dues of a financial year.
        """
        try:
            club = Club.objects.get(id=club_id)
            is_club_admin = is_club_admin_or_creator(request, club)
            is_member = club.members.filter(user=request.user).exists()
            if not is_club_admin and not is_member:
                return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, FinancialYear.DoesNotExist):
            return redirect("clubs:index")
        return render(
            request,
            "clubs/financial_year_individual_dues.html",
            prepare_individual_dues_context(club, financial_year, is_club_admin),
        )
