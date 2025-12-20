from django.conf import settings
from django.db import models

from common.models import BaseTimestampedModel


class ClubStatus(models.TextChoices):
    """
    Enumeration for club status.
    """

    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    DISSOLVED = "dissolved", "Dissolved"


class DuePeriod(models.TextChoices):
    """
    Options for due periods.
    """

    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"


class Club(BaseTimestampedModel, models.Model):
    """
    Model representing an investment club.
    """

    name = models.CharField(max_length=350, unique=True)
    description = models.TextField()
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField()
    status = models.CharField(
        max_length=20, choices=ClubStatus.choices, default=ClubStatus.ACTIVE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_clubs"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_clubs"
    )

    def __str__(self):
        return f"{self.pk} - {self.name}"


class ClubMember(BaseTimestampedModel, models.Model):
    """
    Model representing a member of an investment club.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="club_memberships",
    )
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="members")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(
        default=False
    )  # User has admin privileges in the club
    is_active = models.BooleanField(
        default=True
    )  # User is currently active in the club
    is_confirmed = models.BooleanField(
        default=False
    )  # User has confirmed membership via email or other means
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_sent",
    )
    role = models.CharField(
        max_length=150, blank=True, default="member"
    )  # Role of the member in the club (e.g., Treasurer, Secretary)

    class Meta:
        unique_together = ("user", "club")

    def __str__(self):
        return f"{self.user.first_name} in {self.club.name}"


class FinancialYear(BaseTimestampedModel, models.Model):
    """
    Model representing a financial year for a club.
    """

    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="financial_years"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_years",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_financial_years",
    )

    class Meta:
        unique_together = ("club", "start_date", "end_date")

    def __str__(self):
        return f"FY {self.start_date}->{self.end_date} for {self.club}"


class FinancialYearContribution(BaseTimestampedModel, models.Model):
    """
    Model represents the amounts of money per due period that club
    members are expected to contribute during a financial year.
    """

    financial_year = models.ForeignKey(
        FinancialYear, on_delete=models.CASCADE, related_name="contributions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_period = models.CharField(
        max_length=20, choices=DuePeriod.choices, default=DuePeriod.MONTHLY
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_year_contributions",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_financial_year_contributions",
    )

    def __str__(self):
        return f"{self.financial_year} - {self.amount} - {self.due_period}"


class FinancialYearParticipant(BaseTimestampedModel, models.Model):
    """
    Model representing a participant in a financial year.
    """

    financial_year = models.ForeignKey(
        FinancialYear, on_delete=models.CASCADE, related_name="participants"
    )
    club_member = models.ForeignKey(
        ClubMember, on_delete=models.CASCADE, related_name="financial_years"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_year_participants",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_financial_year_participants",
    )

    class Meta:
        unique_together = ("financial_year", "club_member")

    def __str__(self):
        return f"{self.club_member} in {self.financial_year}"


class IndividualDue(BaseTimestampedModel, models.Model):
    """
    Represents dues that only apply a particular club member within a financial year.
    This can be used for fines, special assessments, or other individual charges.
    """

    financial_year = models.ForeignKey(
        FinancialYear, on_delete=models.CASCADE, related_name="individual_dues"
    )
    club_member = models.ForeignKey(
        ClubMember, on_delete=models.CASCADE, related_name="individual_dues"
    )
    description = models.CharField(max_length=1000)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_individual_dues",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_individual_dues",
    )

    def __str__(self):
        return f"Due {self.amount} - {self.financial_year} - {self.club_member}"


class FinancialTransaction(BaseTimestampedModel, models.Model):
    """
    Model representing a financial transaction within a financial year.
    """

    financial_year = models.ForeignKey(
        FinancialYear, on_delete=models.CASCADE, related_name="transactions"
    )
    description = models.CharField(max_length=1000)
    credit = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )  # Money received
    debit = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )  # Money spent
    transaction_date = models.DateField()
    club_member = models.ForeignKey(
        ClubMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_financial_transactions",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_financial_transactions",
    )

    def __str__(self):
        return f"TSN {self.credit} {self.debit} - {self.transaction_date} - {self.financial_year}"
