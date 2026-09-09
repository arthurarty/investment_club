from datetime import datetime
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import ClubMemberShipForm
from clubs.models import Club, ClubMembership, MembershipStatus
from clubs.views.utils import is_club_admin_or_creator


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
        status = club_membership_form.cleaned_data.get("status")
        is_active = status == MembershipStatus.ACTIVE
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
                "is_active": is_active,
                "category": club_membership_form.cleaned_data.get("category"),
                "status": status,
            },
        )
        messages.success(request, f"{created_user.email} added to club: {club.name}")
        return redirect("clubs:detail", club_id=club.id)


class ClubMemberShipDetailView(LoginRequiredMixin, View):
    """
    View to display details of a single member within a club.
    """

    template = "clubs/member_detail.html"

    def get(self, request, club_id: int, member_id: int):
        """
        Handle GET requests to display member details.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")

        creator_or_admin = is_club_admin_or_creator(request, club)
        is_member = club.members.filter(user=request.user).exists()
        if not creator_or_admin and not is_member:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)

        try:
            member = club.members.select_related("user", "invited_by", "club").get(
                id=member_id
            )
        except ClubMembership.DoesNotExist:
            messages.error(request, message="Member not found in this club.")
            return redirect("clubs:detail", club_id=club.id)

        transactions = member.financial_transactions.select_related(
            "financial_year"
        ).order_by("-transaction_date")
        individual_dues = member.individual_dues.select_related(
            "financial_year"
        ).order_by("-due_date")
        participating_years = member.financial_years.select_related(
            "financial_year"
        ).order_by("-financial_year__start_date")

        transaction_totals = transactions.aggregate(
            total_credit=Sum("credit"),
            total_debit=Sum("debit"),
        )
        total_credit = transaction_totals["total_credit"] or 0
        total_debit = transaction_totals["total_debit"] or 0
        total_individual_dues = (
            individual_dues.aggregate(total=Sum("amount"))["total"] or 0
        )

        context = {
            "club": club,
            "member": member,
            "is_creator_or_admin": creator_or_admin,
            "transactions": transactions,
            "individual_dues": individual_dues,
            "participating_years": participating_years,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "total_individual_dues": total_individual_dues,
        }
        return render(request, self.template, context)
