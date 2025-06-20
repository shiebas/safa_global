import os
import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.forms import ValidationError
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, Field, HTML, ButtonHolder, Submit

from .models import CustomUser, EMPLOYMENT_STATUS, Position, OrganizationType
from geography.models import Province, Region, LocalFootballAssociation, Club, NationalFederation
from membership.models.main import Player, Official, OfficialCertification
from .utils import extract_sa_id_dob_gender

class EmailAuthenticationForm(AuthenticationForm):
    """Custom authentication form using email instead of username"""
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Email Address'

class UniversalRegistrationForm(forms.ModelForm):
    age = forms.IntegerField(label='Age', required=False, disabled=True)
    """
    Simplified registration form for South African context.
    Passport option primarily for player registration by clubs.
    """
    # Account fields
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter a secure password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    # Role selection
    role = forms.ChoiceField(
        choices=[
            ('ADMIN_NATIONAL', 'National Administrator'),
            ('ADMIN_PROVINCE', 'Province Administrator'),
            ('ADMIN_REGION', 'Region Administrator'), 
            ('ADMIN_LOCAL_FED', 'LFA Administrator'),
            ('CLUB_ADMIN', 'Club Administrator')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Identity fields
    id_document_type = forms.ChoiceField(
        choices=[('ID', 'SA ID'), ('PP', 'Passport'), ('OT', 'Other')],
        initial='ID',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_number = forms.CharField(
        max_length=13, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 13-digit ID number'
        })
    )
    passport_number = forms.CharField(
        max_length=25, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter passport number'
        })
    )
    id_number_other = forms.CharField(
        max_length=25, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter document number'
        })
    )
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')], required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Files - ID document moved to identity section, profile photo to compliance
    id_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    profile_photo = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    
    # Geographic fields - for administrators only
    province = forms.ModelChoiceField(
        queryset=Province.objects.all(), 
        required=False, 
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'Select province'
        })
    )
    
    # Consent
    popi_act_consent = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    # Add organization type field
    organization_type = forms.ModelChoiceField(
        queryset=OrganizationType.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select your primary organization type"
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'last_name', 'role', 
            'organization_type', 
            'province', 'region', 'local_federation', 'club',
            'id_document_type', 'id_number', 'passport_number', 'id_number_other',
            'date_of_birth', 'gender', 'id_document', 'profile_photo', 
            'popi_act_consent', 'national_federation', 'age'  # add age
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, registration_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'age'):
            self.fields['age'].initial = self.instance.age
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        
        # Set default role based on registration type
        if registration_type == 'national':
            self.initial['role'] = 'ADMIN_NATIONAL'
            self.fields['role'].widget = forms.HiddenInput()
            
            # For ALL registrations, set SAFA as default national federation
            try:
                safa_federation, _ = NationalFederation.objects.get_or_create(
                    name="South African Football Association",
                    defaults={
                        'acronym': "SAFA",
                        'country_id': 1  # Assuming South Africa has ID 1
                    }
                )
                self.initial['national_federation'] = safa_federation.id
                # Make it read-only for clarity
                if 'national_federation' not in self.fields:
                    self.fields['national_federation'] = forms.ModelChoiceField(
                        queryset=NationalFederation.objects.all(),
                        required=False,
                        widget=forms.Select(attrs={'class': 'form-control', 'readonly': True})
                    )
                self.fields['national_federation'].widget.attrs['readonly'] = True
                self.fields['national_federation'].help_text = "Default: SAFA (All registrations belong to SAFA)"
            except Exception:
                pass
        
        # Add region and local_federation fields dynamically
        self.fields['region'] = forms.ModelChoiceField(
            queryset=Region.objects.none(),
            required=False,  # Will set required dynamically below
            widget=forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Select region'
            })
        )
        self.fields['local_federation'] = forms.ModelChoiceField(
            queryset=LocalFootballAssociation.objects.none(),
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Select local football association'
            })
        )
        # Filter region queryset by selected province
        province_id = self.data.get('province') or self.initial.get('province')
        if province_id:
            try:
                self.fields['region'].queryset = Region.objects.filter(province_id=province_id)
            except (ValueError, TypeError):
                self.fields['region'].queryset = Region.objects.none()
        else:
            self.fields['region'].queryset = Region.objects.none()

        # Filter local_federation queryset by selected region
        region_id = self.data.get('region') or self.initial.get('region')
        if region_id:
            try:
                self.fields['local_federation'].queryset = LocalFootballAssociation.objects.filter(region_id=region_id)
            except (ValueError, TypeError):
                self.fields['local_federation'].queryset = LocalFootballAssociation.objects.none()
        else:
            self.fields['local_federation'].queryset = LocalFootballAssociation.objects.none()
        # Set region required for Region Admin and below
        org_type = self.initial.get('organization_type') or self.data.get('organization_type')
        if org_type:
            try:
                if hasattr(org_type, 'level'):
                    org_level = org_type.level
                else:
                    org_obj = OrganizationType.objects.get(pk=org_type)
                    org_level = org_obj.level
                if org_level in ['REGION', 'LFA', 'CLUB']:
                    self.fields['region'].required = True
                else:
                    self.fields['region'].required = False
            except Exception as e:
                self.fields['region'].required = False
        
        # Create a layout with organization type selection
        self.helper.layout = Layout(
            # Account Information
            Fieldset(
                'Account Information',
                Div(
                    Div(Field('email', css_id='id_email'), css_class='col-md-4'),
                    Div(Field('password1', css_id='id_password1'), css_class='col-md-4'),
                    Div(Field('password2', css_id='id_password2'), css_class='col-md-4'),
                    css_class='row mb-3'
                ),
            ),
            
            # Personal Information
            Fieldset(
                'Personal Information',
                Div(
                    Div(Field('first_name', css_id='id_first_name'), css_class='col-md-6'),
                    Div(Field('last_name', css_id='id_last_name'), css_class='col-md-6'),
                    css_class='row mb-3'
                ),
                Div(
                    Div(Field('organization_type', css_id='id_organization_type'), css_class='col-md-6'),
                    Div(Field('role', css_id='id_role'), css_class='col-md-6'),
                    css_class='row mb-3'
                ),
            ),

            # Organization Information - dynamically shown based on organization type
            Fieldset(
                'Organization Information',
                Div(
                    Div(Field('province', css_id='id_province'), css_class='col-md-12'),
                    css_class='row mb-3 org-field province-field',
                    css_id='province-container',
                    style='display:none;'
                ),
                Div(
                    Div(Field('region', css_id='id_region'), css_class='col-md-12'),
                    css_class='row mb-3 org-field region-field',
                    css_id='region-container',
                    style='display:none;'
                ),
                Div(
                    Div(Field('local_federation', css_id='id_local_federation'), css_class='col-md-12'),
                    css_class='row mb-3 org-field lfa-field',
                    css_id='lfa-container',
                    style='display:none;'
                ),
                Div(
                    Div(Field('club', css_id='id_club'), css_class='col-md-12'),
                    css_class='row mb-3 org-field club-field',
                    css_id='club-container',
                    style='display:none;'
                ),
                css_id='organization-section'
            ),
            
            # Identity Information
            Fieldset(
                'Identity Information',
                Div(
                    Div(Field('id_document_type', css_id='id_id_document_type'), css_class='col-md-4'),
                    Div(
                        Field('id_number', css_id='id_id_number'),
                        HTML('<div id="id_number_error" class="text-danger" style="display:none;"></div>'),
                        css_class='col-md-4',
                        css_id='id_number_box'
                    ),
                    Div(
                        Field('passport_number', css_id='id_passport_number'),
                        css_class='col-md-4',
                        css_id='passport_box',
                        style='display:none;'
                    ),
                    Div(
                        Field('id_number_other', css_id='id_id_number_other'),
                        css_class='col-md-4',
                        css_id='id_number_other_box',
                        style='display:none;'
                    ),
                    css_class='row mb-3'
                ),
                Div(
                    Div(Field('date_of_birth', css_id='id_date_of_birth'), css_class='col-md-6'),
                    Div(Field('gender', css_id='id_gender'), css_class='col-md-6'),
                    css_class='row mb-3'
                ),
                Div(
                    Div(Field('id_document', css_id='id_id_document'), css_class='col-md-12'),
                    css_class='row mb-3'
                ),
            ),
            
            # Compliance Section (including profile photo)
            Fieldset(
                'Compliance Requirements',
                Div(
                    Div(Field('profile_photo', css_id='id_profile_photo'), css_class='col-md-12'),
                    HTML('<div class="form-text mb-3">Please upload a clear profile photo for identification</div>'),
                    css_class='row mb-3'
                ),
                Div(
                    Field('popi_act_consent', css_class='form-check-input'),
                    HTML('<div class="mt-2"><small class="text-muted">By checking this box, you consent to the POPI Act terms</small></div>'),
                    css_class='form-check'
                ),
            ),
            
            # Submit button
            Div(
                Submit('submit', 'Register', css_class='btn btn-primary'),
                css_class='d-grid gap-2 mt-4'
            ),
            
            # JavaScript for field toggling
            HTML('''
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    // ID Type field toggling
                    const idTypeSelect = document.getElementById('id_id_document_type');
                    const idNumberBox = document.getElementById('id_number_box');
                    const passportBox = document.getElementById('passport_box');
                    const otherIdBox = document.getElementById('id_number_other_box');
                    
                    function updateIdFields() {
                        const selectedValue = idTypeSelect.value;
                        
                        // Hide all ID fields first
                        idNumberBox.style.display = 'none';
                        passportBox.style.display = 'none';
                        otherIdBox.style.display = 'none';
                        
                        // Show the appropriate field
                        if (selectedValue === 'ID') {
                            idNumberBox.style.display = 'block';
                        } else if (selectedValue === 'PP') {
                            passportBox.style.display = 'block';
                        } else if (selectedValue === 'OT') {
                            otherIdBox.style.display = 'block';
                        }
                    }
                    
                    // Initial state
                    updateIdFields();
                    
                    // Add change listener
                    idTypeSelect.addEventListener('change', updateIdFields);
                    
                    // Dynamic geographic fields based on role
                    const roleSelect = document.getElementById('id_role');
                    const geoSection = document.getElementById('geographic-section');
                    
                    function updateGeoFields() {
                        const role = roleSelect.value;
                        
                        if (role === 'ADMIN_NATIONAL') {
                            geoSection.style.display = 'none';
                        } else {
                            geoSection.style.display = 'block';
                        }
                    }
                    
                    // Initial state
                    updateGeoFields();
                    
                    // Add change listener
                    roleSelect.addEventListener('change', updateGeoFields);
                    
                    // Organization type handling - add data attributes to options first
                    const orgTypeSelect = document.getElementById('id_organization_type');
                    // Add data-level attribute to each option
                    Array.from(orgTypeSelect.options).forEach(option => {
                        if (option.value) {
                            const text = option.text;
                            if (text.includes('National')) option.setAttribute('data-level', 'NATIONAL');
                            else if (text.includes('Province')) option.setAttribute('data-level', 'PROVINCE');
                            else if (text.includes('Region')) option.setAttribute('data-level', 'REGION');
                            else if (text.includes('Local') || text.includes('LFA')) option.setAttribute('data-level', 'LFA');
                            else if (text.includes('Club')) option.setAttribute('data-level', 'CLUB');
                        }
                    });
                    
                    // Get all organization field containers
                    const nationalFederationContainer = document.getElementById('national-federation-container');
                    const provinceContainer = document.getElementById('province-container');
                    const regionContainer = document.getElementById('region-container');
                    const lfaContainer = document.getElementById('lfa-container');
                    const clubContainer = document.getElementById('club-container');
                    
                    // Function to update visible organization fields
                    function updateOrgFields() {
                        // Get selected organization type level
                        const selectedOption = orgTypeSelect.options[orgTypeSelect.selectedIndex];
                        const orgLevel = selectedOption.getAttribute('data-level');
                        
                        // Hide all organization fields first
                        document.querySelectorAll('.org-field').forEach(field => {
                            field.style.display = 'none';
                        });
                        
                        // Show relevant fields based on organization type
                        switch(orgLevel) {
                            case 'NATIONAL':
                                nationalFederationContainer.style.display = 'flex';
                                break;
                            case 'PROVINCE':
                                provinceContainer.style.display = 'flex';
                                break;
                            case 'REGION':
                                provinceContainer.style.display = 'flex';
                                regionContainer.style.display = 'flex';
                                break;
                            case 'LFA':
                                provinceContainer.style.display = 'flex';
                                regionContainer.style.display = 'flex';
                                lfaContainer.style.display = 'flex';
                                break;
                            case 'CLUB':
                                provinceContainer.style.display = 'flex';
                                regionContainer.style.display = 'flex';
                                lfaContainer.style.display = 'flex';
                                clubContainer.style.display = 'flex';
                                break;
                        }
                    }
                    
                    // Set initial state
                    updateOrgFields();
                    
                    // Add change listeners
                    orgTypeSelect.addEventListener('change', updateOrgFields);
                });
            </script>
            '''),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        # All custom validation removed as requested
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        role = self.cleaned_data['role']
        user.role = role

        org_type = self.cleaned_data.get('organization_type')
        # Clear all org fields first
        user.national_federation = None
        user.province = None
        user.region = None
        user.local_federation = None
        user.club = None

        if org_type:
            level = org_type.level
            # Assign only the relevant organization field(s) based on org type level
            if level == 'NATIONAL':
                user.national_federation = self.cleaned_data.get('national_federation')
            elif level == 'PROVINCE':
                user.province = self.cleaned_data.get('province')
            elif level == 'REGION':
                user.region = self.cleaned_data.get('region')
                user.province = self.cleaned_data.get('province')
            elif level == 'LFA':
                user.local_federation = self.cleaned_data.get('local_federation')
                user.region = self.cleaned_data.get('region')
                user.province = self.cleaned_data.get('province')
            elif level == 'CLUB':
                user.club = self.cleaned_data.get('club')
                user.local_federation = self.cleaned_data.get('local_federation')
                user.region = self.cleaned_data.get('region')
                user.province = self.cleaned_data.get('province')

        # If a club admin is registering a player, inherit club info
        admin_user = self.initial.get('admin_user')
        if admin_user and role == 'PLAYER':
            user.club = admin_user.club
            user.province = admin_user.province
            user.region = admin_user.region
            user.local_federation = admin_user.local_federation
            user.national_federation = admin_user.national_federation

        # Only set region if present in cleaned_data
        if self.cleaned_data.get('region'):
            user.region = self.cleaned_data.get('region')
            print(f"[DEBUG] Assigned region: {user.region} (pk={getattr(user.region, 'pk', None)})")
        else:
            print("[DEBUG] No region assigned in form data!")
        if self.cleaned_data.get('province'):
            user.province = self.cleaned_data.get('province')
        if self.cleaned_data.get('local_federation'):
            user.local_federation = self.cleaned_data.get('local_federation')
        if self.cleaned_data.get('club'):
            user.club = self.cleaned_data.get('club')

        if role in ['ADMIN_NATIONAL', 'ADMIN_PROVINCE', 'ADMIN_REGION', 'ADMIN_LOCAL_FED', 'CLUB_ADMIN']:
            user.is_staff = True
        user.country_code = 'ZAF'
        user.nationality = 'South African'
        user.popi_act_consent = self.cleaned_data.get('popi_act_consent')
        if commit:
            user.save()
            print(f"[DEBUG] User saved with region: {user.region} (pk={getattr(user.region, 'pk', None)})")
        return user

# Create alias for backward compatibility 
NationalUserRegistrationForm = UniversalRegistrationForm

from django import forms
from membership.models import Player, PlayerClubRegistration
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

class ClubAdminPlayerRegistrationForm(forms.ModelForm):
    # Optional email field for player (already in model)
    popi_consent = forms.BooleanField(required=False, label="POPI Consent", help_text="Required for juniors")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make gender and email hidden fields
        self.fields['gender'].widget = forms.HiddenInput()
        self.fields['email'].widget = forms.HiddenInput()
        self.fields['email'].required = False  # Will be auto-generated
        self.fields['date_of_birth'].required = False  # Make DOB not required, will be calculated from ID
        
        # Configure SAFA ID and FIFA ID fields
        self.fields['safa_id'].required = False  # Will be auto-generated if not provided
        self.fields['safa_id'].help_text = "If the player already has a SAFA ID, enter it here. Otherwise, leave blank and it will be auto-generated."
        self.fields['safa_id'].widget.attrs.update({
            'pattern': '[A-Z0-9]{5}',
            'title': '5-character alphanumeric code (all caps)',
            'placeholder': 'e.g. A12B3'
        })
        
        self.fields['fifa_id'].required = False
        self.fields['fifa_id'].help_text = "If the player has a FIFA ID, enter it here. Otherwise, leave blank."
        self.fields['fifa_id'].widget.attrs.update({
            'pattern': '[0-9]{7}',
            'title': '7-digit FIFA identification number',
            'placeholder': 'e.g. 1234567'
        })
        
        # Name validation
        self.fields['first_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        self.fields['last_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        
        # Make ID number accept only digits
        self.fields['id_number'].widget.attrs.update({
            'pattern': '[0-9]{13}', 
            'inputmode': 'numeric',
            'title': 'ID number must be exactly 13 digits'
        })
        
        # Set has_sa_passport to False by default
        self.fields['has_sa_passport'].initial = False
        self.fields['has_sa_passport'].help_text = "Optional: Check this if the player has a South African passport in addition to SA ID (for record purposes only)"
        
        # Configure SA passport related fields
        self.fields['sa_passport_number'].required = False
        self.fields['sa_passport_number'].help_text = "Optional: Enter the South African passport number for record-keeping purposes"
        
        self.fields['sa_passport_document'].required = False
        self.fields['sa_passport_document'].help_text = "Optional: Upload a copy of the SA passport (PDF or image)"
        
        # Configure the expiry date field as a date widget
        self.fields['sa_passport_expiry_date'].required = False
        self.fields['sa_passport_expiry_date'].help_text = "Optional: Enter the expiry date of the SA passport"
        self.fields['sa_passport_expiry_date'].widget = forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control', 'min': datetime.date.today().isoformat()}
        )

    class Meta:
        model = Player
        fields = [
            'first_name', 'last_name',
            'id_document_type', 'id_number', 'passport_number',
            'has_sa_passport', 'sa_passport_number', 'sa_passport_document', 'sa_passport_expiry_date',
            'safa_id', 'fifa_id',
            'gender', 'date_of_birth', 'email',
            'profile_picture', 'id_document',
            'popi_consent',
        ]
        # No widgets override: let JS handle field visibility

    # Keep server-side validation for names, ID/passport uniqueness, etc.
    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('First name must be at least 3 alphabetic characters.')
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('Last name must be at least 3 alphabetic characters.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        id_number = cleaned_data.get('id_number')
        passport_number = cleaned_data.get('passport_number')
        has_sa_passport = cleaned_data.get('has_sa_passport')
        sa_passport_number = cleaned_data.get('sa_passport_number')
        sa_passport_document = cleaned_data.get('sa_passport_document')
        sa_passport_expiry_date = cleaned_data.get('sa_passport_expiry_date')
        popi_consent = cleaned_data.get('popi_consent')
        id_document_type = cleaned_data.get('id_document_type')
        dob = cleaned_data.get('date_of_birth')
        id_document = cleaned_data.get('id_document')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        errors = {}
        
        # Validate ID number format if provided
        if id_number:
            if not re.match(r'^\d{13}$', id_number):
                errors['id_number'] = 'ID number must be exactly 13 digits'
        
        # Only require one of ID or passport, let JS/UI handle toggling
        if not id_number and not passport_number:
            errors['id_number'] = 'Either ID number or passport number is required'
            errors['passport_number'] = 'Either ID number or passport number is required'
        
        # Validate passport document if using passport
        from django.conf import settings
        validate_documents = getattr(settings, 'VALIDATE_PASSPORT_DOCUMENTS', True)
        
        if validate_documents and id_document_type == 'PP' and id_document and passport_number:
            from .utils import validate_passport_document
            
            # Validate the uploaded passport document
            is_valid, messages = validate_passport_document(
                id_document, passport_number, first_name, last_name, dob
            )
            
            # If validation failed, add error
            if not is_valid:
                if any(msg.startswith("Document must be") for msg in messages):
                    errors['id_document'] = f"Passport document validation failed: {', '.join(messages)}"
                else:
                    # For OCR validation failures, show warning but allow submission
                    # Store warning in session for display after redirect
                    request = getattr(self, 'request', None)
                    if request and hasattr(request, 'session'):
                        if 'document_warnings' not in request.session:
                            request.session['document_warnings'] = []
                        request.session['document_warnings'].append(
                            f"Passport document accepted but requires validation: {', '.join(messages)}"
                        )
        
        # If SA passport info is provided (optional), validate what's there
        if has_sa_passport:
            # Only validate passport expiry date if it's provided
            today = timezone.now().date()
            if sa_passport_expiry_date and sa_passport_expiry_date < today:
                errors['sa_passport_expiry_date'] = 'The SA passport has expired. Please provide a valid passport with a future expiry date'
                
            # Validate document format (if provided)
            if sa_passport_document:
                ext = os.path.splitext(sa_passport_document.name)[1].lower()
                if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                    errors['sa_passport_document'] = 'SA passport document must be a PDF or image file (jpg, jpeg, png)'
                
                # If SA passport document is provided with a number, validate it
                if sa_passport_number and validate_documents:
                    from .utils import validate_passport_document
                    
                    # Validate the uploaded SA passport document
                    is_valid, messages = validate_passport_document(
                        sa_passport_document, sa_passport_number, first_name, last_name, dob
                    )
                    
                    # If validation failed, add error
                    if not is_valid:
                        if any(msg.startswith("Document must be") for msg in messages):
                            errors['sa_passport_document'] = f"SA passport document validation failed: {', '.join(messages)}"
                        else:
                            # For OCR validation failures, show warning but allow submission
                            request = getattr(self, 'request', None)
                            if request and hasattr(request, 'session'):
                                if 'document_warnings' not in request.session:
                                    request.session['document_warnings'] = []
                                request.session['document_warnings'].append(
                                    f"SA passport document accepted but requires validation: {', '.join(messages)}"
                                )
        
        # POPI consent required for juniors (under 18)
        if dob:
            age = (timezone.now().date() - dob).days // 365
            if age < 18 and not popi_consent:
                errors['popi_consent'] = 'POPI consent is required for players under 18'
                
        # Ensure id_number is unique
        if id_number and Player.objects.filter(id_number=id_number).exists():
            errors['id_number'] = 'A player with this ID number already exists'
            
        # Ensure passport_number is unique
        if passport_number and Player.objects.filter(passport_number=passport_number).exists():
            errors['passport_number'] = 'A player with this passport number already exists'
            
        # Check if SA passport number is unique
        if sa_passport_number and Player.objects.filter(sa_passport_number=sa_passport_number).exists():
            errors['sa_passport_number'] = 'A player with this South African passport number already exists'
        
        if errors:
            raise ValidationError(errors)
            
        return cleaned_data
        
        # POPI consent required for juniors (under 18)
        if dob:
            age = (timezone.now().date() - dob).days // 365
            if age < 18 and not popi_consent:
                raise ValidationError('POPI consent is required for players under 18.')
                
        # Ensure id_number/passport is unique
        if id_number and Player.objects.filter(id_number=id_number).exists():
            raise ValidationError('A player with this ID number already exists.')
            
        if passport_number and Player.objects.filter(passport_number=passport_number).exists():
            raise ValidationError('A player with this passport number already exists.')
            
        # Check if SA passport number is unique
        if sa_passport_number and Player.objects.filter(sa_passport_number=sa_passport_number).exists():
            raise ValidationError('A player with this South African passport number already exists.')
            
        return cleaned_data

class PlayerClubRegistrationOnlyForm(forms.ModelForm):
    class Meta:
        model = PlayerClubRegistration
        fields = ['position', 'jersey_number', 'height', 'weight', 'notes']

class PlayerUpdateForm(forms.ModelForm):
    """Form for updating player information after registration (including ID documents)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set has_sa_passport to False by default
        if not self.instance.has_sa_passport:
            self.fields['has_sa_passport'].initial = False
        # Help text for the checkbox
        self.fields['has_sa_passport'].help_text = "Optional: Check if player has a South African passport (for record purposes only)"
        # Make the SA passport number field not required initially
        self.fields['sa_passport_number'].required = False
        self.fields['sa_passport_number'].help_text = "Optional: Enter the South African passport number for record-keeping purposes"
        
        # Make phone_number optional
        self.fields['phone_number'].required = False
        self.fields['phone_number'].help_text = "Optional: Enter player's phone number if available"
        
        # Configure profile picture field
        self.fields['profile_picture'].help_text = "Upload player photo (required for player approval)"
        
        # Configure ID document field
        self.fields['id_document'].required = False
        if self.instance.id_document_type == 'ID':
            self.fields['id_document'].help_text = "Upload a copy of the South African ID document (required for approval)"
            self.fields['id_document'].label = "SA ID Document"
        else:
            self.fields['id_document'].help_text = "Upload a copy of the passport document (required for approval)"
            self.fields['id_document'].label = "Passport Document"
        
        # Configure the SA passport document and expiry fields
        self.fields['sa_passport_document'].required = False
        self.fields['sa_passport_document'].help_text = "Optional: Upload a copy of the SA passport (PDF or image)"
        
        # Configure the expiry date field
        self.fields['sa_passport_expiry_date'].required = False
        self.fields['sa_passport_expiry_date'].help_text = "Optional: Enter the expiry date of the SA passport"
        self.fields['sa_passport_expiry_date'].widget = forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control', 'min': datetime.date.today().isoformat()}
        )
    
    class Meta:
        model = Player
        fields = [
            'email', 'phone_number', 'profile_picture', 'id_document',
            'has_sa_passport', 'sa_passport_number', 'sa_passport_document', 'sa_passport_expiry_date',
            'street_address', 'suburb', 'city', 'state', 'postal_code',
        ]
        
    def clean(self):
        from django.conf import settings
        cleaned_data = super().clean()
        sa_passport_number = cleaned_data.get('sa_passport_number')
        id_document = cleaned_data.get('id_document')
        
        # Check if SA passport number is unique (excluding the current instance), but only if provided
        if sa_passport_number:
            existingPlayers = Player.objects.filter(sa_passport_number=sa_passport_number).exclude(pk=self.instance.pk)
            if existingPlayers.exists():
                raise ValidationError('A player with this South African passport number already exists.')
        
        # If document validation is enabled in settings (default to True if not specified)
        validate_documents = getattr(settings, 'VALIDATE_PASSPORT_DOCUMENTS', True)
        
        if validate_documents:
            # If a new passport document is uploaded and player is not using SA ID, validate it
            if id_document and self.instance.id_document_type != 'ID' and hasattr(id_document, 'content_type'):
                # Only validate if the file is new or changed (check if it's a UploadedFile object)
                if hasattr(id_document, 'file') or hasattr(id_document, 'read'):
                    from .utils import validate_passport_document
                    
                    passport_number = self.instance.passport_number
                    first_name = self.instance.first_name
                    last_name = self.instance.last_name
                    dob = self.instance.date_of_birth
                    
                    # Validate the uploaded passport document
                    is_valid, messages = validate_passport_document(
                        id_document, passport_number, first_name, last_name, dob
                    )
                    
                    # If validation failed, add error or warning
                    if not is_valid:
                        # If it's a serious problem, block submission
                        if any(msg.startswith("Document must be") for msg in messages):
                            raise ValidationError(f"Passport document validation failed: {', '.join(messages)}")
                        else:
                            # For OCR validation failures, show warning but allow submission
                            # In a production system, you might want to flag these for manual review
                            from django.contrib import messages as django_messages
                            request = getattr(self, 'request', None)
                            if request:
                                django_messages.warning(
                                    request, 
                                    f"Passport document accepted but requires validation: {', '.join(messages)}"
                                )
    
            # Similarly, if a new SA passport document is uploaded, validate it
            sa_passport_document = cleaned_data.get('sa_passport_document')
            has_sa_passport = cleaned_data.get('has_sa_passport')
            
            if sa_passport_document and has_sa_passport and hasattr(sa_passport_document, 'content_type'):
                # Only validate if the file is new or changed
                if hasattr(sa_passport_document, 'file') or hasattr(sa_passport_document, 'read'):
                    from .utils import validate_passport_document
                    
                    sa_passport_number = cleaned_data.get('sa_passport_number')
                    if sa_passport_number:  # Only validate if SA passport number is provided
                        first_name = self.instance.first_name
                        last_name = self.instance.last_name
                        dob = self.instance.date_of_birth
                        
                        # Validate the SA passport document
                        is_valid, messages = validate_passport_document(
                            sa_passport_document, sa_passport_number, first_name, last_name, dob
                        )
                        
                        # If validation failed, add error or warning
                        if not is_valid:
                            # If it's a serious problem, block submission
                            if any(msg.startswith("Document must be") for msg in messages):
                                raise ValidationError(f"SA passport document validation failed: {', '.join(messages)}")
                            else:
                                # For OCR validation failures, show warning but allow submission
                                # In a production system, you might want to flag these for manual review
                                from django.contrib import messages as django_messages
                                request = getattr(self, 'request', None)
                                if request:
                                    django_messages.warning(
                                        request, 
                                        f"SA passport document accepted but requires validation: {', '.join(messages)}"
                                    )
                
        return cleaned_data

class PlayerClubRegistrationUpdateForm(forms.ModelForm):
    """Form for updating player club registration information"""
    class Meta:
        model = PlayerClubRegistration
        fields = ['position', 'jersey_number', 'height', 'weight', 'notes']


class OfficialCertificationForm(forms.ModelForm):
    """Form for adding certifications to officials"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configure date fields as date input
        self.fields['obtained_date'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['expiry_date'].widget = forms.DateInput(attrs={'type': 'date'})
        
        # Add classes and placeholders
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter certification name'
        })
        
        self.fields['issuing_body'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter organization that issued this certification'
        })
        
        self.fields['certification_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter certification number (if applicable)'
        })
        
        self.fields['notes'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter any additional notes about this certification'
        })
        
        # Set current date as default for obtained_date
        self.fields['obtained_date'].initial = timezone.now().date()
    
    class Meta:
        model = OfficialCertification
        fields = [
            'certification_type', 'level', 'name', 'issuing_body',
            'certification_number', 'obtained_date', 'expiry_date', 
            'document', 'notes'
        ]
        widgets = {
            'certification_type': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
        }


