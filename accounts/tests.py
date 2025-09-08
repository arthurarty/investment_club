from django.test import Client, TestCase
from django.urls import reverse


class LoginViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_login_page(self):
        response = self.client.get(reverse("accounts:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/index.html")
