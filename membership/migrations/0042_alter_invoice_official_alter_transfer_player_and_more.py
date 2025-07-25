# Generated by Django 4.2.23 on 2025-07-23 21:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0001_initial'),
        ('membership', '0041_remove_officialcertification_official'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='official',
            field=models.ForeignKey(blank=True, help_text='Official this invoice is for (if official registration)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='official_invoices', to='registration.official'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='player',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='registration.player'),
        ),
        migrations.DeleteModel(
            name='OfficialCertification',
        ),
    ]
