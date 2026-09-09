from datetime import date
from http import HTTPStatus

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.test import Client
from django.urls import reverse

from accounts.models import CustomUser as User
from accounts.models import GenderChoices
from clubs.models import (
    Club,
    ClubMembership,
    FinancialTransaction,
    FinancialYear,
    FinancialYearParticipant,
    IndividualDue,
    MembershipCategory,
    MembershipStatus,
)
from common.message_test_case import MsgTestCase


class ClubMemberShipCreateViewTestCase(MsgTestCase):
    """
    Test case for the ClubMemberShipCreateView
    """

    test_email = "testuser1@example.com"
    test_password = "testPass1232g"
    view_name = "clubs:club-member-create"

    def setUp(self):
        """
        Set up a test user and client.
        """
        self.user = User.objects.create_user(
            email=self.test_email,
            password=self.test_password,
        )
        self.investment_club = Club.objects.create(
            name="Test Club",
            description="A club for testing.",
            contact_email="jack.doe@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        ClubMembership.objects.get_or_create(
            club=self.investment_club,
            user=self.user,
            defaults={
                "is_admin": True,
                "category": MembershipCategory.COMMITTEE,
                "status": MembershipStatus.ACTIVE,
            },
        )
        self.client = Client()

    def test_get_method(self):
        """
        Test GET request to the clubs list view.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/club_membership_form.html")
        self.assertIn("club", response.context)
        self.assertContains(response, "Fill in the form below")

    def test_get_method_redirect(self):
        """
        Test the get request redirects if logged in user is not a member
        they acting on.
        """
        email, password = "jack@testnet.com", "testPass24AG542@$523(*j"
        User.objects.create_user(
            email=email,
            password=password,
        )
        self.client.login(email=email, password=password)
        response = self.client.get(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_get_method_redirect_error_message(self):
        """
        Test the get request generates an error message when the logged in
        user does not have permission to act on the club.
        """
        email, password = "jack@testnet.com", "testPass24AG542@$523(*j"
        User.objects.create_user(
            email=email,
            password=password,
        )
        self.client.login(email=email, password=password)
        response = self.client.get(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id})
        )
        expected_messages = [
            Message(
                level=messages.ERROR,
                message="You do not have permission to perform this action on this club.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_post_success_new_user_created(self):
        """
        Test successful post that results in a new user being created
        """
        self.client.login(email=self.test_email, password=self.test_password)
        new_member_email = "newmember@example.com"
        response = self.client.post(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id}),
            {
                "email": new_member_email,
                "first_name": "Jane",
                "last_name": "Smith",
                "gender": GenderChoices.FEMALE,
                "phone_number": "+254712345678",
                "occupation": "Engineer",
                "physical_address": "123 Main St",
                "start_date": "2024-01-15",
                "category": MembershipCategory.ORDINARY,
                "status": MembershipStatus.ACTIVE,
            },
        )
        self.assertRedirects(
            response,
            reverse("clubs:detail", kwargs={"club_id": self.investment_club.id}),
        )
        new_user = User.objects.get(email=new_member_email)
        club_member = ClubMembership.objects.filter(
            club=self.investment_club, user=new_user
        ).first()
        self.assertTrue(club_member)
        self.assertTrue(club_member.is_active)
        expected_messages = [
            Message(
                level=messages.SUCCESS,
                message=f"{new_member_email} added to club: {self.investment_club.name}",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_post_success_existing_user_found(self):
        """
        Test successful post with an email for an existing user results in
        an info message about the existing member being found, in addition
        to the success message.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        existing_member_email = "existingmember@example.com"
        User.objects.create_user(
            email=existing_member_email,
            first_name="Jane",
            last_name="Smith",
        )
        response = self.client.post(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id}),
            {
                "email": existing_member_email,
                "first_name": "Jane",
                "last_name": "Smith",
                "gender": GenderChoices.FEMALE,
                "phone_number": "+254712345678",
                "occupation": "Engineer",
                "physical_address": "123 Main St",
                "start_date": "2024-01-15",
                "category": MembershipCategory.ORDINARY,
                "status": MembershipStatus.ACTIVE,
            },
        )
        self.assertRedirects(
            response,
            reverse("clubs:detail", kwargs={"club_id": self.investment_club.id}),
        )
        existing_user = User.objects.get(email=existing_member_email)
        self.assertTrue(
            ClubMembership.objects.filter(
                club=self.investment_club, user=existing_user
            ).exists()
        )
        expected_messages = [
            Message(
                level=messages.INFO,
                message=f"Existing member found and added to club: {self.investment_club.name}",
            ),
            Message(
                level=messages.SUCCESS,
                message=f"{existing_member_email} added to club: {self.investment_club.name}",
            ),
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_post_invalid_phone_number(self):
        """
        Test post with an invalid phone number does not create a user
        or membership and re-renders the form with errors.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        new_member_email = "invalidphone@example.com"
        response = self.client.post(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id}),
            {
                "email": new_member_email,
                "first_name": "Jane",
                "last_name": "Smith",
                "gender": GenderChoices.FEMALE,
                "phone_number": "not-a-number",
                "occupation": "Engineer",
                "physical_address": "123 Main St",
                "start_date": "2024-01-15",
                "category": MembershipCategory.ORDINARY,
                "status": MembershipStatus.ACTIVE,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/club_membership_form.html")
        self.assertFalse(User.objects.filter(email=new_member_email).exists())

    def test_post_phone_number_with_spaces(self):
        """
        Test post with a phone number that contains spaces but is valid
        This should test should pass since that is a valid number
        """
        self.client.login(email=self.test_email, password=self.test_password)
        new_member_email = "phoneNumberSpaces@example.com"
        response = self.client.post(
            reverse(self.view_name, kwargs={"club_id": self.investment_club.id}),
            {
                "email": new_member_email,
                "first_name": "Jane",
                "last_name": "Smith",
                "gender": GenderChoices.FEMALE,
                "phone_number": "+251 77 162 1946",
                "occupation": "Engineer",
                "physical_address": "123 Main St",
                "start_date": "2024-01-15",
                "category": MembershipCategory.ORDINARY,
                "status": MembershipStatus.ACTIVE,
            },
        )
        self.assertRedirects(
            response,
            reverse("clubs:detail", kwargs={"club_id": self.investment_club.id}),
        )
        self.assertTrue(User.objects.filter(email=new_member_email).exists())


class ClubMemberDetailViewTestCase(MsgTestCase):
    """
    Test case for the ClubMemberDetailView
    """

    test_email = "testuser1@example.com"
    test_password = "testPass1232g"
    view_name = "clubs:club-member-detail"

    def setUp(self):
        """
        Set up a test user, club, and member.
        """
        self.user = User.objects.create_user(
            email=self.test_email,
            password=self.test_password,
            first_name="Admin",
            last_name="User",
        )
        self.investment_club = Club.objects.create(
            name="Test Club",
            description="A club for testing.",
            contact_email="jack.doe@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        self.admin_membership = ClubMembership.objects.create(
            club=self.investment_club,
            user=self.user,
            is_admin=True,
            category=MembershipCategory.COMMITTEE,
            status=MembershipStatus.ACTIVE,
        )

        self.member_user = User.objects.create_user(
            email="member@example.com",
            password="memberPassword123",
            first_name="Jane",
            last_name="Doe",
            phone_number="+254712345678",
            occupation="Software Developer",
            physical_address="123 Innovation Way",
        )
        self.member = ClubMembership.objects.create(
            club=self.investment_club,
            user=self.member_user,
            is_admin=False,
            category=MembershipCategory.ORDINARY,
            status=MembershipStatus.ACTIVE,
            invited_by=self.user,
        )
        self.client = Client()

    def test_get_member_detail_unauthenticated(self):
        """
        Test unauthenticated GET request redirects to login.
        """
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={
                    "club_id": self.investment_club.id,
                    "member_id": self.member.id,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(reverse("accounts:index"), response.url)

    def test_get_member_detail_success(self):
        """
        Test GET request to member detail view returns 200 and context data.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={
                    "club_id": self.investment_club.id,
                    "member_id": self.member.id,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/member_detail.html")
        self.assertIn("club", response.context)
        self.assertIn("member", response.context)
        self.assertEqual(response.context["member"], self.member)
        self.assertEqual(response.context["club"], self.investment_club)
        self.assertContains(response, "Jane Doe")
        self.assertContains(response, "member@example.com")
        self.assertContains(response, "+254712345678")

    def test_get_member_detail_non_member_forbidden(self):
        """
        Test user who is not a member of the club receives 403 Forbidden.
        """
        outsider_email = "outsider@example.com"
        outsider_password = "outsiderPassword123"
        User.objects.create_user(
            email=outsider_email,
            password=outsider_password,
        )
        self.client.login(email=outsider_email, password=outsider_password)
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={
                    "club_id": self.investment_club.id,
                    "member_id": self.member.id,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, "clubs/403.html")

    def test_get_member_detail_nonexistent_club(self):
        """
        Test requesting member detail for a non-existent club redirects to clubs:index.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={"club_id": 999999, "member_id": self.member.id},
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, reverse("clubs:index"))

    def test_get_member_detail_nonexistent_member(self):
        """
        Test requesting non-existent member redirects to clubs:detail with error message.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={
                    "club_id": self.investment_club.id,
                    "member_id": 999999,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(
            response,
            reverse("clubs:detail", kwargs={"club_id": self.investment_club.id}),
        )
        expected_messages = [
            Message(
                level=messages.ERROR,
                message="Member not found in this club.",
            )
        ]
        self.assertMessages(response, expected_messages, ordered=True)

    def test_get_member_detail_with_financial_data(self):
        """
        Test member detail page renders transactions, individual dues, and FY participations.
        """
        fy = FinancialYear.objects.create(
            club=self.investment_club,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        FinancialYearParticipant.objects.create(
            financial_year=fy,
            club_member=self.member,
            created_by=self.user,
            updated_by=self.user,
        )
        IndividualDue.objects.create(
            financial_year=fy,
            club_member=self.member,
            description="Late meeting fine",
            amount=5000,
            due_date=date(2024, 6, 1),
            created_by=self.user,
            updated_by=self.user,
        )
        FinancialTransaction.objects.create(
            financial_year=fy,
            club_member=self.member,
            description="Monthly subscription payment",
            credit=50000,
            transaction_date=date(2024, 6, 2),
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(
            reverse(
                self.view_name,
                kwargs={
                    "club_id": self.investment_club.id,
                    "member_id": self.member.id,
                },
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["total_credit"], 50000)
        self.assertEqual(response.context["total_debit"], 0)
        self.assertEqual(response.context["total_individual_dues"], 5000)
        self.assertEqual(len(response.context["transactions"]), 1)
        self.assertEqual(len(response.context["individual_dues"]), 1)
        self.assertEqual(len(response.context["participating_years"]), 1)
        self.assertContains(response, "Monthly subscription payment")
        self.assertContains(response, "Late meeting fine")
