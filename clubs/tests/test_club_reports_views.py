from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.models import (
    Club,
    ClubMembership,
    FinancialYear,
    FinancialYearParticipant,
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
