"""
Example: Per-Brand Risk Score Calculation

This script demonstrates the Risk Score v4.0 methodology which
calculates an individual score for each Brand/Subsidiary in the tenant.

Key differences from v3.0:
- Calculates per-brand (not aggregate)
- Removes Operational Efficiency KPI
- Shows step-by-step calculation for each brand
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.axur_client import AxurClient
from use_cases.risk_scoring.calculator_v4 import calculate_all_brands_risk_score


def main():
    print("Initializing Axur Client...")
    client = AxurClient()
    
    print(f"Customer: {client.customer_id}")
    print("Starting Per-Brand Risk Score calculation...\n")
    
    # Calculate for all brands with verbose output
    results = calculate_all_brands_risk_score(
        client=client,
        days_back=30,
        verbose=True
    )
    
    print(f"\nAnalysis complete. {len(results)} brands analyzed.")


if __name__ == "__main__":
    main()
