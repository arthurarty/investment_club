from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import Club, ClubMembership, MembershipCategory, MembershipStatus


class ClubMemberShipCreateViewTestCase(TestCase):
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
