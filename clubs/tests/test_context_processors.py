from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import Club, ClubMembership


class CurrentClubSidebarTestCase(TestCase):
    """
    Tests for the sidebar's current-club switcher.
    """

    password = "testPass123"

    def setUp(self):
        self.user = User.objects.create_user(
            email="member@example.com", password=self.password
        )
        self.club = self._create_club("Alpha Club", self.user)
        self.other_club = self._create_club("Beta Club", self.user)
        self.client = Client()
        self.client.login(email=self.user.email, password=self.password)

    def _create_club(self, name, user, member=True):
        club = Club.objects.create(
            name=name,
            description="A club.",
            contact_email="club@example.com",
            created_by=user,
            updated_by=user,
        )
        if member:
            ClubMembership.objects.create(user=user, club=club)
        return club

    def test_current_club_shown_on_club_pages(self):
        response = self.client.get(reverse("clubs:detail", args=[self.club.id]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context["sidebar_current_club"], self.club)
        self.assertEqual(response.context["sidebar_current_club_member_count"], 1)
        self.assertContains(response, "Current club")
        self.assertContains(response, "1 member<")
        self.assertContains(response, "Beta Club")

    def test_selected_club_stored_in_session(self):
        self.client.get(reverse("clubs:detail", args=[self.club.id]))
        self.assertEqual(self.client.session["current_club_id"], self.club.id)

    def test_current_club_read_from_session_outside_club_urls(self):
        self.client.get(reverse("clubs:detail", args=[self.other_club.id]))
        response = self.client.get(reverse("clubs:index"))
        self.assertEqual(response.context["sidebar_current_club"], self.other_club)
        self.assertContains(response, "Current club")

    def test_no_current_club_without_selection(self):
        response = self.client.get(reverse("clubs:index"))
        self.assertNotIn("sidebar_current_club", response.context)
        self.assertNotContains(response, "Current club")

    def test_context_processor_does_not_write_session(self):
        self.client.get(reverse("clubs:financial-year", args=[self.club.id]))
        self.assertNotIn("current_club_id", self.client.session)

    def test_stale_session_club_is_ignored(self):
        stranger = User.objects.create_user(
            email="stranger@example.com", password=self.password
        )
        hidden = self._create_club("Hidden Club", stranger)
        session = self.client.session
        session["current_club_id"] = hidden.id
        session.save()
        response = self.client.get(reverse("clubs:index"))
        self.assertNotIn("sidebar_current_club", response.context)

    def test_non_member_club_not_exposed(self):
        stranger = User.objects.create_user(
            email="stranger@example.com", password=self.password
        )
        hidden = self._create_club("Hidden Club", stranger)
        response = self.client.get(reverse("clubs:detail", args=[hidden.id]))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertNotIn("current_club_id", self.client.session)
        self.assertNotContains(
            response, "Hidden Club", status_code=HTTPStatus.FORBIDDEN
        )
