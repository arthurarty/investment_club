from django import forms

from accounts.form_validators.phone_number_validator import validate_phone_number
from accounts.models import GenderChoices
from clubs.models import MembershipCategory, MembershipStatus


class MemberLookupForm(forms.Form):
    """
    Form to look up a member by email.
    """

    email = forms.EmailField(
        required=True,
        label="",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "jane.doe@example.com"}
        ),
    )


class ClubMemberShipForm(forms.Form):
    """
    Form to input the user's membership details
    """

    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    last_name = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    gender = forms.ChoiceField(
        choices=GenderChoices.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        validators=[validate_phone_number],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+254712345678"}
        ),
    )
    occupation = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    physical_address = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    is_admin = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    category = forms.ChoiceField(
        choices=MembershipCategory.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=MembershipStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
