import time

import streamlit as st
import pandas as pd
from scraper import scrape_amazon_br
from comparator import classify
from examples.reckitt_5_skus import EXAMPLE_SKUS


st.set_page_config(page_title="MVP Reckitt Audit", layout="wide")


@st.cache_resource
def _ensure_scrapling_browsers() -> tuple[bool, str]:
    """Roda `scrapling install` uma vez por container pra baixar browsers stealth
    (Camoufox/Chromium). Em Streamlit Cloud o filesystem é efêmero, então pode
    repetir a cada cold start (~30-60s na primeira execução)."""
    import subprocess
    try:
        result = subprocess.run(
            ["scrapling", "install"],
            capture_output=True, text=True, timeout=180,
        )
        ok = result.returncode == 0
        out = (result.stdout or "")[-300:] + " | " + (result.stderr or "")[-300:]
        return ok, out
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


with st.spinner("Preparando ambiente de scraping (~30s na primeira abertura)..."):
    _ensure_scrapling_browsers()


def _parse_price(v) -> float:
    """Aceita float, int ou string com decimal em '.' ou ','. Útil pra paste de
    Google Sheets em pt-BR (vírgula) ou en-US (ponto)."""
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "").replace("\xa0", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        # heurística: o último separador é decimal, o anterior é milhar
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _fmt_brl(v: float) -> str:
    """39.0 → '39,00' (formato pt-BR pro data_editor TextColumn)."""
    return f"{v:.2f}".replace(".", ",")


def _example_rows() -> list[dict]:
    return [
        {"URL": s["url"], "Preço esperado (R$)": _fmt_brl(s["preco_esperado"]),
         "Tolerância (%)": 10, "EAN esperado": s["ean_esperado"]}
        for s in EXAMPLE_SKUS
    ]


def _empty_rows() -> list[dict]:
    return [{"URL": "", "Preço esperado (R$)": "", "Tolerância (%)": 10, "EAN esperado": ""}]


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
- Input via colagem manual em tabela editável (cola direto do Google Sheets).

**Não inclui (fica pra V1+)**:
- Conteúdo (título, descrição, imagens).
- Mercado Livre.
- Login, persistência, histórico, agendamento, alertas por email.
- Upload de CSV.
- Fila e delay pra >20 URLs por sessão.
""")

st.info("Primeira abertura pode demorar ~30s (app dorme com inatividade).")

# ----------------------------------------------------------------------------
# Diagnóstico do servidor — desativado pra V0 (manter código pra V1).
# Reativar comentando o `if False:` abaixo se precisar debugar fetcher.
# ----------------------------------------------------------------------------
# with st.expander("🔧 Diagnóstico do servidor", expanded=False):
#     st.caption("Testa qual fetcher de scraping consegue rodar neste ambiente.")
#     if st.button("Rodar diagnóstico"):
#         import sys as _sys
#         import platform as _platform
#         st.write(f"**Python**: {_platform.python_version()} ({_sys.platform})")
#         try:
#             from scrapling.fetchers import StealthyFetcher
#             st.success("✅ Scrapling import OK")
#             try:
#                 _page = StealthyFetcher().fetch(
#                     "https://www.amazon.com.br/dp/B07PNK7TZK",
#                     headless=True, timeout=30000)
#                 st.success(f"✅ StealthyFetcher fetch OK: status={_page.status} len={len(_page.html_content)}")
#             except Exception as _e:
#                 st.error(f"❌ StealthyFetcher fetch falhou: {type(_e).__name__}: {str(_e)[:300]}")
#         except Exception as _e:
#             st.error(f"❌ Scrapling import falhou: {type(_e).__name__}: {str(_e)[:300]}")
#         try:
#             import requests as _req
#             _r = _req.get(
#                 "https://www.amazon.com.br/dp/B07PNK7TZK",
#                 headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
#                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
#                          "Accept-Language": "pt-BR,pt;q=0.9"},
#                 timeout=15)
#             st.success(f"✅ requests fallback OK: status={_r.status_code} len={len(_r.text)}")
#         except Exception as _e:
#             st.error(f"❌ requests fallback falhou: {type(_e).__name__}: {str(_e)[:300]}")

st.divider()
st.subheader("Lista de URLs pra auditar")
st.write("Cola URLs alertadas pela Lett (4 colunas, dá pra colar direto do Google Sheets). "
         "Os 5 SKUs do PDF Reckitt já vêm preenchidos como exemplo.")

if "input_rows" not in st.session_state:
    st.session_state["input_rows"] = _example_rows()

if st.button("Limpar tudo"):
    st.session_state["input_rows"] = _empty_rows()
    st.session_state["should_run"] = False
    st.rerun()

default_df = pd.DataFrame(st.session_state["input_rows"])

edited = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "URL": st.column_config.TextColumn("URL", required=True),
        "Preço esperado (R$)": st.column_config.TextColumn(
            "Preço esperado (R$)",
            help="Aceita ponto ou vírgula como separador decimal."),
        "Tolerância (%)": st.column_config.NumberColumn(min_value=0, max_value=100, default=10),
        "EAN esperado": st.column_config.TextColumn(
            "EAN esperado",
            help="Captura quando o lojista troca o produto do anúncio. Deixe em branco se não souber."),
    },
    key="data_editor",
)

if st.button("Rodar verificação", type="primary"):
    st.session_state["input_rows"] = edited.to_dict("records")
    st.session_state["should_run"] = True


def _run_audit(rows: list[dict]) -> tuple[list[dict], float]:
    results = []
    valid_rows = [r for r in rows if (r.get("URL") or "").strip()]
    if not valid_rows:
        return results, 0.0
    n = len(valid_rows)
    t0 = time.perf_counter()
    progress = st.progress(0.0, text=f"Buscando URLs... 0/{n}")
    for i, row in enumerate(valid_rows):
        scrape = scrape_amazon_br(row["URL"])
        ean_esp = (row.get("EAN esperado") or "").strip() or None
        expected = {
            "preco_esperado": _parse_price(row.get("Preço esperado (R$)")),
            "tolerancia_pct": float(row.get("Tolerância (%)") or 10),
            "ean_esperado": ean_esp,
        }
        verdict = classify(scrape, expected)
        if not ean_esp:
            ean_match = "—"
        elif scrape.get("ean") is None:
            ean_match = "—"
        elif scrape.get("ean") == ean_esp:
            ean_match = "✅"
        else:
            ean_match = "❌"
        results.append({**scrape, **verdict, "ean_match": ean_match})
        elapsed = time.perf_counter() - t0
        progress.progress((i + 1) / n, text=f"Buscando URLs... {i+1}/{n} ({elapsed:.1f}s)")
    progress.empty()
    return results, time.perf_counter() - t0


def _render_output(results: list[dict], elapsed_s: float):
    counts = {"ok": 0, "problema": 0, "nao_verificavel": 0}
    for r in results:
        counts[r["status"]] += 1

    n = len(results)
    avg = elapsed_s / n if n else 0.0
    st.caption(f"⏱ Auditou {n} URL(s) em {elapsed_s:.1f}s · média {avg:.1f}s/URL")

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
        "EAN bate?": r.get("ean_match", "—"),
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
    results, elapsed = _run_audit(st.session_state["input_rows"])
    if not results:
        st.warning("Nenhuma URL preenchida.")
    else:
        rate_limited = [r for r in results if r.get("error") == "rate_limit"]
        if rate_limited:
            st.error("Limite diário de uso justo do MVP atingido. "
                     "Volte amanhã. Se precisar de mais volume, fale com o Felipe pra evoluir pra V1.")
        else:
            _render_output(results, elapsed)
    st.session_state["should_run"] = False
