from datetime import date, datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views import View

from clubs.models import (
    Club,
    ClubMember,
    DuePeriod,
    FinancialTransaction,
    FinancialYear,
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

    def get_no_of_months(
        self,
        selected_date: date,
        financial_year: FinancialYear,
    ) -> int:
        """
        Return the number of months from the financial year start to the selected date (inclusive).
        """
        start = financial_year.start_date
        return (
            (selected_date.year - start.year) * 12
            + (selected_date.month - start.month)
            + 1
        )

    def get_participants_transactions(
        self,
        club_member: ClubMember,
        financial_year: FinancialYear,
        selected_month: int,
        selected_year: int,
    ):
        """
        Sum up the credits and debits for a single club_member
        """
        return FinancialTransaction.objects.filter(
            financial_year=financial_year,
            transaction_date__month__lte=selected_month,
            transaction_date__year__lte=selected_year,
            club_member=club_member,
        ).aggregate(total_credit=Sum("credit"), total_debit=Sum("debit"))

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display financial reports.
        """
        current_datetime = datetime.now()
        try:
            club = Club.objects.get(id=club_id)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, FinancialYear.DoesNotExist):
            return redirect("clubs:index")
        selected_month = request.GET.get("month")
        selected_year = request.GET.get("year")
        fy_years = list(
            range(
                financial_year.start_date.year,
                financial_year.end_date.year + 1,
            )
        )
        if not selected_month or selected_month not in [str(i) for i in range(1, 13)]:
            selected_month = current_datetime.month
        else:
            selected_month = int(selected_month)
        try:
            if not selected_year or int(selected_year) not in fy_years:
                selected_year = (
                    current_datetime.year
                    if current_datetime.year in fy_years
                    else financial_year.end_date.year
                )
            else:
                selected_year = int(selected_year)
        except (ValueError, TypeError):
            selected_year = (
                current_datetime.year
                if current_datetime.year in fy_years
                else financial_year.end_date.year
            )
        financial_transactions = (
            FinancialTransaction.objects.filter(
                financial_year=financial_year,
                transaction_date__month=selected_month,
                transaction_date__year=selected_year,
            )
            .order_by("transaction_date")
            .select_related("club_member__user")
        )
        cash_flow_totals = FinancialTransaction.objects.filter(
            financial_year=financial_year,
            transaction_date__month=selected_month,
            transaction_date__year=selected_year,
        ).aggregate(total_credit=Sum("credit"), total_debit=Sum("debit"))
        applicable_dues = FinancialYearContribution.objects.filter(
            financial_year=financial_year,
            due_period=DuePeriod.MONTHLY.value,
        )
        selected_month_obj = datetime(selected_year, selected_month, 1)
        selected_date = date(selected_year, selected_month, 1)
        no_of_months = self.get_no_of_months(selected_date, financial_year)
        participants = FinancialYearParticipant.objects.filter(
            financial_year=financial_year
        ).select_related("club_member__user")
        participant_dues = []
        for participant in participants:
            participant_due = calculate_monthly_due_for_participant(
                applicable_dues, participant, no_of_months, selected_month_obj
            )
            transaction_sums = self.get_participants_transactions(
                participant.club_member, financial_year, selected_month, selected_year
            )
            participant_dues.append(
                {
                    "first_name": participant.club_member.user.first_name,
                    "last_name": participant.club_member.user.last_name,
                    "due": participant_due,
                    "total_credit": transaction_sums["total_credit"] or 0,
                    "total_debit": transaction_sums["total_debit"] or 0,
                }
            )
        month_choices = [
            (1, "January"),
            (2, "February"),
            (3, "March"),
            (4, "April"),
            (5, "May"),
            (6, "June"),
            (7, "July"),
            (8, "August"),
            (9, "September"),
            (10, "October"),
            (11, "November"),
            (12, "December"),
        ]
        year_choices = [(y, y) for y in fy_years]
        context = {
            "club": club,
            "financial_year": financial_year,
            "financial_transactions": financial_transactions,
            "selected_month": selected_month_obj,
            "month_choices": month_choices,
            "year_choices": year_choices,
            "sum_credit": cash_flow_totals["total_credit"] or 0,
            "sum_debit": cash_flow_totals["total_debit"] or 0,
            "participant_dues": participant_dues,
        }
        return render(request, "clubs/financial_reports.html", context)
