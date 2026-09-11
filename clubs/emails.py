import dataclasses
import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from clubs.models import Club, ClubMembership, DuePeriod, FinancialTransaction

logger = logging.getLogger(__name__)


@dataclass
class ContributionEmailContext:
    """
    Template context for templates/clubs/emails/contribution_email.html.
    """

    club: Club
    currency: str
    amount: Decimal | None
    contribution_label: str
    total_savings: Decimal
    member: ClubMembership
    contribution_period: datetime.date
    reference: str
    transaction: FinancialTransaction
    payment_method: str
    financial_year_label: str
    period_unit: str
    periods_paid: int
    periods_total: int
    contributions_url: str
    support_url: str
    notification_settings_url: str
    unsubscribe_url: str


def send_contribution_email(transaction: FinancialTransaction, request=None) -> bool:
    """
    Send a contribution receipt email to the member associated with a financial transaction.
    Uses templates/clubs/emails/contribution_email.html.
    Returns True if sent successfully, False otherwise.
    """
    member = transaction.club_member
    if not member or not member.user or not member.user.email:
        logger.warning(
            "Cannot send contribution email for transaction %s: missing club member or email",
            transaction.id,
        )
        return False

    financial_year = transaction.financial_year
    club = financial_year.club

    # Calculate member's total savings across the club
    member_transactions = FinancialTransaction.objects.filter(
        financial_year__club=club,
        club_member=member,
    )
    totals = member_transactions.aggregate(
        total_credit=Sum("credit"),
        total_debit=Sum("debit"),
    )
    total_credit = totals["total_credit"] or Decimal("0")
    total_debit = totals["total_debit"] or Decimal("0")
    total_savings = total_credit - total_debit

    # Calculate financial year label and periods
    if financial_year.start_date.year == financial_year.end_date.year:
        financial_year_label = f"FY {financial_year.start_date.year}"
    else:
        financial_year_label = (
            f"FY {financial_year.start_date.year}/{financial_year.end_date.year}"
        )

    contribution_due = financial_year.contributions.first()
    if contribution_due and contribution_due.due_period == DuePeriod.QUARTERLY:
        period_unit = "Quarters"
        periods_total = 4
    elif contribution_due and contribution_due.due_period == DuePeriod.YEARLY:
        period_unit = "Years"
        periods_total = 1
    else:
        period_unit = "Months"
        periods_total = 12

    periods_paid = FinancialTransaction.objects.filter(
        financial_year=financial_year,
        club_member=member,
        credit__gt=0,
    ).count()

    # Build URLs
    member_detail_path = reverse(
        "clubs:club-member-detail",
        kwargs={"club_id": club.id, "member_id": member.id},
    )
    if request:
        contributions_url = request.build_absolute_uri(member_detail_path)
        notification_settings_url = contributions_url
        unsubscribe_url = contributions_url
        support_url = (
            f"mailto:{club.contact_email}"
            if club.contact_email
            else request.build_absolute_uri(
                reverse("clubs:detail", kwargs={"club_id": club.id})
            )
        )
    else:
        contributions_url = member_detail_path
        notification_settings_url = member_detail_path
        unsubscribe_url = member_detail_path
        support_url = f"mailto:{club.contact_email}" if club.contact_email else "#"

    context = ContributionEmailContext(
        club=club,
        currency="UGX",
        amount=transaction.credit,
        contribution_label="Monthly contribution",
        total_savings=total_savings,
        member=member,
        contribution_period=transaction.transaction_date,
        reference=f"TXN-{transaction.id}",
        transaction=transaction,
        payment_method="Bank Transfer",
        financial_year_label=financial_year_label,
        period_unit=period_unit,
        periods_paid=periods_paid,
        periods_total=periods_total,
        contributions_url=contributions_url,
        support_url=support_url,
        notification_settings_url=notification_settings_url,
        unsubscribe_url=unsubscribe_url,
    )

    try:
        html_content = render_to_string(
            "clubs/emails/contribution_email.html", dataclasses.asdict(context)
        )
        text_content = strip_tags(html_content)
        subject = f"Contribution receipt — {club.name}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = member.user.email

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as e:
        logger.exception(
            "Failed to send contribution receipt email for transaction %s: %s",
            transaction.id,
            e,
        )
        return False
