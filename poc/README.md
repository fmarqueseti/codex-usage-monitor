# Codex Usage Monitor — POC Python

Esta pasta preserva a Proof of Concept original do Codex Usage Monitor. Ela
investiga formas de obter os limites de uso do Codex e fornece uma implementação
de linha de comando para testar o parsing e o App Server.

A POC não faz parte do aplicativo desktop Tauri atual, que está na raiz do
projeto.

## Objetivo

Responder se é possível obter programaticamente os dados apresentados pelo
`/status` do Codex:

- limite de 5 horas;
- limite semanal;
- percentual disponível e utilizado;
- horário/data do reset;
- tempo restante até o reset.

## Estrutura

```text
poc/
├── codex_usage.py             # CLI, modelos, providers e parser
├── backend/                   # MVP web experimental anterior
│   ├── app/
│   │   ├── domain/            # UsageWindow e UsageSnapshot
│   │   ├── providers/         # providers e factory
│   │   └── services/          # UsageService e cache
│   └── requirements.txt
├── frontend/                  # interface web/PWA anterior
├── tests/                     # testes unitários
├── status.example.txt         # exemplo de captura do /status
├── requirements.txt           # POC CLI, sem dependências externas
└── pyproject.toml             # metadados e dependências do backend anterior
```

## Requisitos

Para a CLI principal:

- Python 3.10+;
- biblioteca padrão do Python;
- Codex CLI instalado e autenticado para usar o App Server.

O backend experimental anterior requer FastAPI, Uvicorn e Pydantic, listados
em `backend/requirements.txt`. Ele não é necessário para executar a CLI nem o
aplicativo Tauri.

## Execução da CLI

A partir da raiz do repositório:

```bash
python3 poc/codex_usage.py
```

Sem `--input`, a POC inicia o App Server sem abrir a interface interativa do
Codex:

```text
codex app-server --stdio
  → initialize
  → initialized
  → account/rateLimits/read
```

O resultado é convertido para o modelo textual equivalente ao `/status` e,
em seguida, processado pelo parser.

## Testar com arquivo

Para testar sem depender do App Server:

```bash
cp poc/status.example.txt status.txt
python3 poc/codex_usage.py --input status.txt
python3 poc/codex_usage.py --input status.txt --json
python3 poc/codex_usage.py --input status.txt --raw
```

Também é possível usar uma captura real:

```bash
python3 poc/codex_usage.py --input /caminho/status.txt
```

O formato esperado contém as duas linhas:

```text
5h limit:     [████████████████████] 95% left (resets 19:11)
Weekly limit: [████████████████████] 99% left (resets 14:11 on 19 Sep)
```

Saída JSON inclui `source`, `captured_at`, as duas janelas, `reset_at` com
timezone e `seconds_until_reset`.

## Providers

| Provider | Fonte | Classificação | Uso |
|---|---|---|---|
| `AppServerProvider` | `codex app-server --stdio` | OFFICIAL / DOCUMENTED, experimental no CLI | principal/headless |
| `CliStatusProvider` | `codex /status` | FALLBACK | tentativa não interativa |
| `InputStatusProvider` | arquivo de texto | FALLBACK | testes e troubleshooting |
| `MockUsageProvider` | dados gerados localmente | EXPERIMENTAL | backend anterior |

O provider padrão da CLI é o `AppServerProvider`. A CLI não troca
silenciosamente para mock ou para dados inventados quando um provider falha.

## Parser

`parse_status()` interpreta percentuais de 0% a 100%, calcula:

```text
used_percent = 100 - remaining_percent
```

Também interpreta resets no timezone local do processo:

```text
resets 14:44
resets 09:44 on 19 Sep
```

Saída vazia, incompleta ou desconhecida gera `UsageError`; a POC não infere
valores ausentes.

## Testes

A partir da raiz:

```bash
python3 -m unittest discover -s poc/tests -v
```

Os testes cobrem percentuais, resets, virada de ano, saída incompleta,
formato desconhecido, provider mock e cache do serviço.

## Backend web experimental

O backend FastAPI anterior foi preservado para referência. Se suas dependências
estiverem instaladas:

```bash
pip install -r poc/backend/requirements.txt
uvicorn poc.backend.app.main:app --host 0.0.0.0 --port 8000
```

Ele expõe:

```text
GET /api/health
GET /api/usage
GET /docs
GET /redoc
```

Esse backend não é utilizado pelo Tauri. O cliente desktop consulta o App
Server diretamente através do Rust.

## Investigação e evidências

O Codex CLI instalado durante a investigação era `codex-cli 0.154.0`.

Comandos utilizados:

```bash
codex --version
which codex
file "$(which codex)"
codex app-server --help
codex app-server generate-json-schema --experimental --out /tmp/codex-schema-poc
```

O schema gerado pelo próprio App Server contém os métodos:

- `account/rateLimits/read`, com `usedPercent`, `resetsAt` e janelas primária/secundária;
- `account/usage/read`, voltado a buckets de uso/token, não às janelas 5h e semanal exibidas no `/status`.

O App Server foi considerado a interface estruturada mais adequada para a POC,
mas sua disponibilidade depende de rede, autenticação e evolução do protocolo.

## Classificação das fontes

| Método | Encontrado | Documentado | 5h/Weekly/Reset |
|---|---|---|---|
| `/status` | Sim, na UI interativa | FALLBACK, formato humano | Observado nas três informações |
| App Server `account/rateLimits/read` | Sim | OFFICIAL / DOCUMENTED, experimental no CLI | Modelado a partir de `usedPercent` e `resetsAt` |
| `account/usage/read` | Sim | OFFICIAL / DOCUMENTED | Não confirmado para essas janelas |
| Codex Analytics | Página conhecida | Não confirmado como contrato de integração | Não confirmado |
| Admin API | Referência pública conhecida | Documentada como Admin API | Não confirmado para quota pessoal do Codex |

Endpoints internos observados em erros do App Server, como `/backend-api/wham/*`,
são classificados como **OFFICIAL / INTERNAL** e não são chamados diretamente
por esta POC. Nenhum cookie, token, senha ou API key é armazenado no código.

## Limitações conhecidas

- `codex /status` exige TTY em algumas versões e não é uma fonte headless confiável.
- O App Server pode iniciar, mas falhar ao atualizar modelos ou ao consultar os
  serviços de uso por problemas de rede/autenticação.
- O protocolo App Server e seus schemas podem mudar entre versões do Codex.
- Analytics e Admin API não foram usados como scraping ou API pública nesta POC.
- O backend e o frontend desta pasta são históricos/experimentais; a direção
  ativa do projeto é o aplicativo Tauri na raiz.

## Relação com o projeto atual

```text
poc/codex_usage.py
  → investigação e referência Python

src-tauri/src/lib.rs
  → integração ativa do aplicativo desktop Tauri
```

A lógica da POC foi preservada para comparação e troubleshooting, mas novas
funcionalidades do produto devem ser implementadas no projeto Tauri.
