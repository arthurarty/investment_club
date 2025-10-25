from django.test import TestCase

from accounts.models import CustomUser as User
from clubs.models import (
    Club,
    ClubMember,
    FinancialYear,
    FinancialYearParticipant,
)
from clubs.views.club_financial_view import prepare_financial_year_context


class TestPrepareFinancialYearContext(TestCase):
    """
    Test case for the prepare_financial_year_context function.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, participants, dues, and transactions.
        """
        self.user = User.objects.create_user(
            email="john.doe@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Finance Club",
            description="A club for financial enthusiasts.",
            contact_email="jane@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        self.financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2023-01-01",
            end_date="2023-12-31",
            created_by=self.user,
            updated_by=self.user,
        )
        self.club_member = ClubMember.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
            role="admin",
            invited_by=self.user,
        )
        self.participant = FinancialYearParticipant.objects.create(
            club_member=self.club_member,
            financial_year=self.financial_year,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_context_data(self):
        """
        Test that the context data returned by prepare_financial_year_context is correct.
        """
        context = prepare_financial_year_context(self.club, self.financial_year)

        self.assertIn("club", context)
        self.assertIn("financial_year", context)
        self.assertIn("participants", context)
        self.assertIn("dues", context)
        self.assertIn("transactions", context)
        self.assertIn("financial_contribution_form", context)
        self.assertIn("financial_transaction_form", context)

        self.assertEqual(context["club"], self.club)
        self.assertEqual(context["financial_year"], self.financial_year)
        self.assertEqual(len(context["participants"]), 1)
        self.assertEqual(len(context["dues"]), 0)
        self.assertEqual(len(context["transactions"]), 0)
