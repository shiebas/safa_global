# Generated by Django 4.2.16 on 2025-06-09 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership_cards", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="digitalcard",
            name="qr_image",
            field=models.ImageField(
                blank=True,
                help_text="Generated QR code image with logo",
                null=True,
                upload_to="qr_codes/",
            ),
        ),
    ]
