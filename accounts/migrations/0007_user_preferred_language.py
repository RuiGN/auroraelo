"""Add an optional explicit UI language preference to each user."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_alter_clinicinvitation_initial_role")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pt-br", "Português (Brasil)"),
                    ("en", "English"),
                    ("es", "Español"),
                ],
                default="",
                max_length=5,
            ),
        )
    ]
