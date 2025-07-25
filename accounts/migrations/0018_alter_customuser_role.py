# Generated by Django 4.2.23 on 2025-07-22 06:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_alter_customuser_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('ADMIN_NATIONAL', 'National Federation Admin'), ('ADMIN_PROVINCE', 'Provincial Administrator'), ('ADMIN_REGION', 'Regionial Administrator'), ('ADMIN_LOCAL_FED', 'Local Federation Administrator'), ('CLUB_ADMIN', 'Club Administrator'), ('ASSOCIATION_ADMIN', 'Association Administrator')], default='ADMIN_PROVINCE', max_length=20),
        ),
    ]
