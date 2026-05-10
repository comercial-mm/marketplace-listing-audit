"""Smoke test local pros 5 SKUs Reckitt.

Critério de sucesso: pra cada URL, scrape_amazon_br retorna:
- ok == True
- title contém o termo esperado (Vanish, Veja, Finish, Harpic, Sustagen)
- price é float entre R$ 1.00 e R$ 500.00
- available é True ou False (não None)
- ean é opcional (None aceito; só roda em browser real)

Roda: python3 local_smoke.py
Exit code 0 se 5/5 passam. 1 se algum falha.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scraper import scrape_amazon_br
from examples.reckitt_5_skus import EXAMPLE_SKUS

EXPECTED_TERMS = {
    "B07PNK7TZK": "Vanish",
    "B07DYZ65B5": "Veja",
    "B07DZ8VXQN": "Finish",
    "B07GMHQRNH": "Harpic",
    "B0BSNVX3HV": "Sustagen",
}

PRICE_MIN = 1.0
PRICE_MAX = 500.0


def check(sku):
    url = sku["url"]
    asin = next((a for a in EXPECTED_TERMS if a in url), None)
    term = EXPECTED_TERMS[asin]

    result = scrape_amazon_br(url)
    fails = []

    if not result.get("ok"):
        fails.append(f"ok={result.get('ok')} error={result.get('error')!r}")
        return result, fails

    title = result.get("title") or ""
    if term.lower() not in title.lower():
        fails.append(f"title não contém '{term}': {title[:80]!r}")

    price = result.get("price")
    if price is None:
        fails.append("price=None")
    elif not (PRICE_MIN <= price <= PRICE_MAX):
        fails.append(f"price={price} fora do range [{PRICE_MIN}, {PRICE_MAX}]")

    avail = result.get("available")
    if avail is None:
        fails.append("available=None")

    return result, fails


def main():
    Path("usage.json").unlink(missing_ok=True)
    passed = 0
    for sku in EXAMPLE_SKUS:
        result, fails = check(sku)
        if not fails:
            print(f"PASS {sku['nome_amigavel']}: price={result['price']} avail={result['available']} "
                  f"title={(result.get('title') or '')[:40]!r}")
            passed += 1
        else:
            print(f"FAIL {sku['nome_amigavel']}: {'; '.join(fails)}")
            print(f"     full: {result}")
    print(f"\n=== {passed}/{len(EXAMPLE_SKUS)} passed ===")
    sys.exit(0 if passed == len(EXAMPLE_SKUS) else 1)


if __name__ == "__main__":
    main()
