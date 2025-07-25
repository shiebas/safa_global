# Generated by Django 4.2.23 on 2025-07-08 11:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('geography', '0004_club_affiliation_fees_paid'),
        ('membership', '0025_membershipapplication_alter_invoice_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='membershipapplication',
            name='email_address',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='first_names',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='id_number',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='lfa',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='mobile_number',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='next_of_kin',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='postal_address',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='region_province',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='street_address',
        ),
        migrations.RemoveField(
            model_name='membershipapplication',
            name='surname',
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='member',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='membership.member'),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_applications', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='membershipapplication',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING', max_length=10),
        ),
        migrations.AlterField(
            model_name='membershipapplication',
            name='club',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='membership_applications', to='geography.club'),
        ),
    ]
