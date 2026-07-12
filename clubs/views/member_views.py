from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import ClubMemberShipForm
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
            messages.error(
                request,
                message="You do not have permission to perform this action on this club.",
            )
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
            messages.error(
                request,
                message="You do not have permission to add a new member to this club.",
            )
            return redirect("clubs:detail", club_id=club.id)
        club_membership_form = ClubMemberShipForm(request.POST)
        if not club_membership_form.is_valid():
            return render(
                request,
                self.template,
                {"form": club_membership_form, "club": club},
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
            messages.info(
                request, f"Existing member found and added to club: {club.name}"
            )
        ClubMembership.objects.get_or_create(
            club=club,
            user=created_user,
            defaults={
                "start_date": timezone.make_aware(
                    datetime.combine(
                        club_membership_form.cleaned_data.get("start_date"),
                        datetime.min.time(),
                    )
                ),
                "is_admin": club_membership_form.cleaned_data.get("is_admin"),
                "is_active": club_membership_form.cleaned_data.get("is_active"),
                "category": club_membership_form.cleaned_data.get("category"),
                "status": club_membership_form.cleaned_data.get("status"),
            },
        )
        messages.success(request, f"{created_user.email} added to club: {club.name}")
        return redirect("clubs:detail", club_id=club.id)
