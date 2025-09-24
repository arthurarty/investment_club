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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_clubs"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="updated_clubs"
    )

    def __str__(self):
        return f"{self.pk} - {self.name}"


class ClubMember(BaseTimestampedModel, models.Model):
    """
    Model representing a member of an investment club.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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
    monthly_contribution = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("club", "start_date", "end_date")

    def __str__(self):
        return f"FY {self.start_date.year}-{self.end_date.year} for {self.club}"


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

    class Meta:
        unique_together = ("financial_year", "club_member")

    def __str__(self):
        return f"{self.club_member} in {self.financial_year}"
