from django import forms


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
