from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.form_validators.phone_number_validator import validate_phone_number
from accounts.models import CustomUser as User


@override_settings(RECAPTCHA_TESTING=True)
class LoginViewTestCase(TestCase):
    """Test case for the login view."""

    def setUp(self):
        self.client = Client()

    def test_get_login_page(self):
        """
        Test that the login page is rendered
        """
        response = self.client.get(reverse("accounts:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "accounts/index.html")

    def test_post_invalid_login(self):
        """
        Test that invalid login credentials are handled properly.
        """
        response = self.client.post(
            reverse("accounts:index"),
            {"email": "jack@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "accounts/failed_login.html")

    def test_post_valid_login(self):
        """
        Test that valid login credentials redirect to the clubs index page.
        """
        email, password = "janedoe@example.com", "securepassword123"
        User.objects.create_user(
            email=email,
            password=password,
            first_name="Jane",
            last_name="Doe",
            phone_number="+25171295463",
            physical_address="10 Downing street",
            occupation="Farmer",
        )
        response = self.client.post(
            reverse("accounts:index"),
            {"email": email, "password": password, "captcha": "PASSED"},
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response.url, reverse("clubs:index"))


class PhoneNumberValidationTests(TestCase):
    def test_valid_phone_number(self):
        """
        Given a valid phone number no exception is raised
        """
        validate_phone_number("+256700000000")

    def test_invalid_phone_number_raises_exception(self):
        """
        An invalid phone number raises an exception
        """
        with self.assertRaises(ValidationError):
            validate_phone_number("700000000")
