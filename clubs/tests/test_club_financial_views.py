from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import (
    Club,
    ClubMember,
    DuePeriod,
    FinancialYear,
    FinancialYearContribution,
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


class TestClubFinancialYearCreateView(TestCase):
    """
    Test case for the ClubFinancialYearCreateView.
    """

    def setUp(self):
        """
        Set up test data for clubs and users.
        """
        self.user = User.objects.create_user(
            email="john.doe@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Finance Club",
            description="A club for financial enthusiasts.",
            contact_email=self.user.email,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_create_financial_year_success(self):
        """
        Test the creation of a new financial year via POST request.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse("clubs:financial-year", args=[self.club.id])
        data = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)  # Redirect on success
        self.assertEqual(response.url, reverse("clubs:detail", args=[self.club.id]))
        self.assertTrue(
            FinancialYear.objects.filter(
                club=self.club, start_date="2024-01-01", end_date="2024-12-31"
            ).exists()
        )

    def test_create_financial_year_invalid_data(self):
        """
        Test the creation of a new financial year with invalid data.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse("clubs:financial-year", args=[self.club.id])
        data = {
            "start_date": "invalid-date",
            "end_date": "2022-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)  # Form re-rendered
        self.assertTemplateUsed(response, "clubs/detail.html")
        self.assertFalse(
            FinancialYear.objects.filter(club=self.club, end_date="2022-12-31").exists()
        )


class TestClubFinancialYearDetailView(TestCase):
    """
    Test case for the ClubFinancialYearDetailView.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, and users.
        """
        self.user = User.objects.create_user(
            email="john.doe@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Finance Club",
            description="A club for financial enthusiasts.",
            contact_email=self.user.email,
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

    def test_financial_year_detail_view(self):
        """
        Test accessing the financial year detail view.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-detail",
            args=[self.club.id, self.financial_year.id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_detail.html")
        self.assertIn("club", response.context)
        self.assertIn("financial_year", response.context)

    def test_financial_year_detail_view_not_found(self):
        """
        Test accessing a non-existent financial year detail view.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-detail",
            args=[self.club.id, 9999],  # Non-existent financial year ID
        )
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND
        )  # Redirect on not found
        self.assertEqual(response.url, reverse("clubs:index"))


class TestFinancialYearDueCreateView(TestCase):
    """
    Test case for the FinancialYearDueCreateView.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, and users.
        """
        self.user = User.objects.create_user(
            email="jane.doe@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Investment Club",
            description="A club for investment enthusiasts.",
            contact_email=self.user.email,
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

    def test_create_financial_year_due_success(self):
        """
        Test the creation of a new financial year due via POST request.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-due",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "amount": 50000,
            "due_period": DuePeriod.MONTHLY,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)  # Redirect on success
        self.assertTemplateUsed(response, "clubs/financial_year_detail.html")
        self.assertTrue(
            FinancialYearContribution.objects.filter(
                amount=50000, due_period=DuePeriod.MONTHLY.value
            ).exists()
        )

    def test_create_financial_year_due_invalid_data(self):
        """
        Test the creation of a new financial year due with invalid data.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-due",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "amount": "invalid-amount",
            "due_period": "Q1",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)  # Form re-rendered
        self.assertTemplateUsed(response, "clubs/financial_year_detail.html")


class TestFinancialTransactionCreateView(TestCase):
    """
    Test case for the FinancialTransactionCreateView.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, and users.
        """
        self.user = User.objects.create_user(
            email="jane.doe@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Investment Club",
            description="A club for investment enthusiasts.",
            contact_email=self.user.email,
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

    def test_create_financial_transaction_success(self):
        """
        Test the creation of a new financial transaction via POST request.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-transaction",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "club_member": "",
            "credit": "10000.00",
            "debit": "0.00",
            "transaction_date": "2023-06-15",
            "description": "Membership fee",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)  # Redirect on success
        self.assertEqual(
            response.url,
            reverse(
                "clubs:financial-year-detail",
                args=[self.club.id, self.financial_year.id],
            ),
        )
        self.assertTrue(
            FinancialYear.objects.filter(
                club=self.club, start_date="2023-01-01", end_date="2023-12-31"
            ).exists()
        )

    def test_create_financial_transaction_invalid_data(self):
        """
        Test the creation of a new financial transaction with invalid data.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-transaction",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "club_member": "",
            "credit": "invalid-credit",
            "debit": "0.00",
            "transaction_date": "2023-06-15",
            "description": "Membership fee",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)  # Form re-rendered
        self.assertTemplateUsed(response, "clubs/financial_year_detail.html")
