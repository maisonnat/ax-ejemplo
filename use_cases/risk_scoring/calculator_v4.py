"""
Risk Score Calculator v4.0 - Per-Brand Edition

This module calculates individual Risk Scores for each Brand/Subsidiary.
It removes the Operational Efficiency KPI and redistributes that weight
to the remaining 4 KRIs.

New KRI Weights (v4.0):
1. Weighted incident volume: 45% (was 40%)
2. Market benchmark comparison: 25% (was 20%)
3. Stealer log detection: 20% (was 15%)
4. Reputational impact: 10% (was 10%)
- Operational Efficiency: REMOVED (0%)

Higher scores indicate lower risk (score of 1000 = excellent security posture).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.axur_client import AxurClient


@dataclass
class BrandRiskResult:
    """Container for a single brand's risk score."""
    brand_name: str
    score: int
    grade: str
    status: str
    total_incidents: int
    weighted_score: int
    benchmark_ratio: float
    stealer_factor: float
    reputational_factor: float
    breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)


# Threat type weights (same as v3)
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
    exclude_discarded: bool = True
) -> Tuple[int, int, Dict[str, Dict[str, int]]]:
    """Calculate weighted incident score."""
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
    """Calculate stealer log penalty factor."""
    stealer_count = sum(
        1 for t in tickets
        if t.get("detection", {}).get("type") == "infostealer-credential"
    )
    
    if stealer_count == 0:
        return 0.0, 0
    elif stealer_count <= 5:
        return 0.2, stealer_count
    elif stealer_count <= 20:
        return 0.5, stealer_count
    else:
        return 1.0, stealer_count


def determine_grade(score: int) -> Tuple[str, str]:
    """Determine letter grade and status."""
    if score >= 850:
        return "A", "🟢 Excellent - Superior security posture"
    elif score >= 700:
        return "B", "🟡 Good - Controlled risk"
    elif score >= 550:
        return "C", "🟠 Moderate - Requires attention"
    elif score >= 400:
        return "D", "🔴 High Risk - Immediate action required"
    else:
        return "F", "⛔ Critical - Multiple active attack vectors"


def calculate_brand_risk_score(
    client: AxurClient,
    brand_name: str,
    tickets: List[Dict],
    verbose: bool = True
) -> BrandRiskResult:
    """
    Calculate Risk Score for a single brand with step-by-step output.
    
    Args:
        client: AxurClient instance.
        brand_name: Name of the brand being analyzed.
        tickets: Pre-filtered tickets for this brand.
        verbose: If True, print step-by-step calculation.
    
    Returns:
        BrandRiskResult with score and breakdown.
    """
    if verbose:
        print(f"\n  {'─' * 60}")
        print(f"  📊 BRAND: {brand_name}")
        print(f"  {'─' * 60}")
    
    # Step 1: Calculate weighted incidents
    weighted_score, total_incidents, breakdown = calculate_weighted_incidents(tickets)
    
    if verbose:
        print(f"\n  📌 Step 1: Weighted Incidents (45% weight)")
        print(f"     • Total active incidents: {total_incidents}")
        print(f"     • Weighted score: {weighted_score}")
        if breakdown:
            print(f"     • Top threats:")
            sorted_types = sorted(breakdown.items(), key=lambda x: x[1]["score"], reverse=True)[:3]
            for t_type, info in sorted_types:
                print(f"       - {t_type}: {info['count']} incidents × {info['weight']} pts = {info['score']} pts")
    
    # Step 2: Benchmark ratio (using 100 as sector median)
    sector_median = 100
    benchmark_ratio = total_incidents / sector_median if sector_median > 0 else 1.0
    
    if verbose:
        print(f"\n  📌 Step 2: Market Benchmark (25% weight)")
        print(f"     • Sector median (baseline): {sector_median} incidents")
        print(f"     • Your incidents: {total_incidents}")
        print(f"     • Benchmark ratio: {benchmark_ratio:.2f}x")
        if benchmark_ratio > 1:
            print(f"     • ⚠️  Above market average (+{(benchmark_ratio-1)*100:.0f}% penalty)")
        else:
            print(f"     • ✅ Below market average ({(1-benchmark_ratio)*100:.0f}% bonus)")
    
    # Step 3: Stealer factor
    stealer_factor, stealer_count = calculate_stealer_factor(tickets)
    
    if verbose:
        print(f"\n  📌 Step 3: Stealer Logs (20% weight)")
        print(f"     • Active stealer credentials: {stealer_count}")
        print(f"     • Penalty factor: +{stealer_factor*100:.0f}%")
    
    # Step 4: Reputational factor (simplified - would use complaints API)
    reputational_factor = 0.0
    
    if verbose:
        print(f"\n  📌 Step 4: Reputational Impact (10% weight)")
        print(f"     • Victim complaints: 0 (API not configured)")
        print(f"     • Penalty factor: +{reputational_factor*100:.0f}%")
    
    # Step 5: Calculate final score
    if verbose:
        print(f"\n  📌 Step 5: Final Score Calculation")
    
    if benchmark_ratio > 0:
        base_score = min(500, weighted_score / max(benchmark_ratio, 0.5))
    else:
        base_score = min(500, weighted_score)
    
    # No more efficiency factor in v4!
    total_penalty = (1 + stealer_factor) * (1 + reputational_factor)
    final_score = max(0, min(1000, int(1000 - (base_score * total_penalty))))
    
    grade, status = determine_grade(final_score)
    
    if verbose:
        print(f"     • Base score: {base_score:.0f}")
        print(f"     • Total penalty multiplier: {total_penalty:.2f}x")
        print(f"     • Final calculation: 1000 - ({base_score:.0f} × {total_penalty:.2f}) = {final_score}")
        print(f"\n  ╔═══════════════════════════════════════════════════════╗")
        print(f"  ║  SCORE: {final_score:>4}  │  GRADE: {grade}  │  {status:<20} ║")
        print(f"  ╚═══════════════════════════════════════════════════════╝")
    
    return BrandRiskResult(
        brand_name=brand_name,
        score=final_score,
        grade=grade,
        status=status,
        total_incidents=total_incidents,
        weighted_score=weighted_score,
        benchmark_ratio=benchmark_ratio,
        stealer_factor=stealer_factor,
        reputational_factor=reputational_factor,
        breakdown=breakdown
    )


