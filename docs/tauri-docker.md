# Tauri e Docker

## Objetivo

O projeto agora possui um cliente desktop Tauri 2. A imagem `Dockerfile.tauri`
contém Rust, Node.js, dependências WebKitGTK e a CLI Tauri para reproduzir o
build Linux sem instalar essas ferramentas no host.

## Build

```bash
docker compose -f docker-compose.tauri.yml build
docker compose -f docker-compose.tauri.yml run --rm tauri-build
```

Os artefatos são copiados para `bin/` ao final do build. Eles também permanecem
em `src-tauri/target/release/bundle/` dentro do volume de cache. O build Linux
é validado em container Linux; executáveis Windows/macOS precisam ser
compilados em seus ambientes/toolchains próprios.

## Integração de uso

O cliente Tauri não usa valores fictícios. Ao abrir ou atualizar a tela, o
frontend chama o comando Rust `get_usage`, que inicia no host:

```text
codex app-server --stdio
  → initialize / initialized
  → account/rateLimits/read
  → dados estruturados para o dashboard
```

O executável `codex` precisa estar instalado e autenticado no ambiente em que o
binário Tauri for executado. O Docker serve para compilar o aplicativo; não é
runtime e não recebe `~/.codex` ou credenciais.

Se a consulta falhar, a interface exibe o erro. Ela não substitui a falha por
100% nem ativa o Mock Provider silenciosamente.

Containers Tauri GUI exigem encaminhamento de display (X11/Wayland), por isso o
container desta etapa é voltado ao build. Para desenvolvimento visual rápido,
use `npm install && npm run dev` no host ou configure explicitamente o display.

## Autenticação

Não copie `~/.codex` para a imagem. A futura integração desktop deve executar o
Codex no host e reutilizar a autenticação gerenciada localmente, sem expor
tokens ao frontend.
