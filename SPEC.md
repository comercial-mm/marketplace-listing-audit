# MVP Reckitt Audit — Design Spec

**Data**: 2026-05-10
**Owner**: Felipe (MyMetric)
**Estágio**: V0 demo / piloto gratuito

## Contexto

Reckitt contrata Lett pra checar disponibilidade e conteúdo dos produtos da Reckitt (Vanish, Veja, Finish, Harpic, Sustagen) em Amazon BR e Mercado Livre. Lett scrapeia os marketplaces e gera dashboard de quality check. Time da Reckitt (Nathaly, Nat, Giulia) abre o relatório 1x/semana, valida manualmente os alertas, e edita os anúncios quando confirma problema.

A dor: a Lett dá frequência alta de falso positivo. URLs alertadas como problema estão na verdade OK, e vice-versa. Time gasta tempo validando alertas falsos.

MyMetric quer oferecer ferramenta gratuita pra Reckitt validar alertas mais rapidamente, como porta de entrada pra projeto pago no futuro.

## Escopo do MVP (V0)

**Inclui**:
- Auditoria de disponibilidade: URL existe, produto está sendo vendido (botão comprar).
- Auditoria de preço da Buy Box (oferta principal), com tolerância configurável.
- Verificação opcional de EAN: anúncio aponta pro produto certo (detecta troca de produto).
- Apenas Amazon BR.
- Input via colagem manual em tabela editável dentro do app.
- Modo "exemplo Reckitt": 5 SKUs do PDF pré-populados pra descoberta zero-fricção.
- Teto diário de uso justo (rate limit): protege o app contra uso intenso, dado que o propósito é provar o conceito, não suportar uso recorrente.

**Não inclui (fica pra V1+)**:
- Conteúdo (título, descrição, imagens).
- Mercado Livre.
- Login, persistência, histórico, agendamento, alertas por email.
- Upload de CSV.
- Fila e delay pra >20 URLs por sessão.

## Usuário-alvo e cenário de uso

Giulia (Reckitt) recebe link do Streamlit Cloud pelo Felipe. Giulia é a responsável por checar disponibilidade na rotina semanal, então é a usuária mais aderente ao escopo do MVP (disponibilidade + preço). Acessa pelo browser, clica "Rodar exemplo Reckitt", vê dashboard com os 5 SKUs em ~30s. Depois cola lista de URLs alertadas pela Lett na tabela, com preço esperado, e roda. Avalia se ferramenta resolve a dor de validação manual. Se sim, marca call com Felipe.

Critério de sucesso V0: Giulia testa, confirma valor, marca call.

## Arquitetura

App Streamlit single-page, hospedado no Streamlit Community Cloud (free tier). Sem banco, sem login, sem persistência. Cada sessão é stateless.

### Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | UI Streamlit + orquestração |
| `scraper.py` | Fetch + parse de Amazon BR via Scrapling |
| `comparator.py` | Regras de comparação e classificação de status |
| `requirements.txt` | streamlit, scrapling |
| `.streamlit/config.toml` | Tema, configurações |
| `README.md` | Deploy e dev local |

### Interface entre módulos (contrato congelado)

`scraper.scrape_amazon_br(url: str) -> dict`:

```python
{
    "url": str,
    "ok": bool,                 # True se scrape rodou; False em erro
    "error": str | None,        # "404" | "blocked" | "timeout" | None
    "title": str | None,
    "price": float | None,      # em reais, sem símbolo
    "available": bool | None,
    "ean": str | None,
}
```

`comparator.classify(scrape: dict, expected: dict) -> dict`:

`expected` tem chaves: `preco_esperado: float`, `tolerancia_pct: float`, `ean_esperado: str | None`.

Retorno:

```python
{
    "status": "ok" | "problema" | "nao_verificavel",
    "flags": list[str],         # mensagens em pt-BR
}
```

## UX

### Home

Header com título **"MVP para Giulia, da Reckitt"** e 1 frase curta explicando o que faz.

Logo abaixo do header, `st.expander("Sobre este MVP", expanded=False)` com o conteúdo "Escopo do MVP (V0)" copiado da seção homônima deste spec (listas Inclui / Não inclui). Renderiza com cabeçalho "Escopo do MVP (V0)" e bullets pretos. Propósito: deixar Giulia consciente do que está e do que não está incluído antes de testar, evitando expectativa errada.

Duas seções verticais:

**Modo "Rodar exemplo Reckitt"**: 1 botão grande. Internamente já tem os 5 SKUs do PDF com URLs Amazon, EANs do código de barras e preço esperado de exemplo. Clica, app preenche a tabela e roda.

**Modo "Rodar minha lista"**: `st.data_editor` com 4 colunas:

| URL | Preço esperado (R$) | Tolerância (%) | EAN esperado (opcional) |
|---|---|---|---|

Default: 1 linha vazia, tolerância = 10%. Helper text na coluna EAN: "captura quando o lojista troca o produto do anúncio (deixe em branco se não souber)". Botão "Rodar verificação" abaixo.

### Output

Topo: 3 `st.metric` em colunas:
- 🟢 OK (n)
- 🔴 Problema real (n)
- ⚪ Não verificável (n)

Tabela 1 linha por produto, colunas: Status (emoji), Título extraído, Preço extraído, Disponível?, EAN extraído, Razão (texto da flag), URL (link encurtado).

Botão "Exportar CSV" ao lado da tabela.

## Lógica de scraping (Amazon BR)

`scrape_amazon_br(url)` usa `StealthyFetcher` do Scrapling (browser real com stealth bypass). Extrai 4 campos:

- **Título**: `<span id="productTitle">`.
- **Preço Buy Box**: `.a-price .a-offscreen` (primeira ocorrência da Buy Box; ignorar preços de outros sellers).
- **Disponível**: presença de `#add-to-cart-button` (botão "Adicionar ao carrinho") OU texto "Em estoque".
- **EAN/GTIN**: tabela de detalhes do produto, label "EAN" ou "Código GTIN-13" ou "GTIN".

Parsing de preço: trata `R$ 1.234,56` → `1234.56` (locale pt-BR).

Tratamento de erro:
- Status 404 → `error: "404"`.
- Captcha / página não-produto / anti-bot → `error: "blocked"`.
- Timeout > 30s → `error: "timeout"`.

## Rate limit (uso justo)

Propósito: o MVP é prova de conceito, não infraestrutura pra uso recorrente. O teto serve pra protegê-lo de virar ferramenta operacional sem o investimento em V1.

**Política**:
- Limite global do app: **100 scrapes por dia**, contados a partir de 00:00 UTC.
- Contador local em arquivo `usage.json` no diretório de execução, com formato `{"date": "YYYY-MM-DD", "count": int}`.
- Antes de cada scrape: ler arquivo, comparar data, resetar contador se data ≠ hoje, incrementar.
- Quando count >= 100: app não roda novos scrapes, mostra `st.warning` com texto: "Limite diário de uso justo do MVP atingido. Volte amanhã. Se precisar de mais volume, fale com o Felipe pra evoluir pra V1."
- Streamlit Cloud usa file system efêmero (zera com hibernação). Aceitável: limite efetivo pode ser maior, mas comportamento ainda funciona como freio inicial.
- Implementação no `scraper.py` ou em wrapper antes de chamar `scrape_amazon_br`. Decisão fica com agente Backend.

## Lógica de comparação

Pra cada URL com `ok=True`, aplica 3 checks independentes. Cada flag aparece com texto humano em pt-BR:

1. **Indisponibilidade**: `available == False` → flag `"Indisponível para compra"`.
2. **Preço fora da faixa**: faixa = `preco_esperado × (1 ± tolerancia_pct/100)`. Se `price` fora da faixa → flag `f"Preço R$ {price:.2f} fora da faixa esperada R$ {min:.2f} a R$ {max:.2f}"`.
3. **EAN não bate**: se `ean_esperado` preenchido e diferente de `ean` extraído → flag `"Anúncio aponta pra EAN diferente do esperado (possível troca de produto)"`.

Status final:
- `ok=False` → `nao_verificavel`, flag = error message.
- `ok=True` e sem flags → `ok`.
- `ok=True` e com flags → `problema`.

## Estratégia de execução (split paralelo)

Implementação dividida em 2 agentes paralelos com interface congelada:

**Agente Frontend**: cria `app.py` completo. Header "MVP para Giulia, da Reckitt", expander "Sobre este MVP" com escopo, 2 modos (exemplo / lista), estados, validação, renderização da tabela de output, exportar CSV. Usa stub `scraper.scrape_amazon_br` que retorna dict fake hardcoded (variando os 5 SKUs com diferentes status: 1 OK, 1 indisponível, 1 preço fora, 1 EAN diferente, 1 erro de scrape). Permite Felipe avaliar UX e fluxo no browser local enquanto backend é construído.

**Agente Backend**: cria `scraper.py` (Scrapling StealthyFetcher real contra Amazon BR + rate limit conforme seção dedicada) e `comparator.py` (regras acima). Inclui CLI de teste que roda os 5 URLs do PDF e printa output. Não toca em UI.

**Integração**: trivial. Substituir import do stub pelo módulo real (~5 linhas no `app.py`).

## Plano de teste

1. Local backend: `python -m scraper <url>` nos 5 URLs reais. Confirmar extração de título, preço, disponível, EAN.
2. Local frontend: `streamlit run app.py` com stub. Confirmar UX dos 2 modos, exportar CSV, métricas.
3. Após integração: forçar 1 alerta artificial (preço esperado errado) pra confirmar comparação detecta.
4. Deploy no Streamlit Cloud.
5. Felipe testa link público (acessa de browser sem cache, simulando primeira sessão da Nathaly).
6. Mandar pra Nathaly se OK.

## Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Anti-bot da Amazon bloqueia IP do Streamlit Cloud | Média | Se acontecer no deploy: trocar pra Hugging Face Spaces (IPs diferentes) ou plugar proxy residencial pago (~US$5/mês). Decisão sob demanda. |
| Cold start de 30s no free tier confunde Nathaly | Alta | Copy claro na home: "Primeira abertura demora ~30s, normal." UptimeRobot pinging fica pra V1. |
| Rate limit Amazon em listas grandes | Baixa em V0 | V0 assume <20 URLs/sessão. Documentar limite em V1. |
| Selectors quebrarem com mudança de layout Amazon | Média | Scrapling tem adaptive selectors. Se quebrar, ajuste manual em `scraper.py`. |

## Dependências externas

- Conta GitHub pra repo público (Streamlit Cloud puxa de lá).
- Conta Streamlit Community Cloud (free, login via GitHub).

## Não-objetivos explícitos

- Suportar mais de 20 URLs por sessão.
- Persistência ou histórico.
- Multi-marketplace.
- Multi-usuário ou autenticação.
- Conteúdo (título, descrição, imagens).
- Performance otimizada.

## Localização do código

- Workspace de dev: `builder/experiments/2026-05-10-reckitt-audit-mvp/`
- Repo público de deploy: a criar no GitHub do Felipe (provavelmente `mymetric/reckitt-audit-mvp` ou similar).
