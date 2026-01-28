"""
Utility functions for Axur integration.

Shared helpers for date formatting, encoding, and data manipulation.
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


def configure_encoding() -> None:
    """
    Configure console encoding for Windows compatibility.
    
    Ensures UTF-8 output even on older Windows terminals.
    """
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            pass  # Python < 3.7


def get_date_range(days_back: int = 30) -> tuple:
    """
    Calculate a date range from today.
    
    Args:
        days_back: Number of days to go back from today.
    
    Returns:
        Tuple of (start_date, end_date) as datetime objects.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date


def format_date_for_display(dt: datetime) -> str:
    """Format datetime for user-friendly display."""
    return dt.strftime("%Y-%m-%d")


def format_date_for_api(dt: datetime, end_of_day: bool = False) -> str:
    """
    Format datetime for Axur API queries.
    
    Args:
        dt: The datetime to format.
        end_of_day: If True, sets time to 23:59:59.
    
    Returns:
        ISO-formatted date string suitable for API queries.
    """
    if end_of_day:
        return dt.strftime("%Y-%m-%dT23:59:59")
    return dt.strftime("%Y-%m-%dT00:00:00")


def group_by_type(tickets: List[Dict]) -> Dict[str, int]:
    """
    Group tickets by their detection type and count occurrences.
    
    Args:
        tickets: List of ticket dictionaries from API.
    
    Returns:
        Dictionary mapping ticket types to their counts.
    
    Example:
        >>> counts = group_by_type(tickets)
        >>> print(counts)
        {'phishing': 15, 'malware': 3}
    """
    type_counts: Dict[str, int] = {}
    
    for ticket in tickets:
        ticket_type = ticket.get("detection", {}).get("type", "unknown")
        type_counts[ticket_type] = type_counts.get(ticket_type, 0) + 1
    
    return type_counts


def extract_ticket_key(ticket: Dict) -> str:
    """
    Extract the ticket key from a ticket dictionary.
    
    The key may be in different locations depending on API response format.
    
    Args:
        ticket: Ticket dictionary from API.
    
    Returns:
        The ticket key string, or "N/A" if not found.
    """
    return ticket.get("ticket", {}).get("ticketKey", "N/A")


def extract_ticket_date(ticket: Dict) -> str:
    """
    Extract the creation date from a ticket dictionary.
    
    Args:
        ticket: Ticket dictionary from API.
    
    Returns:
        Date string in YYYY-MM-DD format, or empty string if not found.
    """
    date_str = (
        ticket.get("ticket", {}).get("creation.date", "") or
        ticket.get("detection", {}).get("open", {}).get("date", "")
    )
    return date_str[:10] if date_str else ""


def filter_active_tickets(tickets: List[Dict]) -> List[Dict]:
    """
    Filter out discarded/resolved tickets, keeping only active threats.
    
    Args:
        tickets: List of ticket dictionaries.
    
    Returns:
        Filtered list containing only tickets without 'discarded' resolution.
    """
    return [
        t for t in tickets
        if t.get("current", {}).get("resolution") != "discarded"
    ]
