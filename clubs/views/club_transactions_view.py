from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.formats import date_format
from django.views import View

from clubs.emails import send_contribution_email
from clubs.forms.club_financials_forms import (
    ExpenseForm,
    FinancialTransactionForm,
    FinancialTransactionUpdateForm,
)
from clubs.models import Club, FinancialTransaction, FinancialYear
from clubs.views.club_financial_view import prepare_financial_year_context
from clubs.views.utils import is_club_admin_or_creator


def prepare_expenses_context(
    club: Club,
    financial_year: FinancialYear,
    is_club_admin: bool = True,
    expense_form: ExpenseForm | None = None,
) -> dict:
    """
    Prepare context data for the expenses view of a financial year.
    """
    expenses = (
        FinancialTransaction.objects.filter(financial_year=financial_year, debit__gt=0)
        .select_related("club_member__user", "category")
        .order_by("-transaction_date", "-id")
    )
    months = [
        (d.strftime("%Y-%m"), d.strftime("%B %Y"))
        for d in expenses.dates("transaction_date", "month", order="DESC")
    ]
    return {
        "club": club,
        "financial_year": financial_year,
        "expenses": expenses,
        "expense_count": len(expenses),
        "total_spent": expenses.aggregate(total=Sum("debit"))["total"] or 0,
        "latest_expense": expenses.first(),
        "months": months,
        "categories": club.transaction_categories.all(),
        "is_club_admin": is_club_admin,
        "expense_form": expense_form or ExpenseForm(financial_year=financial_year),
    }


class ClubFinancialYearExpensesView(LoginRequiredMixin, View):
    """
    View to list the expenses (debit transactions) of a financial year.
    """

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display the expenses of a financial year.
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
            "clubs/expenses.html",
            prepare_expenses_context(club, financial_year, is_club_admin),
        )


class FinancialYearTransactionCreateBaseView(LoginRequiredMixin, View):
    """
    Shared flow for views that record a FinancialTransaction for a financial year.

    Subclasses set `form_class` and may override the hooks below.
    """

    form_class = FinancialTransactionForm

    def post(self, request, club_id: int, financial_year_id: int):
        """
        Handle POST requests to record a new financial transaction.
        """
        try:
            club = Club.objects.get(id=club_id)
            financial_year = club.financial_years.get(id=financial_year_id)
            allowed = is_club_admin_or_creator(request, club)
            if not allowed:
                return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
        except (Club.DoesNotExist, FinancialYear.DoesNotExist):
            return redirect("clubs:index")
        form = self.form_class(request.POST, financial_year=financial_year)
        if not form.is_valid():
            return self.form_invalid(request, club, financial_year, form)
        new_transaction = form.save(commit=False)
        new_transaction.financial_year = financial_year
        new_transaction.created_by = request.user
        new_transaction.updated_by = request.user
        new_transaction.save()
        return self.form_valid(request, club, financial_year, new_transaction)

    def form_invalid(self, request, club, financial_year, form):
        """
        Re-render the page the form was submitted from.
        """
        return render(
            request,
            "clubs/financial_year_detail.html",
            prepare_financial_year_context(club, financial_year, True),
        )

    def form_valid(self, request, club, financial_year, transaction):
        """
        Handle a saved transaction.
        """
        raise NotImplementedError


class FinancialTransactionCreateView(FinancialYearTransactionCreateBaseView):
    """
    View to handle the creation of a new financial transaction for a financial year.
    """

    form_class = FinancialTransactionForm

    def form_valid(self, request, club, financial_year, transaction):
        """
        A payment from a member is recorded as a transaction.
        """
        messages.success(
            request,
            message=f"Transaction '{transaction.description}' added successfully.",
        )
        if transaction.credit and not transaction.debit and transaction.club_member:
            send_contribution_email(transaction, request=request)
        return redirect(
            "clubs:financial-year-detail",
            club_id=club.id,
            financial_year_id=financial_year.id,
        )


