from comparator import classify


def test_classify_ok_when_all_match():
    scrape = {
        "url": "x",
        "ok": True,
        "error": None,
        "title": "T",
        "price": 20.0,
        "available": True,
        "ean": "7891035051326",
    }
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": "7891035051326"}
    result = classify(scrape, expected)
    assert result == {"status": "ok", "flags": []}


def test_classify_flags_indisponivel():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 20.0, "available": False, "ean": "X"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "problema"
    assert "Indisponível para compra" in result["flags"]


def test_classify_flags_preco_fora_faixa():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 30.0, "available": True, "ean": "X"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "problema"
    assert any("fora da faixa" in f for f in result["flags"])


def test_classify_preco_dentro_faixa_ok():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 21.5, "available": True, "ean": "X"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "ok"


def test_classify_flags_ean_nao_bate():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 20.0, "available": True, "ean": "9999999999999"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10,
                "ean_esperado": "7891035051326"}
    result = classify(scrape, expected)
    assert result["status"] == "problema"
    assert any("EAN diferente" in f for f in result["flags"])


def test_classify_ignora_ean_quando_nao_esperado():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 20.0, "available": True, "ean": "9999999999999"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "ok"


def test_classify_nao_verificavel_quando_scrape_falhou():
    scrape = {"url": "x", "ok": False, "error": "blocked",
              "title": None, "price": None, "available": None, "ean": None}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "nao_verificavel"
    assert "blocked" in result["flags"]
