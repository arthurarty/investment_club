from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import Club


class ClubListViewTestCase(TestCase):
    """
    Test case for the ClubsListView.
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
        self.investment_club = Club.objects.create(
            name="Test Club",
            description="A club for testing.",
            contact_email="jack.doe@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        self.client = Client()

    def test_get_method(self):
        """
        Test GET request to the clubs list view.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(reverse("clubs:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/index.html")
        self.assertIn("clubs", response.context)
        self.assertContains(response, "Test Club")

    def test_post_method(self):
        """
        Test POST request to create a new club.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.post(
            reverse("clubs:index"),
            {
                "name": "New Club",
                "description": "A new club for testing.",
                "contact_email": "jackdoe@example.com",
                "status": "active",
            },
        )
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND
        )  # Redirect after creation
        self.assertTrue(Club.objects.filter(name="New Club").exists())
        self.assertFalse(Club.objects.filter(name="Invalid Club").exists())
        self.assertEqual(Club.objects.count(), 2)  # One from setUp and one new
        self.assertEqual(
            response.url, reverse("clubs:index")
        )  # Redirects to clubs index

    def test_post_invalid_data(self):
        """
        Test POST request with invalid data.
        """
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.post(
            reverse("clubs:index"),
            {
                "name": "",  # Name is required, so this should fail
                "description": "A club without a name.",
                "contact_email": "invalidemail",  # Invalid email format
                "status": "active",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)  # Form re-rendered
        self.assertTemplateUsed(response, "clubs/index.html")
        self.assertIn("create_club_form", response.context)
        self.assertEqual(Club.objects.count(), 1)  # No new club created
