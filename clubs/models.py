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

    name = models.CharField(max_length=100)
    description = models.TextField()
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField()
    status = models.CharField(
        max_length=20, choices=ClubStatus.choices, default=ClubStatus.ACTIVE
    )

    def __str__(self):
        return str(self.name)
