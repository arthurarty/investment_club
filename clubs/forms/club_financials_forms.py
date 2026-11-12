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
        fields = ["amount", "due_period", "description"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"step": "5000.00", "class": "form-control"}
            ),
            "due_period": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-select"}),
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

    def __init__(self, *args, club=None, financial_year=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.financial_year = financial_year
        if club is not None:
            self.fields["club_member"].queryset = ClubMembership.objects.filter(
                club=club, is_active=True
            ).select_related("user")

    def clean_club_member(self):
        member = self.cleaned_data["club_member"]
        if (
            self.financial_year
            and self.financial_year.participants.filter(club_member=member).exists()
        ):
            raise forms.ValidationError(
                "This member is already a participant in this financial year."
            )
        return member


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


class CommaSeparatedNumberInput(forms.TextInput):
    """
    Text input whose submitted value may contain thousands separators.
    """

    def value_from_datadict(self, data, files, name):
        value = super().value_from_datadict(data, files, name)
        return value.replace(",", "") if isinstance(value, str) else value


class ExpenseForm(FinancialTransactionForm):
    """
    Form for recording an expense (money paid out) for a Financial Year.
    """

    class Meta(FinancialTransactionForm.Meta):
        fields = ["club_member", "debit", "transaction_date", "description"]
        labels = {"debit": "Amount"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["debit"].required = True
        # The amount is shown comma separated (e.g. 1,250,000) as it is typed,
        # so use a text input and strip the commas before validation.
        self.fields["debit"].widget = CommaSeparatedNumberInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "0",
                "data-amount-input": "",
            }
        )

    def clean_debit(self):
        """
        An expense must be a positive amount.
        """
        debit = self.cleaned_data["debit"]
        if debit <= 0:
            raise forms.ValidationError("The amount must be greater than zero.")
        return debit


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
