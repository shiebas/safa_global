# Generated by Django 4.2.16 on 2025-06-11 22:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("geography", "0002_club_fifa_id_club_payment_confirmed_and_more"),
        ("accounts", "0010_customuser_club_id_customuser_local_federation_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrganizationType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("NATIONAL", "National Federation"),
                            ("PROVINCE", "Province"),
                            ("REGION", "Region"),
                            ("LFA", "Local Football Association"),
                            ("CLUB", "Club"),
                        ],
                        max_length=20,
                    ),
                ),
                ("requires_approval", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["level"],
            },
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="club_id",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="local_federation_id",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="province_id",
        ),
        migrations.RemoveField(
            model_name="customuser",
            name="region_id",
        ),
        migrations.AddField(
            model_name="customuser",
            name="club",
            field=models.ForeignKey(
                blank=True,
                help_text="Club this user belongs to (required for political leaders)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="geography.club",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="is_political_position",
            field=models.BooleanField(
                default=False,
                help_text="Whether this user holds a politically elected position",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="local_federation",
            field=models.ForeignKey(
                blank=True,
                help_text="Local Football Association this user belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="geography.localfootballassociation",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="national_federation",
            field=models.ForeignKey(
                blank=True,
                help_text="National federation this user belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="geography.nationalfederation",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="province",
            field=models.ForeignKey(
                blank=True,
                help_text="Province this user belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="geography.province",
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="region",
            field=models.ForeignKey(
                blank=True,
                help_text="Region this user belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="geography.region",
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="country_code",
            field=models.CharField(
                blank=True,
                default="ZAF",
                help_text="Default is ZAF for South African citizens",
                max_length=3,
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="id_number",
            field=models.CharField(
                blank=True,
                help_text="13-digit South African ID number for citizens",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="organization_type",
            field=models.ForeignKey(
                blank=True,
                help_text="Primary organization type this user belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="accounts.organizationtype",
            ),
        ),
    ]
