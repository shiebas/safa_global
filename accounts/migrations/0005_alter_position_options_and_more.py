# Generated by Django 5.2.3 on 2025-06-20 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_remove_position_level_manual"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="position",
            options={"ordering": ["title"]},
        ),
        # Remove constraint operation removed because the constraint doesn't exist
        migrations.RemoveField(
            model_name="position",
            name="level",
        ),
        migrations.AlterField(
            model_name="position",
            name="title",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
