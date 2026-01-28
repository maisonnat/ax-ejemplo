"""
Axur Risk Assessment Toolkit v4.0

A comprehensive toolkit for security risk assessment using the Axur Platform API.
This application provides interactive analysis tools for security teams and executives.

Features:
    - Risk Score v3.0 (KRI methodology)
    - DREAD threat prioritization
    - STRIDE threat classification
    - OnePixel detection analysis
    - Credential exposure monitoring

Usage:
    python main.py

For more information, see README.md.
"""

import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Configure encoding for Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Import modules
from core.axur_client import AxurClient
from core.utils import configure_encoding
from use_cases.risk_scoring.calculator import calculate_risk_score
from use_cases.threat_detection.onepixel import (
    filter_by_origin, 
    DETECTION_ORIGINS,
    get_origin_summary,
    format_ticket_list,
    export_to_csv
)
from use_cases.executive_reports.generator import analyze_dread, classify_stride


def show_banner() -> None:
    """Display application banner."""
    print("=" * 70)
    print("  ╔════════════════════════════════════════════════════════════════╗")
    print("  ║       AXUR RISK ASSESSMENT v4.0 - Enterprise Edition          ║")
    print("  ╚════════════════════════════════════════════════════════════════╝")
    print("=" * 70)


def show_menu() -> None:
    """Display main menu options."""
    print("""
  Select the analysis type you want to run:

  ┌─────────────────────────────────────────────────────────────────┐
  │  [1] RISK SCORE v3.0 (KRI)                                      │
  │      📊 Executive view: Single score 0-1000                     │
  │      Compare your posture vs market. Ideal for reports.         │
  ├─────────────────────────────────────────────────────────────────┤
  │  [2] DREAD ANALYSIS                                             │
  │      🎯 Prioritization: Which incidents to address first?       │
  │      Individual score per ticket based on impact.               │
  ├─────────────────────────────────────────────────────────────────┤
  │  [3] STRIDE CLASSIFICATION                                      │
  │      📈 Threat matrix: What attack types dominate?              │
  │      Group incidents into 6 strategic categories.               │
  ├─────────────────────────────────────────────────────────────────┤
  │  [4] COMPLETE REPORT                                            │
  │      📋 Run all 3 analyses above                                │
  ├─────────────────────────────────────────────────────────────────┤
  │  [5] FILTER BY DETECTION ORIGIN                                 │
  │      📡 Search tickets by source (OnePixel, API, Platform)      │
  └─────────────────────────────────────────────────────────────────┘

  [0] Exit
""")


