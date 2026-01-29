"""
Example 01: Hello Axur

This simple script demonstrates how to connect to the Axur API 
and fetch your basic customer information.
"""

import sys
import os

# Add parent directory to path to use the core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.axur_client import AxurClient

def main():
    print("Connecting to Axur Platform...")
    
    # 1. Initialize Client (Load API Key from config.json)
    try:
        client = AxurClient()
    except Exception as e:
        print(f"Error: {e}")
        return

    # 2. Verify Connection
    print(f"✅ Authenticated as Customer ID: {client.customer_id}")
    
    # 3. Get Assets (Brands/Domains)
    print("\nRequesting Customer Assets...")
    brands, domains = client.get_customer_assets()
    
    print(f"Found {len(brands)} Brands and {len(domains)} Domains monitored.")
    
    if brands:
        print(f"\nExample Brand: {brands[0]['name']}")

if __name__ == "__main__":
    main()
