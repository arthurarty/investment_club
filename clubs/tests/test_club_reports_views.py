from datetime import date

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import (
    Club,
    ClubMembership,
    FinancialTransaction,
    FinancialYear,
    FinancialYearParticipant,
    IndividualDue,
)
from clubs.views.club_reports_view import FinancialReportView


class TestGetNoOfMonths(TestCase):
    """
    Test case for FinancialReportView.get_no_of_months method.
    """

    def setUp(self):
        """
        Set up test data for clubs and financial years.
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
        self.view = FinancialReportView()

    def test_first_month_of_same_year(self):
        """
        Selected date in first month of FY returns 1.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2023, 1, 1), financial_year), 1
        )

    def test_third_month_of_same_year(self):
        """
        Selected date in third month of FY returns 3.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2023, 3, 1), financial_year), 3
        )

    def test_last_month_of_same_year(self):
        """
        Selected date in last month of single-year FY returns 12.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2023, 12, 1), financial_year), 12
        )

    def test_multi_year_fy_first_year(self):
        """
        Selected date in first year of multi-year FY returns correct count.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2024, 3, 1), financial_year), 3
        )

    def test_multi_year_fy_second_year(self):
        """
        Selected date in second year of multi-year FY returns correct count.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2025, 3, 1), financial_year), 15
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2025, 1, 1), financial_year), 13
        )

    def test_fy_starting_mid_year(self):
        """
        FY starting in July returns correct count for selected months.
        """
        financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 7, 1),
            end_date=date(2024, 6, 30),
            created_by=self.user,
            updated_by=self.user,
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2023, 7, 1), financial_year), 1
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2023, 9, 1), financial_year), 3
        )
        self.assertEqual(
            self.view.get_no_of_months(date(2024, 6, 1), financial_year), 12
        )


