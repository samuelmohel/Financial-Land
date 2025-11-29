import logging
import time
import requests
from requests.exceptions import RequestException
from config import settings
from utils.circuit_breaker import CircuitBreaker

cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)


class ToolExecutionError(Exception):
    pass


def get_exchange_rate(source_currency: str, target_currency: str) -> float:
    """
    Fetches the real-time exchange rate between two currencies.

    Args:
        source_currency: The currency to convert from (e.g., "USD").
        target_currency: The currency to convert to (e.g., "EUR").

    Returns:
        The exchange rate (e.g., 0.92 for USD/EUR).
    """
    # Build an API URL based on configured provider. If a key is provided, many providers
    # require the key to be placed in the path (e.g. https://v6.exchangerate-api.com/v6/KEY/latest/USD)
    base_url = settings.EXCHANGE_RATE_BASE_URL.rstrip('/')
    api_key = settings.EXCHANGE_RATE_API_KEY or settings.FINANCIAL_DATA_API_KEY or ''

    if api_key:
        # This works for Exchangerate-API-esque URLs: /v6/{KEY}/latest/{BASE}
        api_url = f"{base_url}/{api_key}/latest/{source_currency.upper()}"
        headers = {}
    else:
        # Some services use a query parameter `base` instead of a key-in-path
        api_url = f"{base_url}/latest?base={source_currency.upper()}"
        headers = {}

    logger = logging.getLogger(__name__)
    key_name = 'get_exchange_rate'
    if cb.is_open(key_name):
        raise ToolExecutionError('Circuit breaker is open for get_exchange_rate')

    retries = 3
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(api_url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            rates = data.get('rates', {})
            rate = rates.get(target_currency.upper())
            if rate is None:
                raise KeyError(f"Target currency '{target_currency}' not found in response")
            cb.record_success(key_name)
            return float(rate)

        except RequestException as e:
            logger.error("Network/API error fetching exchange rate (attempt %s): %s", attempt, e)
            if attempt == retries:
                cb.record_failure(key_name)
                raise ToolExecutionError(str(e))
            time.sleep(backoff)
            backoff *= 2.0
        except KeyError as e:
            # No point retrying if the currency isn't present
            logger.warning("Target currency not found in API response: %s", e)
            raise ToolExecutionError(str(e))

if __name__ == '__main__':
    # Example usage:
    rate = get_exchange_rate("USD", "EUR")
    logger = logging.getLogger(__name__)
    logger.info("1 USD = %s EUR", rate)