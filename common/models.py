from django.db import models
from django.utils import timezone


class BaseTimestampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    "created_at" and "updated_at" fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Make sure created_at and updated_at are timezone-aware before saving
        if not self.created_at:
            self.created_at = timezone.now()
        # Always update 'updated_at' timestamp on every save
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
