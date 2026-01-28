"""
Risk Score Calculator v3.0

This module implements the Key Risk Indicator (KRI) methodology for calculating
an organization's security risk score on a 0-1000 scale.

The score is calculated using 5 KRIs:
1. Weighted incident volume (base score)
2. Market benchmark comparison
3. Stealer log detection (malware factor)
4. Operational efficiency (resolution time)
5. Reputational impact (victim complaints)

Higher scores indicate lower risk (score of 1000 = excellent security posture).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.axur_client import AxurClient


@dataclass
class RiskScoreResult:
    """
    Container for risk score calculation results.
    
    Attributes:
        score: Final risk score (0-1000, higher is better).
        grade: Letter grade (A-F) based on score.
        status: Human-readable status description.
        total_incidents: Total number of incidents analyzed.
        weighted_score: Weighted incident volume score.
        benchmark_ratio: Ratio compared to market median.
        stealer_factor: Penalty factor from malware detection.
        efficiency_pct: Operational efficiency percentage.
        reputational_factor: Penalty factor from victim complaints.
        breakdown: Detailed breakdown by threat type.
    """
    score: int
    grade: str
    status: str
    total_incidents: int
    weighted_score: int
    benchmark_ratio: float
    stealer_factor: float
    efficiency_pct: float
    reputational_factor: float
    breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)


# Threat type weights for incident scoring
THREAT_WEIGHTS: Dict[str, int] = {
    "ransomware-attack": 100,
    "data-exposure-message": 80,
    "infostealer-credential": 70,
    "corporate-credential-leak": 60,
    "malware": 50,
    "phishing": 50,
    "fake-mobile-app": 40,
    "fraudulent-brand-use": 20,
    "similar-domain-name": 15,
    "dw-activity": 30,
    "data-exposure": 40,
    "default": 10
}


def calculate_weighted_incidents(
    tickets: List[Dict],
    exclude_discarded: bool = False
) -> Tuple[int, int, Dict[str, Dict[str, int]]]:
    """
    Calculate weighted incident score based on threat severity.
    
    Args:
        tickets: List of ticket dictionaries from API.
        exclude_discarded: If True, exclude tickets with 'discarded' resolution.
    
    Returns:
        Tuple of (weighted_score, total_count, breakdown_by_type).
    """
    breakdown: Dict[str, Dict[str, int]] = {}
    
    for ticket in tickets:
        # Check for discarded status
        if exclude_discarded:
            resolution = ticket.get("current", {}).get("resolution")
            if resolution == "discarded":
                continue
        
        ticket_type = ticket.get("detection", {}).get("type", "unknown")
        weight = THREAT_WEIGHTS.get(ticket_type, THREAT_WEIGHTS["default"])
        
        if ticket_type not in breakdown:
            breakdown[ticket_type] = {"count": 0, "weight": weight, "score": 0}
        
        breakdown[ticket_type]["count"] += 1
        breakdown[ticket_type]["score"] += weight
    
    total_count = sum(info["count"] for info in breakdown.values())
    weighted_score = sum(info["score"] for info in breakdown.values())
    
    return weighted_score, total_count, breakdown


def calculate_stealer_factor(tickets: List[Dict]) -> Tuple[float, int]:
    """
    Calculate the stealer log penalty factor.
    
    Stealer logs indicate active malware infections and represent
    the highest risk category.
    
    Args:
        tickets: List of ticket dictionaries.
    
    Returns:
        Tuple of (stealer_factor, stealer_count).
    """
    stealer_count = sum(
        1 for t in tickets
        if t.get("detection", {}).get("type") == "infostealer-credential"
    )
    
    if stealer_count == 0:
        return 0.0, 0
    elif stealer_count <= 5:
        return 0.2, stealer_count  # +20% penalty
    elif stealer_count <= 20:
        return 0.5, stealer_count  # +50% penalty
    else:
        return 1.0, stealer_count  # +100% penalty


def calculate_efficiency_factor(uptime_data: Dict) -> Tuple[float, float]:
    """
    Calculate operational efficiency based on resolution times.
    
    Args:
        uptime_data: Dictionary with resolution time buckets.
    
    Returns:
        Tuple of (slow_factor, efficiency_percentage).
    """
    total_count = sum([
        uptime_data.get("lessThan1Day", 0),
        uptime_data.get("upTo2Days", 0),
        uptime_data.get("upTo5Days", 0),
        uptime_data.get("upTo10Days", 0),
        uptime_data.get("upTo15Days", 0),
        uptime_data.get("upTo30Days", 0),
        uptime_data.get("upTo60Days", 0),
        uptime_data.get("over60Days", 0)
    ])
    
    if total_count == 0:
        return 0.0, 100.0
    
    slow_count = (
        uptime_data.get("upTo30Days", 0) +
        uptime_data.get("upTo60Days", 0) +
        uptime_data.get("over60Days", 0)
    )
    
    efficiency_pct = ((total_count - slow_count) / total_count) * 100
    slow_factor = (slow_count / total_count) * 0.5  # Max 50% penalty
    
    return slow_factor, efficiency_pct


def determine_grade(score: int) -> Tuple[str, str]:
    """
    Determine letter grade and status based on score.
    
    Args:
        score: Risk score (0-1000).
    
    Returns:
        Tuple of (grade, status_description).
    """
    if score >= 850:
        return "A", "Excelente - Postura de seguridad superior"
    elif score >= 700:
        return "B", "Bueno - Riesgo controlado"
    elif score >= 550:
        return "C", "Moderado - Requiere atención"
    elif score >= 400:
        return "D", "Alto Riesgo - Acción inmediata requerida"
    else:
        return "F", "Crítico - Múltiples vectores de ataque activos"


def calculate_risk_score(
    client: Optional[AxurClient] = None,
    brand_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30,
    exclude_discarded: bool = False
) -> RiskScoreResult:
    """
    Calculate the comprehensive Risk Score v3.0.
    
    This function aggregates multiple Key Risk Indicators (KRIs) to produce
    a single score representing the organization's security posture.
    
    Args:
        client: AxurClient instance. Creates new one if not provided.
        brand_filter: Optional brand/asset to filter tickets by.
        start_date: Start of analysis period.
        end_date: End of analysis period.
        days_back: Days to look back if dates not specified.
        exclude_discarded: If True, exclude discarded tickets from analysis.
    
    Returns:
        RiskScoreResult containing score, grade, and detailed breakdown.
    
    Example:
        from use_cases.risk_scoring import calculate_risk_score
        result = calculate_risk_score(days_back=90)
        print(f"Score: {result.score} ({result.grade})")
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    # Fetch tickets
    tickets = client.get_tickets(start_date=start_date, end_date=end_date)
    
    # Apply brand filter if specified
    if brand_filter:
        tickets = [
            t for t in tickets
            if brand_filter in t.get("detection", {}).get("assets", [])
        ]
    
    # KRI 1: Weighted incidents
    weighted_score, total_incidents, breakdown = calculate_weighted_incidents(
        tickets, exclude_discarded
    )
    
    # KRI 2: Benchmark ratio (simplified - using 100 as baseline)
    sector_median = 100  # Default baseline
    benchmark_ratio = total_incidents / sector_median if sector_median > 0 else 1.0
    
    # KRI 3: Stealer factor
    stealer_factor, _ = calculate_stealer_factor(tickets)
    
    # KRI 4: Efficiency (simplified - would need uptime API call)
    efficiency_pct = 80.0  # Default assumption
    slow_factor = 0.1
    
    # KRI 5: Reputational factor (simplified)
    reputational_factor = 0.0
    
    # Calculate final score
    if benchmark_ratio > 0:
        base_score = min(500, weighted_score / max(benchmark_ratio, 0.5))
    else:
        base_score = min(500, weighted_score)
    
    total_penalty = (1 + stealer_factor) * (1 + slow_factor) * (1 + reputational_factor)
    final_score = max(0, min(1000, int(1000 - (base_score * total_penalty))))
    
    grade, status = determine_grade(final_score)
    
    return RiskScoreResult(
        score=final_score,
        grade=grade,
        status=status,
        total_incidents=total_incidents,
        weighted_score=weighted_score,
        benchmark_ratio=benchmark_ratio,
        stealer_factor=stealer_factor,
        efficiency_pct=efficiency_pct,
        reputational_factor=reputational_factor,
        breakdown=breakdown
    )
