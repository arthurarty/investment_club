from datetime import date

from django.test import TestCase

from accounts.models import CustomUser as User
from clubs.models import Club, FinancialYear
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
