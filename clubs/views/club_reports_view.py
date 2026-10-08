import logging
from calendar import monthrange
from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from http import HTTPStatus

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.db.models import QuerySet, Sum
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.views import View

from clubs.context_processors import CURRENT_CLUB_SESSION_KEY
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
from clubs.views.utils import is_club_admin_or_creator

logger = logging.getLogger(__name__)

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
    is_club_admin: bool

    def to_dict(self) -> dict:
        # Shallow on purpose: dataclasses.asdict would deep-copy model
        # instances and turn ParticipantDue objects back into dicts.
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class MonthlyReportEmailContext:
    """
    Template context for templates/clubs/emails/monthly_report_email.html.
    """

    club: Club
    financial_year: FinancialYear
    report_month: date
    recipient_first_name: str
    currency: str
    paid: Decimal
    due: Decimal
    financial_year_paid_to_date: Decimal
    is_fully_paid: bool
    other_members_count: int
    others_paid: Decimal
    club_collected: Decimal
    club_due: Decimal
    collected_pct: int
    remaining_pct: int
    fully_paid_count: int
    member_count: int
    expenses: list[dict]
    total_expenses: Decimal
    net_added: Decimal
    report_url: str
    settings_url: str
    unsubscribe_url: str

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class MonthlyFigures:
    """
    Per-member amounts (keyed by club member id) for one monthly report.
    """

    paid_in_month: dict[int, Decimal]
    paid_to_date: dict[int, Decimal]
    due_by_member: dict[int, Decimal]

    def is_fully_paid(self, member_id: int) -> bool:
        due = self.due_by_member[member_id]
        return due > 0 and self.paid_to_date.get(member_id, Decimal("0")) >= due


def get_month_end(month_date: date | datetime) -> date:
    """
    Return the last day of the month that `month_date` falls in.
    """
    return date(
        month_date.year,
        month_date.month,
        monthrange(month_date.year, month_date.month)[1],
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
        due_date__lte=get_month_end(selected_month_obj),
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
        end_of_month = get_month_end(selected_month_obj)
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
            is_club_admin=club.members.filter(
                user=request.user, is_admin=True
            ).exists(),
        )
        return render(request, "clubs/financial_reports.html", context.to_dict())


