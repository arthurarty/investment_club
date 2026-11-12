from http import HTTPStatus

from django.contrib import messages
from django.contrib.messages.storage.base import Message
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser as User
from clubs.forms.club_financials_forms import FinancialTransactionForm
from clubs.models import (
    DEFAULT_TRANSACTION_CATEGORIES,
    Club,
    ClubMembership,
    FinancialTransaction,
    FinancialYear,
    TransactionCategory,
)
from common.message_test_case import MsgTestCase


class CategoryTestDataMixin:
    """
    Shared club, admin user and financial year for the category tests.
    """

    def setUp(self):
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
        ClubMembership.objects.create(user=self.user, club=self.club, is_admin=True)
        self.financial_year = FinancialYear.objects.create(
            club=self.club,
            start_date="2026-01-01",
            end_date="2026-12-31",
            created_by=self.user,
            updated_by=self.user,
        )
        self.other_club = Club.objects.create(
            name="Other Club",
            description="Another club.",
            contact_email="other@example.com",
            created_by=self.user,
            updated_by=self.user,
        )
        self.category = self.club.transaction_categories.get(name="Bank charges")
        self.url = reverse("clubs:categories", args=[self.club.id])


class TestTransactionCategoryModel(CategoryTestDataMixin, TestCase):
    """
    Test case for the TransactionCategory model and the club defaults.
    """

    def test_new_club_gets_default_categories(self):
        names = self.club.transaction_categories.values_list("name", flat=True)

        self.assertCountEqual(names, DEFAULT_TRANSACTION_CATEGORIES)

    def test_default_categories_record_the_club_creator(self):
        self.assertEqual(self.category.created_by, self.user)

    def test_updating_a_club_does_not_add_categories_again(self):
        self.club.description = "Updated"
        self.club.save()

        self.assertEqual(
            self.club.transaction_categories.count(),
            len(DEFAULT_TRANSACTION_CATEGORIES),
        )

    def test_str_returns_name(self):
        self.assertEqual(str(self.category), "Bank charges")

    def test_name_is_unique_per_club_ignoring_case(self):
        with self.assertRaises(IntegrityError):
            TransactionCategory.objects.create(
                club=self.club,
                name="BANK CHARGES",
                created_by=self.user,
                updated_by=self.user,
            )

    def test_category_in_use_cannot_be_deleted(self):
        FinancialTransaction.objects.create(
            financial_year=self.financial_year,
            description="Ledger fee",
            debit=5000,
            transaction_date="2026-10-04",
            category=self.category,
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ProtectedError):
            self.category.delete()


class TestClubCategoryListView(CategoryTestDataMixin, MsgTestCase):
    """
    Test case for listing and adding a club's transaction categories.
    """

    def test_member_can_list_categories(self):
        member = User.objects.create_user(
            email="member@example.com", password="testPass123"
        )
        ClubMembership.objects.create(user=member, club=self.club)
        self.client.force_login(member)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "clubs/categories.html")
        self.assertContains(response, "Bank charges")
        self.assertFalse(response.context["is_club_admin"])

    def test_list_counts_transactions_per_category(self):
        FinancialTransaction.objects.create(
            financial_year=self.financial_year,
            description="Ledger fee",
            debit=5000,
            transaction_date="2026-10-04",
            category=self.category,
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        counts = {c.name: c.transaction_count for c in response.context["categories"]}
        self.assertEqual(counts["Bank charges"], 1)
        self.assertEqual(counts["Admin Expenses"], 0)

    def test_non_member_cannot_list_categories(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", password="testPass123"
        )
        self.client.force_login(outsider)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unknown_club_redirects_to_index(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("clubs:categories", args=[99999]))

        self.assertRedirects(response, reverse("clubs:index"))

    def test_admin_can_add_category(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, {"name": "  Investments "}, follow=True)

        self.assertRedirects(response, self.url)
        category = self.club.transaction_categories.get(name="Investments")
        self.assertEqual(category.created_by, self.user)
        self.assertMessages(
            response,
            [
                Message(
                    level=messages.SUCCESS,
                    message="Category 'Investments' added successfully.",
                )
            ],
        )

    def test_duplicate_name_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url, {"name": "bank CHARGES"})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.context["category_form"].errors["name"])
        self.assertEqual(
            self.club.transaction_categories.count(),
            len(DEFAULT_TRANSACTION_CATEGORIES),
        )

    def test_same_name_allowed_in_another_club(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"name": "Investments"})
        ClubMembership.objects.create(
            user=self.user, club=self.other_club, is_admin=True
        )

        self.client.post(
            reverse("clubs:categories", args=[self.other_club.id]),
            {"name": "Investments"},
        )

        self.assertEqual(
            TransactionCategory.objects.filter(name="Investments").count(), 2
        )

    def test_non_admin_cannot_add_category(self):
        member = User.objects.create_user(
            email="member@example.com", password="testPass123"
        )
        ClubMembership.objects.create(user=member, club=self.club)
        self.client.force_login(member)

        response = self.client.post(self.url, {"name": "Investments"})

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertFalse(TransactionCategory.objects.filter(name="Investments"))


