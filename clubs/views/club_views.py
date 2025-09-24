from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_creation_form import ClubCreationForm
from clubs.forms.club_financials_forms import (
    FinancialYearForm,
    FinancialYearParticipantForm,
)
from clubs.forms.club_membership_form import MemberLookupForm
from clubs.models import Club


class ClubsListView(LoginRequiredMixin, View):
    """
    View to display a list of investment clubs.
    """

    def get(self, request):
        """
        Handle GET requests to display the list of clubs.
        """
        current_user = request.user
        clubs = (
            Club.objects.filter(created_by=current_user)
            .order_by("created_at")
            .all()[:10]
        )
        context = {
            "clubs": clubs,
            "create_club_form": ClubCreationForm(),
        }
        return render(request, "clubs/index.html", context)

    def post(self, request):
        """
        Handle POST requests to create a new club.
        """
        form = ClubCreationForm(request.POST)
        if not form.is_valid():
            current_user = request.user
            clubs = (
                Club.objects.filter(created_by=current_user)
                .order_by("created_at")
                .all()[:10]
            )
            context = {
                "clubs": clubs,
                "create_club_form": form,
            }
            return render(request, "clubs/index.html", context)
        new_club = form.save(commit=False)
        new_club.created_by = request.user
        new_club.updated_by = request.user
        new_club.save()
        form.save_m2m()  # Save many-to-many relationships if any
        return redirect("clubs:index")


class ClubDetailView(LoginRequiredMixin, View):
    """
    View to display details of a specific investment club.
    """

    def get(self, request, club_id):
        """
        Handle GET requests to display club details.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")
        members = club.members.select_related("user").all()[:25]
        context = {
            "club": club,
            "members": members,
            "look_up_form": MemberLookupForm(),
            "financial_year_form": FinancialYearForm(),
        }
        return render(request, "clubs/detail.html", context)


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
        form.save_m2m()  # Save many-to-many relationships if any

        # Automatically add the club creator as a participant in the new financial year
        participant_form = FinancialYearParticipantForm(
            data={
                "club_member": request.user.clubmember_set.get(club=club).id,
                "financial_year": new_financial_year.id,
            }
        )
        if participant_form.is_valid():
            participant = participant_form.save(commit=False)
            participant.created_by = request.user
            participant.updated_by = request.user
            participant.save()

        return redirect("clubs:detail", club_id=club.id)