def get_date_range() -> Tuple[datetime, datetime]:
    """
    Prompt user to select a date range.
    
    Returns:
        Tuple of (start_date, end_date).
    """
    print("\n  📅 Date Range Selection:")
    print("    [1] Last 7 days")
    print("    [2] Last 30 days (Default)")
    print("    [3] Last 90 days")
    print("    [4] Custom (YYYY-MM-DD)")
    
    choice = input("\n  Option [1-4] (Enter = 30 days): ").strip()
    
    end = datetime.now()
    
    if choice == "1":
        start = end - timedelta(days=7)
    elif choice == "3":
        start = end - timedelta(days=90)
    elif choice == "4":
        try:
            s_str = input("    Start date (YYYY-MM-DD): ").strip()
            e_str = input("    End date   (YYYY-MM-DD): ").strip()
            start = datetime.strptime(s_str, "%Y-%m-%d")
            end = datetime.strptime(f"{e_str} 23:59:59", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print("  ⚠️  Invalid format. Using 30 days.")
            start = end - timedelta(days=30)
    else:
        start = end - timedelta(days=30)
    
    return start, end


def run_risk_score(client: AxurClient, start: datetime, end: datetime) -> None:
    """Execute Risk Score v3.0 analysis."""
    print("\n" + "=" * 65)
    print("  RISK SCORE v3.0 (KRI)")
    print("=" * 65)
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


def run_dread_analysis(client: AxurClient, start: datetime, end: datetime) -> None:
    """Execute DREAD analysis."""
    print("\n" + "=" * 65)
    print("  DREAD ANALYSIS - Risk Prioritization")
    print("=" * 65)
    print(f"  Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print("\n  Analyzing threats...")
    
    results = analyze_dread(
        client=client,
        start_date=start,
        end_date=end,
        limit=20
    )
    
    if not results:
        print("\n  ⚠️  No tickets found in the specified period.")
        return
    
    print(f"\n  Found {len(results)} tickets. Top 10 by risk:\n")
    print(f"  {'KEY':<12} │ {'TYPE':<25} │ {'SCORE':<6} │ PRIORITY")
    print(f"  {'─' * 60}")
    
    for r in results[:10]:
        print(f"  {r.ticket_key:<12} │ {r.ticket_type[:25]:<25} │ {r.total_score:<6} │ {r.priority}")


def run_stride_classification(client: AxurClient, start: datetime, end: datetime) -> None:
    """Execute STRIDE classification."""
    print("\n" + "=" * 65)
    print("  STRIDE CLASSIFICATION - Threat Categories")
    print("=" * 65)
    print(f"  Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print("\n  Classifying threats...")
    
    results = classify_stride(
        client=client,
        start_date=start,
        end_date=end
    )
    
    if not results:
        print("\n  ⚠️  No tickets found in the specified period.")
        return
    
    print("\n  Threat distribution by category:\n")
    
    for r in results:
        bar_len = int(r.percentage / 5)  # Scale to 20 chars max
        bar = "█" * bar_len
        print(f"  {r.category} │ {r.name[:35]:<35}")
        print(f"    │ {bar} {r.count} ({r.percentage:.1f}%)")
        print()


def run_origin_filter(client: AxurClient) -> None:
    """Filter tickets by detection origin."""
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
    
    start, end = get_date_range()
    
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
    
    # Optional: Show ticket details
    print("\n  Show ticket details? (for platform verification)")
    show_details = input("  [Y/n]: ").strip().lower()
    
    if show_details in ["y", "yes", "s", "si", ""]:
        formatted = format_ticket_list(tickets)
        
        print(f"\n  {'─' * 60}")
        print(f"  {'KEY':<15} │ {'TYPE':<25} │ {'DATE':<12}")
        print(f"  {'─' * 60}")
        
        for t in formatted[:15]:
            print(f"  {t['key']:<15} │ {t['type'][:25]:<25} │ {t['date']:<12}")
        
        if len(formatted) > 15:
            print(f"\n  ... and {len(formatted) - 15} more tickets")
        
        print(f"  {'─' * 60}")
        
        # Optional: Export to CSV
        export = input("\n  Export to CSV? [y/N]: ").strip().lower()
        if export in ["y", "yes", "s", "si"]:
            filename = f"tickets_{selected_origin}_{start.strftime('%Y%m%d')}"
            filepath = export_to_csv(tickets, filename, selected_origin)
            print(f"  ✅ Exported to: {filepath}")


def main() -> None:
    """Main application entry point."""
    configure_encoding()
    
    client = AxurClient()
    
    while True:
        show_banner()
        show_menu()
        
        try:
            choice = input("  Select an option [0-5]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        
        if choice == "0":
            print("\n  👋 Goodbye!\n")
            break
        
        elif choice == "1":
            start, end = get_date_range()
            run_risk_score(client, start, end)
            input("\n  Press ENTER to continue...")
        
        elif choice == "2":
            start, end = get_date_range()
            run_dread_analysis(client, start, end)
            input("\n  Press ENTER to continue...")
        
        elif choice == "3":
            start, end = get_date_range()
            run_stride_classification(client, start, end)
            input("\n  Press ENTER to continue...")
        
        elif choice == "4":
            start, end = get_date_range()
            print("\n  Running complete report...\n")
            run_risk_score(client, start, end)
            run_dread_analysis(client, start, end)
            run_stride_classification(client, start, end)
            input("\n  Press ENTER to continue...")
        
        elif choice == "5":
            run_origin_filter(client)
            input("\n  Press ENTER to continue...")
        
        else:
            print("\n  ⚠️  Invalid option. Please try again.")


if __name__ == "__main__":
    main()
