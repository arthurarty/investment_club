from django import forms

from accounts.form_validators.phone_number_validator import validate_phone_number
from accounts.models import GenderChoices
from clubs.models import MembershipCategory, MembershipStatus


class ClubMemberShipForm(forms.Form):
    """
    Form to input the user's membership details
    """

    email = forms.EmailField(
        max_length=254, widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
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
        max_length=15,
    )
    occupation = forms.CharField(
        max_length=200, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    physical_address = forms.CharField(
        max_length=200, widget=forms.TextInput(attrs={"class": "form-control"})
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
