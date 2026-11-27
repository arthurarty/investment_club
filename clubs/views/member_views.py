from datetime import datetime
from http import HTTPStatus
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import (
    ClubMemberShipForm,
    ClubMembershipUpdateForm,
)
from clubs.models import (
    Club,
    ClubMembership,
    MembershipCategory,
    MembershipStatus,
)
from clubs.views.utils import is_club_admin_or_creator

MEMBER_PAGE_SIZES = (5, 10, 25, 50)
MEMBER_ROLE_FILTERS = {
    "admin": Q(is_admin=True),
    "committee": Q(is_admin=False, category=MembershipCategory.COMMITTEE),
    "ordinary": Q(is_admin=False, category=MembershipCategory.ORDINARY),
}
MEMBER_STATUS_FILTERS = {
    "active": Q(is_active=True),
    "inactive": Q(is_active=False),
}


def _page_window(current: int, total: int) -> list[int | None]:
    """
    Page numbers to show in the pager; None marks an ellipsis gap.
    """
    if total <= 7:
        return list(range(1, total + 1))
    pages: list[int | None] = [1]
    if current > 3:
        pages.append(None)
    pages.extend(range(max(2, current - 1), min(total - 1, current + 1) + 1))
    if current < total - 2:
        pages.append(None)
    pages.append(total)
    return pages


class ClubMemberListView(LoginRequiredMixin, View):
    """
    Dedicated page listing every member of a club. Search, role and status
    filters and pagination are driven by GET query parameters.
    """

    template = "clubs/members.html"

    def get(self, request, club_id: int):
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")

        creator_or_admin = is_club_admin_or_creator(request, club)
        is_member = club.members.filter(user=request.user).exists()
        if not creator_or_admin and not is_member:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)

        search = request.GET.get("q", "").strip()
        role = request.GET.get("role", "")
        status = request.GET.get("status", "")
        try:
            per_page = int(request.GET.get("per_page", MEMBER_PAGE_SIZES[0]))
        except ValueError:
            per_page = MEMBER_PAGE_SIZES[0]
        if per_page not in MEMBER_PAGE_SIZES:
            per_page = MEMBER_PAGE_SIZES[0]

        members = club.members.select_related("user").order_by(
            "user__first_name", "user__last_name", "id"
        )
        if search:
            members = members.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )
        if role in MEMBER_ROLE_FILTERS:
            members = members.filter(MEMBER_ROLE_FILTERS[role])
        else:
            role = ""
        if status in MEMBER_STATUS_FILTERS:
            members = members.filter(MEMBER_STATUS_FILTERS[status])
        else:
            status = ""

        query_params = {"q": search, "role": role, "status": status}
        query_params["per_page"] = per_page
        page_obj = Paginator(members, per_page).get_page(request.GET.get("page"))
        context = {
            "club": club,
            "page_obj": page_obj,
            "members": page_obj.object_list,
            "page_numbers": _page_window(page_obj.number, page_obj.paginator.num_pages),
            "total_members": club.members.count(),
            "is_creator_or_admin": creator_or_admin,
            "search": search,
            "selected_role": role,
            "status": status,
            "per_page": per_page,
            "query_string": urlencode({k: v for k, v in query_params.items() if v}),
            "page_sizes": MEMBER_PAGE_SIZES,
        }
        return render(request, self.template, context)


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
    View to display details of a single member within a club and update membership details.
    """

    template = "clubs/member_detail.html"

    def _get_member_context(
        self, club: Club, member: ClubMembership, creator_or_admin: bool, form=None
    ) -> dict:
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

        if form is None:
            form = ClubMembershipUpdateForm(instance=member)

        return {
            "club": club,
            "member": member,
            "is_creator_or_admin": creator_or_admin,
            "transactions": transactions,
            "individual_dues": individual_dues,
            "participating_years": participating_years,
            "total_credit": total_credit,
            "total_debit": total_debit,
            "total_individual_dues": total_individual_dues,
            "form": form,
            "membership_form": form,
        }

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

        context = self._get_member_context(club, member, creator_or_admin)
        return render(request, self.template, context)

    def post(self, request, club_id: int, member_id: int):
        """
        Handle POST requests to update membership details.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")

        creator_or_admin = is_club_admin_or_creator(request, club)
        if not creator_or_admin:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)

        try:
            member = club.members.select_related("user", "invited_by", "club").get(
                id=member_id
            )
        except ClubMembership.DoesNotExist:
            messages.error(request, message="Member not found in this club.")
            return redirect("clubs:detail", club_id=club.id)

        form = ClubMembershipUpdateForm(request.POST, instance=member)
        if not form.is_valid():
            context = self._get_member_context(
                club, member, creator_or_admin, form=form
            )
            return render(request, self.template, context)

        updated_member = form.save()
        messages.success(
            request,
            f"Membership details for {updated_member.user.email} updated successfully.",
        )
        return redirect(
            "clubs:club-member-detail",
            club_id=club.id,
            member_id=member.id,
        )
