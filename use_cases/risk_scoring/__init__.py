# Risk Scoring Use Case
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.interfaces import UseCase
from core.axur_client import AxurClient
from .calculator import calculate_risk_score_per_brand

class RiskScoringUseCase(UseCase):
    @property
    def name(self) -> str:
        return "RISK SCORE v3.0 (KRI)"
        
    @property
    def description(self) -> str:
        return "Executive view: Score per Brand (0-1000)"
        
    def run(self, client: AxurClient) -> None:
        print("\n" + "=" * 65)
        print("  RISK SCORE v3.0 (KRI) - Per Brand Analysis")
        print("=" * 65)
        
        # Simple date selection (defaults to 30 days for demo flow)
        end = datetime.now()
        start = end - timedelta(days=30)
        
        # Call the new per-brand calculator
        results = calculate_risk_score_per_brand(
            client=client,
            start_date=start,
            end_date=end,
            verbose=True # Prints the step-by-step
        )
        
        print("\n" + "="*65)
        print(f"  FINAL SUMMARY TABLE")
        print("="*65)
        print(f"  {'BRAND':<30} | {'SCORE':<8} | {'GRADE':<5} | {'INCIDENTS'}")
        print("  " + "-" * 60)
        
        for r in sorted(results, key=lambda x: x.score):
            print(f"  {r.brand_name[:30]:<30} | {r.score:<8} | {r.grade:<5} | {r.total_incidents}")
            
        print("\n  Note: Calculation based on 'incident.date' (Confirmed Threats).")
        input("\n  Press ENTER to continue...")
