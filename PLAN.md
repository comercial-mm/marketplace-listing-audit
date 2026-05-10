# MVP Reckitt Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir app Streamlit que audita URLs Amazon BR contra preço esperado, EAN esperado e disponibilidade. Servir como porta de entrada gratuita pra Giulia (Reckitt) testar a substituição da Lett.

**Architecture:** Single-page Streamlit, sem persistência. `app.py` orquestra; `scraper.py` busca via Scrapling StealthyFetcher; `comparator.py` aplica 3 regras de classificação; `examples/reckitt_5_skus.py` fornece o modo exemplo. Rate limit por arquivo local. Deploy via Streamlit Community Cloud.

**Tech Stack:** Python 3.11, Streamlit ≥1.32, Scrapling ≥0.4.7, pytest, pandas (vem com Streamlit).

**Reference:** Spec completo em `SPEC.md` no mesmo diretório. Contratos de função (`scrape_amazon_br`, `classify`) são congelados pelo spec e não podem ser alterados sem revisar o spec.

**Parallel execution:** Tasks 2 (backend) e 3 (frontend) são independentes e devem ser despachadas em paralelo, cada uma pra um agente diferente. Cada uma é auto-contida e usa só o contrato do spec como referência cruzada.

---

## Task 1: Scaffold do projeto (sequencial, antes de tudo)

**Files:**
- Create: `requirements.txt`
- Create: `.streamlit/config.toml`
- Create: `README.md`
- Create: `examples/reckitt_5_skus.py`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1.1: Criar `requirements.txt`**

```
streamlit>=1.32,<2.0
scrapling>=0.4.7,<0.5
pytest>=8.0
pandas>=2.0
```

- [ ] **Step 1.2: Criar `.streamlit/config.toml`**

```toml
[theme]
base = "light"
primaryColor = "#FF4B4B"

[server]
headless = true

[browser]
gatherUsageStats = false
```

- [ ] **Step 1.3: Criar `examples/reckitt_5_skus.py`**

```python
"""5 SKUs do PDF MVP_Reckitt pra modo exemplo do app e fixture de teste."""

EXAMPLE_SKUS = [
    {
        "url": "https://www.amazon.com.br/Manchas-Crystal-Action-Econ%C3%B4mico-Vanish/dp/B07PNK7TZK/?th=1",
        "ean_esperado": "7891035051326",
        "preco_esperado": 35.00,
        "tolerancia_pct": 15,
        "nome_amigavel": "Vanish Crystal White Oxi Action 1kg",
    },
    {
        "url": "https://www.amazon.com.br/Veja-Limpador-Multiuso-Original-Squeeze/dp/B07DYZ65B5/",
        "ean_esperado": "7891035216206",
        "preco_esperado": 13.00,
        "tolerancia_pct": 15,
        "nome_amigavel": "Veja Gold Original 750ml",
    },
    {
        "url": "https://www.amazon.com.br/Finish-P%C3%B3-Power-Powder/dp/B07DZ8VXQN/",
        "ean_esperado": "7891035024351",
        "preco_esperado": 45.00,
        "tolerancia_pct": 15,
        "nome_amigavel": "Finish Pó 1kg",
    },
    {
        "url": "https://www.amazon.com.br/Desinfetante-Sanit%C3%A1rio-500Ml-Power-Harpic/dp/B07GMHQRNH/",
        "ean_esperado": "7891035128103",
        "preco_esperado": 14.00,
        "tolerancia_pct": 15,
        "nome_amigavel": "Harpic Power Plus Marine 500ml",
    },
    {
        "url": "https://www.amazon.com.br/Sustagen-Senior-Complemento-Alimentar-Baunilha/dp/B0BSNVX3HV/",
        "ean_esperado": "7898941911294",
        "preco_esperado": 90.00,
        "tolerancia_pct": 15,
        "nome_amigavel": "Sustagen Senior Baunilha 370g",
    },
]
```

- [ ] **Step 1.4: Criar `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v
```

- [ ] **Step 1.5: Criar `tests/__init__.py`**

Arquivo vazio.

- [ ] **Step 1.6: Criar `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
usage.json
.venv/
.streamlit/secrets.toml
```

- [ ] **Step 1.7: Criar `README.md`**

```markdown
# MVP para Giulia, da Reckitt

Auditor de URLs de Amazon BR. Confere preço, disponibilidade e EAN contra valores esperados informados pelo usuário.

## Dev local

\`\`\`bash
pip install -r requirements.txt
streamlit run app.py
\`\`\`

## Deploy

Streamlit Community Cloud. Conectar repo público; entrypoint `app.py`.

## Estrutura

- `app.py`: UI Streamlit.
- `scraper.py`: Scrapling StealthyFetcher contra Amazon BR + rate limit.
- `comparator.py`: regras de classificação.
- `examples/reckitt_5_skus.py`: 5 SKUs do modo exemplo.
- `tests/`: testes pytest.

Spec completo em `SPEC.md`.
```

- [ ] **Step 1.8: Commit**

```bash
git add requirements.txt .streamlit/config.toml README.md examples/reckitt_5_skus.py pytest.ini tests/__init__.py .gitignore
git commit -m "chore: scaffold mvp reckitt-audit"
```

---

## Task 2: Backend — `comparator.py` + `scraper.py` (PARALELO com Task 3)

**Owner:** agente-backend

**Files:**
- Create: `comparator.py`
- Create: `scraper.py`
- Create: `tests/test_comparator.py`
- Create: `tests/test_scraper.py`
- Create: `tests/fixtures/amazon_vanish.html` (HTML salvo de uma das URLs)

**Reference contract** (do `SPEC.md`):

```python
# scraper.scrape_amazon_br
{
    "url": str,
    "ok": bool,
    "error": str | None,        # "404" | "blocked" | "timeout" | "rate_limit"
    "title": str | None,
    "price": float | None,
    "available": bool | None,
    "ean": str | None,
}

# comparator.classify(scrape: dict, expected: dict) -> dict
# expected = {"preco_esperado": float, "tolerancia_pct": float, "ean_esperado": str | None}
{
    "status": "ok" | "problema" | "nao_verificavel",
    "flags": list[str],
}
```

### Task 2A: `comparator.py` (TDD)

- [ ] **Step 2A.1: Test caso OK (sem flags)**

`tests/test_comparator.py`:

```python
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
```

Run: `pytest tests/test_comparator.py -v`. Expected: FAIL ("comparator not importable").

- [ ] **Step 2A.2: Implementar minimum**

`comparator.py`:

```python
def classify(scrape: dict, expected: dict) -> dict:
    if not scrape["ok"]:
        return {"status": "nao_verificavel", "flags": [scrape.get("error") or "erro desconhecido"]}
    flags = []
    if scrape["available"] is False:
        flags.append("Indisponível para compra")
    preco = scrape.get("price")
    p_esp = expected["preco_esperado"]
    tol = expected["tolerancia_pct"] / 100
    p_min = p_esp * (1 - tol)
    p_max = p_esp * (1 + tol)
    if preco is not None and (preco < p_min or preco > p_max):
        flags.append(f"Preço R$ {preco:.2f} fora da faixa esperada R$ {p_min:.2f} a R$ {p_max:.2f}")
    ean_esp = expected.get("ean_esperado")
    if ean_esp and scrape.get("ean") and ean_esp != scrape["ean"]:
        flags.append("Anúncio aponta pra EAN diferente do esperado (possível troca de produto)")
    return {"status": "ok" if not flags else "problema", "flags": flags}
```

Run: `pytest tests/test_comparator.py -v`. Expected: PASS.

- [ ] **Step 2A.3: Test indisponibilidade**

Adicionar a `tests/test_comparator.py`:

```python
def test_classify_flags_indisponivel():
    scrape = {"url": "x", "ok": True, "error": None, "title": "T",
              "price": 20.0, "available": False, "ean": "X"}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "problema"
    assert "Indisponível para compra" in result["flags"]
```

Run pytest. Expected: PASS (já implementado).

- [ ] **Step 2A.4: Test preço fora da faixa**

```python
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
```

Run pytest. Expected: PASS.

- [ ] **Step 2A.5: Test EAN não bate (e ignora se não esperado)**

```python
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
```

Run pytest. Expected: PASS.

- [ ] **Step 2A.6: Test scrape falhou → não verificável**

```python
def test_classify_nao_verificavel_quando_scrape_falhou():
    scrape = {"url": "x", "ok": False, "error": "blocked",
              "title": None, "price": None, "available": None, "ean": None}
    expected = {"preco_esperado": 20.0, "tolerancia_pct": 10, "ean_esperado": None}
    result = classify(scrape, expected)
    assert result["status"] == "nao_verificavel"
    assert "blocked" in result["flags"]
```

Run pytest. Expected: PASS.

- [ ] **Step 2A.7: Commit**

```bash
git add comparator.py tests/test_comparator.py
git commit -m "feat: comparator com regras de disponibilidade, preço e EAN"
```

### Task 2B: `scraper.py` com rate limit

Estratégia: salvar HTML real de 1 URL como fixture, testar parsing offline. Smoke test online só roda manualmente.

- [ ] **Step 2B.1: Capturar fixture HTML**

Run no shell:

```bash
mkdir -p tests/fixtures
python -c "
from scrapling.fetchers import StealthyFetcher
url = 'https://www.amazon.com.br/Manchas-Crystal-Action-Econ%C3%B4mico-Vanish/dp/B07PNK7TZK/?th=1'
page = StealthyFetcher().fetch(url, headless=True)
open('tests/fixtures/amazon_vanish.html', 'w').write(page.html_content)
print('saved', len(page.html_content), 'bytes')
"
```

Se Scrapling falhar no install ou anti-bot bloquear: salvar manualmente. Abrir URL no Chrome, View Source, salvar como `tests/fixtures/amazon_vanish.html`.

Expected: arquivo > 100KB existe em `tests/fixtures/amazon_vanish.html`.

- [ ] **Step 2B.2: Test parsing de título a partir da fixture**

`tests/test_scraper.py`:

```python
from pathlib import Path
from scraper import parse_amazon_html

FIXTURE = Path(__file__).parent / "fixtures" / "amazon_vanish.html"


def test_parse_title():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert "Vanish" in result["title"]
```

Run: `pytest tests/test_scraper.py -v`. Expected: FAIL.

- [ ] **Step 2B.3: Implementar `parse_amazon_html`**

`scraper.py`:

```python
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
    cleaned = raw.replace("R$", "").strip().replace(".", "").replace(",", ".")
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
```

Run pytest. Expected: PASS.

- [ ] **Step 2B.4: Test parsing de preço, disponibilidade e EAN da fixture**

```python
def test_parse_price_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert result["price"] is not None
    assert 5.0 < result["price"] < 200.0  # sanity range


def test_parse_availability_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert result["available"] is not None


def test_parse_ean_present():
    html = FIXTURE.read_text()
    result = parse_amazon_html(html)
    assert result["ean"] == "7891035051326" or result["ean"] is None  # tolerante se Amazon esconde EAN
```

Run pytest. Se algum teste falhar, ajustar regex em `scraper.py` até passar.

- [ ] **Step 2B.5: Implementar rate limit**

Adicionar a `scraper.py`:

```python
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
```

Test pra rate limit:

```python
import json
from pathlib import Path
from scraper import _check_and_increment_usage, DAILY_LIMIT, USAGE_FILE


def test_rate_limit_increments(tmp_path, monkeypatch):
    fake = tmp_path / "usage.json"
    monkeypatch.setattr("scraper.USAGE_FILE", fake)
    permitido, count = _check_and_increment_usage()
    assert permitido is True
    assert count == 1


def test_rate_limit_blocks_after_max(tmp_path, monkeypatch):
    fake = tmp_path / "usage.json"
    fake.write_text(json.dumps({"date": __import__("datetime").date.today().isoformat(),
                                 "count": DAILY_LIMIT}))
    monkeypatch.setattr("scraper.USAGE_FILE", fake)
    permitido, count = _check_and_increment_usage()
    assert permitido is False
```

Run pytest. Expected: PASS.

- [ ] **Step 2B.6: Implementar `scrape_amazon_br` (entrypoint público)**

```python
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
```

- [ ] **Step 2B.7: CLI de teste manual**

Adicionar ao final de `scraper.py`:

```python
if __name__ == "__main__":
    import sys
    from pprint import pprint
    if len(sys.argv) < 2:
        print("uso: python scraper.py <url> [<url> ...]")
        sys.exit(1)
    for url in sys.argv[1:]:
        print(f"\n=== {url} ===")
        pprint(scrape_amazon_br(url))
```

Smoke test manual:

