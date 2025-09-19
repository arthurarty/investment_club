from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser as User


class ClubListViewTestCase(TestCase):
    test_email = "testuser@example.com"
    test_password = "testPass123"

    def setUp(self):
        self.user = User.objects.create_user(
            email=self.test_email,
            password=self.test_password,
        )
        self.client = Client()

    def test_get_clubs_list_view(self):
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(reverse("clubs:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/index.html")

    # def test_post_invalid_login(self):
    #     response = self.client.post(
    #         reverse("accounts:index"),
    #         {"email": "jack@example.com", "password": "wrongpassword"},
    #     )
    #     self.assertEqual(response.status_code, HTTPStatus.OK)
    #     self.assertTemplateUsed(response, "accounts/failed_login.html")
