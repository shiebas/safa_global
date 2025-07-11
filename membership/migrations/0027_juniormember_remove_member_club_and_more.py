# Generated by Django 4.2.23 on 2025-07-10 13:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('geography', '0004_club_affiliation_fees_paid'),
        ('membership', '0026_remove_membershipapplication_email_address_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='JuniorMember',
            fields=[
                ('member_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='membership.member')),
                ('guardian_name', models.CharField(max_length=100, verbose_name='Guardian Name')),
                ('guardian_email', models.EmailField(max_length=254, verbose_name='Guardian Email')),
                ('guardian_phone', models.CharField(max_length=20, verbose_name='Guardian Phone')),
                ('school', models.CharField(blank=True, max_length=100, verbose_name='School')),
            ],
            options={
                'verbose_name': 'Junior Member',
                'verbose_name_plural': 'Junior Members',
            },
            bases=('membership.member',),
        ),
        migrations.RemoveField(
            model_name='member',
            name='club',
        ),
        migrations.RemoveField(
            model_name='member',
            name='expiry_date',
        ),
        migrations.RemoveField(
            model_name='member',
            name='membership_number',
        ),
        migrations.RemoveField(
            model_name='member',
            name='organization_type',
        ),
        migrations.RemoveField(
            model_name='member',
            name='registration_date',
        ),
        migrations.RemoveField(
            model_name='member',
            name='role',
        ),
        migrations.RemoveField(
            model_name='member',
            name='user',
        ),
        migrations.AddField(
            model_name='member',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_members', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='member',
            name='approved_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='member',
            name='lfa',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='geography.localfootballassociation'),
        ),
        migrations.AddField(
            model_name='member',
            name='member_type',
            field=models.CharField(choices=[('JUNIOR', 'Junior Member (Under 18)'), ('SENIOR', 'Senior Member (18+)'), ('OFFICIAL', 'Club Official'), ('ADMIN', 'Administrator')], default='SENIOR', max_length=20, verbose_name='Member Type'),
        ),
        migrations.AddField(
            model_name='member',
            name='province',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='geography.province'),
        ),
        migrations.AddField(
            model_name='member',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='geography.region'),
        ),
        migrations.AddField(
            model_name='member',
            name='rejection_reason',
            field=models.TextField(blank=True, verbose_name='Rejection Reason'),
        ),
        migrations.AlterField(
            model_name='member',
            name='created',
            field=model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='member',
            name='modified',
            field=model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='member',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending Approval'), ('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('SUSPENDED', 'Suspended'), ('REJECTED', 'Rejected')], default='PENDING', max_length=10, verbose_name='Membership Status'),
        ),
        migrations.CreateModel(
            name='ClubRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('registration_date', models.DateField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('SUSPENDED', 'Suspended')], default='PENDING', max_length=20)),
                ('position', models.CharField(blank=True, max_length=50)),
                ('jersey_number', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_registrations', to='geography.club')),
                ('member', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='club_registration', to='membership.member')),
            ],
            options={
                'verbose_name': 'Club Registration',
                'verbose_name_plural': 'Club Registrations',
                'unique_together': {('member', 'club')},
            },
        ),
    ]
