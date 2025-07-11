/**
 * South African ID Number validation utility
 * Provides functions to validate SA ID numbers using the Luhn algorithm.
 */

/**
 * Validates a South African ID number using the Luhn algorithm.
 * @param {string} idNumber - The 13-digit SA ID number to validate
 * @returns {Object} Validation result object with is_valid, error_message, and extracted information
 */
function validateSAIDNumber(idNumber) {
    const result = {
        isValid: false,
        errorMessage: null,
        citizenship: null,
        gender: null,
        dateOfBirth: null
    };

    // Basic validation
    if (!idNumber) {
        result.errorMessage = "ID number is required";
        return result;
    }

    if (!/^\d+$/.test(idNumber)) {
        result.errorMessage = "ID number must contain only digits";
        return result;
    }

    if (idNumber.length !== 13) {
        result.errorMessage = "ID number must be exactly 13 digits";
        return result;
    }

    try {
        // Extract birth date components
        const year = parseInt(idNumber.substring(0, 2));
        const month = parseInt(idNumber.substring(2, 4));
        const day = parseInt(idNumber.substring(4, 6));

        // Determine century
        const currentYear = new Date().getFullYear() % 100;
        let fullYear = year > currentYear ? 1900 + year : 2000 + year;

        // Validate date components
        if (month < 1 || month > 12) {
            result.errorMessage = "ID number contains invalid month";
            return result;
        }

        // Check days in month
        const lastDay = new Date(fullYear, month, 0).getDate();
        if (day < 1 || day > lastDay) {
            result.errorMessage = "ID number contains invalid day";
            return result;
        }

        // Create date object
        const dob = new Date(fullYear, month - 1, day);
        result.dateOfBirth = dob;

        // Extract gender
        const genderDigits = parseInt(idNumber.substring(6, 10));
        result.gender = genderDigits >= 5000 ? "M" : "F";

        // Extract citizenship
        const citizenshipDigit = parseInt(idNumber.charAt(10));
        result.citizenship = citizenshipDigit === 0 ? "SA Citizen" : "Permanent Resident";

        // Luhn algorithm validation
        let checksum = 0;
        let alternate = false;

        // Process digits from right to left
        for (let i = idNumber.length - 1; i >= 0; i--) {
            let digit = parseInt(idNumber.charAt(i));
            
            if (alternate) {
                digit *= 2;
                if (digit > 9) {
                    digit -= 9;
                }
            }
            
            checksum += digit;
            alternate = !alternate;
        }

        // If checksum is divisible by 10, the ID is valid
        if (checksum % 10 === 0) {
            result.isValid = true;
        } else {
            result.errorMessage = "ID number checksum is invalid";
        }

        return result;
    } catch (e) {
        console.error("Error validating SA ID number:", e);
        result.errorMessage = `Error validating ID number: ${e.message}`;
        return result;
    }
}

/**
 * Formats a date object as YYYY-MM-DD
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDateYMD(date) {
    if (!date) return '';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}
