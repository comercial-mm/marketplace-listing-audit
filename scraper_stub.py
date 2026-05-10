"""Stub temporário do scraper. Retorna dados fake variados pra desenvolvimento de UI.
Será substituído pelo módulo real `scraper` na integração."""

import time
import random


_FAKE_DATA = {
    "B07PNK7TZK": {  # Vanish — OK
        "title": "Tira Manchas em Pó Vanish Crystal White Oxi Action Roupas Brancas 1kg",
        "price": 35.50, "available": True, "ean": "7891035051326",
    },
    "B07DYZ65B5": {  # Veja — indisponível
        "title": "Limpador Multiuso Veja Gold Original Squeeze 750ml",
        "price": 13.90, "available": False, "ean": "7891035216206",
    },
    "B07DZ8VXQN": {  # Finish — preço fora
        "title": "Finish Detergente em Pó Power Powder 1kg",
        "price": 89.00, "available": True, "ean": "7891035024351",
    },
    "B07GMHQRNH": {  # Harpic — EAN diferente
        "title": "Desinfetante Sanitário em Gel Harpic Power Plus Marine 500ml",
        "price": 14.50, "available": True, "ean": "0000000000000",
    },
    "B0BSNVX3HV": {  # Sustagen — erro de scrape
        "title": None, "price": None, "available": None, "ean": None,
    },
}


def scrape_amazon_br(url: str) -> dict:
    time.sleep(random.uniform(0.5, 1.5))  # simula latência
    base = {"url": url, "ok": False, "error": None, "title": None,
            "price": None, "available": None, "ean": None}
    for asin, data in _FAKE_DATA.items():
        if asin in url:
            if data["title"] is None:
                return {**base, "error": "blocked"}
            return {"url": url, "ok": True, "error": None, **data}
    # URL desconhecida → simula scrape OK genérico
    return {"url": url, "ok": True, "error": None, "title": "Produto Genérico",
            "price": 19.90, "available": True, "ean": "0000000000000"}
