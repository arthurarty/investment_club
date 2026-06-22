from django import forms

from clubs.models import ClubMembership


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


class ClubMemberShipForm(forms.ModelForm):
    """
    Form to input the user's membership details
    """

    class Meta:
        model = ClubMembership
        fields = ["start_date", "is_admin", "is_active", "category", "status"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "is_admin": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