class SendMonthlyReportEmailsView(LoginRequiredMixin, View):
    """
    Email the monthly report to every participant of a financial year.

    POST only. Requires ``month`` and ``year`` (the year must fall within the
    financial year); only club admins may trigger it.
    """

    currency = "UGX"

    @staticmethod
    def parse_report_month(
        month: str | None, year: str | None, financial_year: FinancialYear
    ) -> date | None:
        """
        Return the first day of the requested month, or None if month or year
        is missing or invalid.
        """
        try:
            month_number, year_number = int(month), int(year)
        except (TypeError, ValueError):
            return None
        if not 1 <= month_number <= 12:
            return None
        if not (
            financial_year.start_date.year
            <= year_number
            <= financial_year.end_date.year
        ):
            return None
        return date(year_number, month_number, 1)

    def post(self, request, club_id, financial_year_id):
        club = Club.objects.filter(id=club_id).first()
        if not club:
            return redirect("clubs:index")
        if not ClubMembership.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            messages.error(
                request,
                message="You do not have permission to send reports for this club.",
            )
            return redirect("clubs:detail", club_id=club.id)
        financial_year = club.financial_years.filter(id=financial_year_id).first()
        if not financial_year:
            return redirect("clubs:detail", club_id=club.id)

        reports_url = self.reports_path(club, financial_year)
        report_month = self.parse_report_month(
            request.POST.get("month"), request.POST.get("year"), financial_year
        )
        if not report_month:
            messages.error(
                request,
                "Select a valid month and year within the financial year.",
            )
            return redirect(reports_url)

        participants = list(
            FinancialYearParticipant.objects.filter(
                financial_year=financial_year
            ).select_related("club_member__user")
        )
        if not participants:
            messages.info(request, "This financial year has no participants.")
            return redirect(reports_url)

        sent, failed = 0, 0
        for recipient, context in self.build_contexts(
            request, club, financial_year, participants, report_month
        ):
            if self.send_email(context, recipient):
                sent += 1
            else:
                failed += 1
        if sent:
            messages.success(
                request,
                f"{report_month:%B %Y} report sent to {sent} "
                f"participant{'s' if sent != 1 else ''}.",
            )
        if failed:
            messages.error(
                request,
                f"Could not send the report to {failed} "
                f"participant{'s' if failed != 1 else ''}.",
            )
        return redirect(reports_url)

    @staticmethod
    def reports_path(club: Club, financial_year: FinancialYear) -> str:
        return reverse(
            "clubs:financial-reports",
            kwargs={"club_id": club.id, "financial_year_id": financial_year.id},
        )

    def build_contexts(
        self,
        request,
        club: Club,
        financial_year: FinancialYear,
        participants: list[FinancialYearParticipant],
        report_month: date,
    ) -> list[tuple[str, MonthlyReportEmailContext]]:
        """
        Build a (recipient email, context) pair per participant for the month.
        """
        month_transactions = FinancialTransaction.objects.filter(
            financial_year=financial_year,
            transaction_date__year=report_month.year,
            transaction_date__month=report_month.month,
        )
        figures = MonthlyFigures(
            paid_in_month=self.totals_by_member(month_transactions, "credit"),
            paid_to_date=self.totals_by_member(
                FinancialTransaction.objects.filter(
                    financial_year=financial_year,
                    transaction_date__lte=get_month_end(report_month),
                ),
                "credit",
            ),
            due_by_member=self.compute_due_by_member(
                financial_year, participants, report_month
            ),
        )
        club_fields = self.build_club_fields(
            request,
            club,
            financial_year,
            participants,
            report_month,
            month_transactions,
            figures,
        )
        built = (
            self.build_participant_context(request, participant, club_fields, figures)
            for participant in participants
        )
        return [item for item in built if item]

    def compute_due_by_member(
        self,
        financial_year: FinancialYear,
        participants: list[FinancialYearParticipant],
        report_month: date,
    ) -> dict[int, Decimal]:
        """
        Total due per member from the start of the financial year to the end of
        the month.
        """
        zero = Decimal("0")
        no_of_months = FinancialReportView().get_no_of_months(
            report_month, financial_year
        )
        monthly_due = (
            FinancialYearContribution.objects.filter(
                financial_year=financial_year, due_period=DuePeriod.MONTHLY.value
            ).aggregate(total=Sum("amount"))["total"]
            or zero
        )
        individual_due = self.totals_by_member(
            IndividualDue.objects.filter(
                financial_year=financial_year,
                due_date__lte=get_month_end(report_month),
            ),
            "amount",
        )
        return {
            p.club_member_id: monthly_due * no_of_months
            + individual_due.get(p.club_member_id, zero)
            for p in participants
        }

    def build_club_fields(
        self,
        request,
        club: Club,
        financial_year: FinancialYear,
        participants: list[FinancialYearParticipant],
        report_month: date,
        month_transactions,
        figures: "MonthlyFigures",
    ) -> dict:
        """
        Club-wide fields shared by every participant's email context.
        """
        zero = Decimal("0")
        club_collected = (
            month_transactions.aggregate(total=Sum("credit"))["total"] or zero
        )
        club_collected_to_date = sum(
            (figures.paid_to_date.get(p.club_member_id, zero) for p in participants),
            zero,
        )
        club_due = sum(figures.due_by_member.values(), zero)
        collected_pct = (
            min(100, round(club_collected_to_date / club_due * 100))
            if club_due > 0
            else 0
        )
        expenses, total_expenses = self.compute_expenses(month_transactions)
        report_url = request.build_absolute_uri(
            self.reports_path(club, financial_year)
            + f"?month={report_month.month}&year={report_month.year}"
        )
        return {
            "club": club,
            "financial_year": financial_year,
            "report_month": report_month,
            "currency": self.currency,
            "club_collected": club_collected,
            "club_due": club_due,
            "collected_pct": collected_pct,
            "remaining_pct": 100 - collected_pct,
            "fully_paid_count": sum(
                figures.is_fully_paid(p.club_member_id) for p in participants
            ),
            "member_count": len(participants),
            "expenses": expenses,
            "total_expenses": total_expenses,
            "net_added": club_collected - total_expenses,
            "report_url": report_url,
        }

    @staticmethod
    def totals_by_member(queryset, field: str) -> dict[int, Decimal]:
        """
        Sum `field` per club member, keyed by club member id.
        """
        rows = queryset.values("club_member").annotate(total=Sum(field))
        return {row["club_member"]: row["total"] or Decimal("0") for row in rows}

    def compute_expenses(self, month_transactions) -> tuple[list[dict], Decimal]:
        """
        Return the month's expense line items and their total.
        """
        expense_rows = month_transactions.filter(debit__gt=0).order_by(
            "transaction_date", "id"
        )
        expenses = [
            {
                "description": e.description,
                "date_label": f"{e.transaction_date:%d %b}",
                "amount": e.debit,
            }
            for e in expense_rows
        ]
        total_expenses = sum((e["amount"] for e in expenses), Decimal("0"))
        return expenses, total_expenses

    def build_participant_context(
        self,
        request,
        participant: FinancialYearParticipant,
        club_fields: dict,
        figures: "MonthlyFigures",
    ) -> tuple[str, MonthlyReportEmailContext] | None:
        """
        Build the (recipient email, context) pair for one participant, or None
        if the member has no email address.
        """
        member = participant.club_member
        user = member.user
        if not user.email:
            logger.warning("Skipping monthly report for member %s: no email", member.id)
            return None
        zero = Decimal("0")
        paid = figures.paid_in_month.get(member.id, zero)
        member_url = request.build_absolute_uri(
            reverse(
                "clubs:club-member-detail",
                kwargs={"club_id": club_fields["club"].id, "member_id": member.id},
            )
        )
        context = MonthlyReportEmailContext(
            **club_fields,
            recipient_first_name=user.first_name or user.email,
            paid=paid,
            due=figures.due_by_member[member.id],
            financial_year_paid_to_date=figures.paid_to_date.get(member.id, zero),
            is_fully_paid=figures.is_fully_paid(member.id),
            other_members_count=club_fields["member_count"] - 1,
            others_paid=club_fields["club_collected"] - paid,
            settings_url=member_url,
            unsubscribe_url=member_url,
        )
        return user.email, context

    def send_email(self, context: MonthlyReportEmailContext, recipient: str) -> bool:
        """
        Render and send one report email. Returns True on success.
        """
        try:
            html_content = render_to_string(
                "clubs/emails/monthly_report_email.html", context.to_dict()
            )
            message = EmailMultiAlternatives(
                subject=f"{context.report_month:%B %Y} report — {context.club.name}",
                body=strip_tags(html_content),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
            )
            message.attach_alternative(html_content, "text/html")
            message.send()
            return True
        except Exception:
            logger.exception(
                "Failed to send monthly report to %s for club %s",
                recipient,
                context.club.id,
            )
            return False


class FinancialReportListView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            club_id = request.session.get(CURRENT_CLUB_SESSION_KEY)
            club = Club.objects.get(id=club_id)
            is_club_admin = is_club_admin_or_creator(request, club)
            is_member = club.members.filter(user=request.user).exists()
            if not is_club_admin and not is_member:
                return render(request, "clubs/403.html", status=HTTPStatus.FORBIDDEN)
            financial_years = list(club.financial_years.order_by("-start_date")[:25])
        except Club.DoesNotExist:
            return redirect("clubs:index")
        return render(
            request,
            "clubs/financial_year_list.html",
            {"club": club, "financial_years": financial_years},
        )
