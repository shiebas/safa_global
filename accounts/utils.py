import datetime
from django.forms import ValidationError
import os
import re
import logging
from django.conf import settings
# Import utilities for invoice creation
from django.utils import timezone
from django.db import transaction
import random
import string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


# Setup logging
logger = logging.getLogger(__name__)

# Optional imports - will be used if available, otherwise fallback to basic validation
# Setup flags for available libraries
PILLOW_AVAILABLE = False
TESSERACT_AVAILABLE = False
PYMUPDF_AVAILABLE = False

# Setup for checking module availability without importing
import importlib.util

# Check for PIL/Pillow
try:
    pillow_spec = importlib.util.find_spec("PIL")
    PILLOW_AVAILABLE = pillow_spec is not None
    if PILLOW_AVAILABLE:
        logger.info("PIL/Pillow is available for document processing")
    else:
        logger.warning("PIL/Pillow module not found")
except Exception as e:
    logger.warning(f"Error checking PIL/Pillow availability: {e}")
    PILLOW_AVAILABLE = False

# Check for pytesseract
try:
    tesseract_spec = importlib.util.find_spec("pytesseract")
    TESSERACT_AVAILABLE = tesseract_spec is not None
    if TESSERACT_AVAILABLE:
        logger.info("pytesseract module is available for OCR")
        
        # We still need to check if the actual Tesseract binary is available
        # But we'll do this at runtime when needed, not during import
    else:
        logger.warning("pytesseract module not found")
except Exception as e:
    logger.warning(f"Error checking pytesseract availability: {e}")
    TESSERACT_AVAILABLE = False

# Try to import PyMuPDF, but don't actually do the import at the module level
# Instead, just check if it's available and set the flag
try:
    # Just check if the module is available without actually importing it
    import importlib.util
    pymupdf_spec = importlib.util.find_spec("fitz")
    PYMUPDF_AVAILABLE = pymupdf_spec is not None
    if PYMUPDF_AVAILABLE:
        logger.info("PyMuPDF is available for PDF processing")
    else:
        logger.warning("PyMuPDF module not found")
except (ImportError, AttributeError, NameError) as e:
    logger.warning(f"Error checking PyMuPDF availability: {e}")
    PYMUPDF_AVAILABLE = False

