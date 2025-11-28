import logging
import requests
from config import settings

def verify_company_registry(company_name: str) -> dict:
    """
    Queries an external registry (simulated) to verify a company's status and details.

    Args:
        company_name: The name of the company to check.

    Returns:
        A dictionary of the company's verified details.
    """
    logger = logging.getLogger(__name__)
    logger.info("Checking registry for: %s", company_name)
    
    # Prefer calling an API when REGISTRY_API_URL is configured
    if settings.REGISTRY_API_URL:
        try:
            resp = requests.get(f"{settings.REGISTRY_API_URL}/search", params={"q": company_name}, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            logger.exception("Failed to reach registry API at %s", settings.REGISTRY_API_URL)
            # fall back to simulation

    # In a real app, this fallback is a simulation
    if "Tesla" in company_name:
        return {
            "name": "Tesla, Inc.",
            "status": "Active",
            "cik": "0001318605",
            "country": "USA",
            "date_founded": "2003-07-01"
        }
    else:
        return {"name": company_name, "status": "Not Found", "details": None}