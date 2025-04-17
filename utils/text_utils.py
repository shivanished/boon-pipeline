"""
Utilities for text processing and extraction.
"""

import re
from typing import Optional, List, Tuple, Dict, Any


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract phone number from text if available.
    
    Args:
        text: Text that might contain a phone number
        
    Returns:
        Extracted phone number or None if not found
    """
    if not text:
        return None
    
    # Simple regex for phone number extraction
    pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    
    return None


def parse_address(address: str) -> Tuple[str, str, str, str]:
    """
    Parse address string into components.
    
    Args:
        address: Full address string
        
    Returns:
        Tuple of (street, city, state, zip)
    """
    if not address:
        return "", "", "", ""
    
    # For basic cases, try to extract state and zip
    state_zip_pattern = r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)"
    match = re.search(state_zip_pattern, address)
    
    if match:
        state = match.group(1)
        zip_code = match.group(2)
        # Remove state and zip from the address
        remaining = address.replace(match.group(0), "").strip()
        
        # Try to find the city
        city_pattern = r"([A-Za-z\s]+),"
        city_match = re.search(city_pattern, remaining)
        if city_match:
            city = city_match.group(1).strip()
            # Remove city and comma from the address
            street = remaining.replace(f"{city},", "").strip()
        else:
            # If we can't find a specific pattern, make an educated guess
            parts = remaining.split(',')
            if len(parts) > 1:
                city = parts[-1].strip()
                street = ','.join(parts[:-1]).strip()
            else:
                # If no commas, make a best guess
                city = ""
                street = remaining
    else:
        # Try another pattern where city, state and zip are at the end
        city_state_zip_pattern = r"([A-Za-z\s]+),?\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)"
        match = re.search(city_state_zip_pattern, address)
        
        if match:
            city = match.group(1).strip()
            state = match.group(2)
            zip_code = match.group(3)
            
            # Remove city, state, zip from the address
            street = address.replace(match.group(0), "").strip()
        else:
            # If we can't parse with regex, return the original address
            return address, "", "", ""
    
    return street, city, state, zip_code


def extract_reference_numbers(text: str) -> List[Tuple[str, str]]:
    """
    Extract reference numbers and their types from text.
    
    Args:
        text: Text containing reference numbers
        
    Returns:
        List of tuples (reference_type, reference_number)
    """
    if not text:
        return []
    
    references = []
    
    # Split by commas or similar delimiters
    parts = re.split(r'[,;]', text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Try to find patterns like "PO#: 12345" or "PO: 12345"
        pattern = r"([A-Za-z]+)(?:#|:)?\s*(\d+)"
        match = re.search(pattern, part)
        if match:
            ref_type = match.group(1).upper()
            ref_number = match.group(2)
            references.append((ref_type, ref_number))
        else:
            # If no specific type is found, assume it's a reference number
            if re.search(r'\d+', part):
                references.append(("REF", part))
    
    return references


def extract_company_code(company_name: str) -> str:
    """
    Extract a company code for TMS from a company name.
    
    In a real implementation, this would query a database of known companies.
    For this example, we'll generate a simple code from the name.
    
    Args:
        company_name: The company name
        
    Returns:
        A company code
    """
    if not company_name:
        return "UNKNOWN"
    
    words = company_name.upper().split()
    if not words:
        return "UNKNOWN"
    
    # Take first 4 letters of first word, or whole word if shorter
    code = words[0][:4]
    return code


def clean_text(text: str) -> str:
    """
    Clean text by removing extra spaces, normalizing whitespace, etc.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text