def validate_sa_id_number(id_number):
    """
    Validates a South African ID number using the Luhn algorithm.
    
    Args:
        id_number (str): 13-digit South African ID number.
        
    Returns:
        dict: {
            'is_valid': bool,
            'error_message': str or None,
            'citizenship': str or None,
            'gender': str or None,
            'date_of_birth': datetime.date or None
        }
    """
    result = {
        'is_valid': False,
        'error_message': None,
        'citizenship': None,
        'gender': None,
        'date_of_birth': None
    }
    
    # Basic validation
    if not id_number:
        result['error_message'] = "ID number is required"
        return result
    
    if not isinstance(id_number, str) or not id_number.isdigit():
        result['error_message'] = "ID number must contain only digits"
        return result
    
    if len(id_number) != 13:
        result['error_message'] = "ID number must be exactly 13 digits"
        return result
    
    # Extract components
    try:
        # Extract and validate birth date
        year = int(id_number[:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        # Determine century
        current_year = datetime.date.today().year % 100
        full_year = 1900 + year if year > current_year else 2000 + year
        
        try:
            dob = datetime.date(full_year, month, day)
            result['date_of_birth'] = dob
        except ValueError:
            result['error_message'] = "ID number contains invalid birth date"
            return result
        
        # Extract gender
        gender_digits = int(id_number[6:10])
        gender = "Male" if gender_digits >= 5000 else "Female"
        gender_code = "M" if gender_digits >= 5000 else "F"
        result['gender'] = gender_code
        
        # Extract citizenship
        citizenship_digit = int(id_number[10])
        result['citizenship'] = "SA Citizen" if citizenship_digit == 0 else "Permanent Resident"
        
        # Luhn algorithm validation
        digits = [int(d) for d in id_number]
        checksum = 0
        
        for i in range(len(digits)):
            digit = digits[i]
            # Every second digit from right to left is doubled
            if (len(digits) - i) % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        
        # If checksum is divisible by 10, the ID is valid
        if checksum % 10 == 0:
            result['is_valid'] = True
        else:
            result['error_message'] = "ID number checksum is invalid"
        
        return result
    except Exception as e:
        logger.error(f"Error validating SA ID number: {str(e)}")
        result['error_message'] = f"Error validating ID number: {str(e)}"
        return result

def extract_sa_id_dob_gender(id_number):
    """
    Extracts date of birth and gender from a South African ID number.
    Args:
        id_number (str): 13-digit South African ID number.
    Returns:
        tuple: (date_of_birth (datetime.date or None), gender (str or None))
    """
    if not id_number or len(id_number) != 13 or not id_number.isdigit():
        return (None, None)
    
    try:
        year = int(id_number[:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])

        current_year = datetime.date.today().year % 100
        full_year = 1900 + year if year > current_year else 2000 + year

        # This will raise ValueError if the date is invalid
        dob = datetime.date(full_year, month, day)

        gender_digits = int(id_number[6:10])
        gender = "Male" if gender_digits >= 5000 else "Female"

        return (dob, gender)
    except (ValueError, TypeError):
        return (None, None)

def validate_passport_document(passport_document, passport_number, first_name, last_name, dob=None):
    """
    Validates a passport document by extracting and verifying contents.
    Checks if passport number, name, and DOB match the provided info.
    
    Args:
        passport_document: The uploaded passport document file
        passport_number (str): The passport number to verify against
        first_name (str): First name to verify
        last_name (str): Last name to verify
        dob (datetime.date, optional): Date of birth to verify
    
    Returns:
        tuple: (is_valid (bool), messages (list))
    """
    if not passport_document:
        return False, ["No passport document provided"]
    
    # Check if file extension is supported
    ext = os.path.splitext(passport_document.name)[1].lower()
    if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        return False, ["Document must be a PDF or image file (jpg, jpeg, png)"]
    
    # If we don't have the OCR libraries available, fall back to basic validation
    if not (PILLOW_AVAILABLE and TESSERACT_AVAILABLE and PYMUPDF_AVAILABLE):
        logger.warning("OCR libraries not available. Falling back to basic document validation.")
        # Do basic file validation - at minimum check file size and type
        if passport_document.size > 10 * 1024 * 1024:  # Max 10MB
            return False, ["Document file is too large (max 10MB)"]
        
        # Basic check passed - in production you might want to flag this for manual review
        return True, ["Document accepted. OCR validation not available - document will require manual verification."]
    
    try:
        # Extract text from the document based on file type
        extracted_text = ""
        
        if ext == '.pdf' and PYMUPDF_AVAILABLE:
            try:
                # Dynamically import PyMuPDF when needed
                fitz = importlib.import_module("fitz")
                
                with fitz.open(stream=passport_document.read(), filetype="pdf") as doc:
                    for page in doc:
                        extracted_text += page.get_text()
                passport_document.seek(0)  # Reset file pointer after reading
            except Exception as e:
                logger.error(f"PyMuPDF error processing PDF: {e}")
                return True, ["Document accepted. PDF processing error - document will require manual verification."]
        elif PILLOW_AVAILABLE and TESSERACT_AVAILABLE:
            try:
                # Dynamically import PIL and pytesseract when needed
                PIL = importlib.import_module("PIL")
                Image = PIL.Image
                pytesseract = importlib.import_module("pytesseract")
                
                img = Image.open(passport_document)
                extracted_text = pytesseract.image_to_string(img)
            except Exception as e:
                logger.error(f"OCR error processing image: {e}")
                return True, ["Document accepted. Image processing error - document will require manual verification."]
        else:
            # If we got here, it means the imports were available but something went wrong
            return True, ["Document accepted. OCR processing unavailable - document will require manual verification."]
        
        # Normalize text for case-insensitive comparison
        extracted_text = extracted_text.lower()
        first_name_lower = first_name.lower()
        last_name_lower = last_name.lower()
        passport_number_clean = re.sub(r'\s+', '', passport_number).lower()
        
        # Initialize validation results
        validation_results = {
            'passport_number': False,
            'first_name': False,
            'last_name': False,
            'dob': True if dob is None else False  # Skip DOB check if not provided
        }
        
        # Check passport number
        if passport_number_clean in re.sub(r'\s+', '', extracted_text):
            validation_results['passport_number'] = True
        
        # Check names (more flexible check for names)
        if first_name_lower in extracted_text:
            validation_results['first_name'] = True
        
        if last_name_lower in extracted_text:
            validation_results['last_name'] = True
        
        # Check DOB if provided
        if dob:
            # Try different date formats
            date_formats = [
                dob.strftime('%d.%m.%Y'),
                dob.strftime('%d/%m/%Y'),
                dob.strftime('%d-%m-%Y'),
                dob.strftime('%d %b %Y'),
                dob.strftime('%d %B %Y')
            ]
            
            for date_format in date_formats:
                if date_format.lower() in extracted_text:
                    validation_results['dob'] = True
                    break
        
        # Prepare validation messages
        messages = []
        is_valid = True
        
        if not validation_results['passport_number']:
            messages.append(f"Passport number '{passport_number}' not found in document")
            is_valid = False
        
        if not validation_results['first_name']:
            messages.append(f"First name '{first_name}' not found in document")
            is_valid = False
        
        if not validation_results['last_name']:
            messages.append(f"Last name '{last_name}' not found in document")
            is_valid = False
        
        if dob and not validation_results['dob']:
            messages.append(f"Date of birth not found in document or doesn't match")
            is_valid = False
        
        if is_valid:
            messages.append("Document validation successful")
        
        return is_valid, messages
    
    except Exception as e:
        logger.error(f"Error validating passport document: {str(e)}")
        # In case of errors, allow the document but flag for manual verification
        return True, [f"Document accepted but requires manual verification. Automatic validation error: {str(e)}"]

def create_player_invoice(player, club, issued_by=None, is_junior=False):
    """
    Create an invoice for player registration.

    Args:
        player (Player): The player to create an invoice for.
        club (Club): The club the player is registering with.
        issued_by (CustomUser, optional): The user issuing the invoice. Defaults to None.
        is_junior (bool): If True, use junior registration fee. Defaults to False.

    Returns:
        Invoice: The created invoice or None if an error occurs.
    """
    from membership.models import Invoice, InvoiceItem, Member
    from decimal import Decimal

    logger.info(f"Attempting to create invoice for player: {player.id}")

    try:
        issuer_member = None
        if issued_by and issued_by.is_authenticated:
            try:
                issuer_member = Member.objects.get(user=issued_by)
                logger.info(f"Invoice will be issued by member: {issuer_member.id}")
            except Member.DoesNotExist:
                logger.warning(
                    f"User '{issued_by.email}' (ID: {issued_by.id}) created an invoice "
                    f"but does not have a corresponding Member profile. Invoice will have no issuer."
                )

        fee_amount = Decimal("100.00") if is_junior else Decimal("200.00")
        registration_type = "Junior Registration" if is_junior else "Senior Registration"
        invoice_number = f"REG-{player.safa_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        with transaction.atomic():
            invoice = Invoice.objects.create(
                invoice_type='REGISTRATION',
                amount=fee_amount,
                status='PENDING',
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=30),
                player=player,
                club=club,
                issued_by=issuer_member,  # This can now be None
                invoice_number=invoice_number
            )
            logger.info(f"Successfully created invoice {invoice.invoice_number} for player {player.id}")

            InvoiceItem.objects.create(
                invoice=invoice,
                description=f"{registration_type} Fee",
                quantity=1,
                unit_price=fee_amount,
                sub_total=fee_amount
            )
            logger.info(f"Successfully created invoice item for invoice {invoice.invoice_number}")

            return invoice

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR creating player invoice for player {player.id}: {e}", exc_info=True)
        return None

def generate_unique_safa_id():
    """
    Generates a unique 5-character SAFA ID.
    Format: A combination of uppercase letters and numbers (e.g., A12B3)
    
    Returns:
        str: A unique 5-character SAFA ID
    """
    from django.utils.crypto import get_random_string
    from membership.models import Member
    
    # Generate a unique code
    while True:
        code = get_random_string(length=5, allowed_chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        if not Member.objects.filter(safa_id=code).exists():
            return code

def create_official_invoice(official, club=None, association=None, issued_by=None, position_type=None):
    """
    Create an invoice for official registration
    
    Args:
        official (Official): The official to create an invoice for
        club (Club, optional): The club the official is registering with
        association (Association, optional): The association the official is registering with
        issued_by (Member): The admin who issued the invoice
        position_type (str): Type of position - determines fee amount
        
    Returns:
        Invoice: The created invoice
    """
    try:
        # Import at function level to avoid circular imports
        from membership.models import Invoice, InvoiceItem
        
        # Set fee amount based on position type
        # Default fee is R150, but can be adjusted based on position
        fee_amount = 150.00
        position_title = "Standard Position"
        
        if official.position:
            position_title = official.position.title
            # Check if referee or coach for higher fee
            if "referee" in position_title.lower():
                fee_amount = 250.00
            elif "coach" in position_title.lower():
                fee_amount = 200.00
        
        # Generate a reference number
        invoice_number_prefix = f"REG-OFF-{official.membership_number or official.id}-{timezone.now().strftime('%Y%m%d')}"

        with transaction.atomic():
            # Create invoice
            invoice = Invoice(
                invoice_type='REGISTRATION',
                amount=fee_amount,
                status='PENDING',
                issue_date=timezone.now().date(),
                player=None,  # Not a player registration
                official=official,  # Link to official
                club=club,
                association=association,
                issued_by=issued_by,
                invoice_number=invoice_number_prefix # Use invoice_number field
            )
            invoice.save()
            
            # Create invoice item
            item = InvoiceItem(
                invoice=invoice,
                description=f"{position_title} Registration Fee",
                quantity=1,
                unit_price=fee_amount,
                sub_total=fee_amount
            )
            item.save()
            
            return invoice
    except Exception as e:
        logger.error(f"Error creating official invoice: {str(e)}")
        return None
    

def send_activation_email(request, user):
    subject = 'Activate Your Account'
    activation_link = request.build_absolute_uri(
        f'/accounts/activate/{user.activation_token}/'
    )
    html_message = render_to_string('accounts/activation_email.html', {
        'user': user,
        'activation_link': activation_link,
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )