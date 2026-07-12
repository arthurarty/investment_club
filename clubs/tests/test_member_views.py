from http import HTTPStatus

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.test import Client
from django.urls import reverse

from accounts.models import CustomUser as User
from accounts.models import GenderChoices
from clubs.models import Club, ClubMembership, MembershipCategory, MembershipStatus
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
                "is_active": True,
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
        self.assertTrue(
            ClubMembership.objects.filter(
                club=self.investment_club, user=new_user
            ).exists()
        )
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
