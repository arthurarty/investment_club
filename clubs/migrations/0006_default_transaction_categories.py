from django.db import migrations

DEFAULT_TRANSACTION_CATEGORIES = {
    "Bank charges": "#2f5aa8",
    "Admin Expenses": "#6b3fa0",
    "Member Contributions": "#2e7d4f",
}


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
            color=color,
            created_by_id=club.created_by_id,
            updated_by_id=club.updated_by_id,
        )
        for club in Club.objects.all()
        for name, color in DEFAULT_TRANSACTION_CATEGORIES.items()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0005_transaction_categories"),
    ]

    operations = [
        migrations.RunPython(add_default_categories, migrations.RunPython.noop),
    ]
