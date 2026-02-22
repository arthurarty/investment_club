from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views import View

from clubs.models import (
    Club,
    DuePeriod,
    FinancialTransaction,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
)


def compute_monthly_due(dues, no_of_months: int) -> float:
    """
    Compute the total monthly due for a given financial year and no of months
    since the financial year started.
    """
    dues = dues.aggregate(total_due=Sum("amount"))
    total_due = dues["total_due"] or 0
    return total_due * no_of_months


def calculate_monthly_due_for_participant(
    dues,
    participant: FinancialYearParticipant,
    no_of_months: int,
    selected_month_obj: datetime,
) -> float:
    """
    Calculate the due for given participant.
    """
    monthly_dues = compute_monthly_due(dues, no_of_months)
    individual_dues = IndividualDue.objects.filter(
        financial_year=participant.financial_year,
        club_member=participant.club_member,
        due_date__month__lte=selected_month_obj.month,
    ).aggregate(total_individual_due=Sum("amount"))
    return monthly_dues + (individual_dues["total_individual_due"] or 0)


class FinancialReportView(LoginRequiredMixin, View):
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
        cash_flow_totals = FinancialTransaction.objects.filter(
            financial_year=financial_year, transaction_date__month=selected_month
        ).aggregate(total_credit=Sum("credit"), total_debit=Sum("debit"))
        applicable_dues = FinancialYearContribution.objects.filter(
            financial_year=financial_year,
            due_period=DuePeriod.MONTHLY.value,
        )
        selected_month_obj = datetime(current_datetime.year, int(selected_month), 1)
        no_of_months = (selected_month_obj.month - financial_year.start_date.month) + 1
        total_computed_due = compute_monthly_due(applicable_dues, no_of_months)
        participants = FinancialYearParticipant.objects.filter(
            financial_year=financial_year
        ).select_related("club_member__user")
        participant_dues = []
        for participant in participants:
            participant_due = calculate_monthly_due_for_participant(
                applicable_dues, participant, no_of_months, selected_month_obj
            )
            participant_dues.append(
                {
                    "first_name": participant.club_member.user.first_name,
                    "last_name": participant.club_member.user.last_name,
                    "due": participant_due,
                }
            )
        context = {
            "club": club,
            "financial_year": financial_year,
            "financial_transactions": financial_transactions,
            "selected_month": selected_month_obj,
            "sum_credit": cash_flow_totals["total_credit"] or 0,
            "sum_debit": cash_flow_totals["total_debit"] or 0,
            "total_monthly_due": total_computed_due,
            "applicable_dues": applicable_dues,
            "participants": participants,
            "participant_dues": participant_dues,
        }
        return render(request, "clubs/financial_reports.html", context)
