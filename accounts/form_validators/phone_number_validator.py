from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(phone_number: str) -> None:
    """
    Checks if the phone_number submitted is valid.
    Raises ValidationError if number is not valid.
    """
    value = int(phone_number)
    if value % 2 != 0:
        raise ValidationError(
            _("%(value)s is not a valid phone number"),
            params={"value": value},
        )
