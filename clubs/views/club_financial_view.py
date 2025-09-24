from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_financials_forms import (
    FinancialYearForm,
)
from clubs.forms.club_membership_form import MemberLookupForm
from clubs.models import Club


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