class ExpenseCreateView(FinancialYearTransactionCreateBaseView):
    """
    View to handle the recording of a new expense for a financial year.
    """

    form_class = ExpenseForm

    def form_invalid(self, request, club, financial_year, form):
        """
        Re-render the expenses page with the form errors.
        """
        return render(
            request,
            "clubs/expenses.html",
            prepare_expenses_context(club, financial_year, True, expense_form=form),
        )

    def form_valid(self, request, club, financial_year, transaction):
        """
        Confirm the expense and return to the expenses page.
        """
        messages.success(
            request,
            message=f"Expense '{transaction.description}' recorded successfully.",
        )
        return redirect(
            "clubs:financial-year-expenses",
            club_id=club.id,
            financial_year_id=financial_year.id,
        )


# Tracked transaction fields mapped to how the history names them.
TRANSACTION_HISTORY_LABELS = {
    "description": "Description",
    "credit": "Credit",
    "debit": "Debit",
    "transaction_date": "Date",
    "category_id": "Category",
    "club_member_id": "Member",
}


def history_value(event, field: str) -> str:
    """
    How the history shows the value a tracked field had at an event.
    Returns an empty string when the field was not set.
    """
    value = getattr(event, field)
    if value is None:
        return ""
    try:
        if field in ("credit", "debit"):
            return f"Ugx {value:,.2f}"
        if field == "transaction_date":
            return date_format(value, "M j, Y")
        if field == "category_id":
            return event.category.name
        if field == "club_member_id":
            return user_display_name(event.club_member.user)
    except ObjectDoesNotExist:
        # Events outlive the category or member they point to.
        return "Removed"
    return str(value)


def user_display_name(user) -> str:
    """
    A user's full name, falling back to their email when no name is set.
    """
    return f"{user.first_name} {user.last_name}".strip() or user.email


def prepare_transaction_history(transaction: FinancialTransaction) -> list[dict]:
    """
    Build the history of a transaction from its tracked events, newest first.

    Each entry has the `user` who acted, `when` they did, and for edits the
    `changes`: a `field` name with its `old` and `new` value for each field
    that changed.
    """
    events = list(
        transaction.events.select_related(
            "updated_by", "category", "club_member__user"
        ).order_by("pgh_id")
    )
    history = []
    if not events or events[0].pgh_label != "insert":
        # Recorded before history tracking was set up.
        history.append(
            {
                "user": user_display_name(transaction.created_by),
                "when": transaction.created_at,
                "changes": None,
            }
        )
    previous = None
    for event in events:
        entry = {
            "user": user_display_name(event.updated_by),
            "when": event.pgh_created_at,
            "changes": None,
        }
        if event.pgh_label != "insert":
            # With no earlier event (the transaction predates history
            # tracking) there is nothing to compare against, so the edit is
            # listed without naming fields.
            entry["changes"] = [
                {
                    "field": label,
                    "old": history_value(previous, field),
                    "new": history_value(event, field),
                }
                for field, label in TRANSACTION_HISTORY_LABELS.items()
                if previous is not None
                and getattr(previous, field) != getattr(event, field)
            ]
        history.append(entry)
        previous = event
    history.reverse()
    return history


