"""
Axur API Client Module

This module provides a clean, reusable interface for interacting with the Axur Platform API.
It handles authentication, pagination, date formatting, and error handling.

Example:
    from core.axur_client import AxurClient
    
    client = AxurClient()
    tickets = client.get_tickets(days_back=30)
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


class AxurClient:
    """
    A client for interacting with the Axur Platform API.
    
    Handles authentication, pagination, and provides methods for common operations
    such as fetching tickets, credentials, and customer assets.
    
    Attributes:
        base_url: The base URL for the Axur API.
        customer_id: The customer identifier for API requests.
        page_size: Maximum number of items per API request (max 200).
    """
    
    DEFAULT_BASE_URL = "https://api.axur.com/gateway/1.0/api"
    MAX_PAGE_SIZE = 200
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        customer_id: Optional[str] = None,
        base_url: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the Axur client.
        
        Args:
            api_key: Axur API key. If not provided, loads from config.json.
            customer_id: Customer identifier. If not provided, loads from config.json.
            base_url: API base URL. Defaults to Axur's production endpoint.
            config_path: Path to config.json. Defaults to project root.
        """
        config = self._load_config(config_path)
        
        self.api_key = api_key or config.get("api_key", "")
        self.customer_id = customer_id or config.get("customer_id", "")
        self.base_url = base_url or config.get("base_url", self.DEFAULT_BASE_URL)
        self.page_size = self.MAX_PAGE_SIZE
        
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if config_path is None:
            # Look for config.json in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _format_date(self, dt: datetime, end_of_day: bool = False) -> str:
        """
        Format datetime for API queries.
        
        Args:
            dt: The datetime to format.
            end_of_day: If True, sets time to 23:59:59. Otherwise 00:00:00.
        
        Returns:
            ISO-formatted date string.
        """
        if end_of_day:
            return dt.strftime("%Y-%m-%dT23:59:59")
        return dt.strftime("%Y-%m-%dT00:00:00")
    
    def _paginate(
        self, 
        endpoint: str, 
        params: List[Tuple[str, str]],
        result_key: str = "tickets"
    ) -> List[Dict]:
        """
        Handle paginated API requests.
        
        Args:
            endpoint: Full API endpoint URL.
            params: List of query parameter tuples (supports duplicate keys).
            result_key: The key in JSON response containing the items array.
        
        Returns:
            List of all items across all pages.
        """
        all_items = []
        page = 1
        
        while True:
            current_params = params + [("page", str(page))]
            
            try:
                response = requests.get(
                    endpoint, 
                    headers=self._headers, 
                    params=current_params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get(result_key, [])
                    
                    if not items:
                        break
                    
                    all_items.extend(items)
                    
                    if len(items) < self.page_size:
                        break
                    
                    page += 1
                    
                elif response.status_code == 429:
                    # Rate limited - could implement retry logic here
                    raise Exception("API rate limit exceeded. Please wait and try again.")
                else:
                    raise Exception(f"API error {response.status_code}: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                raise Exception(f"Network error: {str(e)}")
        
        return all_items
    
    def get_tickets(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 30,
        originator: Optional[str] = None,
        ticket_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve tickets from the Axur platform.
        
        Args:
            start_date: Start of date range. Defaults to days_back from now.
            end_date: End of date range. Defaults to now.
            days_back: Number of days to look back if start_date not provided.
            originator: Filter by detection origin (e.g., "onepixel", "platform").
            ticket_type: Filter by ticket type (e.g., "phishing", "malware").
        
        Returns:
            List of ticket dictionaries.
        
        Example:
            tickets = client.get_tickets(days_back=90, originator="onepixel")
        """
        endpoint = f"{self.base_url}/tickets-api/tickets"
        
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days_back)
        
        params = [
            ("ticket.customer", self.customer_id),
            ("open.date", f"ge:{self._format_date(start_date)}"),
            ("open.date", f"le:{self._format_date(end_date, end_of_day=True)}"),
            ("pageSize", str(self.page_size)),
            ("sortBy", "open.date"),
            ("order", "desc")
        ]
        
        if originator:
            params.append(("ticket.creation.originator", originator))
        
        if ticket_type:
            params.append(("type", ticket_type))
        
        return self._paginate(endpoint, params, result_key="tickets")
    
    def get_customer_assets(self) -> Tuple[List[Dict], Dict[str, str]]:
        """
        Retrieve customer brands and domain mappings.
        
        Returns:
            Tuple of (brands_list, domain_to_brand_map):
            - brands_list: List of brand dictionaries with name, key, official_website.
            - domain_to_brand_map: Dictionary mapping domain names to brand names.
        
        Example:
            brands, domain_map = client.get_customer_assets()
            print(f"Found {len(brands)} brands")
        """
        endpoint = f"{self.base_url}/customers/customers"
        brands = []
        domain_to_brand = {}
        
        try:
            response = requests.get(endpoint, headers=self._headers, timeout=30)
            
            if response.status_code != 200:
                return brands, domain_to_brand
            
            customers = response.json()
            
            for customer in customers:
                if customer.get("key") != self.customer_id:
                    continue
                
                assets = customer.get("assets", [])
                domains = []
                
                for asset in assets:
                    category = asset.get("category")
                    
                    if category == "BRAND" and asset.get("active", True):
                        brand_info = {
                            "name": asset.get("name"),
                            "key": asset.get("key"),
                            "official_website": None
                        }
                        for prop in asset.get("properties", []):
                            if prop.get("name") == "OFFICIAL_WEBSITE":
                                brand_info["official_website"] = prop.get("value", "")
                        brands.append(brand_info)
                    
                    elif category == "DOMAIN" and asset.get("active", True):
                        domain_name = asset.get("name")
                        if domain_name:
                            domains.append(domain_name)
                
                # Map domains to brands
                for domain in domains:
                    matched_brand = self._match_domain_to_brand(domain, brands)
                    domain_to_brand[domain] = matched_brand
                
                break
        
        except requests.exceptions.RequestException:
            pass
        
        return brands, domain_to_brand
    
    def _match_domain_to_brand(self, domain: str, brands: List[Dict]) -> Optional[str]:
        """Match a domain to its corresponding brand based on official website."""
        domain_lower = domain.lower()
        domain_base = domain_lower.split(".")[0]
        
        for brand in brands:
            official_site = (brand.get("official_website") or "").lower()
            
            if domain_lower in official_site:
                return brand["name"]
            
            if domain_base in official_site and len(domain_base) > 3:
                return brand["name"]
        
        return None
    
    def get_credentials(
        self,
        domain: Optional[str] = None,
        days_back: int = 30,
        status: str = "NEW,IN_TREATMENT"
    ) -> List[Dict]:
        """
        Retrieve exposed credentials from the Exposure API.
        
        Args:
            domain: Filter by specific domain.
            days_back: Number of days to look back.
            status: Credential status filter.
        
        Returns:
            List of credential dictionaries.
        """
        endpoint = f"{self.base_url}/exposure-api/credentials"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = [
            ("customer", self.customer_id),
            ("status", status),
            ("created", f"ge:{start_date.strftime('%Y-%m-%d')}"),
            ("created", f"le:{end_date.strftime('%Y-%m-%d')}"),
            ("pageSize", str(self.page_size))
        ]
        
        if domain:
            params.append(("domain", domain))
        
        return self._paginate(endpoint, params, result_key="credentials")


# Convenience function for quick access
def create_client(**kwargs) -> AxurClient:
    """
    Factory function to create an AxurClient instance.
    
    Example:
        from core.axur_client import create_client
        client = create_client()
    """
    return AxurClient(**kwargs)
