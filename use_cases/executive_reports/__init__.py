# Executive Reports Use Case
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.interfaces import UseCase
from core.axur_client import AxurClient
from .generator import analyze_dread, classify_stride

class ExecutiveReportsUseCase(UseCase):
    @property
    def name(self) -> str:
        return "COMPLETE REPORT (DREAD + STRIDE)"
        
    @property
    def description(self) -> str:
        return "Full analysis: Risk Prioritization & Threat Categorization"
        
    def run(self, client: AxurClient) -> None:
        end = datetime.now()
        start = end - timedelta(days=30)
        
        print("\n" + "=" * 65)
        print("  EXECUTIVE REPORT GENERATOR")
        print("=" * 65)
        print(f"  Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        # Run DREAD
        print("\n  [1/2] Running DREAD Analysis...")
        results_dread = analyze_dread(client=client, start_date=start, end_date=end, limit=10)
        if results_dread:
            print(f"\n  Found {len(results_dread)} high-priority tickets:")
            print(f"  {'KEY':<12} │ {'TYPE':<25} │ {'SCORE':<6} │ PRIORITY")
            print(f"  {'─' * 60}")
            for r in results_dread[:5]:
                print(f"  {r.ticket_key:<12} │ {r.ticket_type[:25]:<25} │ {r.total_score:<6} │ {r.priority}")
        else:
            print("  No significant threats found for DREAD analysis.")

        # Run STRIDE
        print("\n  [2/2] Running STRIDE Classification...")
        results_stride = classify_stride(client=client, start_date=start, end_date=end)
        
        if results_stride:
            print("\n  Threat distribution by category:\n")
            for r in results_stride:
                bar_len = int(r.percentage / 5)
                bar = "█" * bar_len
                print(f"  {r.category} │ {r.name[:35]:<35}")
                print(f"    │ {bar} {r.count} ({r.percentage:.1f}%)")
        else:
            print("  No data available for STRIDE classification.")
            
        input("\n  Press ENTER to continue...")
