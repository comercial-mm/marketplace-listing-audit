import streamlit as st
import pandas as pd
from scraper import scrape_amazon_br
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


def _run_audit(rows: list[dict]) -> list[dict]:
    results = []
    valid_rows = [r for r in rows if r.get("URL", "").strip()]
    if not valid_rows:
        return results
    progress = st.progress(0, text="Buscando URLs...")
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
        rate_limited = [r for r in results if r.get("error") == "rate_limit"]
        if rate_limited:
            st.error("Limite diário de uso justo do MVP atingido. "
                     "Volte amanhã. Se precisar de mais volume, fale com o Felipe pra evoluir pra V1.")
        else:
            _render_output(results)
    st.session_state["should_run"] = False