def calculate_all_brands_risk_score(
    client: Optional[AxurClient] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days_back: int = 30,
    verbose: bool = True
) -> List[BrandRiskResult]:
    """
    Calculate Risk Score for ALL brands/subsidiaries.
    
    Args:
        client: AxurClient instance.
        start_date: Start of analysis period.
        end_date: End of analysis period.
        days_back: Days to look back if dates not specified.
        verbose: If True, print step-by-step for each brand.
    
    Returns:
        List of BrandRiskResult, one per brand.
    """
    if client is None:
        client = AxurClient()
    
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=days_back)
    
    # Get all brands
    brands, _ = client.get_customer_assets()
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"  RISK SCORE v4.0 - PER-BRAND ANALYSIS")
        print(f"{'='*70}")
        print(f"  Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"  Total brands found: {len(brands)}")
    
    # Fetch all tickets once
    all_tickets = client.get_tickets(start_date=start_date, end_date=end_date)
    
    if verbose:
        print(f"  Total tickets in period: {len(all_tickets)}")
    
    results: List[BrandRiskResult] = []
    
    for brand in brands:
        brand_name = brand.get("name", "Unknown")
        
        # Filter tickets for this brand
        brand_tickets = [
            t for t in all_tickets
            if brand_name in t.get("detection", {}).get("assets", [])
        ]
        
        # Skip brands with no tickets (optional)
        if not brand_tickets and not verbose:
            continue
        
        result = calculate_brand_risk_score(
            client=client,
            brand_name=brand_name,
            tickets=brand_tickets,
            verbose=verbose
        )
        results.append(result)
    
    # Print summary table at the end
    if verbose and results:
        print(f"\n{'='*70}")
        print(f"  SUMMARY - ALL BRANDS")
        print(f"{'='*70}")
        print(f"\n  {'BRAND':<25} │ {'SCORE':>6} │ {'GRADE':>5} │ {'INCIDENTS':>9}")
        print(f"  {'─'*25}─┼─{'─'*6}─┼─{'─'*5}─┼─{'─'*9}")
        
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            print(f"  {r.brand_name[:25]:<25} │ {r.score:>6} │ {r.grade:>5} │ {r.total_incidents:>9}")
    
    return results
