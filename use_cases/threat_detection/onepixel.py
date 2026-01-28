"""
OnePixel Detection Filter

This module provides functionality for filtering and analyzing tickets
based on their detection origin, with special focus on OnePixel tracking.

OnePixel is Axur's proprietary tracking script that detects when users
visit phishing pages impersonating a protected brand.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.axur_client import AxurClient
from core.utils import group_by_type, extract_ticket_key, extract_ticket_date


# Available detection origins
DETECTION_ORIGINS: Dict[str, str] = {
    "onepixel": "OnePixel - Automatic detection via protection script",
    "platform": "Platform - Detected by Axur platform monitoring",
    "api": "API - Manually inserted via API integration",
    "collector": "Collector - Detected by specific collectors"
}


def filter_by_origin(
    client: Optional[AxurClient] = None,
    origin: str = "onepixel",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30
) -> List[Dict]:
    """
    Retrieve tickets filtered by their detection origin.
    
    Args:
        client: AxurClient instance. Creates new one if not provided.
        origin: The detection origin to filter by (onepixel, platform, api, collector).
        start_date: Start of date range.
        end_date: End of date range.
        days_back: Days to look back if dates not specified.
    
    Returns:
        List of ticket dictionaries matching the origin filter.
    
    Example:
        tickets = filter_by_origin(origin="onepixel", days_back=90)
        print(f"Found {len(tickets)} OnePixel detections")
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    return client.get_tickets(
        start_date=start_date,
        end_date=end_date,
        originator=origin
    )


def get_origin_summary(tickets: List[Dict]) -> Dict[str, int]:
    """
    Get a summary of tickets grouped by threat type.
    
    Args:
        tickets: List of ticket dictionaries.
    
    Returns:
        Dictionary mapping threat types to their counts.
    """
    return group_by_type(tickets)


def format_ticket_list(
    tickets: List[Dict],
    limit: Optional[int] = None
) -> List[Dict[str, str]]:
    """
    Format tickets for display with key, type, and date.
    
    Args:
        tickets: List of ticket dictionaries.
        limit: Maximum number of tickets to return.
    
    Returns:
        List of formatted ticket dictionaries with key, type, and date fields.
    
    Example:
        formatted = format_ticket_list(tickets, limit=10)
        for t in formatted:
            print(f"{t['key']} - {t['type']} - {t['date']}")
    """
    # Sort by date descending
    sorted_tickets = sorted(
        tickets,
        key=lambda x: x.get("ticket", {}).get("creation.date", ""),
        reverse=True
    )
    
    if limit:
        sorted_tickets = sorted_tickets[:limit]
    
    result = []
    for ticket in sorted_tickets:
        result.append({
            "key": extract_ticket_key(ticket),
            "type": ticket.get("detection", {}).get("type", "unknown"),
            "date": extract_ticket_date(ticket)
        })
    
    return result


def export_to_csv(
    tickets: List[Dict],
    filename: str,
    origin: str = "unknown"
) -> str:
    """
    Export tickets to CSV file for external analysis.
    
    Args:
        tickets: List of ticket dictionaries.
        filename: Output filename (without extension).
        origin: Detection origin for metadata.
    
    Returns:
        Path to the created CSV file.
    """
    full_path = f"{filename}.csv"
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("key,type,date,status,origin\n")
        
        for ticket in tickets:
            key = extract_ticket_key(ticket)
            t_type = ticket.get("detection", {}).get("type", "")
            date = extract_ticket_date(ticket)
            status = ticket.get("current", {}).get("status", "")
            f.write(f"{key},{t_type},{date},{status},{origin}\n")
    
    return full_path
