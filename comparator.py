def classify(scrape: dict, expected: dict) -> dict:
    if not scrape["ok"]:
        return {"status": "nao_verificavel", "flags": [scrape.get("error") or "erro desconhecido"]}
    flags = []
    if scrape["available"] is False:
        flags.append("Indisponível para compra")
    preco = scrape.get("price")
    p_esp = expected["preco_esperado"]
    tol = expected["tolerancia_pct"] / 100
    if p_esp > 0 and preco is not None:
        p_min = p_esp * (1 - tol)
        p_max = p_esp * (1 + tol)
        if preco < p_min or preco > p_max:
            flags.append(f"Preço R$ {preco:.2f} fora da faixa esperada R$ {p_min:.2f} a R$ {p_max:.2f}")
    ean_esp = expected.get("ean_esperado")
    if ean_esp and scrape.get("ean") and ean_esp != scrape["ean"]:
        flags.append("Anúncio aponta pra EAN diferente do esperado (possível troca de produto)")
    return {"status": "ok" if not flags else "problema", "flags": flags}
