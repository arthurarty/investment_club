from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_financials_forms import FinancialYearParticipantForm
from clubs.models import Club, FinancialYear, FinancialYearParticipant
from clubs.views.utils import is_club_admin_or_creator


def prepare_participants_context(
    club: Club,
    financial_year: FinancialYear,
    is_club_admin: bool = True,
    participant_form: FinancialYearParticipantForm | None = None,
) -> dict:
    """
    Prepare context data for the participants view of a financial year.
    """
    participants = FinancialYearParticipant.objects.filter(
        financial_year=financial_year
    ).select_related("club_member__user")
    return {
        "club": club,
        "financial_year": financial_year,
        "participants": participants,
        "is_club_admin": is_club_admin,
        "participant_form": participant_form
        or FinancialYearParticipantForm(club=club, financial_year=financial_year),
    }


class ClubParticipantListView(LoginRequiredMixin, View):
    """
    View to list the members taking part in a financial year.
    """

    def get(self, request, club_id: int, financial_year_id: int):
        """
        Handle GET requests to display the participants of a financial year.
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
            "clubs/financial_year_participants.html",
            prepare_participants_context(club, financial_year, is_club_admin),
        )
