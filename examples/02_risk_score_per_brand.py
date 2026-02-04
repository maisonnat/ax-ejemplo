"""
Example: Calculate Risk Score Per Brand (Filial)

This example demonstrates how to calculate the Risk Score v3.0 for each brand
individually, using the "incident.date" filter to count only confirmed threats.

Updated Logic:
- Filters by 'incident.date' (Confirmed threats only)
- Removes 'Operational Efficiency' KPI
- Redistributes weights: 45% Incidents, 25% Benchmark, 20% Stealer
"""

import sys
import os

# Ensure we can find the 'core' and 'use_cases' modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.axur_client import create_client
from use_cases.risk_scoring.calculator import calculate_risk_score_per_brand

def main():
    print("Initializing Axur Client...")
    # Requires API Key in config.json or environment variable
    client = create_client()
    
    print("\nStarting Risk Score Calculation (Per Brand)...")
    print("------------------------------------------------")
    
    # Calculate for last 30 days
    # verbose=True prints the step-by-step logic
    results = calculate_risk_score_per_brand(client=client, days_back=30, verbose=True)
    
    print("\n" + "="*60)
    print(f"  FINAL SUMMARY: {len(results)} BRANDS EVALUATED")
    print("="*60)
    print(f"{'BRAND':<30} | {'SCORE':<10} | {'GRADE':<5} | {'INCIDENTS'}")
    print("-" * 60)
    
    for r in sorted(results, key=lambda x: x.score):
        print(f"{r.brand_name[:30]:<30} | {r.score:<10} | {r.grade:<5} | {r.total_incidents}")

if __name__ == "__main__":
    main()
