# Risk Scoring Use Case
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.interfaces import UseCase
from core.axur_client import AxurClient
from .calculator import calculate_risk_score

class RiskScoringUseCase(UseCase):
    @property
    def name(self) -> str:
        return "RISK SCORE v3.0 (KRI)"
        
    @property
    def description(self) -> str:
        return "Executive view: Single score 0-1000 vs Market Benchmark"
        
    def run(self, client: AxurClient) -> None:
        print("\n" + "=" * 65)
        print("  RISK SCORE v3.0 (KRI)")
        print("=" * 65)
        
        # Simple date selection (defaults to 30 days for demo flow)
        end = datetime.now()
        start = end - timedelta(days=30)
        print(f"  Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        print("\n  Calculating risk score...")
        
        result = calculate_risk_score(
            client=client,
            start_date=start,
            end_date=end
        )
        
        print(f"""
  ╔═══════════════════════════════════════════════════════════╗
  ║  FINAL SCORE: {result.score:>4}  │  GRADE: {result.grade}                        ║
  ╚═══════════════════════════════════════════════════════════╝
  
  Status: {result.status}
  
  Summary:
    • Total incidents: {result.total_incidents}
    • Weighted score: {result.weighted_score}
    • Benchmark ratio: {result.benchmark_ratio:.2f}x
    • Stealer factor: +{result.stealer_factor * 100:.0f}%
    • Efficiency: {result.efficiency_pct:.0f}%
""")
        
        if result.breakdown:
            print("  Top threat types:")
            sorted_types = sorted(
                result.breakdown.items(), 
                key=lambda x: x[1]["score"], 
                reverse=True
            )[:5]
            for t_type, info in sorted_types:
                print(f"    • {t_type}: {info['count']} incidents ({info['score']} pts)")
        
        input("\n  Press ENTER to continue...")