```bash
python scraper.py "https://www.amazon.com.br/Manchas-Crystal-Action-Econ%C3%B4mico-Vanish/dp/B07PNK7TZK/?th=1"
```

Expected output: dict com `ok=True`, `title` contendo "Vanish", `price` numérico, `available=True`, `ean="7891035051326"`.

- [ ] **Step 2B.8: Commit**

```bash
git add scraper.py tests/test_scraper.py tests/fixtures/amazon_vanish.html
git commit -m "feat: scraper amazon br com rate limit + fixture"
```

---

## Task 3: Frontend — `app.py` (PARALELO com Task 2)

**Owner:** agente-frontend

**Files:**
- Create: `app.py`
- Create: `scraper_stub.py` (stub que será substituído na integração)

**Não toca em**: `scraper.py`, `comparator.py`. Esses são do agente backend.

**Reference contract** (do `SPEC.md`): mesmo da Task 2.

- [ ] **Step 3.1: Criar `scraper_stub.py`**

Stub que retorna 5 dicts com mix variado de status. App importa isso temporariamente; integração troca por `scraper` real.

```python
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
```

- [ ] **Step 3.2: Criar `app.py` — header e expander de escopo**

```python
import streamlit as st
import pandas as pd
from scraper_stub import scrape_amazon_br  # TROCAR PARA: from scraper import scrape_amazon_br
from comparator import classify
from examples.reckitt_5_skus import EXAMPLE_SKUS


st.set_page_config(page_title="MVP Reckitt Audit", layout="wide")

st.title("MVP para Giulia, da Reckitt")
st.caption("Confere preço, disponibilidade e EAN dos seus URLs Amazon BR contra o esperado. "
           "Pra validar alertas da Lett mais rápido.")

with st.expander("Sobre este MVP", expanded=False):
    st.markdown("""
### Escopo do MVP (V0)

**Inclui**:
- Auditoria de disponibilidade: URL existe, produto está sendo vendido (botão comprar).
- Auditoria de preço da Buy Box (oferta principal), com tolerância configurável.
- Verificação opcional de EAN: anúncio aponta pro produto certo (detecta troca de produto).
- Apenas Amazon BR.
- Input via colagem manual em tabela editável dentro do app.
- Modo "exemplo Reckitt": 5 SKUs do PDF pré-populados pra descoberta zero-fricção.

**Não inclui (fica pra V1+)**:
- Conteúdo (título, descrição, imagens).
- Mercado Livre.
- Login, persistência, histórico, agendamento, alertas por email.
- Upload de CSV.
- Fila e delay pra >20 URLs por sessão.
""")

st.info("Primeira abertura pode demorar ~30s (app dorme com inatividade).")
```

- [ ] **Step 3.3: Modo "Rodar exemplo Reckitt"**

Adicionar ao `app.py`:

```python
st.divider()
st.subheader("Modo 1 — Rodar exemplo Reckitt")
st.write("Testa os 5 SKUs do PDF MVP_Reckitt sem precisar colar nada.")

if st.button("▶ Rodar exemplo Reckitt", type="primary"):
    rows = [
        {"URL": s["url"], "Preço esperado (R$)": s["preco_esperado"],
         "Tolerância (%)": s["tolerancia_pct"], "EAN esperado": s["ean_esperado"]}
        for s in EXAMPLE_SKUS
    ]
    st.session_state["input_rows"] = rows
    st.session_state["should_run"] = True
```

- [ ] **Step 3.4: Modo "Rodar minha lista"**

Adicionar:

```python
st.divider()
st.subheader("Modo 2 — Rodar minha lista")
st.write("Cola URLs alertadas pela Lett, com preço esperado. Tolerância em % e EAN são opcionais.")

default_df = pd.DataFrame(
    st.session_state.get("input_rows", [
        {"URL": "", "Preço esperado (R$)": 0.0, "Tolerância (%)": 10,
         "EAN esperado": ""}
    ])
)

edited = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "URL": st.column_config.TextColumn("URL", required=True),
        "Preço esperado (R$)": st.column_config.NumberColumn(format="%.2f", min_value=0.0),
        "Tolerância (%)": st.column_config.NumberColumn(min_value=0, max_value=100, default=10),
        "EAN esperado": st.column_config.TextColumn(
            "EAN esperado",
            help="Captura quando o lojista troca o produto do anúncio. Deixe em branco se não souber."),
    },
    key="data_editor",
)

if st.button("Rodar verificação"):
    st.session_state["input_rows"] = edited.to_dict("records")
    st.session_state["should_run"] = True
```

