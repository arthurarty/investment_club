from django import forms

from clubs.models import (
    ClubMembership,
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
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
                attrs={"step": "5000.00", "class": "form-control"}
            ),
            "due_period": forms.Select(attrs={"class": "form-select"}),
        }


class FinancialYearParticipantForm(forms.ModelForm):
    """
    Form for adding a participant to a Financial Year.
    """

    class Meta:
        model = FinancialYearParticipant
        fields = ["club_member"]
        widgets = {
            "club_member": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, club=None, **kwargs):
        super().__init__(*args, **kwargs)
        if club is not None:
            self.fields["club_member"].queryset = ClubMembership.objects.filter(
                club=club, is_active=True
            ).select_related("user")


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
                attrs={"step": "1.00", "class": "form-control"}
            ),
            "debit": forms.NumberInput(attrs={"step": "1.00", "class": "form-control"}),
            "transaction_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "credit": "Credit (money received)",
            "debit": "Debit (money paid out)",
        }

    def __init__(self, *args, financial_year: FinancialYear = None, **kwargs):
        super().__init__(*args, **kwargs)
        if financial_year is not None:
            self.fields["club_member"].queryset = ClubMembership.objects.filter(
                financial_years__financial_year=financial_year,
                financial_years__is_active=True,
            ).select_related("user")


class IndividualDueForm(forms.ModelForm):
    """
    Form for creating an IndividualDue for a Financial Year.
    """

    class Meta:
        model = IndividualDue
        fields = ["club_member", "description", "amount", "due_date"]
        widgets = {
            "club_member": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "amount": forms.NumberInput(
                attrs={"step": "0.01", "class": "form-control"}
            ),
            "due_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }

    def __init__(self, *args, club=None, **kwargs):
        super().__init__(*args, **kwargs)
        if club is not None:
            self.fields["club_member"].queryset = ClubMembership.objects.filter(
                club=club, is_active=True
            ).select_related("user")
