from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views import View

from clubs.forms.club_financials_forms import TransactionCategoryForm
from clubs.models import Club
from clubs.views.utils import is_club_admin_or_creator


def prepare_categories_context(
    club: Club,
    is_club_admin: bool = True,
    category_form: TransactionCategoryForm | None = None,
) -> dict:
    """
    Prepare context data for the transaction categories view of a club.
    """
    categories = club.transaction_categories.annotate(
        transaction_count=Count("transactions")
    )
    return {
        "club": club,
        "categories": categories,
        "is_club_admin": is_club_admin,
        "category_form": category_form or TransactionCategoryForm(club=club),
    }


class ClubCategoryListView(LoginRequiredMixin, View):
    """
    View to list a club's transaction categories and add new ones.
    """

    def get(self, request, club_id: int):
        """
        Handle GET requests to display the categories of a club.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")
        is_club_admin = is_club_admin_or_creator(request, club)
        is_member = club.members.filter(user=request.user).exists()
        if not is_club_admin and not is_member:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
        return render(
            request,
            "clubs/categories.html",
            prepare_categories_context(club, is_club_admin),
        )

    def post(self, request, club_id: int):
        """
        Handle POST requests to add a new category to a club.
        """
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return redirect("clubs:index")
        if not is_club_admin_or_creator(request, club):
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
        form = TransactionCategoryForm(request.POST, club=club)
        if not form.is_valid():
            return render(
                request,
                "clubs/categories.html",
                prepare_categories_context(club, True, category_form=form),
            )
        category = form.save(commit=False)
        category.club = club
        category.created_by = request.user
        category.updated_by = request.user
        category.save()
        messages.success(
            request, message=f"Category '{category.name}' added successfully."
        )
        return redirect("clubs:categories", club_id=club.id)