- [ ] **Step 3.5: Execução e renderização do output**

Adicionar:

```python
def _run_audit(rows: list[dict]) -> list[dict]:
    results = []
    progress = st.progress(0, text="Buscando URLs...")
    valid_rows = [r for r in rows if r.get("URL", "").strip()]
    for i, row in enumerate(valid_rows):
        scrape = scrape_amazon_br(row["URL"])
        ean_esp = (row.get("EAN esperado") or "").strip() or None
        expected = {
            "preco_esperado": float(row.get("Preço esperado (R$)") or 0),
            "tolerancia_pct": float(row.get("Tolerância (%)") or 10),
            "ean_esperado": ean_esp,
        }
        verdict = classify(scrape, expected)
        results.append({**scrape, **verdict})
        progress.progress((i + 1) / len(valid_rows))
    progress.empty()
    return results


def _render_output(results: list[dict]):
    counts = {"ok": 0, "problema": 0, "nao_verificavel": 0}
    for r in results:
        counts[r["status"]] += 1

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 OK", counts["ok"])
    c2.metric("🔴 Problema real", counts["problema"])
    c3.metric("⚪ Não verificável", counts["nao_verificavel"])

    emoji = {"ok": "🟢", "problema": "🔴", "nao_verificavel": "⚪"}
    table = pd.DataFrame([{
        "Status": emoji[r["status"]],
        "Título extraído": r.get("title") or "—",
        "Preço extraído": f"R$ {r['price']:.2f}" if r.get("price") else "—",
        "Disponível?": "Sim" if r.get("available") else ("Não" if r.get("available") is False else "—"),
        "EAN extraído": r.get("ean") or "—",
        "Razão": "; ".join(r.get("flags", [])) or "—",
        "URL": r.get("url"),
    } for r in results])

    st.dataframe(table, use_container_width=True, hide_index=True,
                 column_config={"URL": st.column_config.LinkColumn()})

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Exportar CSV", csv, file_name="reckitt_audit.csv", mime="text/csv")


if st.session_state.get("should_run") and st.session_state.get("input_rows"):
    st.divider()
    st.subheader("Resultado")
    results = _run_audit(st.session_state["input_rows"])
    if not results:
        st.warning("Nenhuma URL preenchida.")
    else:
        # Detecta rate limit do scraper real
        rate_limited = [r for r in results if r.get("error") == "rate_limit"]
        if rate_limited:
            st.error("Limite diário de uso justo do MVP atingido. "
                     "Volte amanhã. Se precisar de mais volume, fale com o Felipe pra evoluir pra V1.")
        else:
            _render_output(results)
    st.session_state["should_run"] = False
```

- [ ] **Step 3.6: Smoke test manual**

```bash
streamlit run app.py
```

Validar no browser:
1. Header "MVP para Giulia, da Reckitt" visível.
2. Expander "Sobre este MVP" abre e mostra escopo.
3. Botão "Rodar exemplo Reckitt" preenche tabela e roda → mostra 5 linhas com mix de status (1 OK, 1 indisponível, 1 preço fora, 1 EAN diferente, 1 não verificável).
4. Tabela editável aceita colar URLs + preços.
5. Botão "Rodar verificação" funciona.
6. Métricas no topo do output mostram contagem correta.
7. Botão "Exportar CSV" baixa CSV.

- [ ] **Step 3.7: Commit**

```bash
git add app.py scraper_stub.py
git commit -m "feat: front streamlit com stub de scraper"
```

---

## Task 4: Integração (sequencial, depois de Tasks 2 e 3)

**Files:**
- Modify: `app.py:3` (trocar import)
- Delete: `scraper_stub.py`

- [ ] **Step 4.1: Trocar import no `app.py`**

Edit em `app.py`, linha 3:

```python
# antes:
from scraper_stub import scrape_amazon_br
# depois:
from scraper import scrape_amazon_br
```

- [ ] **Step 4.2: Smoke test integrado**

```bash
streamlit run app.py
```

Clica "Rodar exemplo Reckitt". Espera ~30-60s (5 URLs scraping real).

