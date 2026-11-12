from django.db import migrations

DEFAULT_TRANSACTION_CATEGORIES = (
    "Bank charges",
    "Admin Expenses",
    "Member Contributions",
)


def add_default_categories(apps, schema_editor):
    """
    Give the clubs that existed before categories were introduced the same
    default categories that new clubs are created with.
    """
    Club = apps.get_model("clubs", "Club")
    TransactionCategory = apps.get_model("clubs", "TransactionCategory")
    TransactionCategory.objects.bulk_create(
        TransactionCategory(
            club=club,
            name=name,
            created_by_id=club.created_by_id,
            updated_by_id=club.updated_by_id,
        )
        for club in Club.objects.all()
        for name in DEFAULT_TRANSACTION_CATEGORIES
    )


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0005_transaction_categories"),
    ]

    operations = [
        migrations.RunPython(add_default_categories, migrations.RunPython.noop),
    ]
