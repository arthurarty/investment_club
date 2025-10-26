from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from clubs.models import (
    Club,
    FinancialTransaction,
)


class FinancialReportsView(LoginRequiredMixin, View):
    """
    View to display financial reports for a specific financial year of a club.
    """

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display financial reports.
        """
        current_datetime = datetime.now()
        try:
            club = Club.objects.get(id=club_id)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, club.financial_years.model.DoesNotExist):
            return redirect("clubs:index")
        selected_month = request.GET.get("month")
        if not selected_month or selected_month not in [str(i) for i in range(1, 13)]:
            selected_month = current_datetime.month
        financial_transactions = (
            FinancialTransaction.objects.filter(
                financial_year=financial_year,
                transaction_date__month=selected_month,
            )
            .order_by("transaction_date")
            .select_related("club_member__user")
        )
        context = {
            "club": club,
            "financial_year": financial_year,
            "financial_transactions": financial_transactions,
            "selected_month": datetime(current_datetime.year, int(selected_month), 1),
        }
        return render(request, "clubs/financial_reports.html", context)
