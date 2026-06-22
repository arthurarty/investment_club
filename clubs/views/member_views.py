from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import ClubMemberShipForm, MemberLookupForm
from clubs.models import Club, ClubMembership


class ClubMemberShipCreateView(LoginRequiredMixin, View):
    """
    Create a user and add them as a member to a club
    """

    template = "clubs/club_membership_form.html"

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
        return render(request, self.template, context)

    def post(self, request, club_id: int):
        club = Club.objects.filter(id=club_id).first()
        if not club:
            return redirect("clubs:index")
        if not ClubMembership.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        club_membership_form = ClubMemberShipForm(request.POST)
        if not club_membership_form.is_valid():
            return render(
                request,
                self.template,
                {"form": club_membership_form},
            )
        created_user, created = User.objects.get_or_create(
            email=club_membership_form.cleaned_data.get("email"),
            defaults={
                "first_name": club_membership_form.cleaned_data.get("first_name"),
                "last_name": club_membership_form.cleaned_data.get("last_name"),
                "gender": club_membership_form.cleaned_data.get("gender"),
                "phone_number": club_membership_form.cleaned_data.get("phone_number"),
                "occupation": club_membership_form.cleaned_data.get("occupation"),
                "physical_address": club_membership_form.cleaned_data.get(
                    "physical_address"
                ),
            },
        )
        if not created:
            # Todo: notify user that a member is linked to an existing user.
            print("existing user added as member")
        ClubMembership.objects.get_or_create(
            club=club,
            user=created_user,
            defaults={
                "start_date": club_membership_form.cleaned_data.get("start_date"),
                "is_admin": club_membership_form.cleaned_data.get("is_admin"),
                "is_active": club_membership_form.cleaned_data.get("is_active"),
                "category": club_membership_form.cleaned_data.get("category"),
                "status": club_membership_form.cleaned_data.get("status"),
            },
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
