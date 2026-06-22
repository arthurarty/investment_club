from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from accounts.forms.user_creation_form import UserCreationForm
from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import ClubMemberShipForm, MemberLookupForm
from clubs.models import Club, ClubMembership


class ClubMemberShipCreateView(LoginRequiredMixin, View):
    """
    Create a user and add them as a member to a club
    """

    def get(self, request, club_id: int):
        club = Club.objects.filter(id=club_id).first()
        if not club:
            return redirect("clubs:index")
        if not ClubMembership.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        context = {
            "form": ClubMemberShipForm(),
            "club": club,
        }
        return render(request, "clubs/club_membership_form.html", context)

    def post(self, request, club_id: int):
        club = Club.objects.filter(id=club_id).first()
        if not club:
            return redirect("clubs:index")
        if not ClubMembership.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        user_creation_form = UserCreationForm(request.POST)
        if not user_creation_form.is_valid():
            return render(
                request,
                "accounts/user_creation.html",
                {"form": user_creation_form},
            )
        created_user = User.objects.create_user(**user_creation_form.cleaned_data)
        ClubMembership.objects.get_or_create(
            club=club, user=created_user, is_admin=False
        )
        return redirect("clubs:detail", club_id=club.id)


class ClubMemberView(LoginRequiredMixin, View):
    """
    View to add a member to a club.
    """

    def get(self, request, club_id: int):
        """
        Handle get requests to add a member to a club.
        """
        club = Club.objects.filter(id=club_id).first()
        if not club:
            return redirect("clubs:index")
        if not ClubMembership.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        form = MemberLookupForm(request.GET)
        if not form.is_valid():
            return redirect("clubs:detail", club_id=club.id)
        user = User.objects.filter(email=form.cleaned_data["email"]).first()
        if not user:
            return redirect("clubs:detail", club_id=club.id)
        ClubMembership.objects.get_or_create(club=club, user=user, is_admin=False)
        return redirect("clubs:detail", club_id=club.id)
