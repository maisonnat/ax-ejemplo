"""
Risk Score Calculator v3.0

This module implements the Key Risk Indicator (KRI) methodology for calculating
an organization's security risk score on a 0-1000 scale.

The score is calculated using 4 KRIs (Redistributed Weights):
1. Weighted incident volume (45%)
2. Market benchmark comparison (25%)
3. Stealer log detection (20%)
4. Reputational impact (10%)

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

@dataclass
class BrandRiskScore:
    """
    Container for per-brand risk score results.
    """
    brand_name: str
    score: int
    grade: str
    total_incidents: int
    weighted_score: int
    stealer_count: int
    breakdown: Dict[str, Dict[str, int]]


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
    """
    breakdown: Dict[str, Dict[str, int]] = {}
    
    for ticket in tickets:
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


def determine_grade(score: int) -> Tuple[str, str]:
    """
    Determine letter grade and status based on score.
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


def calculate_risk_score_per_brand(
    client: Optional[AxurClient] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30,
    verbose: bool = True
) -> List[BrandRiskScore]:
    """
    Calculate Risk Score for each brand individually.
    
    Args:
        client: AxurClient instance.
        start_date: Start of analysis period.
        end_date: End of analysis period.
        days_back: Days to look back.
        verbose: Print step-by-step details.
        
    Returns:
        List of BrandRiskScore objects.
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
        
    if verbose:
        print(f"\n--- Risk Score Calculation Step-by-Step ---")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print("Using 'incident.date' to filter confirmed threats.\n")
    
    # 1. Get all brands
    brands, _ = client.get_customer_assets()
    results = []
    
    # 2. Get confirmed incidents for the whole tenant
    # Note: Fetching all tickets first to optimize calls, then filtering in memory
    all_tickets = client.get_tickets(
        start_date=start_date, 
        end_date=end_date, 
        date_field="incident.date" # CRITICAL: Only confirmed incidents
    )
    
    if verbose:
         print(f"Total confirmed incidents found for tenant: {len(all_tickets)}\n")

    for brand in brands:
        brand_name = brand["name"]
        brand_key = brand.get("key")
        
        # Robust filtering: Check Name or Key
        brand_tickets = []
        for t in all_tickets:
            assets = t.get("detection", {}).get("assets", [])
            # Normalize assets to strings if needed
            assets_str = [str(a).strip() for a in assets]
            
            if brand_name in assets_str:
                brand_tickets.append(t)
            elif brand_key and brand_key in assets_str:
                brand_tickets.append(t)
        
        if verbose:
            print(f"Evaluating Brand: {brand_name}")
            print(f"  > Incidents: {len(brand_tickets)}")
        
        # KRI 1: Weighted incidents (45%)
        # Logic: Higher weighted score -> Higher base penalty
        weighted_score, total_count, breakdown = calculate_weighted_incidents(brand_tickets)
        if verbose:
            print(f"  > Weighted Threat Score: {weighted_score}")
            
        # KRI 2: Benchmark (25%)
        # Simplified: Using 50 as brand-level median (assumed lower than tenant level)
        sector_median = 50 
        benchmark_ratio = total_count / sector_median if sector_median > 0 else 1.0
        
        # KRI 3: Stealer Factor (20%)
        stealer_factor, stealer_count = calculate_stealer_factor(brand_tickets)
        if verbose and stealer_count > 0:
             print(f"  > active Stealer Logs: {stealer_count} (Penalty: +{stealer_factor:.0%})")
        
        # KRI 4: Reputation (10%) - Placeholder
        reputational_factor = 0.0
        
        # Calculation
        # Base Score (0-500) derived from weighted incidents
        # Formula: The more incidents, the lower the base score (Higher penalty)
        if benchmark_ratio > 0:
            base_penalty = min(500, weighted_score / max(benchmark_ratio, 0.5))
        else:
            base_penalty = min(500, weighted_score)
            
        # Multipliers
        total_penalty_multiplier = (1 + stealer_factor) * (1 + reputational_factor)
        
        # Final Score
        final_penalty = base_penalty * total_penalty_multiplier
        final_score = max(0, min(1000, int(1000 - final_penalty)))
        
        grade, _ = determine_grade(final_score)
        
        if verbose:
             print(f"  > Final Score: {final_score} ({grade})\n")
        
        results.append(BrandRiskScore(
            brand_name=brand_name,
            score=final_score,
            grade=grade,
            total_incidents=total_count,
            weighted_score=weighted_score,
            stealer_count=stealer_count,
            breakdown=breakdown
        ))
        
    return results

def calculate_risk_score(
    client: Optional[AxurClient] = None,
    brand_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30,
    exclude_discarded: bool = False
) -> RiskScoreResult:
    """
    Legacy aggregated calculation. (Kept for compatibility, but logic updated slightly)
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    # UPDATED: Use incident.date by default even for legacy call
    tickets = client.get_tickets(
        start_date=start_date, 
        end_date=end_date,
        date_field="incident.date" 
    )
    
    if brand_filter:
        tickets = [
            t for t in tickets
            if brand_filter in t.get("detection", {}).get("assets", [])
        ]
    
    weighted_score, total_incidents, breakdown = calculate_weighted_incidents(
        tickets, exclude_discarded
    )
    
    sector_median = 100 
    benchmark_ratio = total_incidents / sector_median if sector_median > 0 else 1.0
    
    stealer_factor, _ = calculate_stealer_factor(tickets)
    
    # Efficiency is REMOVED/Disabled
    efficiency_pct = 0.0 
    slow_factor = 0.0
    
    reputational_factor = 0.0
    
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
        efficiency_pct=efficiency_pct, # Now 0
        reputational_factor=reputational_factor,
        breakdown=breakdown
    )
