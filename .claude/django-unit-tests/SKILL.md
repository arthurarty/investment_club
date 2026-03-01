---
name: django-unit-tests
description: >
  Write high-quality unit tests for Django 6.0 applications using Django's built-in test classes.
  Use this skill whenever the user wants to write, generate, or improve tests for Django views,
  models, forms, serializers, signals, management commands, middleware, or any other Django component.
  Trigger this skill when the user mentions "Django test", "unit test", "TestCase", "test coverage",
  or asks to "test my view/model/form/API". Also trigger when the user shares Django code and asks
  to test it, even if they don't explicitly use the word "test".
---

# Django 6.0 Unit Testing Skill

This skill covers writing professional, thorough unit tests for Django 6.0 applications using
Django's built-in testing framework (`django.test`).
Always read the user's code carefully before writing tests — don't guess at field names, method signatures, or business logic.

## Base Classes

Choose the right base class for each test:

| Class | Use when |
|---|---|
| `django.test.TestCase` | Any test that touches the database (wraps each test in a transaction, rolled back after) |
| `django.test.SimpleTestCase` | No database access — pure logic, forms without DB, utility functions |
| `django.test.TransactionTestCase` | Testing transaction behaviour, signals that require `on_commit`, or raw SQL |
| `django.test.LiveServerTestCase` | Selenium / browser tests against a real running server |

Default to `TestCase` unless there's a specific reason to use another.

## Test Structure Principles

1. **One assertion per test** where reasonable — makes failures easy to diagnose
2. **Descriptive names**: `test_login_redirects_to_dashboard_on_success`, not `test_login`
3. **AAA pattern**: Arrange → Act → Assert
4. **No logic in tests**: avoid loops and conditionals — use `subTest` for variations
5. **Isolated**: use `setUp` / `setUpTestData` for shared state; never rely on test ordering

```python
from django.test import TestCase

class OrderModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Run once for the whole class — use for read-only shared objects
        cls.user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")

    def setUp(self):
        # Run before every test — use for objects that get mutated
        self.order = Order.objects.create(user=self.user, total=Decimal("19.99"))
```

## What to Test by Component

### Models
- Field defaults, `__str__`, `save()` overrides, custom managers, `clean()` validation
- `Meta` constraints (unique_together, CheckConstraint) — catch `IntegrityError` / `ValidationError`
- Custom QuerySet methods
- Properties and cached properties

```python
from django.test import TestCase
from django.db import IntegrityError
from myapp.models import Product

class ProductModelTests(TestCase):

    def test_str_returns_product_name(self):
        product = Product(name="Widget", price=Decimal("9.99"))

        self.assertEqual(str(product), "Widget")

    def test_price_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(name="Widget", price=Decimal("-1.00"))

    def test_is_available_returns_false_when_stock_zero(self):
        product = Product(name="Widget", price=Decimal("9.99"), stock=0)

        self.assertFalse(product.is_available)
```

### Views
Use `self.client` (a `Client` instance available on every `TestCase`). Use `RequestFactory` when you want to test the view function directly without middleware.

- Status codes for each HTTP method
- Redirect targets (`assertRedirects`)
- Context variables
- Permission / authentication gates (test both authenticated and anonymous)
- Form errors surfaced in context

```python
from django.test import TestCase
from django.urls import reverse

class ProductDetailViewTests(TestCase):

    def test_returns_404_for_unknown_slug(self):
        response = self.client.get("/products/does-not-exist/")

        self.assertEqual(response.status_code, 404)

    def test_create_requires_login(self):
        response = self.client.post(reverse("products:create"), {})

        self.assertRedirects(response, f"/login/?next={reverse('products:create')}")

    def test_authenticated_user_can_access_create(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("products:create"))

        self.assertEqual(response.status_code, 200)

    def test_context_contains_product(self):
        response = self.client.get(reverse("products:detail", args=[self.product.slug]))

        self.assertEqual(response.context["product"], self.product)
```

### Forms
- Valid data → `form.is_valid()` is `True`, `cleaned_data` correct
- Each invalid case → specific field error present
- Cross-field validation (`clean()` method)

```python
from django.test import SimpleTestCase
from myapp.forms import SignupForm

class SignupFormTests(SimpleTestCase):

    def test_valid_data_passes(self):
        form = SignupForm(data={"username": "alice", "password1": "s3cr3t!X", "password2": "s3cr3t!X"})

        self.assertTrue(form.is_valid())

    def test_mismatched_passwords_fail(self):
        form = SignupForm(data={"username": "alice", "password1": "secret", "password2": "wrong"})

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)
```