class ClubAdminOfficialRegistrationForm(forms.ModelForm):
    # Optional email field for official (already in model)
    popi_consent = forms.BooleanField(required=False, label="POPI Consent", help_text="Required for all officials")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make gender and email hidden fields
        self.fields['gender'].widget = forms.HiddenInput()
        self.fields['email'].widget = forms.HiddenInput()
        self.fields['email'].required = False  # Will be auto-generated
        
        # Name validation
        self.fields['first_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        self.fields['last_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        
        # Make ID number accept only digits
        self.fields['id_number'].widget.attrs.update({
            'pattern': '[0-9]{13}', 
            'inputmode': 'numeric',
            'title': 'ID number must be exactly 13 digits'
        })
        
        # Configure SAFA ID and FIFA ID fields
        self.fields['safa_id'].required = False  # Will be auto-generated if not provided
        self.fields['safa_id'].help_text = "If the official already has a SAFA ID, enter it here. Otherwise, leave blank and it will be auto-generated."
        self.fields['safa_id'].widget.attrs.update({
            'pattern': '[A-Z0-9]{5}',
            'title': '5-character alphanumeric code (all caps)',
            'placeholder': 'e.g. A12B3'
        })
        
        self.fields['fifa_id'].required = False
        self.fields['fifa_id'].help_text = "If the official has a FIFA ID, enter it here. Otherwise, leave blank."
        self.fields['fifa_id'].widget.attrs.update({
            'pattern': '[0-9]{7}',
            'title': '7-digit FIFA identification number',
            'placeholder': 'e.g. 1234567'
        })
        
        # Filter positions to only show positions available at club level
        self.fields['position'].queryset = self.fields['position'].queryset.filter(
            levels__contains='CLUB', is_active=True)
        self.fields['position'].help_text = "Select the official's role or position in the club"
        self.fields['position'].required = True

    class Meta:
        model = Official
        fields = [
            'first_name', 'last_name',
            'id_document_type', 'id_number', 'passport_number',
            'gender', 'date_of_birth', 'email',
            'position', 'certification_number', 'certification_document',
            'certification_expiry_date', 'referee_level',
            'safa_id', 'fifa_id',
            'profile_picture', 'id_document',
            'popi_consent',
        ]

    # Keep server-side validation for names, ID/passport uniqueness, etc.
    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('First name must be at least 3 alphabetic characters.')
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('Last name must be at least 3 alphabetic characters.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        id_number = cleaned_data.get('id_number')
        passport_number = cleaned_data.get('passport_number')
        popi_consent = cleaned_data.get('popi_consent')
        id_document_type = cleaned_data.get('id_document_type')
        dob = cleaned_data.get('date_of_birth')
        id_document = cleaned_data.get('id_document')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        errors = {}
        
        # Validate ID number format if provided
        if id_number:
            if not re.match(r'^\d{13}$', id_number):
                errors['id_number'] = 'ID number must be exactly 13 digits'
        
        # Only require one of ID or passport, let JS/UI handle toggling
        if not id_number and not passport_number:
            errors['id_number'] = 'Either ID number or passport number is required'
            errors['passport_number'] = 'Either ID number or passport number is required'
        
        # Validate passport document if using passport
        from django.conf import settings
        validate_documents = getattr(settings, 'VALIDATE_PASSPORT_DOCUMENTS', True)
        
        if validate_documents and id_document_type == 'PP' and id_document and passport_number:
            from .utils import validate_passport_document
            
            # Validate the uploaded passport document
            is_valid, messages = validate_passport_document(
                id_document, passport_number, first_name, last_name, dob
            )
            
            # If validation failed, add error
            if not is_valid:
                if any(msg.startswith("Document must be") for msg in messages):
                    errors['id_document'] = f"Passport document validation failed: {', '.join(messages)}"
                else:
                    # For OCR validation failures, show warning but allow submission
                    # Store warning in session for display after redirect
                    request = getattr(self, 'request', None)
                    if request and hasattr(request, 'session'):
                        if 'document_warnings' not in request.session:
                            request.session['document_warnings'] = []
                        request.session['document_warnings'].append(
                            f"Passport document accepted but requires validation: {', '.join(messages)}"
                        )
        
        # POPI consent required for everyone
        if not popi_consent:
            errors['popi_consent'] = 'POPI consent is required'
                
        # Ensure id_number is unique across all members
        if id_number:
            from membership.models import Member
            if Member.objects.filter(id_number=id_number).exists():
                errors['id_number'] = 'A member with this ID number already exists'
            
        # Ensure passport_number is unique across all members
        if passport_number:
            from membership.models import Member
            if Member.objects.filter(passport_number=passport_number).exists():
                errors['passport_number'] = 'A member with this passport number already exists'
        
        if errors:
            raise ValidationError(errors)
            
        return cleaned_data

class PositionForm(forms.ModelForm):
    """Form for creating and editing positions with level checkboxes"""
    LEVEL_CHOICES = [
        ('NATIONAL', 'National Level'),
        ('PROVINCE', 'Province Level'),
        ('REGION', 'Region Level'),
        ('LFA', 'LFA Level'),
        ('CLUB', 'Club Level'),
        ('ASSOCIATION', 'Association Level'),
    ]
    
    level_checkboxes = forms.MultipleChoiceField(
        choices=LEVEL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Available at Levels",
        help_text="Select all levels where this position can be used"
    )
    
    class Meta:
        model = Position
        fields = ['title', 'description', 'employment_type', 'is_active', 'requires_approval']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If instance exists, populate checkboxes from levels string
        if self.instance and self.instance.pk and self.instance.levels:
            selected_levels = [level.strip() for level in self.instance.levels.split(',')]
            self.initial['level_checkboxes'] = selected_levels
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Convert selected checkboxes to comma-separated string
        selected_levels = self.cleaned_data.get('level_checkboxes', [])
        if selected_levels:
            instance.levels = ','.join(selected_levels)
        else:
            # Default to all levels if none selected
            instance.levels = 'NATIONAL,PROVINCE,REGION,LFA,CLUB'
        
        if commit:
            instance.save()
        
        return instance

class AssociationOfficialRegistrationForm(forms.ModelForm):
    """Form for registering officials at Association level"""
    # Optional email field for official (already in model)
    popi_consent = forms.BooleanField(required=False, label="POPI Consent", help_text="Required for all officials")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make gender and email hidden fields
        self.fields['gender'].widget = forms.HiddenInput()
        self.fields['email'].widget = forms.HiddenInput()
        self.fields['email'].required = False  # Will be auto-generated
        
        # Name validation
        self.fields['first_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        self.fields['last_name'].widget.attrs.update({
            'pattern': '[A-Za-z]{3,}', 
            'minlength': '3', 
            'title': 'Only letters, at least 3 characters'
        })
        
        # Make ID number accept only digits
        self.fields['id_number'].widget.attrs.update({
            'pattern': '[0-9]{13}', 
            'inputmode': 'numeric',
            'title': 'ID number must be exactly 13 digits'
        })
        
        # Configure SAFA ID and FIFA ID fields
        self.fields['safa_id'].required = False  # Will be auto-generated if not provided
        self.fields['safa_id'].help_text = "If the official already has a SAFA ID, enter it here. Otherwise, leave blank and it will be auto-generated."
        self.fields['safa_id'].widget.attrs.update({
            'pattern': '[A-Z0-9]{5}',
            'title': '5-character alphanumeric code (all caps)',
            'placeholder': 'e.g. A12B3'
        })
        
        self.fields['fifa_id'].required = False
        self.fields['fifa_id'].help_text = "If the official has a FIFA ID, enter it here. Otherwise, leave blank."
        self.fields['fifa_id'].widget.attrs.update({
            'pattern': '[0-9]{7}',
            'title': '7-digit FIFA identification number',
            'placeholder': 'e.g. 1234567'
        })
        # Filter positions to only show positions available at association level
        self.fields['position'].queryset = self.fields['position'].queryset.filter(
            levels__contains='ASSOCIATION', is_active=True)
        self.fields['position'].help_text = "Select the official's role or position in the association"
        self.fields['position'].required = True
        
    class Meta:
        model = Official
        fields = [
            'first_name', 'last_name',
            'id_document_type', 'id_number', 'passport_number',
            'gender', 'date_of_birth', 'email',
            'position', 'certification_number', 'certification_document',
            'certification_expiry_date', 'referee_level',
            'safa_id', 'fifa_id',
            'profile_picture', 'id_document',
            'popi_consent',
        ]

    # Keep server-side validation for names, ID/passport uniqueness, etc.
    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('First name must be at least 3 alphabetic characters.')
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '')
        if not value.isalpha() or len(value) < 3:
            raise ValidationError('Last name must be at least 3 alphabetic characters.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        id_number = cleaned_data.get('id_number')
        passport_number = cleaned_data.get('passport_number')
        popi_consent = cleaned_data.get('popi_consent')
        id_document_type = cleaned_data.get('id_document_type')
        dob = cleaned_data.get('date_of_birth')
        id_document = cleaned_data.get('id_document')
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        errors = {}
        
        # Validate ID number format if provided
        if id_number:
            if not re.match(r'^\d{13}$', id_number):
                errors['id_number'] = 'ID number must be exactly 13 digits'
        
        # Only require one of ID or passport, let JS/UI handle toggling
        if not id_number and not passport_number:
            errors['id_number'] = 'Either ID number or passport number is required'
            errors['passport_number'] = 'Either ID number or passport number is required'
        
        # Validate passport document if using passport
        from django.conf import settings
        validate_documents = getattr(settings, 'VALIDATE_PASSPORT_DOCUMENTS', True)
        
        if validate_documents and id_document_type == 'PP' and id_document and passport_number:
            from .utils import validate_passport_document
            
            # Validate the uploaded passport document
            is_valid, messages = validate_passport_document(
                id_document, passport_number, first_name, last_name, dob
            )
            
            # If validation failed, add error
            if not is_valid:
                if any(msg.startswith("Document must be") for msg in messages):
                    errors['id_document'] = f"Passport document validation failed: {', '.join(messages)}"
                else:
                    # For OCR validation failures, show warning but allow submission
                    # Store warning in session for display after redirect
                    request = getattr(self, 'request', None)
                    if request and hasattr(request, 'session'):
                        if 'document_warnings' not in request.session:
                            request.session['document_warnings'] = []
                        request.session['document_warnings'].append(
                            f"Passport document accepted but requires validation: {', '.join(messages)}"
                        )
        
        # POPI consent required for everyone
        if not popi_consent:
            errors['popi_consent'] = 'POPI consent is required'
                
        # Ensure id_number is unique across all members
        if id_number:
            from membership.models import Member
            if Member.objects.filter(id_number=id_number).exists():
                errors['id_number'] = 'A member with this ID number already exists'
            
        # Ensure passport_number is unique across all members
        if passport_number:
            from membership.models import Member
            if Member.objects.filter(passport_number=passport_number).exists():
                errors['passport_number'] = 'A member with this passport number already exists'
        
        if errors:
            raise ValidationError(errors)
            
        return cleaned_data