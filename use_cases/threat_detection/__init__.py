# Threat Detection Use Case
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.interfaces import UseCase
from core.axur_client import AxurClient
from .onepixel import filter_by_origin, DETECTION_ORIGINS, get_origin_summary, export_to_csv

class ThreatDetectionUseCase(UseCase):
    @property
    def name(self) -> str:
        return "FILTER BY ORIGIN (OnePixel/API)"
        
    @property
    def description(self) -> str:
        return "Search tickets by source (OnePixel, API, Platform)"
        
    def run(self, client: AxurClient) -> None:
        print("\n" + "=" * 65)
        print("  FILTER BY DETECTION ORIGIN")
        print("=" * 65)
        
        print("\n  Available detection origins:")
        origins = list(DETECTION_ORIGINS.keys())
        for i, origin in enumerate(origins, 1):
            desc = DETECTION_ORIGINS[origin]
            print(f"    [{i}] {origin.capitalize():<10} - {desc}")
        print("    [0] Cancel")
        
        try:
            choice = int(input("\n  Select origin #: "))
            if choice == 0 or choice > len(origins):
                return
            
            selected_origin = origins[choice - 1]
        except (ValueError, IndexError):
            print("  ⚠️  Invalid selection.")
            return
        
        # Simple date selection (defaults to 30 days)
        end = datetime.now()
        start = end - timedelta(days=30)
        
        print(f"\n  🔍 Searching for tickets with origin '{selected_origin}'...")
        
        tickets = filter_by_origin(
            client=client,
            origin=selected_origin,
            start_date=start,
            end_date=end
        )
        
        if not tickets:
            print(f"  ℹ️  No tickets found with origin '{selected_origin}' in the period.")
            return
        
        print(f"\n  ✅ Found {len(tickets)} tickets detected by {selected_origin.upper()}")
        
        # Summary by type
        summary = get_origin_summary(tickets)
        print("\n  Summary by type:")
        for t_type, count in sorted(summary.items(), key=lambda x: -x[1])[:10]:
            print(f"    • {t_type}: {count}")
            
        print("\n  For full details, please check the CSV export option in the main menu (Legacy Mode).")
        input("\n  Press ENTER to continue...")