class TestTransactionCategoryAssignment(CategoryTestDataMixin, TestCase):
    """
    Test case for assigning a category when recording transactions.
    """

    def setUp(self):
        super().setUp()
        self.expense_url = reverse(
            "clubs:financial-year-expense",
            args=[self.club.id, self.financial_year.id],
        )
        self.transaction_url = reverse(
            "clubs:financial-transaction",
            args=[self.club.id, self.financial_year.id],
        )
        self.client.force_login(self.user)

    def test_form_offers_only_the_clubs_categories(self):
        form = FinancialTransactionForm(financial_year=self.financial_year)

        self.assertQuerySetEqual(
            form.fields["category"].queryset,
            self.club.transaction_categories.all(),
        )

    def test_expense_is_saved_with_category(self):
        self.client.post(
            self.expense_url,
            {
                "debit": "15000",
                "transaction_date": "2026-10-05",
                "description": "Ledger fee",
                "category": self.category.id,
            },
        )

        expense = FinancialTransaction.objects.get(description="Ledger fee")
        self.assertEqual(expense.category, self.category)

    def test_transaction_is_saved_with_category(self):
        category = self.club.transaction_categories.get(name="Member Contributions")

        self.client.post(
            self.transaction_url,
            {
                "credit": "50000",
                "transaction_date": "2026-10-05",
                "description": "October contribution",
                "category": category.id,
            },
        )

        transaction = FinancialTransaction.objects.get(
            description="October contribution"
        )
        self.assertEqual(transaction.category, category)

    def test_category_is_optional(self):
        self.client.post(
            self.expense_url,
            {
                "debit": "15000",
                "transaction_date": "2026-10-05",
                "description": "Misc",
            },
        )

        expense = FinancialTransaction.objects.get(description="Misc")
        self.assertIsNone(expense.category)

    def test_category_of_another_club_is_rejected(self):
        foreign = self.other_club.transaction_categories.first()

        response = self.client.post(
            self.expense_url,
            {
                "debit": "15000",
                "transaction_date": "2026-10-05",
                "description": "Foreign",
                "category": foreign.id,
            },
        )

        self.assertTrue(response.context["expense_form"].errors["category"])
        self.assertFalse(FinancialTransaction.objects.filter(description="Foreign"))

    def test_expenses_page_shows_category_and_filter(self):
        FinancialTransaction.objects.create(
            financial_year=self.financial_year,
            description="Ledger fee",
            debit=5000,
            transaction_date="2026-10-04",
            category=self.category,
            created_by=self.user,
            updated_by=self.user,
        )

        response = self.client.get(
            reverse(
                "clubs:financial-year-expenses",
                args=[self.club.id, self.financial_year.id],
            )
        )

        self.assertContains(response, f'data-category="{self.category.id}"')
        self.assertContains(response, 'id="expenseCategory"')

    def test_financial_year_page_shows_category(self):
        FinancialTransaction.objects.create(
            financial_year=self.financial_year,
            description="Stationery",
            debit=5000,
            transaction_date="2026-10-04",
            category=self.club.transaction_categories.get(name="Admin Expenses"),
            created_by=self.user,
            updated_by=self.user,
        )

        response = self.client.get(
            reverse(
                "clubs:financial-year-detail",
                args=[self.club.id, self.financial_year.id],
            )
        )

        self.assertContains(response, "Admin Expenses")
