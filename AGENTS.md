# Repository Guidelines

## Project Structure & Module Organization

The active application is a Tauri desktop app:

- `src/`: Vite frontend (`main.js`, `config.js`, `styles.css`).
- `src-tauri/`: Rust commands, Tauri configuration, icons, and Cargo files.
- `docs/`: Tauri/Docker documentation and security-audit artifacts.
- `bin/`: locally generated installers and AppImage output; keep them out of Git.
- `poc/`: archived Python CLI, FastAPI prototype, legacy frontend, and tests.

The frontend invokes the Rust `get_usage` command. Rust starts the locally
authenticated `codex app-server --stdio` process and reads
`account/rateLimits/read`.

## Build, Test, and Development Commands

```bash
npm install                         # Install frontend/Tauri tooling
npm run dev                         # Start the Vite development server
npm run tauri:build                 # Build locally with the Tauri toolchain
docker compose -f docker-compose.tauri.yml run --rm tauri-build
                                    # Reproducible Linux build; updates bin/
python3 -m unittest discover -s poc/tests -v
                                    # Test the archived Python POC
```

Run the packaged Linux app from `bin/appimage/`. The host must have an
authenticated `codex` executable available in `PATH`.

## Coding Style & Naming Conventions

Use two spaces for JavaScript and four spaces for Rust/Python. Use `camelCase`
for JavaScript functions/variables, `snake_case` for Rust/Python identifiers,
and uppercase `SCREAMING_SNAKE_CASE` for frontend constants. Keep refresh and
other user-facing settings in `src/config.js`, not inline in application logic.
Avoid new dependencies unless the existing toolchain cannot provide the need.

## Testing Guidelines

New Python behavior belongs in `poc/tests/test_*.py` and must use the standard
library test runner. For Tauri changes, at minimum run the Docker build, which
validates Vite bundling and Rust compilation. Manually verify the dashboard,
refresh button, error state, and real Codex usage response when available.

## Commit & Pull Request Guidelines

No usable Git history is available in this checkout, so follow concise
Conventional Commit-style messages, for example `fix: correct refresh interval`
or `docs: update Tauri setup`. Pull requests should describe behavior changes,
include validation commands and results, identify platform limitations, and
attach screenshots for visible dashboard changes.

## Security & Configuration

Never commit `.env`, Codex credentials, cookies, tokens, API keys, or generated
binary output. The application relies on Codex authentication on the host; do
not copy `~/.codex` into Docker or expose credentials to the frontend. Keep
`CODEX_COMMAND` limited to trusted local configuration and never derive it from
user input.
