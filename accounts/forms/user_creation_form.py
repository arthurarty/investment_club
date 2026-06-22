from django import forms

from accounts.form_validators.phone_number_validator import validate_phone_number
from accounts.models import GenderChoices


class UserCreationForm(forms.Form):
    """
    Form for user login.
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
