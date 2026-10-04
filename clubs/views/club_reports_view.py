from calendar import monthrange
from dataclasses import dataclass, fields
from datetime import date, datetime
from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet, Sum
from django.shortcuts import redirect, render
from django.views import View

from clubs.models import (
    Club,
    ClubMembership,
    DuePeriod,
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
)

MONTH_CHOICES = [
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


@dataclass
class ParticipantDue:
    """
    A participant's due, credits and debits up to the selected month.
    """

    user_id: int
    first_name: str
    last_name: str
    due: float
    total_credit: float
    total_debit: float


@dataclass
class FinancialReportContext:
    """
    Template context for the financial report page.
    """

    club: Club
    financial_year: FinancialYear
    financial_transactions: QuerySet[FinancialTransaction]
    selected_month: datetime
    month_choices: list[tuple[int, str]]
    year_choices: list[tuple[int, int]]
    sum_credit: float
    sum_debit: float
    participant_dues: list[ParticipantDue]
    member_options: list[ParticipantDue]
    selected_member: str
    active_tab: str
    sum_due: float
    sum_paid: float
    total_members: int

    def to_dict(self) -> dict:
        # Shallow on purpose: dataclasses.asdict would deep-copy model
        # instances and turn ParticipantDue objects back into dicts.
        return {f.name: getattr(self, f.name) for f in fields(self)}


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

    def get_selected_month_and_year(
        self,
        selected_month: str | None,
        selected_year: str | None,
        financial_year: FinancialYear,
        fy_years: list[int],
    ) -> tuple[int, int]:
        """
        Resolve and validate month/year from request params. Return defaults when invalid.
        """
        current_datetime = datetime.now()
        if not selected_month or selected_month not in [str(i) for i in range(1, 13)]:
            month = current_datetime.month
            year = current_datetime.year
        else:
            month = int(selected_month)
            try:
                if not selected_year or int(selected_year) not in fy_years:
                    year = (
                        current_datetime.year
                        if current_datetime.year in fy_years
                        else financial_year.end_date.year
                    )
                else:
                    year = int(selected_year)
            except (ValueError, TypeError):
                year = (
                    current_datetime.year
                    if current_datetime.year in fy_years
                    else financial_year.end_date.year
                )
        return (month, year)

    def build_participant_dues(
        self,
        financial_year: FinancialYear,
        selected_month_obj: datetime,
        selected_month: int,
        selected_year: int,
    ) -> list[ParticipantDue]:
        """
        Build the list of participant dues with credits and debits for each participant.
        """
        no_of_months = self.get_no_of_months(
            date(selected_year, selected_month, 1), financial_year
        )
        applicable_dues = FinancialYearContribution.objects.filter(
            financial_year=financial_year,
            due_period=DuePeriod.MONTHLY.value,
        )
        participants = FinancialYearParticipant.objects.filter(
            financial_year=financial_year
        ).select_related("club_member__user")
        participant_dues = []
        for participant in participants:
            participant_due = calculate_monthly_due_for_participant(
                applicable_dues, participant, no_of_months, selected_month_obj
            )
            transaction_sums = self.get_participants_transactions(
                participant.club_member, financial_year, selected_month_obj
            )
            participant_dues.append(
                ParticipantDue(
                    user_id=participant.club_member.user_id,
                    first_name=participant.club_member.user.first_name,
                    last_name=participant.club_member.user.last_name,
                    due=participant_due,
                    total_credit=transaction_sums["total_credit"] or 0,
                    total_debit=transaction_sums["total_debit"] or 0,
                )
            )
        return participant_dues

    def get_participants_transactions(
        self,
        club_member: ClubMembership,
        financial_year: FinancialYear,
        selected_month_obj: datetime,
    ):
        """
        Sum up the credits and debits for a single club_member up to and including
        the selected month.
        """
        last_day = monthrange(selected_month_obj.year, selected_month_obj.month)[1]
        end_of_month = date(selected_month_obj.year, selected_month_obj.month, last_day)
        return FinancialTransaction.objects.filter(
            financial_year=financial_year,
            transaction_date__lte=end_of_month,
            club_member=club_member,
        ).aggregate(total_credit=Sum("credit"), total_debit=Sum("debit"))

    def get(self, request, club_id, financial_year_id):
        """
        Handle GET requests to display financial reports.
        """
        try:
            club = Club.objects.get(id=club_id)
            is_creator = club.created_by_id == request.user.id
            is_member = club.members.filter(user=request.user).exists()
            if not is_creator and not is_member:
                return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
            financial_year = club.financial_years.get(id=financial_year_id)
        except (Club.DoesNotExist, FinancialYear.DoesNotExist):
            return redirect("clubs:index")
        fy_years = list(
            range(
                financial_year.start_date.year,
                financial_year.end_date.year + 1,
            )
        )
        selected_month, selected_year = self.get_selected_month_and_year(
            request.GET.get("month"),
            request.GET.get("year"),
            financial_year,
            fy_years,
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
        selected_month_obj = datetime(selected_year, selected_month, 1)
        participant_dues = self.build_participant_dues(
            financial_year,
            selected_month_obj,
            selected_month,
            selected_year,
        )
        member_options = participant_dues
        selected_member = request.GET.get("member", "")
        if selected_member.isdigit():
            participant_dues = [
                p for p in participant_dues if p.user_id == int(selected_member)
            ]
        else:
            selected_member = ""
        year_choices = [(y, y) for y in fy_years]
        context = FinancialReportContext(
            club=club,
            financial_year=financial_year,
            financial_transactions=financial_transactions,
            selected_month=selected_month_obj,
            month_choices=MONTH_CHOICES,
            year_choices=year_choices,
            sum_credit=cash_flow_totals["total_credit"] or 0,
            sum_debit=cash_flow_totals["total_debit"] or 0,
            participant_dues=participant_dues,
            member_options=member_options,
            selected_member=selected_member,
            active_tab=(
                "monthly"
                if selected_member or request.GET.get("tab") == "monthly"
                else "cashflow"
            ),
            sum_due=sum(p.due for p in member_options),
            sum_paid=sum(p.total_credit for p in member_options),
            total_members=len(member_options),
        )
        return render(request, "clubs/financial_reports.html", context.to_dict())
