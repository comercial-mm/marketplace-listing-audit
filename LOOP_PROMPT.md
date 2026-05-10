# Ralph Loop — Scrapling local working

## Goal

Fazer `StealthyFetcher().fetch(url, headless=True)` rodar com sucesso em ambiente local Mac Intel (Darwin x86_64), retornando HTML > 100KB de uma URL Amazon BR.

## Current state

- Mac: macOS Monterey 12.x, Intel x86_64.
- Homebrew Python 3.13.7 instalado em `/usr/local/bin/python3.13`.
- Venv em `/Users/fcamara/Projects/Claude/builder/.venv-scrapling/` com `scrapling[fetchers]` instalado.
- `scrapling install` rodou parcialmente (Playwright browsers + dependencies). publicsuffix.org SSL warning — não-fatal.
- **Erro atual**: `from scrapling.fetchers import StealthyFetcher` levanta:
  ```
  ImportError: dlopen(.../curl_cffi/_wrapper.abi3.so, 0x0002):
  symbol not found in flat namespace (_SCDynamicStoreCopyProxies)
  ```
- Causa: o wheel pré-compilado de `curl_cffi` (versão atual instalada) não linka com framework `SystemConfiguration` do macOS. `otool -L` mostra só `libc++` e `libSystem.B.dylib`, falta `/System/Library/Frameworks/SystemConfiguration.framework/SystemConfiguration`.

## Success criterion (verbatim)

```bash
source /Users/fcamara/Projects/Claude/builder/.venv-scrapling/bin/activate
cd /Users/fcamara/Projects/Claude/builder/experiments/2026-05-10-reckitt-audit-mvp
python -c "
from scrapling.fetchers import StealthyFetcher
p = StealthyFetcher().fetch('https://www.amazon.com.br/dp/B07PNK7TZK', headless=True, timeout=30000)
assert p.status == 200, f'status={p.status}'
assert len(p.html_content) > 100000, f'len={len(p.html_content)}'
print('OK', p.status, len(p.html_content))
"
```

Exit 0 e print `OK 200 <len>`.

## Approaches to try (in order)

1. **Recompile curl_cffi from source**: `pip uninstall curl_cffi -y && pip install --no-binary=:all: curl_cffi`. Requer libcurl headers (`brew install curl-impersonate` ou similar). Após compile, conferir `otool -L` mostra SystemConfiguration framework.

2. **Versão alternativa de curl_cffi**: testar `pip install 'curl_cffi==0.7.4'`, `0.8.0`, etc, até achar wheel que linke corretamente. Listar versões: `pip index versions curl_cffi`.

3. **Install via conda-forge**: `conda install -c conda-forge curl-cffi` — pode ter wheel diferente. Requer miniconda/mambaforge.

4. **install_name_tool patch**: `install_name_tool -change @rpath/SystemConfiguration.framework/SystemConfiguration /System/Library/Frameworks/SystemConfiguration.framework/SystemConfiguration .../_wrapper.abi3.so`. Ajusta o linkage do binário existente.

5. **Setar DYLD_FORCE_FLAT_NAMESPACE=0**: env var pra forçar two-level namespace na carga do .so. `DYLD_FORCE_FLAT_NAMESPACE=0 python -c "..."`.

6. **Set `DYLD_FALLBACK_FRAMEWORK_PATH`**: apontar pra location de SystemConfiguration. `DYLD_FALLBACK_FRAMEWORK_PATH=/System/Library/Frameworks python ...`.

7. **Use system Python (não framework)**: `/usr/bin/python3` é o Python do macOS (linka com tudo do sistema). Criar venv com ele e tentar.

8. **Use DynamicFetcher em vez de StealthyFetcher**: DynamicFetcher usa Playwright direto (sem Camoufox/curl_cffi). Pode dar resultado equivalente sem o problema do curl_cffi. Validar se `from scrapling.fetchers import DynamicFetcher; DynamicFetcher().fetch(url)` funciona.

9. **Bypass curl_cffi**: encontrar import path no scrapling que não dispara import de curl_cffi. Pode haver feature flag ou flag de runtime.

## Workflow per iteration

1. Hipótese: qual approach.
2. Executar comando(s).
3. Rodar success criterion bash above.
4. Se OK → done.
5. Se falhar → registrar erro, próxima approach.

## Stop conditions

- Critério atinge OK.
- OU: tentou todos approaches 1-9 sem sucesso → reportar lista de tentativas e razão de cada falha. Considerar cair pra fallback `requests` permanentemente.

## Hard rules

- Não mudar código do app/scraper só pra contornar o problema do StealthyFetcher (esse é objetivo separado). Foco aqui é fazer Scrapling rodar local.
- Não rodar `pip install` que afete o venv da vault principal. Só mexer em `.venv-scrapling`.
- Não chamar Amazon mais de 5 vezes (1 por iteração só).
- Logs verbose pra debug.
