# Ralph Loop — Reckitt MVP Local Extraction

## Goal

Make `python3.11 local_smoke.py` exit 0 (5/5 SKUs PASS) from this directory.

## Current state

Baseline: 3/5 PASS. Veja (R$ 0,01) e Harpic (R$ 0,03) falham porque a regex de preço em `scraper.py::_extract_price` pega "preço por unidade" (`apex-priceperunit-value`) ou "você economiza" antes da Buy Box real (`apex-pricetopay-value` / `priceToPay`).

## Success criterion (verbatim, do not change)

```bash
cd /Users/fcamara/Projects/Claude/builder/experiments/2026-05-10-reckitt-audit-mvp
python3.11 local_smoke.py
```

Exit code 0 + `=== 5/5 passed ===` na última linha.

## Constraints

- **Don't modify** `local_smoke.py`, `comparator.py`, `app.py`, `examples/reckitt_5_skus.py`, `tests/test_comparator.py`. Only `scraper.py` (and possibly `requirements.txt` and `tests/test_scraper.py`).
- **Pytest must continue green**: rodar `python3.11 -m pytest tests/ -v` após qualquer mudança. Não regredir.
- **Não chamar Amazon excessivamente**: cada iteração que chama `scrape_amazon_br` faz 1 request HTTP por SKU. Salvar HTML em fixture e iterar offline quando possível.

## Approaches to try (in order, escalating)

1. **Buy Box-anchored regex**: encontrar `apex-pricetopay-value` ou `priceToPay` no HTML, e a partir desse índice procurar o próximo span de preço (pode estar em `a-price-whole` + `a-price-fraction`, não em `a-offscreen`).
2. **Filtrar a-offscreen ignorando context "perUnit", "basisprice", "strike"**: scan dos `<span class="a-offscreen">R$X</span>` e ignorar os que estão dentro de elementos com `apex-priceperunit-value`, `apex-basisprice-value`, `data-a-strike="true"`, ou cuja string anterior contém "Você economiza" / "De:" / "por unidade".
3. **a-price-whole / a-price-fraction**: a Buy Box renderiza preço como `<span class="a-price-whole">8</span><span class="a-price-fraction">29</span>` — extrair os dois e combinar.
4. **JSON-LD inline**: procurar `<script type="application/ld+json">` com schema `Product` e extrair `offers.price`.
5. **Mediana / heurística**: dentre todos os preços encontrados na página, pegar a mediana ou o maior abaixo de R$ 500. Buy Box raramente é o menor (cents de desconto) nem o maior (oferta cara de revenda).
6. **Install Scrapling deps que faltam**: o erro stealthy é `ModuleNotFoundError: No module named 'patchright'`. Rodar `pip3.11 install patchright camoufox playwright` e ver se StealthyFetcher passa a funcionar local. Cuidado: `curl_cffi` no macOS tem bug `_SCDynamicStoreCopyProxies` — pode bloquear. Se conseguir Scrapling local, é a melhor opção (mais robusto contra Amazon).
7. **Cache HTML local**: salvar HTML dos 5 SKUs em `tests/fixtures/*.html` na primeira iteração que rodar OK, e desenvolver/iterar regex contra fixture (zero rede, instantâneo).

## Workflow per iteration

1. Hipótese: qual approach acima.
2. Editar `scraper.py::_extract_price` (e/ou helpers).
3. Rodar `python3.11 -m pytest tests/ -v` — verde?
4. Rodar `python3.11 local_smoke.py` — quantos passam?
5. Se 5/5 → done.
6. Se regrediu (menos que baseline 3/5) → reverter ou ajustar.
7. Loop.

## Stop conditions

- 5/5 PASS no local_smoke.py.
- OU: tentou todos os approaches 1-7 sem sucesso → reporta lista de approaches tentados e razão de cada falha. Não tenta caminhos não listados sem reportar.

## Hard rules

- Nunca pular `pytest`.
- Nunca chamar mais de 5 URLs por iteração (1 por SKU). Cache em fixture se for iterar mais.
- Nunca commitar nem fazer push pra remote.
- Mantenha logs em stderr verbose pra debug.
