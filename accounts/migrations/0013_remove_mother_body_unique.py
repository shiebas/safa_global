# Generated by Django 4.2.23 on 2025-07-14 11:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geography', '0004_club_affiliation_fees_paid'),
        ('accounts', '0012_alter_customuser_options_alter_customuser_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='mother_body',
            field=models.ForeignKey(blank=True, help_text='The mother body this user belongs to (defaults to SAFAM)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custom_users', to='geography.motherbody'),
        ),
    ]
