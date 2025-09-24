from django import forms

from clubs.models import FinancialYear, FinancialYearParticipant


class FinancialYearForm(forms.ModelForm):
    """
    Form for creating or updating a Financial Year.
    """

    class Meta:
        model = FinancialYear
        fields = ["start_date", "end_date", "monthly_contribution"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "monthly_contribution": forms.NumberInput(
                attrs={"step": "10000.00", "class": "form-control"}
            ),
        }


class FinancialYearParticipantForm(forms.ModelForm):
    """
    Form for adding a participant to a Financial Year.
    """

    class Meta:
        model = FinancialYearParticipant
        fields = ["club_member", "financial_year"]
