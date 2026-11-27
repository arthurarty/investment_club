from http import HTTPStatus

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import (
    Club,
    ClubMembership,
    DuePeriod,
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
)
from clubs.views.club_financial_view import prepare_financial_year_context
from clubs.views.club_transactions_view import prepare_transaction_history
from common.message_test_case import MsgTestCase


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
        self.club_member = ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
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


class TestClubFinancialYearCreateView(MsgTestCase):
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
        ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=False,
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
        self.assertEqual(
            response.url, reverse("clubs:financial-year-list", args=[self.club.id])
        )
        self.assertTrue(
            FinancialYear.objects.filter(
                club=self.club, start_date="2024-01-01", end_date="2024-12-31"
            ).exists()
        )
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message="Financial year 2024-01-01 - 2024-12-31 created successfully.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

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
        self.assertTemplateUsed(response, "clubs/financial_years.html")
        self.assertFalse(
            FinancialYear.objects.filter(club=self.club, end_date="2022-12-31").exists()
        )

    def test_create_financial_year_creator_not_member_gets_403(self):
        """
        Test that a club creator who is not a member gets 403.
        """
        creator = User.objects.create_user(
            email="creator@example.com", password="testPass123"
        )
        club = Club.objects.create(
            name="Creator Only Club",
            description="Club where creator is not a member.",
            contact_email=creator.email,
            created_by=creator,
            updated_by=creator,
        )
        self.client.login(email=creator.email, password="testPass123")
        url = reverse("clubs:financial-year", args=[club.id])
        data = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")
        self.assertFalse(
            FinancialYear.objects.filter(
                club=club, start_date="2024-01-01", end_date="2024-12-31"
            ).exists()
        )

    def test_create_financial_year_non_admin_non_creator_gets_403(self):
        """
        Test that a user who is a member but neither admin nor creator gets 403.
        """
        regular_member = User.objects.create_user(
            email="regular.member@example.com", password="testPass123"
        )
        ClubMembership.objects.create(
            user=regular_member,
            club=self.club,
            is_admin=False,
        )
        self.client.login(email=regular_member.email, password="testPass123")
        url = reverse("clubs:financial-year", args=[self.club.id])
        data = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")
        self.assertFalse(
            FinancialYear.objects.filter(
                club=self.club, start_date="2024-01-01", end_date="2024-12-31"
            ).exists()
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
        self.club_member = ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
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


class TestFinancialYearDueCreateView(MsgTestCase):
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
        ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=False,
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
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message=f"Due of 50000 added for {DuePeriod.MONTHLY.value}.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

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

    def test_create_financial_year_due_non_admin_non_creator_gets_403(self):
        """
        Test that a user who is a member but neither admin nor creator gets 403.
        """
        regular_member = User.objects.create_user(
            email="regular.member@example.com", password="testPass123"
        )
        ClubMembership.objects.create(
            user=regular_member,
            club=self.club,
            is_admin=False,
        )
        self.client.login(email=regular_member.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-due",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "amount": 50000,
            "due_period": DuePeriod.MONTHLY,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")
        self.assertFalse(
            FinancialYearContribution.objects.filter(
                amount=50000, due_period=DuePeriod.MONTHLY.value
            ).exists()
        )


class TestFinancialTransactionCreateView(MsgTestCase):
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
        ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=False,
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
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message="Transaction 'Membership fee' added successfully.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

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


class TestFinancialYearParticipantCreateView(MsgTestCase):
    """
    Test case for the FinancialYearParticipantCreateView.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, club members, and users.
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
        self.club_member = ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
            invited_by=self.user,
        )

    def test_create_participant_requires_login(self):
        """
        Test that unauthenticated users are redirected to login.
        """
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        response = self.client.post(url, {"club_member": self.club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("accounts", response.url)

    def test_create_participant_success(self):
        """
        Test the creation of a new financial year participant via POST request.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        data = {"club_member": self.club_member.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(
            response.url,
            reverse(
                "clubs:financial-year-participants",
                args=[self.club.id, self.financial_year.id],
            ),
        )
        self.assertTrue(
            FinancialYearParticipant.objects.filter(
                financial_year=self.financial_year,
                club_member=self.club_member,
            ).exists()
        )
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message=f"{self.user.email} added as a participant.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_create_participant_sets_created_by_and_updated_by(self):
        """
        Test that created_by and updated_by are set to the requesting user.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        data = {"club_member": self.club_member.id}
        self.client.post(url, data)
        participant = FinancialYearParticipant.objects.get(
            financial_year=self.financial_year,
            club_member=self.club_member,
        )
        self.assertEqual(participant.created_by, self.user)
        self.assertEqual(participant.updated_by, self.user)

    def test_create_participant_invalid_data(self):
        """
        Test the creation of a participant with invalid data re-renders the form.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        data = {"club_member": ""}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_participants.html")
        self.assertFalse(
            FinancialYearParticipant.objects.filter(
                financial_year=self.financial_year,
            ).exists()
        )

    def test_create_participant_already_exists(self):
        """
        Test that adding an existing participant again re-renders the form
        and does not create a duplicate.
        """
        FinancialYearParticipant.objects.create(
            financial_year=self.financial_year,
            club_member=self.club_member,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        response = self.client.post(url, {"club_member": self.club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_participants.html")
        self.assertEqual(
            FinancialYearParticipant.objects.filter(
                financial_year=self.financial_year,
                club_member=self.club_member,
            ).count(),
            1,
        )

    def test_create_participant_nonexistent_club_redirects_to_index(self):
        """
        Test that POST to non-existent club redirects to clubs index.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[9999, self.financial_year.id],
        )
        response = self.client.post(url, {"club_member": self.club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, reverse("clubs:index"))

    def test_create_participant_nonexistent_financial_year_redirects_to_index(self):
        """
        Test that POST to non-existent financial year redirects to clubs index.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, 9999],
        )
        response = self.client.post(url, {"club_member": self.club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, reverse("clubs:index"))

    def test_create_participant_non_admin_non_creator_gets_403(self):
        """
        Test that a user who is a member but neither admin nor creator gets 403.
        """
        regular_member = User.objects.create_user(
            email="regular.member@example.com", password="testPass123"
        )
        other_club_member = ClubMembership.objects.create(
            user=regular_member,
            club=self.club,
            is_admin=False,
        )
        self.client.login(email=regular_member.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[self.club.id, self.financial_year.id],
        )
        response = self.client.post(url, {"club_member": other_club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")
        self.assertFalse(
            FinancialYearParticipant.objects.filter(
                financial_year=self.financial_year,
                club_member=other_club_member,
            ).exists()
        )

    def test_create_participant_creator_not_member_gets_403(self):
        """
        Test that a club creator who is not a member gets 403.
        """
        creator = User.objects.create_user(
            email="creator@example.com", password="testPass123"
        )
        club = Club.objects.create(
            name="Creator Only Club",
            description="Club where creator is not a member.",
            contact_email=creator.email,
            created_by=creator,
            updated_by=creator,
        )
        financial_year = FinancialYear.objects.create(
            club=club,
            start_date="2023-01-01",
            end_date="2023-12-31",
            created_by=creator,
            updated_by=creator,
        )
        member_to_add = ClubMembership.objects.create(
            user=User.objects.create_user(
                email="member@example.com", password="testPass123"
            ),
            club=club,
            is_admin=False,
        )
        self.client.login(email=creator.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-participant",
            args=[club.id, financial_year.id],
        )
        response = self.client.post(url, {"club_member": member_to_add.id})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")


class TestFinancialYearIndividualDueCreateView(MsgTestCase):
    """
    Test case for the FinancialYearIndividualDueCreateView.
    """

    def setUp(self):
        """
        Set up test data for clubs, financial years, club members, and users.
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
        self.club_member = ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
        )

    def test_create_individual_due_success(self):
        """
        Test the creation of a new individual due via POST request.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-individual-due",
            args=[self.club.id, self.financial_year.id],
        )
        data = {
            "club_member": self.club_member.id,
            "description": "Late payment fine",
            "amount": "500.00",
            "due_date": "2023-06-15",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(
            response.url,
            reverse(
                "clubs:financial-year-individual-dues",
                args=[self.club.id, self.financial_year.id],
            ),
        )
        self.assertTrue(
            IndividualDue.objects.filter(
                financial_year=self.financial_year,
                club_member=self.club_member,
                description="Late payment fine",
            ).exists()
        )
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message=(
                    f"Individual due 'Late payment fine' of 500.00 added "
                    f"for {self.user.email}."
                ),
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_create_individual_due_invalid_data(self):
        """
        Test that invalid data re-renders the individual dues page.
        """
        self.client.login(email=self.user.email, password="testPass123")
        url = reverse(
            "clubs:financial-year-individual-due",
            args=[self.club.id, self.financial_year.id],
        )
        response = self.client.post(url, {"club_member": self.club_member.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_individual_dues.html")
        self.assertFalse(IndividualDue.objects.exists())


class TestFinancialYearListPages(TestCase):
    """
    Test case for the participants and individual dues pages.
    """

    def setUp(self):
        """
        Set up a club with a financial year, a participant and an individual due.
        """
        self.user = User.objects.create_user(
            email="jane.doe@example.com",
            password="testPass123",
            first_name="Jane",
            last_name="Doe",
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
        self.club_member = ClubMembership.objects.create(
            user=self.user,
            club=self.club,
            is_admin=True,
            invited_by=self.user,
        )
        FinancialYearParticipant.objects.create(
            club_member=self.club_member,
            financial_year=self.financial_year,
            created_by=self.user,
            updated_by=self.user,
        )
        IndividualDue.objects.create(
            club_member=self.club_member,
            financial_year=self.financial_year,
            description="Late payment fine",
            amount="500.00",
            due_date="2023-06-15",
            created_by=self.user,
            updated_by=self.user,
        )
        self.args = [self.club.id, self.financial_year.id]
        self.client.login(email=self.user.email, password="testPass123")

    def test_participants_page(self):
        response = self.client.get(
            reverse("clubs:financial-year-participants", args=self.args)
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_participants.html")
        self.assertEqual(len(response.context["participants"]), 1)
        self.assertEqual(response.context["sidebar_participant_count"], 1)
        self.assertContains(response, self.user.email)

    def test_individual_dues_page(self):
        response = self.client.get(
            reverse("clubs:financial-year-individual-dues", args=self.args)
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_year_individual_dues.html")
        self.assertEqual(len(response.context["individual_dues"]), 1)
        self.assertContains(response, "Late payment fine")

    def test_transactions_page_has_no_tabs_and_sidebar_links_to_pages(self):
        response = self.client.get(
            reverse("clubs:financial-year-detail", args=self.args)
        )
        self.assertNotContains(response, 'class="si-tabs"')
        self.assertNotContains(response, "Late payment fine")
        for name in (
            "clubs:financial-year-participants",
            "clubs:financial-year-individual-dues",
        ):
            self.assertContains(response, f'href="{reverse(name, args=self.args)}"')

    def test_pages_forbidden_for_non_members(self):
        stranger = User.objects.create_user(
            email="stranger@example.com", password="testPass123"
        )
        self.client.login(email=stranger.email, password="testPass123")
        for name in (
            "clubs:financial-year-participants",
            "clubs:financial-year-individual-dues",
        ):
            response = self.client.get(reverse(name, args=self.args))
            self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_pages_redirect_for_unknown_financial_year(self):
        for name in (
            "clubs:financial-year-participants",
            "clubs:financial-year-individual-dues",
        ):
            response = self.client.get(reverse(name, args=[self.club.id, 9999]))
            self.assertRedirects(response, reverse("clubs:index"))


class TestClubFinancialYearExpensesView(TestCase):
    """
    Test case for the financial year expenses view.
    """

    def setUp(self):
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
        ClubMembership.objects.create(user=self.user, club=self.club, is_admin=True)
        self.financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2026-01-01",
            end_date="2026-12-31",
            created_by=self.user,
            updated_by=self.user,
        )
        for description, credit, debit in (
            ("Meeting refreshments", None, 120000),
            ("Bank charges", None, 15000),
            ("Monthly contribution", 50000, None),
        ):
            FinancialTransaction.objects.create(
                financial_year=self.financial_year,
                description=description,
                credit=credit,
                debit=debit,
                transaction_date="2026-10-04",
                created_by=self.user,
                updated_by=self.user,
            )
        self.url = reverse(
            "clubs:financial-year-expenses",
            args=[self.club.id, self.financial_year.id],
        )

    def test_lists_only_debit_transactions(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/expenses.html")
        self.assertEqual(response.context["expense_count"], 2)
        self.assertEqual(response.context["total_spent"], 135000)
        self.assertNotContains(response, "Monthly contribution")

    def test_non_member_forbidden(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", password="testPass123"
        )
        self.client.force_login(outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class TestExpenseCreateView(TestClubFinancialYearExpensesView):
    """
    Test case for recording an expense through the dedicated create view.
    """

    def setUp(self):
        super().setUp()
        self.member = ClubMembership.objects.get(user=self.user, club=self.club)
        FinancialYearParticipant.objects.create(
            financial_year=self.financial_year,
            club_member=self.member,
            created_by=self.user,
            updated_by=self.user,
        )
        self.create_url = reverse(
            "clubs:financial-year-expense",
            args=[self.club.id, self.financial_year.id],
        )

    def test_creates_expense_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.create_url,
            {
                "debit": "25000",
                "transaction_date": "2026-10-05",
                "description": "Printing",
            },
        )
        self.assertRedirects(response, self.url)
        expense = FinancialTransaction.objects.get(description="Printing")
        self.assertEqual(expense.debit, 25000)
        self.assertIsNone(expense.credit)
        self.assertEqual(expense.created_by, self.user)

    def test_accepts_comma_separated_amount(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.create_url,
            {
                "debit": "1,250,000",
                "transaction_date": "2026-10-05",
                "description": "Venue",
            },
        )
        self.assertRedirects(response, self.url)
        expense = FinancialTransaction.objects.get(description="Venue")
        self.assertEqual(expense.debit, 1250000)

    def test_accepts_amount_above_eight_digits(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.create_url,
            {
                "debit": "100,000,000",
                "transaction_date": "2026-10-05",
                "description": "Land",
            },
        )
        self.assertRedirects(response, self.url)
        expense = FinancialTransaction.objects.get(description="Land")
        expense.refresh_from_db()
        self.assertEqual(expense.debit, 100000000)

    def test_rejects_non_positive_amount(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.create_url,
            {"debit": "0", "transaction_date": "2026-10-05", "description": "Bad"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/expenses.html")
        self.assertTrue(response.context["expense_form"].errors["debit"])
        self.assertFalse(FinancialTransaction.objects.filter(description="Bad"))

    def test_non_admin_forbidden(self):
        other = User.objects.create_user(email="m@example.com", password="testPass123")
        ClubMembership.objects.create(user=other, club=self.club)
        self.client.force_login(other)
        response = self.client.post(
            self.create_url,
            {"debit": "100", "transaction_date": "2026-10-05", "description": "X"},
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)


class TestFinancialTransactionDetailView(MsgTestCase):
    """
    Test case for viewing and editing a single financial transaction.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="testPass123",
            first_name="Ada",
            last_name="Admin",
        )
        self.member_user = User.objects.create_user(
            email="member@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="Finance Club",
            description="A club for financial enthusiasts.",
            contact_email="jane@example.com",
            created_by=self.admin,
            updated_by=self.admin,
        )
        ClubMembership.objects.create(user=self.admin, club=self.club, is_admin=True)
        self.member = ClubMembership.objects.create(
            user=self.member_user, club=self.club
        )
        self.financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2026-01-01",
            end_date="2026-12-31",
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.transaction = FinancialTransaction.objects.create(
            financial_year=self.financial_year,
            description="Monthly contribution",
            credit=120000,
            transaction_date="2026-11-01",
            club_member=self.member,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.url = reverse(
            "clubs:financial-transaction-detail",
            args=[self.club.id, self.financial_year.id, self.transaction.id],
        )
        self.valid_data = {
            "description": "November contribution",
            "credit": "150,000",
            "debit": "",
            "transaction_date": "2026-11-02",
            "category": "",
            "club_member": self.member.id,
        }

    def test_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("next=", response.url)

    def test_admin_sees_transaction_and_edit_form(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/transaction_detail.html")
        self.assertEqual(response.context["transaction"], self.transaction)
        self.assertTrue(response.context["is_money_in"])
        self.assertContains(response, "Edit transaction")
        self.assertEqual(response.context["transaction_form"].initial["credit"], 120000)

    def test_member_sees_transaction_without_edit_form(self):
        self.client.force_login(self.member_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "Monthly contribution")
        self.assertIsNone(response.context["transaction_form"])
        self.assertNotContains(response, "Edit transaction")

    def test_non_member_forbidden(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", password="testPass123"
        )
        self.client.force_login(outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_transaction_of_another_financial_year_redirects(self):
        other_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2025-01-01",
            end_date="2025-12-31",
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "clubs:financial-transaction-detail",
                args=[self.club.id, other_year.id, self.transaction.id],
            )
        )

        self.assertRedirects(
            response,
            reverse("clubs:financial-year-detail", args=[self.club.id, other_year.id]),
        )

    def test_history_starts_with_who_recorded_it(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        history = response.context["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["user"], "Ada Admin")
        self.assertIsNone(history[0]["changes"])
        self.assertIsNone(response.context["last_edited"])

    def test_admin_can_edit_transaction(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, self.url)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.description, "November contribution")
        self.assertEqual(self.transaction.credit, 150000)
        self.assertEqual(self.transaction.updated_by, self.admin)
        self.assertMessages(
            response,
            [Message(messages.SUCCESS, "Transaction 'November contribution' updated.")],
        )

    def record_event(self, label, **changes):
        """
        Record a history event the way the database triggers do in Postgres
        (the tests run on SQLite, which has no triggers).
        """
        for field, value in changes.items():
            setattr(self.transaction, field, value)
        return FinancialTransaction.pgh_event_model.objects.create(
            pgh_obj=self.transaction,
            pgh_label=label,
            id=self.transaction.id,
            financial_year=self.financial_year,
            description=self.transaction.description,
            credit=self.transaction.credit,
            debit=self.transaction.debit,
            transaction_date=self.transaction.transaction_date,
            category=self.transaction.category,
            club_member=self.transaction.club_member,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def test_edits_are_listed_in_history_newest_first(self):
        self.record_event("insert")
        self.record_event("update", description="November contribution", credit=150000)
        self.record_event("update", club_member=None)

        history = prepare_transaction_history(self.transaction)

        self.assertIsNone(history[2]["changes"])
        self.assertEqual(
            history[1]["changes"],
            [
                {
                    "field": "Description",
                    "old": "Monthly contribution",
                    "new": "November contribution",
                },
                {
                    "field": "Credit",
                    "old": "Ugx 120,000.00",
                    "new": "Ugx 150,000.00",
                },
            ],
        )
        self.assertEqual(
            history[0]["changes"],
            [{"field": "Member", "old": "member@example.com", "new": ""}],
        )

    def test_history_shows_old_and_new_values(self):
        self.record_event("insert")
        self.record_event("update", debit=5000, transaction_date="2026-11-02")
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertContains(response, "<s>None</s>", html=True)
        self.assertContains(response, "<b>Ugx 5,000.00</b>", html=True)
        self.assertContains(response, "<s>Nov 1, 2026</s>", html=True)
        self.assertContains(response, "<b>Nov 2, 2026</b>", html=True)

    def test_history_of_untracked_transaction_keeps_who_recorded_it(self):
        self.record_event("update", description="November contribution")

        history = prepare_transaction_history(self.transaction)

        self.assertEqual(len(history), 2)
        self.assertIsNone(history[1]["changes"])
        self.assertEqual(history[0]["changes"], [])

    def test_last_edited_comes_from_latest_edit(self):
        event = self.record_event("update", description="November contribution")
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.context["last_edited"], event.pgh_created_at)

    def test_unchanged_submission_does_not_save(self):
        self.client.force_login(self.admin)
        unchanged = {
            "description": "Monthly contribution",
            "credit": "120,000",
            "debit": "",
            "transaction_date": "2026-11-01",
            "category": "",
            "club_member": self.member.id,
        }
        saved_at = self.transaction.updated_at

        response = self.client.post(self.url, unchanged)

        self.assertRedirects(response, self.url)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.updated_at, saved_at)

    def test_member_cannot_edit_transaction(self):
        self.client.force_login(self.member_user)

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.description, "Monthly contribution")

    def test_edit_requires_an_amount(self):
        self.client.force_login(self.admin)

        response = self.client.post(self.url, {**self.valid_data, "credit": ""})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.context["transaction_form"].non_field_errors())
        self.assertEqual(
            response.context["transaction"].description, "Monthly contribution"
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.credit, 120000)


class TestClubFinancialYearListView(TestCase):
    """
    Test case for the ClubFinancialYearListView.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="list.member@example.com", password="testPass123"
        )
        self.club = Club.objects.create(
            name="List Club",
            description="Club for the list view.",
            contact_email=self.user.email,
            created_by=self.user,
            updated_by=self.user,
        )
        ClubMembership.objects.create(user=self.user, club=self.club, is_admin=True)
        self.financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2024-01-01",
            end_date="2024-12-31",
            created_by=self.user,
            updated_by=self.user,
        )
        self.url = reverse("clubs:financial-year-list", args=[self.club.id])

    def test_lists_financial_years(self):
        self.client.login(email=self.user.email, password="testPass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/financial_years.html")
        self.assertContains(response, "FY 2024")

    def test_non_member_gets_403(self):
        stranger = User.objects.create_user(
            email="stranger.list@example.com", password="testPass123"
        )
        self.client.login(email=stranger.email, password="testPass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_unknown_club_redirects_to_index(self):
        self.client.login(email=self.user.email, password="testPass123")
        response = self.client.get(reverse("clubs:financial-year-list", args=[9999]))
        self.assertRedirects(response, reverse("clubs:index"))
