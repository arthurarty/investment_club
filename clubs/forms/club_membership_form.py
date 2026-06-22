from django import forms

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
