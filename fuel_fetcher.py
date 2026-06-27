import urllib.request
import re
from database import get_fuel_price, update_fuel_price

def fetch_doe_fuel_price():
    """
    Fetch current gasoline price from DOE Philippines.
    Returns float price per liter, or None if failed.
    """
    try:
        urls = [
            "https://www.doe.gov.ph/price-monitor",
            "https://www.doe.gov.ph/petroleum-products-price-monitor",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as response:
                    html = response.read().decode("utf-8", errors="ignore")
                    # Look for gasoline price patterns like 75.50 or 68.50
                    patterns = [
                        r'[Gg]asoline[^\d]*?([\d]{2,3}\.[\d]{1,2})',
                        r'[Uu]nlead[^\d]*?([\d]{2,3}\.[\d]{1,2})',
                        r'RON\s*91[^\d]*?([\d]{2,3}\.[\d]{1,2})',
                        r'RON\s*95[^\d]*?([\d]{2,3}\.[\d]{1,2})',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            price = float(match.group(1))
                            if 50.0 <= price <= 120.0:  # sanity check
                                return price
            except Exception:
                continue
        return None
    except Exception:
        return None


def get_latest_fuel_price():
    """
    Try to fetch from DOE. If failed, fall back to database value.
    Returns (price, source) where source is 'DOE' or 'cached'
    """
    doe_price = fetch_doe_fuel_price()
    if doe_price:
        update_fuel_price(doe_price)
        return doe_price, "DOE"
    else:
        cached = get_fuel_price()
        return cached, "cached"


if __name__ == "__main__":
    price, source = get_latest_fuel_price()
    print(f"Fuel price: ₱{price:.2f}/L (source: {source})")
