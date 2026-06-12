import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy


def validate_phone_number(phone_number: str) -> None:
    """
    Checks if the phone_number submitted is valid.
    Raises ValidationError if number is not valid.
    """
    try:
        _ = phonenumbers.parse(phone_number, None)
    except phonenumbers.phonenumberutil.NumberParseException as exc:
        raise ValidationError(
            gettext_lazy("%(value)s is not a valid phone number"),
            params={"value": phone_number},
        ) from exc
