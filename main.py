"""
Axur Risk Assessment Toolkit v4.0

A comprehensive toolkit for security risk assessment using the Axur Platform API.
This application provides interactive analysis tools for security teams and executives.

Features:
    - Dynamic Use Case Loader (Library Architecture)
    - Plug-and-Play Extensibility
    - Enterprise-grade API Connector

Usage:
    python main.py

For more information, see README.md.
"""

import sys
from typing import List

# Configure encoding for Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Import Core
from core.axur_client import AxurClient
from core.utils import configure_encoding
from core.interfaces import UseCase

# Import Librarian
from use_cases import get_available_use_cases


def show_banner() -> None:
    """Display application banner."""
    print("=" * 70)
    print("  ╔════════════════════════════════════════════════════════════════╗")
    print("  ║       AXUR RISK ASSESSMENT v4.0 - Enterprise Edition          ║")
    print("  ╚════════════════════════════════════════════════════════════════╝")
    print("=" * 70)


def show_menu(use_cases: List[UseCase]) -> None:
    """Display dynamic main menu options."""
    print("\n  Select the analysis type you want to run:\n")
    print("  ┌─────────────────────────────────────────────────────────────────┐")
    
    for i, uc in enumerate(use_cases, 1):
        print(f"  │  [{i}] {uc.name:<54} │")
        print(f"  │      {uc.description:<59}│")
        if i < len(use_cases):
            print("  ├─────────────────────────────────────────────────────────────────┤")
            
    print("  └─────────────────────────────────────────────────────────────────┘")
    print("\n  [0] Exit\n")


def main() -> None:
    """Main application entry point."""
    configure_encoding()
    
    # Initialize Client
    client = AxurClient()
    
    # Load Use Cases ( The Books in the Library )
    try:
        use_cases = get_available_use_cases()
        # Sort by name to ensure consistent order
        use_cases.sort(key=lambda x: x.name)
    except Exception as e:
        print(f"CRITICAL ERROR loading use cases: {e}")
        return
    
    while True:
        show_banner()
        show_menu(use_cases)
        
        try:
            choice_str = input(f"  Select an option [0-{len(use_cases)}]: ").strip()
            
            if choice_str == "0":
                print("\n  👋 Goodbye!\n")
                break
                
            choice_idx = int(choice_str) - 1
            
            if 0 <= choice_idx < len(use_cases):
                selected_case = use_cases[choice_idx]
                selected_case.run(client)
            else:
                print("\n  ⚠️  Invalid option. Please try again.")
                
        except (ValueError, KeyboardInterrupt, EOFError):
            if isinstance(choice_str, str) and choice_str.lower() in ['exit', 'quit']:
                break
            print("\n  ⚠️  Invalid input.")


if __name__ == "__main__":
    main()