class FinancialTransactionDetailView(LoginRequiredMixin, View):
    """
    View to show a single financial transaction, and let club admins edit it.
    """

    template_name = "clubs/transaction_detail.html"

    def load(self, request, club_id, financial_year_id, transaction_id):
        """
        Fetch the club, financial year and transaction named in the URL.
        Returns (club, financial_year, transaction, is_club_admin, response);
        when `response` is set the request should end with it.
        """
        try:
            club = Club.objects.get(id=club_id)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, FinancialYear.DoesNotExist):
            return None, None, None, False, redirect("clubs:index")
        is_club_admin = is_club_admin_or_creator(request, club)
        is_member = club.members.filter(user=request.user).exists()
        if not is_club_admin and not is_member:
            forbidden = render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
            return club, financial_year, None, False, forbidden
        transaction = (
            financial_year.transactions.select_related(
                "club_member__user", "category", "created_by"
            )
            .filter(id=transaction_id)
            .first()
        )
        if transaction is None:
            not_found = redirect(
                "clubs:financial-year-detail",
                club_id=club.id,
                financial_year_id=financial_year.id,
            )
            return club, financial_year, None, is_club_admin, not_found
        return club, financial_year, transaction, is_club_admin, None

    def render_detail(
        self, request, club, financial_year, transaction, is_club_admin, form=None
    ):
        """
        Render the transaction page. Admins also get the edit form.
        """
        history = prepare_transaction_history(transaction)
        edits = [entry for entry in history if entry["changes"] is not None]
        if is_club_admin and form is None:
            form = FinancialTransactionUpdateForm(
                instance=transaction, financial_year=financial_year
            )
        context = {
            "club": club,
            "financial_year": financial_year,
            "transaction": transaction,
            "is_money_in": (transaction.credit or 0) >= (transaction.debit or 0),
            "recorded_by": user_display_name(transaction.created_by),
            "last_edited": edits[0]["when"] if edits else None,
            "history": history,
            "is_club_admin": is_club_admin,
            "transaction_form": form,
        }
        return render(request, self.template_name, context)

    def get(self, request, club_id, financial_year_id, transaction_id):
        """
        Handle GET requests to display a transaction to club members.
        """
        club, financial_year, transaction, is_club_admin, response = self.load(
            request, club_id, financial_year_id, transaction_id
        )
        if response:
            return response
        return self.render_detail(
            request, club, financial_year, transaction, is_club_admin
        )

    def post(self, request, club_id, financial_year_id, transaction_id):
        """
        Handle POST requests to edit a transaction. Club admins only.
        """
        club, financial_year, transaction, is_club_admin, response = self.load(
            request, club_id, financial_year_id, transaction_id
        )
        if response:
            return response
        if not is_club_admin:
            return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
        form = FinancialTransactionUpdateForm(
            request.POST, instance=transaction, financial_year=financial_year
        )
        if not form.is_valid():
            # The form has modified the instance; show the saved values.
            transaction.refresh_from_db()
            return self.render_detail(
                request, club, financial_year, transaction, True, form=form
            )
        if form.has_changed():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(
                request, message=f"Transaction '{updated.description}' updated."
            )
        return redirect(
            "clubs:financial-transaction-detail",
            club_id=club.id,
            financial_year_id=financial_year.id,
            transaction_id=transaction.id,
        )


class IncomeView(LoginRequiredMixin, View):
    """
    View to display details of a specific financial year for a club.
    """

    def prepare_income_context(
        self,
        club: Club,
        financial_year: FinancialYear,
        is_club_admin: bool = True,
        expense_form: ExpenseForm | None = None,
    ):
        """
        Prepare a context that contains only the credits/revenue received by a club.
        """
        credits = (
            FinancialTransaction.objects.filter(
                financial_year=financial_year, credit__gt=0
            )
            .select_related("club_member__user", "category")
            .order_by("-transaction_date", "-id")
        )
        months = [
            (d.strftime("%Y-%m"), d.strftime("%B %Y"))
            for d in credits.dates("transaction_date", "month", order="DESC")
        ]
        return {
            "club": club,
            "financial_year": financial_year,
            "credits": credits,
            "credit_count": len(credits),
            "total_received": credits.aggregate(total=Sum("credit"))["total"] or 0,
            "latest_credit": credits.first(),
            "months": months,
            "categories": club.transaction_categories.all(),
            "is_club_admin": is_club_admin,
            "expense_form": expense_form or ExpenseForm(financial_year=financial_year),
        }

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display the expenses of a financial year.
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
            "clubs/revenue.html",
            self.prepare_income_context(club, financial_year, is_club_admin),
        )