### DRF Serializers & API Views
Use `APIClient` from `rest_framework.test` (a thin wrapper around Django's `Client`). Subclass `TestCase` as normal.

```python
from django.test import TestCase
from rest_framework.test import APIClient

class ProductAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_list_returns_200(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)

    def test_list_paginates(self):
        Product.objects.bulk_create([Product(name=f"P{i}", price=Decimal("1.00")) for i in range(25)])

        response = self.client.get("/api/products/")

        self.assertIn("next", response.data)
        self.assertEqual(len(response.data["results"]), 20)

    def test_create_requires_authentication(self):
        response = self.client.post("/api/products/", {"name": "Widget", "price": "9.99"})

        self.assertEqual(response.status_code, 401)
```

### Signals
- Use `TransactionTestCase` when the signal fires inside `on_commit`
- Otherwise `TestCase` is fine; use `mail.outbox` for email signals

```python
from django.test import TestCase
from django.core import mail

class WelcomeEmailSignalTests(TestCase):

    def test_welcome_email_sent_on_user_creation(self):
        User.objects.create_user(username="alice", email="alice@example.com", password="pass")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])
```

### Management Commands
Use `call_command` and capture output with `StringIO`.

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class ImportProductsCommandTests(TestCase):

    def test_creates_products_from_csv(self):
        out = StringIO()
        call_command("import_products", "test_data/products.csv", stdout=out)

        self.assertTrue(Product.objects.filter(name="Widget").exists())
        self.assertIn("Imported", out.getvalue())
```

### Middleware
Instantiate middleware with a dummy `get_response` and call it with a `RequestFactory` request.

```python
from django.test import TestCase, RequestFactory
from myapp.middleware import MaintenanceModeMiddleware

class MaintenanceMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MaintenanceModeMiddleware(get_response=lambda r: None)

    def test_returns_503_when_maintenance_flag_set(self):
        with self.settings(MAINTENANCE_MODE=True):
            request = self.factory.get("/")
            response = self.middleware(request)

        self.assertEqual(response.status_code, 503)
```

## setUp vs setUpTestData

- **`setUpTestData(cls)`** — class method, runs once, DB objects shared across all tests in the class. Fast. Only use for objects that tests won't mutate.
- **`setUp(self)`** — runs before every test. Use for objects that get changed, or when you need a clean slate.

## Factories with factory_boy

Use `factory_boy` to avoid repetitive `Model.objects.create(...)` calls:

```python
# tests/factories.py
import factory
from django.contrib.auth.models import User
from myapp.models import Product

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password")

class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    name = factory.Sequence(lambda n: f"Product {n}")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    owner = factory.SubFactory(UserFactory)
```

Use them in `setUpTestData` or `setUp`:

```python
from tests.factories import UserFactory, ProductFactory

class ProductViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.product = ProductFactory(owner=cls.user)
```

## Mocking

Use `unittest.mock` directly — `patch` as a decorator or context manager:

```python
from unittest.mock import patch
from django.test import TestCase

class CheckoutTests(TestCase):

    @patch("myapp.services.PaymentGateway.charge")
    def test_payment_gateway_called_with_correct_amount(self, mock_charge):
        mock_charge.return_value = {"id": "ch_123"}
        self.client.force_login(self.user)

        self.client.post(f"/carts/{self.cart.id}/checkout/", {"token": "tok_visa"})

        mock_charge.assert_called_once_with(amount=self.cart.total, token="tok_visa")
```

Patch at the **import site** (where the name is used), not where it's defined.

Use `override_settings` as a context manager or decorator for settings changes:

```python
from django.test import TestCase, override_settings

class FeatureFlagTests(TestCase):

    @override_settings(FEATURE_NEW_CHECKOUT=True)
    def test_new_checkout_flow_shown_when_flag_enabled(self):
        response = self.client.get(reverse("checkout"))
        self.assertContains(response, "new-checkout")
```

## Django 6.0-Specific Notes

- **Async views**: use `django.test.AsyncClient` — `await self.async_client.get("/async-view/")`
- **`STORAGES` setting** replaces `DEFAULT_FILE_STORAGE` — override in tests with `@override_settings(STORAGES={...})`
- **`facet_choices`** on `SimpleListFilter` — test via admin `changelist_view` with `?field=value`
- **Multiple databases**: set `databases` on the `TestCase` class: `databases = ["default", "analytics"]`
- **`on_commit` hooks**: use `TransactionTestCase` or `TestCase.captureOnCommitCallbacks()` (Django 4.1+)

```python
# Testing on_commit with TestCase (Django 4.1+)
def test_task_queued_after_order_saved(self):
    with self.captureOnCommitCallbacks(execute=True):
        Order.objects.create(user=self.user, total=Decimal("9.99"))

    self.mock_task.assert_called_once()
```

## Coverage

Aim for:
- 100% branch coverage on business logic (models, services, forms)
- 90%+ line coverage on views/serializers
- Don't obsess over coverage for boilerplate (migrations, `__init__.py`, settings)

Run coverage with:
```bash
coverage run manage.py test myapp
coverage report --show-missing
coverage html  # for a browsable HTML report
```

## File Layout

```
tests/
├── __init__.py
├── factories.py         # factory_boy factories
├── test_models.py
├── test_views.py
├── test_forms.py
├── test_serializers.py
├── test_signals.py
├── test_commands.py
└── test_middleware.py
```

Run all tests with:
```bash
python manage.py test
python manage.py test myapp.tests.test_models  # single module
python manage.py test --verbosity=2            # verbose output
python manage.py test --keepdb                 # reuse test DB for speed
```

## Quick Checklist Before Delivering Tests

- [ ] Tests are actually runnable (correct imports, correct class/method names)
- [ ] Each test has a single, clear assertion focus
- [ ] Edge cases covered: empty inputs, boundary values, permission denied, not found
- [ ] No hardcoded PKs or UUIDs — use factory-created objects
- [ ] Async views tested with `AsyncClient` if applicable
- [ ] Mocks patched at the right import path
- [ ] `setUpTestData` used for expensive read-only setup; `setUp` for mutable state