Expected:
- Pelo menos 4 dos 5 URLs retornam scrape OK.
- Status visíveis na tabela. Pelo menos 1 OK, 0 ou mais não-verificáveis aceitáveis.
- Nenhum crash.

Se >2 URLs caírem em "blocked": IP do laptop tá sendo barrado pela Amazon. Esperar 10min ou trocar de rede.

- [ ] **Step 4.3: Forçar 1 alerta artificial**

Modo 2: cola um dos URLs reais com preço esperado errado de propósito (ex: R$ 1,00). Roda. Confirma que a flag de "Preço fora da faixa" aparece em vermelho.

- [ ] **Step 4.4: Remover stub**

```bash
rm scraper_stub.py
git add -u app.py
git rm scraper_stub.py
git commit -m "feat: integrar back+front, remover stub"
```

---

## Task 5: Deploy (sequencial, depois de Task 4)

**Files:**
- Create: repo público no GitHub.
- Create: app no Streamlit Community Cloud.

Felipe executa Steps 5.1, 5.2, 5.4 (precisa de credenciais dele). Agente faz Step 5.3 e Step 5.5.

- [ ] **Step 5.1: Criar repo público GitHub**

Felipe:

```bash
cd builder/experiments/2026-05-10-reckitt-audit-mvp
gh repo create mymetric/reckitt-audit-mvp --public --source=. --remote=origin --push
```

(Ou criar manual em github.com e seguir push instructions.)

- [ ] **Step 5.2: Conectar no Streamlit Community Cloud**

Felipe:
1. Acessar https://share.streamlit.io
2. New app → escolhe repo `mymetric/reckitt-audit-mvp`.
3. Branch: `main`. Main file path: `app.py`.
4. Deploy.

- [ ] **Step 5.3: Smoke test público**

Agente (após Felipe sinalizar deploy concluído):

Pega URL pública (formato `https://<slug>.streamlit.app`) e abre em modo anônimo.

Valida:
- Carrega em <60s no cold start.
- Header e expander visíveis.
- "Rodar exemplo Reckitt" funciona em deploy (Streamlit Cloud IP não bloqueado pela Amazon).

Se Amazon bloquear: documentar em `SPEC.md` como risco materializado, e propor fallback (Hugging Face Spaces ou proxy residencial).

- [ ] **Step 5.4: Felipe testa o link**

Felipe abre link em browser fresh. Confere fluxo de ponta a ponta.

- [ ] **Step 5.5: Commit final + handoff pra Felipe**

Status: V0 publicado. Próximo passo (manual): Felipe envia link pra Giulia.

```bash
git tag v0
git push origin v0
```

---

## Self-Review

**Spec coverage:**

- ✅ Auditoria disponibilidade: Task 2A (comparator) + 2B (scraper.available).
- ✅ Auditoria preço Buy Box: Task 2A + 2B (regex `.a-price .a-offscreen`).
- ✅ EAN opcional: Task 2A.5 + 2B.3 (`_extract_ean`).
- ✅ Apenas Amazon BR: scraper só tem `scrape_amazon_br`.
- ✅ Colagem manual: Task 3.4 (`st.data_editor`).
- ✅ Modo exemplo: Task 1.3 (fixtures) + Task 3.3 (botão).
- ✅ Teto diário: Task 2B.5 (`_check_and_increment_usage`).
- ✅ Header novo: Task 3.2.
- ✅ Expander de escopo: Task 3.2.
- ✅ Split paralelo: Task 2 e 3 explicitamente marcadas.
- ✅ Integração: Task 4.
- ✅ Deploy Streamlit Cloud: Task 5.

**Sem placeholders:** verificado. Todos os steps têm código concreto ou comando executável.

**Type consistency:** `scrape_amazon_br` retorna o mesmo schema em scraper real (Task 2B.6) e stub (Task 3.1). `classify` recebe o mesmo `expected` shape em todos os testes e no app.

**Granularidade:** Tasks 2 e 3 são grandes mas internamente quebradas em sub-passos. Cada step tem código concreto.

---

## Execução

Após este plano, voltar pra conversa principal e despachar via `superpowers:dispatching-parallel-agents` (Tasks 2 e 3 paralelas) ou `superpowers:subagent-driven-development` (sequencial mas com fresh agent por task).
