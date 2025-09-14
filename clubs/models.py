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
