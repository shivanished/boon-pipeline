"""
Utilities for handling date and time conversions.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List

from constants import Constants

def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse date string in various formats to datetime object.
    
    Args:
        date_str: A string containing a date in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or date_str.strip() == "":
        return None
    
    formats = [
        "%m/%d/%y %H:%M",  # 01/28/25 11:00
        "%m/%d/%Y %H:%M",  # 01/28/2025 11:00
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format
        "%Y-%m-%d %H:%M:%S",  # Standard format
        "%Y%m%d%H%M%S%z",  # TMS format like 20221108000000-0700
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try to handle special cases using regex
    try:
        # Try to extract date and time using regex
        date_pattern = r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})"
        time_pattern = r"(\d{1,2}):(\d{1,2})"
        
        date_match = re.search(date_pattern, date_str)
        time_match = re.search(time_pattern, date_str)
        
        if date_match:
            month, day, year = date_match.groups()
            month = int(month)
            day = int(day)
            year = int(year)
            
            # Handle 2-digit years
            if year < 100:
                year += 2000 if year < 50 else 1900
            
            # Default to midnight if no time is specified
            hour, minute = 0, 0
            
            if time_match:
                hour, minute = map(int, time_match.groups())
                
            return datetime(year, month, day, hour, minute)
    except Exception:
        pass
    
    # If all parsing attempts fail
    return None


def format_datetime_for_tms(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime for TMS system.
    
    Args:
        dt: datetime object to format
        
    Returns:
        Formatted datetime string or None if dt is None
    """
    if dt is None:
        return None
    
    return dt.strftime(Constants.TMS_TIME_FORMAT)


def is_valid_appointment_window(start: Optional[datetime], end: Optional[datetime]) -> bool:
    """
    Check if the appointment window is valid.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        True if valid, False otherwise
    """
    if start is None or end is None:
        return False
    
    # End should be after start
    if end <= start:
        return False
    
    # Appointment window shouldn't be more than 24 hours
    if (end - start) > timedelta(hours=24):
        return False
    
    return True


def get_max_appointment_window(datetime_str: str) -> tuple:
    """
    Get a reasonable appointment window if only one time is provided.
    
    Args:
        datetime_str: A string containing a datetime
        
    Returns:
        Tuple of (start_datetime, end_datetime) as strings in TMS format
    """
    dt = parse_datetime(datetime_str)
    if not dt:
        return None, None
    
    # Default to a 2-hour window
    start_dt = dt
    end_dt = dt + timedelta(hours=2)
    
    return (
        format_datetime_for_tms(start_dt),
        format_datetime_for_tms(end_dt)
    )