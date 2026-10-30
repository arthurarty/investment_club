from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views import View

from clubs.emails import send_contribution_email
from clubs.forms.club_financials_forms import ExpenseForm, FinancialTransactionForm
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
        .select_related("club_member__user")
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