class TestMemberFilter(TestCase):
    """
    Test the member filter query parameter on the financial report view.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="john.doe@example.com",
            password="testPass123",
            first_name="John",
            last_name="Doe",
        )
        self.other = User.objects.create_user(
            email="jane.roe@example.com",
            password="testPass123",
            first_name="Jane",
            last_name="Roe",
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
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            created_by=self.user,
            updated_by=self.user,
        )
        for u in (self.user, self.other):
            member = ClubMembership.objects.create(
                user=u, club=self.club, invited_by=self.user
            )
            FinancialYearParticipant.objects.create(
                club_member=member,
                financial_year=self.financial_year,
                created_by=self.user,
                updated_by=self.user,
            )
        self.client.force_login(self.user)
        self.url = reverse(
            "clubs:financial-reports", args=[self.club.id, self.financial_year.id]
        )

    def test_no_filter_returns_all_participants(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["participant_dues"]), 2)
        self.assertEqual(response.context["active_tab"], "cashflow")

    def test_filter_by_user_id(self):
        response = self.client.get(self.url, {"member": self.other.id})
        dues = response.context["participant_dues"]
        self.assertEqual([d.user_id for d in dues], [self.other.id])
        self.assertEqual(len(response.context["member_options"]), 2)
        self.assertEqual(response.context["active_tab"], "monthly")

    def test_filter_does_not_affect_club_total(self):
        unfiltered = self.client.get(self.url)
        filtered = self.client.get(self.url, {"member": self.other.id})
        self.assertEqual(filtered.context["sum_due"], unfiltered.context["sum_due"])
        self.assertEqual(filtered.context["sum_paid"], unfiltered.context["sum_paid"])
        self.assertEqual(filtered.context["total_members"], 2)

    def test_invalid_filter_is_ignored(self):
        response = self.client.get(self.url, {"member": "abc"})
        self.assertEqual(len(response.context["participant_dues"]), 2)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@example.com",
)
class TestSendMonthlyReportEmails(TestCase):
    """
    Test sending the monthly report to every participant.
    """

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com", password="x", first_name="Ada"
        )
        self.other = User.objects.create_user(
            email="bob@example.com", password="x", first_name="Bob"
        )
        self.club = Club.objects.create(
            name="Finance Club",
            description="d",
            contact_email="c@example.com",
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.fy = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.members = {}
        for u, is_admin in ((self.admin, True), (self.other, False)):
            m = ClubMembership.objects.create(
                user=u, club=self.club, is_admin=is_admin, invited_by=self.admin
            )
            self.members[u] = m
            FinancialYearParticipant.objects.create(
                club_member=m,
                financial_year=self.fy,
                created_by=self.admin,
                updated_by=self.admin,
            )
        FinancialTransaction.objects.create(
            financial_year=self.fy,
            description="Dues",
            credit=500,
            transaction_date=date(2023, 3, 5),
            club_member=self.members[self.admin],
            created_by=self.admin,
            updated_by=self.admin,
        )
        FinancialTransaction.objects.create(
            financial_year=self.fy,
            description="Refreshments",
            debit=120,
            transaction_date=date(2023, 3, 6),
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.url = reverse("clubs:send-monthly-report", args=[self.club.id, self.fy.id])

    def test_sends_one_email_per_participant(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"month": 3, "year": 2023})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            sorted(m.to[0] for m in mail.outbox),
            ["admin@example.com", "bob@example.com"],
        )
        body = next(
            m for m in mail.outbox if m.to == ["admin@example.com"]
        ).alternatives[0][0]
        self.assertIn("Hi Ada", body)
        self.assertIn("March 2023 report", body)
        self.assertIn("Refreshments", body)
        self.assertIn("UGX 380", body)  # 500 collected - 120 spent

    def test_month_and_year_are_required(self):
        self.client.force_login(self.admin)
        for data in (
            {},
            {"month": 3},
            {"year": 2023},
            {"month": 13, "year": 2023},
            {"month": "abc", "year": 2023},
            {"month": 3, "year": 2030},
        ):
            with self.subTest(data=data):
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_button_only_shown_to_admins(self):
        reports_url = reverse(
            "clubs:financial-reports", args=[self.club.id, self.fy.id]
        )
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reports_url), "sendMonthlyReportModal")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reports_url), "sendMonthlyReportModal")

    def test_non_admin_cannot_send(self):
        self.client.force_login(self.other)
        self.client.post(self.url, {"month": 3, "year": 2023})
        self.assertEqual(len(mail.outbox), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class TestIndividualDuesAcrossCalendarYears(TestCase):
    """
    Individual dues count towards every later month of a financial year, even
    when the financial year spans two calendar years.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="a@example.com", password="x")
        self.club = Club.objects.create(
            name="Finance Club",
            description="d",
            contact_email="c@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        self.fy = FinancialYear.objects.create(
            club=self.club,
            start_date=date(2023, 10, 1),
            end_date=date(2024, 9, 30),
            created_by=self.user,
            updated_by=self.user,
        )
        member = ClubMembership.objects.create(
            user=self.user, club=self.club, is_admin=True, invited_by=self.user
        )
        FinancialYearParticipant.objects.create(
            club_member=member,
            financial_year=self.fy,
            created_by=self.user,
            updated_by=self.user,
        )
        IndividualDue.objects.create(
            financial_year=self.fy,
            club_member=member,
            description="Fine",
            amount=100,
            due_date=date(2023, 11, 5),
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.force_login(self.user)

    def test_report_includes_due_from_previous_calendar_year(self):
        url = reverse("clubs:financial-reports", args=[self.club.id, self.fy.id])
        response = self.client.get(url, {"month": 2, "year": 2024})
        self.assertEqual(response.context["participant_dues"][0].due, 100)

    def test_report_excludes_due_after_selected_month(self):
        url = reverse("clubs:financial-reports", args=[self.club.id, self.fy.id])
        response = self.client.get(url, {"month": 10, "year": 2023})
        self.assertEqual(response.context["participant_dues"][0].due, 0)
