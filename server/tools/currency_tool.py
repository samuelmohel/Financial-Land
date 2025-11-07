# server/tools/currency_tool.py
import requests
from typing import Dict, Any


def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    url = "https://api.exchangerate.host/convert"
    params = {"from": from_currency.upper(), "to": to_currency.upper(), "amount": amount}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "amount": amount,
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "result": data.get("result"),
            "rate": (data.get("info") or {}).get("rate"),
            "date": data.get("date"),
        }
    except Exception as e:
        return {"error": str(e)}
