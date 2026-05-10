import re
import sys
import traceback
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
    # Primary: Buy Box (apex-pricetopay-value) com a-price-whole + a-price-fraction.
    # Estrutura típica:
    #   apex-pricetopay-value...<span class="a-price-whole">37<span class="a-price-decimal">,</span></span><span class="a-price-fraction">04</span>
    m = re.search(
        r'apex-pricetopay-value.*?'
        r'<span class="a-price-whole">([\d.]+)<.*?'
        r'<span class="a-price-fraction">(\d+)</span>',
        html, re.DOTALL,
    )
    if m:
        whole = m.group(1).replace(".", "")  # remove separador de milhar
        frac = m.group(2)
        try:
            return float(f"{whole}.{frac}")
        except ValueError:
            pass
    # Secondary: JSON inline com "priceAmount": <number>.
    m = re.search(r'"priceAmount"\s*:\s*([\d.]+)', html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    # Tertiary: a-offscreen ignorando spans pequenos típicos de preço-por-unidade.
    # Pega o primeiro com R$ X,XX que não seja absurdamente pequeno (>= R$ 1,00).
    for raw in re.findall(
        r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', html
    ):
        cleaned = raw.replace("R$", "").replace("&nbsp;", "").replace("\xa0", "").strip()
        if not cleaned:
            continue
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            val = float(cleaned)
            if val >= 1.0:
                return val
        except ValueError:
            continue
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


_REQUESTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


def _fetch_via_stealthy(url: str) -> tuple[int, str]:
    """Caminho A: Scrapling StealthyFetcher. Requer browser stealth instalado."""
    from scrapling.fetchers import StealthyFetcher
    page = StealthyFetcher().fetch(url, headless=True, timeout=30000)
    return page.status, page.html_content


def _fetch_via_requests(url: str) -> tuple[int, str]:
    """Caminho B (fallback): requests com headers de Chrome realista.
    Mais frágil contra anti-bot mas zero-dep e funciona em muitos casos da Amazon BR."""
    import requests
    r = requests.get(url, headers=_REQUESTS_HEADERS, timeout=15, allow_redirects=True)
    return r.status_code, r.text


def scrape_amazon_br(url: str) -> dict:
    """Entrypoint público. Aplica rate limit, tenta fetchers em cascade, parseia."""
    base = {"url": url, "ok": False, "error": None, "title": None,
            "price": None, "available": None, "ean": None}

    permitido, _ = _check_and_increment_usage()
    if not permitido:
        return {**base, "error": "rate_limit"}

    status, html = None, None
    for fetcher_name, fetcher in [("stealthy", _fetch_via_stealthy), ("requests", _fetch_via_requests)]:
        try:
            status, html = fetcher(url)
            print(f"[scraper] {fetcher_name} OK status={status} len={len(html)} url={url[-30:]}",
                  file=sys.stderr, flush=True)
            break
        except Exception as e:
            print(f"[scraper] {fetcher_name} FAILED for {url}: {type(e).__name__}: {str(e)[:200]}",
                  file=sys.stderr, flush=True)
            if fetcher_name == "stealthy":
                # silencia traceback grande do stealthy pra não poluir log; mostra só do último.
                continue
            traceback.print_exc(file=sys.stderr)

    if html is None:
        return {**base, "error": "blocked: todos os fetchers falharam"}
    if status == 404:
        return {**base, "error": "404"}
    if status >= 400:
        return {**base, "error": f"http_{status}"}

    parsed = parse_amazon_html(html)
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
