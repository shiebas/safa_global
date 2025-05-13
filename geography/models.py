# geography/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# ===== CHOICE DEFINITIONS =====
DOCUMENT_TYPES = (
    ('BC', _('Birth Certificate')),
    ('PP', _('Passport')),
    ('ID', _('National ID')),
    ('DL', _('Driver License')),
    ('OT', _('Other')),
)

GENDER_CHOICES = (
    ('M', _('Male')),
    ('F', _('Female')),
    ('O', _('Other')),
    ('U', _('Undisclosed')),
)

ROLES = (
    ('ADMIN', _('System Admin')),
    ('CLUB', _('Club Manager')),
    ('PLAYER', _('Player')),
    ('REFEREE', _('Referee')),
    ('FED_ADMIN', _('Federation Admin')),
    ('PUBLIC', _('Public User')),
    ('COACH', _('Coach')),
    ('EXECUTIVE', _('Exco Member')),
)

# ===== MODEL DEFINITION =====
class CustomUser(AbstractUser):
    # Core Fields
    role = models.CharField(max_length=10, choices=ROLES, default='PLAYER')
    name = models.CharField(max_length=50, blank=True)
    surname = models.CharField(max_length=100, blank=True)
    user_name = models.CharField(max_length=50, blank=True, unique=True)
    email = models.EmailField(_('email address'), blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Identification
    id_number = models.CharField(max_length=20, blank=True)
    id_document_type = models.CharField(
        max_length=2,
        choices=DOCUMENT_TYPES,
        default='ID'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True
    )

    # Sports Fields
    club_affiliation = models.CharField(max_length=100, blank=True)
    federation_code = models.CharField(max_length=3, blank=True)
    province_code = models.CharField(max_length=3, blank=True)
    region_code = models.CharField(max_length=3, blank=True)
    fifa_id = models.CharField(max_length=10, unique=True, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # Media
    profile_picture = models.ImageField(
        upload_to='user_profiles/',
        null=True,
        blank=True,
        default='user_profiles/default.png',
        help_text=_('Profile picture (max 2MB)')
    )

    # ===== METHODS =====
    @property
    def membership_id(self):
        """Generate SAFA ID: SAFA{federation}{province}{user_id}"""
        if not self.pk:  # For unsaved instances
            return "SAFA000XX0000"
        return f"SAFA{self.federation_code or '000'}{self.province_code or 'XX'}{str(self.pk).zfill(4)}"

    def clean(self):
        """Validate all fields"""
        errors = {}

        # Gender validation
        if self.gender and self.gender not in dict(GENDER_CHOICES):
            errors['gender'] = _("Invalid gender selection")

        # Document type validation
        if self.id_document_type not in dict(DOCUMENT_TYPES):
            errors['id_document_type'] = _("Invalid document type")

        # FIFA ID validation
        if self.fifa_id and not self.fifa_id.startswith('FIFA-'):
            errors['fifa_id'] = _("Must start with 'FIFA-'")

        if errors:
            raise ValidationError(errors)
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.membership_id})"

# World Governing Bodies

class GoverningBody(models.Model):
    name = models.CharField(max_length=100, unique=True)
    acronym = models.CharField(max_length=20, unique=True)  # e.g. "FIFA"
    founded_date = models.DateField(null=True, blank=True)
    headquarters = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)

    # Logo with default fallback
    logo = models.ImageField(
        upload_to='governing_bodies/logos/',
        default='governing_bodies/default_logo.png',
        blank=True
    )

    def logo_preview(self):
        from django.utils.html import mark_safe
        if self.logo:
            return mark_safe(f'<img src="{self.logo.url}" style="max-height: 50px;" />')
        return mark_safe('<img src="/static/governing_bodies/default_logo.png" style="max-height: 50px;" />')

    def clean(self):
        """Validate acronym is uppercase"""
        if not self.acronym.isupper():
            raise ValidationError("Acronym must be in uppercase (e.g. FIFA)")

    def __str__(self):
        return f"{self.name} ({self.acronym})"

    class Meta:
        verbose_name_plural = "Governing Bodies"
        ordering = ['name']
