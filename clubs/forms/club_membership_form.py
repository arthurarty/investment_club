from django import forms

from accounts.form_validators.phone_number_validator import validate_phone_number
from accounts.models import GenderChoices
from clubs.models import ClubMembership, MembershipCategory, MembershipStatus


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
        max_length=18,
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
    category = forms.ChoiceField(
        choices=MembershipCategory.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=MembershipStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class ClubMembershipUpdateForm(forms.ModelForm):
    """
    Form for updating a member's club membership details.
    """

    class Meta:
        model = ClubMembership
        fields = [
            "start_date",
            "end_date",
            "category",
            "status",
            "is_admin",
            "is_active",
            "is_confirmed",
        ]
        labels = {
            "start_date": "Join Date",
            "end_date": "End Date",
            "category": "Membership Category",
            "status": "Membership Status",
            "is_admin": "Admin Privileges",
            "is_active": "Active Member",
            "is_confirmed": "Confirmed Membership",
        }
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_admin": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_confirmed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        status = cleaned_data.get("status")

        if start_date and end_date:
            start_d = start_date.date() if hasattr(start_date, "date") else start_date
            if end_date < start_d:
                self.add_error(
                    "end_date", "End date cannot be earlier than start date."
                )

        if status and status != MembershipStatus.ACTIVE:
            cleaned_data["is_active"] = False

        return cleaned_data
