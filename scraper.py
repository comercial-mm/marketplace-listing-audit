import re
from pathlib import Path
from datetime import date
import json


def parse_amazon_html(html: str) -> dict:
    """Parse HTML de página de produto Amazon BR. Retorna dict parcial."""
    title = _extract_text(html, r'<span[^>]*id="productTitle"[^>]*>([^<]+)</span>')
    price = _extract_price(html)
    available = _extract_availability(html)
    ean = _extract_ean(html)
    return {"title": title.strip() if title else None, "price": price,
            "available": available, "ean": ean}


def _extract_text(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return m.group(1) if m else None


def _extract_price(html: str) -> float | None:
    # Buy Box: primeira ocorrência de .a-price .a-offscreen.
    m = re.search(
        r'class="a-price[^"]*"[^>]*>\s*<span class="a-offscreen">([^<]+)</span>',
        html, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1)
    # "R$ 1.234,56" → 1234.56
    cleaned = raw.replace("R$", "").replace("&nbsp;", "").replace("\xa0", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_availability(html: str) -> bool | None:
    if 'id="add-to-cart-button"' in html:
        return True
    if "Indisponível no momento" in html or "Atualmente, não temos" in html:
        return False
    if 'id="availability"' in html and "Em estoque" in html:
        return True
    return None


def _extract_ean(html: str) -> str | None:
    # Tabela de detalhes pode usar "EAN", "GTIN-13", "Código EAN".
    for label in ["EAN", "GTIN-13", "GTIN", "Código de barras"]:
        m = re.search(rf'{label}[^0-9]*([0-9]{{12,14}})', html)
        if m:
            return m.group(1)
    return None


USAGE_FILE = Path("usage.json")
DAILY_LIMIT = 100


def _check_and_increment_usage() -> tuple[bool, int]:
    """Retorna (permitido, count_após). Se count já no limite, permitido=False."""
    today = date.today().isoformat()
    try:
        data = json.loads(USAGE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"date": today, "count": 0}
    if data.get("date") != today:
        data = {"date": today, "count": 0}
    if data["count"] >= DAILY_LIMIT:
        return False, data["count"]
    data["count"] += 1
    USAGE_FILE.write_text(json.dumps(data))
    return True, data["count"]


def scrape_amazon_br(url: str) -> dict:
    """Entrypoint público. Aplica rate limit, busca, parseia."""
    base = {"url": url, "ok": False, "error": None, "title": None,
            "price": None, "available": None, "ean": None}

    permitido, _ = _check_and_increment_usage()
    if not permitido:
        return {**base, "error": "rate_limit"}

    try:
        from scrapling.fetchers import StealthyFetcher
        page = StealthyFetcher().fetch(url, headless=True, timeout=30000)
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg:
            return {**base, "error": "timeout"}
        return {**base, "error": "blocked"}

    if page.status == 404:
        return {**base, "error": "404"}
    if page.status >= 400:
        return {**base, "error": "blocked"}

    parsed = parse_amazon_html(page.html_content)
    return {"url": url, "ok": True, "error": None, **parsed}


if __name__ == "__main__":
    import sys
    from pprint import pprint
    if len(sys.argv) < 2:
        print("uso: python scraper.py <url> [<url> ...]")
        sys.exit(1)
    for url in sys.argv[1:]:
        print(f"\n=== {url} ===")
        pprint(scrape_amazon_br(url))
