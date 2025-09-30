from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_financials_forms import (
    FinancialYearForm,
)
from clubs.forms.club_membership_form import MemberLookupForm
from clubs.models import (
    Club,
    FinancialTransaction,
    FinancialYearContribution,
    FinancialYearParticipant,
)


class ClubFinancialYearCreateView(LoginRequiredMixin, View):
    """
    View to handle the creation of a new financial year for a club.
    """

    def post(self, request, club_id):
        """
        Handle POST requests to create a new financial year.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")

        form = FinancialYearForm(request.POST)
        if not form.is_valid():
            members = club.members.select_related("user").all()[:25]
            context = {
                "club": club,
                "members": members,
                "look_up_form": MemberLookupForm(),
                "financial_year_form": form,
            }
            return render(request, "clubs/detail.html", context)

        new_financial_year = form.save(commit=False)
        new_financial_year.club = club
        new_financial_year.created_by = request.user
        new_financial_year.updated_by = request.user
        new_financial_year.save()
        return redirect("clubs:detail", club_id=club.id)


class ClubFinancialYearDetailView(LoginRequiredMixin, View):
    """
    View to display details of a specific financial year for a club.
    """

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display the financial year details.
        """
        try:
            club = Club.objects.get(id=club_id)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, club.financial_years.model.DoesNotExist):
            return redirect("clubs:index")
        participants = FinancialYearParticipant.objects.filter(
            financial_year=financial_year
        ).select_related("club_member__user")
        dues = FinancialYearContribution.objects.filter(
            financial_year=financial_year
        ).order_by("due_period")
        transactions = (
            FinancialTransaction.objects.filter(financial_year=financial_year)
            .order_by("-transaction_date")
            .select_related("club_member__user")
        )
        context = {
            "club": club,
            "financial_year": financial_year,
            "participants": participants,
            "dues": dues,
            "transactions": transactions,
        }
        return render(request, "clubs/financial_year_detail.html", context)
