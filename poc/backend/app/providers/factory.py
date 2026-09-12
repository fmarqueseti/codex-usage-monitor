import os
from pathlib import Path

from poc.codex_usage import AppServerProvider, CliStatusProvider, InputStatusProvider
from .legacy import LegacyAdapter
from .mock import MockUsageProvider


def build_provider(name: str | None = None):
    selected = (name or os.getenv("USAGE_PROVIDER", "app_server")).lower()
    command = os.getenv("CODEX_COMMAND", "codex")
    timeout = float(os.getenv("CODEX_APP_SERVER_TIMEOUT", "15"))
    if selected == "app_server":
        return LegacyAdapter(AppServerProvider(command, timeout))
    if selected == "cli":
        return LegacyAdapter(CliStatusProvider(command, timeout))
    if selected == "input":
        return LegacyAdapter(InputStatusProvider(Path(os.getenv("STATUS_INPUT", "status.txt"))))
    if selected == "mock":
        return MockUsageProvider()
    raise ValueError(f"Provider desconhecido: {selected}")
