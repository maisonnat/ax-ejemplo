"""
Executive Reports Generator

This module provides DREAD and STRIDE analysis for security incident prioritization
and threat categorization. These methodologies help executives understand the
risk landscape and prioritize remediation efforts.

DREAD: Damage, Reproducibility, Exploitability, Affected users, Discoverability
STRIDE: Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.axur_client import AxurClient


# STRIDE categorization mapping
STRIDE_MAPPING: Dict[str, str] = {
    # Spoofing (Identity impersonation)
    "phishing": "S",
    "fake-social-media-profile": "S",
    "executive-fake-social-media-profile": "S",
    "similar-domain-name": "S",
    # Tampering (Data modification)
    "fraudulent-brand-use": "T",
    "fake-mobile-app": "T",
    # Repudiation (Deniability)
    "unauthorized-sale": "R",
    "unauthorized-distribution": "R",
    # Information Disclosure
    "corporate-credential-leak": "I",
    "code-secret-leak": "I",
    "database-exposure": "I",
    "data-exposure-website": "I",
    "data-exposure-message": "I",
    "other-sensitive-data": "I",
    "executive-credential-leak": "I",
    "executive-personalinfo-leak": "I",
    # Denial of Service
    "ransomware-attack": "D",
    "infrastructure-exposure": "D",
    "malware": "D",
    # Elevation of Privilege
    "infostealer-credential": "E",
    "executive-card-leak": "E",
    "executive-mobile-phone": "E",
}

STRIDE_NAMES: Dict[str, str] = {
    "S": "Spoofing (Identity Impersonation)",
    "T": "Tampering (Data Modification)",
    "R": "Repudiation (Deniability)",
    "I": "Information Disclosure",
    "D": "Denial of Service",
    "E": "Elevation of Privilege",
}


# DREAD factor weights by ticket type
DREAD_WEIGHTS: Dict[str, Dict[str, int]] = {
    "phishing": {
        "damage": 7, "reproducibility": 9, "exploitability": 8,
        "affected_users": 8, "discoverability": 9
    },
    "ransomware-attack": {
        "damage": 10, "reproducibility": 5, "exploitability": 4,
        "affected_users": 9, "discoverability": 3
    },
    "infostealer-credential": {
        "damage": 9, "reproducibility": 8, "exploitability": 7,
        "affected_users": 6, "discoverability": 4
    },
    "corporate-credential-leak": {
        "damage": 8, "reproducibility": 4, "exploitability": 6,
        "affected_users": 7, "discoverability": 5
    },
    "malware": {
        "damage": 8, "reproducibility": 6, "exploitability": 5,
        "affected_users": 7, "discoverability": 4
    },
    "fake-mobile-app": {
        "damage": 6, "reproducibility": 7, "exploitability": 6,
        "affected_users": 5, "discoverability": 8
    },
    "similar-domain-name": {
        "damage": 4, "reproducibility": 7, "exploitability": 5,
        "affected_users": 3, "discoverability": 8
    },
    "fraudulent-brand-use": {
        "damage": 5, "reproducibility": 6, "exploitability": 4,
        "affected_users": 4, "discoverability": 7
    },
}

DEFAULT_DREAD: Dict[str, int] = {
    "damage": 5, "reproducibility": 5, "exploitability": 5,
    "affected_users": 5, "discoverability": 5
}


@dataclass
class DreadResult:
    """Result of DREAD analysis for a single ticket."""
    ticket_key: str
    ticket_type: str
    total_score: int
    damage: int
    reproducibility: int
    exploitability: int
    affected_users: int
    discoverability: int
    priority: str  # Critical, High, Medium, Low


@dataclass
class StrideResult:
    """Result of STRIDE classification."""
    category: str
    name: str
    count: int
    percentage: float
    threat_types: List[str] = field(default_factory=list)


def calculate_dread_score(ticket: Dict) -> DreadResult:
    """
    Calculate DREAD score for a single ticket.
    
    DREAD is a risk assessment model that evaluates:
    - Damage: How bad would an attack be?
    - Reproducibility: How easy is it to reproduce?
    - Exploitability: How easy is it to launch an attack?
    - Affected users: How many users would be impacted?
    - Discoverability: How easy is it to discover the vulnerability?
    
    Args:
        ticket: Ticket dictionary from API.
    
    Returns:
        DreadResult with individual scores and total.
    """
    ticket_key = ticket.get("ticket", {}).get("ticketKey", "N/A")
    ticket_type = ticket.get("detection", {}).get("type", "unknown")
    
    weights = DREAD_WEIGHTS.get(ticket_type, DEFAULT_DREAD)
    
    total = sum(weights.values())
    
    if total >= 40:
        priority = "Critical"
    elif total >= 30:
        priority = "High"
    elif total >= 20:
        priority = "Medium"
    else:
        priority = "Low"
    
    return DreadResult(
        ticket_key=ticket_key,
        ticket_type=ticket_type,
        total_score=total,
        damage=weights["damage"],
        reproducibility=weights["reproducibility"],
        exploitability=weights["exploitability"],
        affected_users=weights["affected_users"],
        discoverability=weights["discoverability"],
        priority=priority
    )


def analyze_dread(
    client: Optional[AxurClient] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30,
    limit: int = 100
) -> List[DreadResult]:
    """
    Perform DREAD analysis on recent tickets.
    
    Args:
        client: AxurClient instance.
        start_date: Start of analysis period.
        end_date: End of analysis period.
        days_back: Days to look back if dates not specified.
        limit: Maximum number of tickets to analyze.
    
    Returns:
        List of DreadResult objects sorted by score (highest first).
    
    Example:
        results = analyze_dread(days_back=30)
        for r in results[:10]:
            print(f"{r.ticket_key}: {r.total_score} ({r.priority})")
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    tickets = client.get_tickets(start_date=start_date, end_date=end_date)
    
    if limit:
        tickets = tickets[:limit]
    
    results = [calculate_dread_score(t) for t in tickets]
    
    return sorted(results, key=lambda x: x.total_score, reverse=True)


