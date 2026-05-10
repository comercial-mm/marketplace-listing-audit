# MVP para Giulia, da Reckitt

Auditor de URLs de Amazon BR. Confere preço, disponibilidade e EAN contra valores esperados informados pelo usuário.

## Dev local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Streamlit Community Cloud. Conectar repo público; entrypoint `app.py`.

## Estrutura

- `app.py`: UI Streamlit.
- `scraper.py`: Scrapling StealthyFetcher contra Amazon BR + rate limit.
- `comparator.py`: regras de classificação.
- `examples/reckitt_5_skus.py`: 5 SKUs do modo exemplo.
- `tests/`: testes pytest.

Spec completo em `SPEC.md`. Plano de implementação em `PLAN.md`.
