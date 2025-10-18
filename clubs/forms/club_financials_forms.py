from django import forms

from clubs.models import (
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
)


class FinancialYearForm(forms.ModelForm):
    """
    Form for creating or updating a Financial Year.
    """

    class Meta:
        model = FinancialYear
        fields = ["start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }


class FinancialYearContributionForm(forms.ModelForm):
    """
    Form for adding a contribution to a Financial Year.
    """

    class Meta:
        model = FinancialYearContribution
        fields = ["amount", "due_period"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"step": "10000.00", "class": "form-control"}
            ),
            "due_period": forms.Select(attrs={"class": "form-select"}),
        }


class FinancialYearParticipantForm(forms.ModelForm):
    """
    Form for adding a participant to a Financial Year.
    """

    class Meta:
        model = FinancialYearParticipant
        fields = ["club_member", "financial_year"]


class FinancialTransactionForm(forms.ModelForm):
    """
    Form for recording a financial transaction for a Financial Year.
    """

    class Meta:
        model = FinancialTransaction
        fields = ["club_member", "credit", "debit", "transaction_date", "description"]
        widgets = {
            "club_member": forms.Select(attrs={"class": "form-select"}),
            "credit": forms.NumberInput(
                attrs={"step": "10000.00", "class": "form-control"}
            ),
            "debit": forms.NumberInput(
                attrs={"step": "10000.00", "class": "form-control"}
            ),
            "transaction_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