def classify_stride(
    client: Optional[AxurClient] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30
) -> List[StrideResult]:
    """
    Classify tickets into STRIDE threat categories.
    
    STRIDE is a threat modeling framework that categorizes threats into:
    - Spoofing: Impersonating something or someone else
    - Tampering: Modifying data or code
    - Repudiation: Claiming to not have performed an action
    - Information Disclosure: Exposing information to unauthorized parties
    - Denial of Service: Disrupting service availability
    - Elevation of Privilege: Gaining elevated access
    
    Args:
        client: AxurClient instance.
        start_date: Start of analysis period.
        end_date: End of analysis period.
        days_back: Days to look back if dates not specified.
    
    Returns:
        List of StrideResult objects sorted by count.
    
    Example:
        categories = classify_stride(days_back=90)
        for cat in categories:
            print(f"{cat.name}: {cat.count} ({cat.percentage:.1f}%)")
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    tickets = client.get_tickets(start_date=start_date, end_date=end_date)
    
    # Count by STRIDE category
    category_data: Dict[str, Dict] = {
        cat: {"count": 0, "types": set()}
        for cat in STRIDE_NAMES
    }
    total = 0
    
    for ticket in tickets:
        ticket_type = ticket.get("detection", {}).get("type", "unknown")
        category = STRIDE_MAPPING.get(ticket_type, "I")  # Default to Info Disclosure
        
        category_data[category]["count"] += 1
        category_data[category]["types"].add(ticket_type)
        total += 1
    
    # Build results
    results = []
    for cat, data in category_data.items():
        if data["count"] > 0:
            results.append(StrideResult(
                category=cat,
                name=STRIDE_NAMES[cat],
                count=data["count"],
                percentage=(data["count"] / total * 100) if total > 0 else 0,
                threat_types=list(data["types"])
            ))
    
    return sorted(results, key=lambda x: x.count, reverse=True)
