from django import forms

from clubs.models import Club


class ClubCreationForm(forms.ModelForm):
    """
    From to create a new investment club.
    """

    class Meta:
        model = Club
        fields = ["name", "description", "contact_email", "contact_phone", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }
