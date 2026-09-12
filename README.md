# Codex Usage Monitor

Aplicativo desktop Linux para consultar e exibir os limites de uso do Codex.
O projeto ativo utiliza Tauri 2, Rust e um frontend leve em Vite/JavaScript.

## Overview

O aplicativo consulta o Codex App Server localmente, sem abrir uma sessão
interativa do Codex CLI:

```text
Frontend Tauri
    ↓ invoke("get_usage")
Comando Rust
    ↓
codex app-server --stdio
    ↓ account/rateLimits/read
Dashboard desktop
```

## Créditos e inspiração

Este projeto foi inspirado na ideia de [Adriano Santos](https://github.com/adrianosantostreina), 
que criou um monitor para o Claude Code. O Codex Usage Monitor adapta essa
ideia ao acompanhamento dos limites de uso do Codex.

O projeto foi elaborado integralmente com o auxílio da inteligência artificial
[OpenAI Codex](https://openai.com/codex/), incluindo a investigação técnica, a
implementação, a documentação e os testes.

A POC Python e o backend FastAPI anteriores foram preservados em `poc/` para
referência, testes e troubleshooting. Eles não fazem parte da execução do
aplicativo Tauri.

## Architecture

```text
index.html
└── src/
    ├── main.js       # dashboard, atualização e countdown
    └── styles.css    # interface responsiva

src-tauri/
├── src/lib.rs        # comando get_usage e comunicação JSON-RPC
├── src/main.rs       # entry point desktop
├── icons/            # ícones do aplicativo
└── tauri.conf.json   # configuração do bundle
```

O frontend não contém credenciais e não acessa endpoints do ChatGPT
diretamente. O processo Rust executa o `codex` instalado no host e utiliza a
autenticação gerenciada pelo próprio Codex.

## Requirements

Para executar o binário:

- Linux x86_64;
- Codex CLI instalado e autenticado;
- acesso de rede necessário ao App Server;
- bibliotecas de runtime WebKitGTK compatíveis com Tauri.

Para compilar pelo Docker, basta ter Docker e Docker Compose.

## Configuration

O executável procura `codex` no `PATH`. É possível alterar o nome/caminho por
variável de ambiente:

```bash
CODEX_COMMAND=/caminho/para/codex
```

Não configure senhas, cookies, tokens ou API keys. O container de build não
recebe credenciais do host.

## Running the packaged application

O AppImage gerado fica em `bin/appimage/`:

```bash
./bin/appimage/'Codex Usage Monitor_0.1.0_amd64.AppImage'
```

Também são gerados pacotes DEB e RPM em `bin/deb/` e `bin/rpm/`.

## Building with Docker

O Docker é utilizado como ambiente reproduzível de compilação, não como
ambiente de execução do aplicativo:

```bash
docker compose -f docker-compose.tauri.yml build
docker compose -f docker-compose.tauri.yml run --rm tauri-build
```

Os artefatos são copiados automaticamente para `bin/`. O build Linux deve ser
realizado em ambiente Linux; builds para Windows e macOS exigem os toolchains
correspondentes.

Detalhes do ambiente estão em [docs/tauri-docker.md](docs/tauri-docker.md).

## Development

Para desenvolvimento, instale Node.js, Rust e as dependências nativas do
Tauri no host:

```bash
npm install
npm run dev
npm run tauri:build
```

O build Docker é o caminho recomendado para gerar os artefatos Linux.

## Usage data

O comando Rust envia ao App Server:

```text
initialize
initialized
account/rateLimits/read
```

Os campos `usedPercent` e `resetsAt` são convertidos para os cartões de 5 horas
e semanal. O frontend calcula o countdown localmente e atualiza os dados a cada
15 minutos (configurável em `USAGE_REFRESH_INTERVAL_MINUTES`, em
`src/config.js`) ou quando o usuário pressiona `↻ Atualizar`.

Se a consulta falhar, o aplicativo apresenta o erro. Ele não substitui uma
falha por valores fictícios, não ativa um mock silenciosamente e não exibe 100%
como valor padrão.

## Current status

- cliente desktop Tauri 2 implementado;
- integração Rust com `codex app-server --stdio`;
- consulta `account/rateLimits/read`;
- dashboard com percentuais reais;
- barras de progresso e countdown local;
- atualização manual e automática;
- estados visuais para níveis críticos;
- AppImage, DEB e RPM gerados pelo Docker;
- POC Python preservada em `poc/`.

## Security

O aplicativo assume que o usuário já autenticou o Codex no próprio host. Não
são armazenados ou enviados pelo projeto senha do ChatGPT, cookies, tokens,
API keys ou credenciais no frontend.

O comando executado pelo Rust é fixo (`app-server --stdio`) e não pode ser
fornecido por requisições da interface.

## Limitations

- A integração depende da disponibilidade e compatibilidade do App Server da
  versão instalada do Codex.
- `account/rateLimits/read` pode evoluir junto com o App Server/CLI.
- Falhas de rede, autenticação ou atualização de modelos podem impedir a
  consulta.
- O container não possui a autenticação do host; o binário deve ser executado
  no host onde o Codex está instalado e autenticado.
- Ainda não há histórico, banco de dados, sincronização remota ou cloud.

## Archived POC

O diretório `poc/` contém o material anterior, mantido fora do build Tauri:

```text
poc/
├── codex_usage.py
├── backend/          # backend FastAPI anterior
├── frontend/         # frontend web anterior
├── tests/
├── status.example.txt
└── pyproject.toml
```

## Roadmap

Possíveis evoluções do aplicativo desktop: histórico local, gráficos, alertas,
seleção de providers, instaladores e suporte a outras plataformas desktop.
