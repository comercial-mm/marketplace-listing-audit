# MVP para Giulia, da Reckitt

Auditor de URLs de Amazon BR. Confere preço, disponibilidade e EAN contra valores esperados informados pelo usuário.

## Dev local

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Mac Intel: `_SCDynamicStoreCopyProxies` ImportError

O wheel padrão de `curl_cffi >= 0.14.0` (puxado por `scrapling[fetchers]`)
tem bug de linkage no macOS Intel x86_64 (não linka com framework
SystemConfiguration). Workaround é forçar curl_cffi 0.7.4 só localmente:

```bash
python3.13 -m venv .venv-scrapling
source .venv-scrapling/bin/activate
pip install "scrapling[fetchers]"
pip install "curl_cffi==0.7.4"  # downgrade pós scrapling
scrapling install                # baixa browsers Camoufox/Chromium
```

No Streamlit Cloud (Linux x86_64) o wheel padrão funciona, então
`requirements.txt` não pinna curl_cffi.

## Deploy

Streamlit Community Cloud. Conectar repo público; entrypoint `app.py`.

## Estrutura

- `app.py`: UI Streamlit.
- `scraper.py`: Scrapling StealthyFetcher contra Amazon BR + rate limit.
- `comparator.py`: regras de classificação.
- `examples/reckitt_5_skus.py`: 5 SKUs do modo exemplo.
- `tests/`: testes pytest.

Spec completo em `SPEC.md`. Plano de implementação em `PLAN.md`.
