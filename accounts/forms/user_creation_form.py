from django import forms

from accounts.models import CustomUser


class UserCreationForm(forms.ModelForm):
    """
    Form for user login.
    """

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "gender",
            "phone_number",
            "occupation",
            "physical_address",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "occupation": forms.TextInput(attrs={"class": "form-control"}),
            "physical_address": forms.TextInput(attrs={"class": "form-control"}),
        }
