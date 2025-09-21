from http import HTTPStatus

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import Club, ClubMember


class MemberLookUpViewTestCase(TestCase):
    """
    Test case for the MemberLookUpView.
    """

    test_email = "testuser@example.com"
    test_password = "testPass123"

    def setUp(self):
        """
        Set up a test user and client.
        """
        self.user = User.objects.create_user(
            email=self.test_email,
            password=self.test_password,
        )
        self.second_user = User.objects.create_user(
            email="cindy@example.com",
            password="anotherPass123",
            first_name="Cindy",
            last_name="Doe",
        )
        self.investment_club = Club.objects.create(
            name="Test Club",
            description="A club for testing.",
            contact_email="jack.doe@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        ClubMember.objects.create(
            club=self.investment_club,
            user=self.user,
            is_admin=True,
        )
        self.client = Client()

    def test_post_method_unauthenticated(self):
        """
        Test POST request to the member lookup view when user is not authenticated.
        """
        response = self.client.post(
            reverse("clubs:member-lookup", args=[self.investment_club.id]),
            {
                "email": "jack@example.com",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(settings.LOGIN_URL, response.url)

    def test_post_method_non_admin(self):
        """
        Test POST request to the member lookup view when user is not an admin of the club.
        """
        non_admin_user_password = "testPass123"
        non_admin_user = User.objects.create_user(
            email="mary@example.com",
            password=non_admin_user_password,
        )
        self.client.login(email=non_admin_user.email, password=non_admin_user_password)
        response = self.client.post(
            reverse("clubs:member-lookup", args=[self.investment_club.id]),
            {
                "email": "jack@example.com",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(
            reverse("clubs:detail", args=[self.investment_club.id]), response.url
        )

    def test_post_method_admin_valid_email(self):
        """
        Test POST request to the member lookup view when user is an admin of the club
        and provides a valid email.
        """
        self.client.login(email=self.user.email, password=self.test_password)
        response = self.client.post(
            reverse("clubs:member-lookup", args=[self.investment_club.id]),
            {
                "email": self.second_user.email,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.second_user.first_name)


class AddMemberToClubViewTestCase(TestCase):
    """
    Test case for the AddMemberToClubView.
    """

    test_email = "testuser@example.com"
    test_password = "testPass123"

    def setUp(self):
        """
        Set up a test user and client.
        """
        self.user = User.objects.create_user(
            email=self.test_email,
            password=self.test_password,
        )
        self.second_user = User.objects.create_user(
            email="cindy@example.com",
            password="anotherPass123",
            first_name="Cindy",
            last_name="Doe",
        )
        self.investment_club = Club.objects.create(
            name="Test Club",
            description="A club for testing.",
            contact_email="jack.doe@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        ClubMember.objects.create(
            club=self.investment_club,
            user=self.user,
            is_admin=True,
        )
        self.client = Client()

    def test_get_method_unauthenticated(self):
        """
        Test GET request to the add member view when user is not authenticated.
        """
        response = self.client.get(
            reverse("clubs:add-member", args=[self.investment_club.id]),
            {
                "email": self.second_user.email,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(settings.LOGIN_URL, response.url)

    def test_get_method_non_admin(self):
        """
        Test GET request to the add member view when user is not an admin of the club.
        """
        non_admin_user_password = "testPass123"
        non_admin_user = User.objects.create_user(
            email="mary@example.com",
            password=non_admin_user_password,
        )
        self.client.login(email=non_admin_user.email, password=non_admin_user_password)
        response = self.client.get(
            reverse("clubs:add-member", args=[self.investment_club.id]),
            {
                "email": self.second_user.email,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(
            reverse("clubs:detail", args=[self.investment_club.id]), response.url
        )

    def test_get_method_admin_valid_email(self):
        """
        Test GET request to the add member view when user is an admin of the club
        and provides a valid email.
        """
        self.client.login(email=self.user.email, password=self.test_password)
        response = self.client.get(
            reverse("clubs:add-member", args=[self.investment_club.id]),
            {
                "email": self.second_user.email,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn(
            reverse("clubs:detail", args=[self.investment_club.id]), response.url
        )
        self.assertTrue(
            ClubMember.objects.filter(
                club=self.investment_club, user=self.second_user
            ).exists()
        )
