#!/usr/bin/env python3
"""Small, standard-library-only Codex usage monitor POC."""

from __future__ import annotations

import argparse
import json
import re
import selectors
import shutil
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class UsageError(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageWindow:
    name: str
    remaining_percent: int
    used_percent: int
    reset_text: str
    reset_at: datetime
    seconds_until_reset: int

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "remaining_percent": self.remaining_percent,
            "used_percent": self.used_percent,
            "reset_text": self.reset_text,
            "reset_at": self.reset_at.isoformat(),
            "seconds_until_reset": self.seconds_until_reset,
        }


class UsageProvider(ABC):
    @abstractmethod
    def read(self) -> tuple[str, str]:
        """Return (source, human-readable status output)."""


class CliStatusProvider(UsageProvider):
    """Best-effort probe of the CLI; copied files remain the reliable fallback."""

    def __init__(self, executable: str = "codex", timeout: float = 8.0):
        self.executable = executable
        self.timeout = timeout

    def read(self) -> tuple[str, str]:
        executable = shutil.which(self.executable)
        if not executable:
            raise UsageError(
                "ERRO: não foi possível encontrar o executável 'codex'.\n"
                "Verifique: which codex"
            )
        try:
            result = subprocess.run(
                [executable, "/status"],
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            raise UsageError(_interactive_message(output)) from exc
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 and not _has_status_lines(output):
            if "auth" in output.lower() or "login" in output.lower():
                raise UsageError("ERRO: verifique a autenticação do Codex com 'codex login'.")
            raise UsageError(_interactive_message(output))
        return "codex /status", output


class AppServerProvider(UsageProvider):
    """Headless provider using the App Server JSON-RPC protocol."""

    def __init__(self, executable: str = "codex", timeout: float = 15.0):
        self.executable = executable
        self.timeout = timeout

    def read(self) -> tuple[str, str]:
        executable = shutil.which(self.executable)
        if not executable:
            raise UsageError("ERRO: não foi possível encontrar o executável 'codex'.\nVerifique: which codex")
        process = subprocess.Popen(
            [executable, "app-server", "--stdio"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            self._send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "codex-usage-monitor", "version": "0.1.0"},
                "capabilities": {},
            }})
            self._read_response(process, 1)
            self._send(process, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
            self._send(process, {"jsonrpc": "2.0", "id": 2, "method": "account/rateLimits/read", "params": {
                "excludeResetCreditDetails": True,
            }})
            response = self._read_response(process, 2)
            if "error" in response:
                error = response["error"]
                raise UsageError(f"App Server não conseguiu ler os limites: {error.get('message', error)}")
            return "codex app-server account/rateLimits/read", _rate_limits_to_status(response.get("result", {}))
        except (OSError, subprocess.SubprocessError) as exc:
            raise UsageError(f"ERRO ao iniciar o Codex App Server: {exc}") from exc
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    @staticmethod
    def _send(process, message: dict) -> None:
        if process.stdin is None:
            raise UsageError("App Server não abriu stdin.")
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def _read_response(self, process, request_id: int) -> dict:
        if process.stdout is None:
            raise UsageError("App Server não abriu stdout.")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + self.timeout
        try:
            while time.monotonic() < deadline:
                events = selector.select(max(0.1, deadline - time.monotonic()))
                if not events:
                    continue
                line = process.stdout.readline()
                if not line:
                    break
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise UsageError("App Server retornou uma mensagem JSON inválida.") from exc
                if message.get("id") == request_id:
                    return message
        finally:
            selector.close()
        raise UsageError("Tempo esgotado aguardando resposta do Codex App Server.")


def _rate_limits_to_status(result: dict) -> str:
    snapshots = result.get("rateLimitsByLimitId") or {}
    snapshot = snapshots.get("codex") or result.get("rateLimits") or {}
    windows = []
    for key in ("primary", "secondary"):
        window = snapshot.get(key)
        if isinstance(window, dict) and window.get("resetsAt") is not None and window.get("usedPercent") is not None:
            windows.append((window.get("windowDurationMins"), window))
    windows.sort(key=lambda pair: pair[0] if pair[0] is not None else 0)
    if len(windows) < 2:
        raise UsageError("Resposta do App Server não contém as janelas 5h e Weekly.")
    now = datetime.now().astimezone()
    lines = []
    for label, (_, window) in zip(("5h", "Weekly"), windows[:2]):
        used = int(window["usedPercent"])
        if not 0 <= used <= 100:
            raise UsageError("Resposta do App Server contém percentual inválido.")
        reset = datetime.fromtimestamp(int(window["resetsAt"]), tz=now.tzinfo)
        reset_text = reset.strftime("%H:%M")
        if reset.date() != now.date():
            reset_text += reset.strftime(" on %-d %b")
        bar = "█" * round((100 - used) / 100 * 20)
        lines.append(f"{label} limit: [{bar:<20}] {100 - used}% left (resets {reset_text})")
    return "\n".join(lines)


class InputStatusProvider(UsageProvider):
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> tuple[str, str]:
        try:
            return "status.txt", self.path.read_text(encoding="utf-8")
        except OSError as exc:
            if isinstance(exc, FileNotFoundError):
                raise UsageError(
                    f"ERRO: arquivo de entrada não encontrado: '{self.path}'.\n"
                    "Copie a saída de /status para esse arquivo ou informe outro caminho com --input."
                ) from exc
            raise UsageError(f"ERRO: não foi possível ler '{self.path}': {exc}") from exc


def _interactive_message(raw: str) -> str:
    detail = raw.strip()
    if "not a terminal" in detail.lower():
        detail = "O Codex exige entrada e saída conectadas a um terminal (TTY)."
    suffix = f"\nSaída capturada:\n{detail}" if detail else ""
    return (
        "A versão atual do Codex disponibiliza /status apenas em um terminal\n"
        "interativo. Utilize --input status.txt para validar o parser."
        + suffix
    )


def _has_status_lines(text: str) -> bool:
    return bool(re.search(r"(?im)^\s*(?:5h|weekly)\s+limit\s*:", text))


def _reset_datetime(reset_text: str, now: datetime) -> datetime:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?:\s+on\s+(\d{1,2})\s+([A-Za-z]{3,9}))?", reset_text.strip())
    if not match:
        raise UsageError(f"Formato de reset desconhecido: {reset_text!r}")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise UsageError(f"Horário de reset inválido: {reset_text!r}")
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if match.group(3):
        day = int(match.group(3))
        try:
            candidate = datetime.strptime(
                f"{now.year} {match.group(4)} {day} {hour}:{minute}", "%Y %B %d %H:%M"
            ).replace(tzinfo=now.tzinfo)
        except ValueError:
            try:
                candidate = datetime.strptime(
                    f"{now.year} {match.group(4)[:3]} {day} {hour}:{minute}", "%Y %b %d %H:%M"
                ).replace(tzinfo=now.tzinfo)
            except ValueError as exc:
                raise UsageError(f"Data de reset inválida: {reset_text!r}") from exc
        if candidate <= now:
            candidate = candidate.replace(year=candidate.year + 1)
    else:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
    return candidate


def parse_status(text: str, now: Optional[datetime] = None) -> dict:
    """Parse the human output of /status, rejecting incomplete/unknown output."""
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    windows = {}
    pattern = re.compile(
        r"^\s*(5h|weekly)\s+limit\s*:.*?\b(\d{1,3})%\s+left\s+\(\s*resets\s+([^)]*?)\s*\)", re.I
    )
    for line in text.splitlines():
        match = pattern.search(re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line))
        if not match:
            continue
        remaining = int(match.group(2))
        if remaining > 100:
            raise UsageError(f"Percentual inválido na saída: {line.strip()}")
        reset_text = " ".join(match.group(3).split())
        reset_at = _reset_datetime(reset_text, now)
        windows["five_hour" if match.group(1).lower() == "5h" else "weekly"] = UsageWindow(
            "5-hour" if match.group(1).lower() == "5h" else "Weekly",
            remaining, 100 - remaining, reset_text, reset_at,
            max(0, int((reset_at - now).total_seconds())),
        )
    if "five_hour" not in windows or "weekly" not in windows:
        raise UsageError(
            "Formato da saída do /status desconhecido ou incompleto; nenhum dado foi inferido.\n"
            "Saída bruta:\n" + (text.rstrip() or "<vazia>")
        )
    return {"five_hour": windows["five_hour"].as_dict(), "weekly": windows["weekly"].as_dict()}


def _duration(seconds: int) -> str:
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{days}d {hours:02d}h {minutes:02d}m" if days else f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render(data: dict) -> str:
    lines = ["╔══════════════════════════════════════════════════╗", "║              CODEX USAGE MONITOR                ║", "╠══════════════════════════════════════════════════╣"]
    for key in ("five_hour", "weekly"):
        item = data[key]
        label = item["name"]
        lines += [f"║ {label:<48}║", f"║ {'█' * round(item['remaining_percent'] / 100 * 24):<24} {item['remaining_percent']:>3}% available{' ' * (9 if item['remaining_percent'] < 100 else 6)}║", f"║ Used: {item['used_percent']}%{' ' * 41}║", f"║ Reset: {item['reset_text']:<40}║", f"║ In:    {_duration(item['seconds_until_reset']):<40}║", "║                                                  ║"]
    lines += ["╠══════════════════════════════════════════════════╣", f"║ Updated: {data['captured_at']:<39}║", "╚══════════════════════════════════════════════════╝"]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Monitora os limites exibidos pelo Codex /status.")
    parser.add_argument("--input", type=Path, help="arquivo com a saída copiada de /status")
    parser.add_argument("--json", action="store_true", help="produz JSON válido")
    parser.add_argument("--raw", action="store_true", help="mostra somente a saída bruta")
    args = parser.parse_args(argv)
    try:
        provider: UsageProvider = InputStatusProvider(args.input) if args.input else AppServerProvider()
        source, raw = provider.read()
        if args.raw:
            print(raw, end="" if raw.endswith("\n") else "\n")
            return 0
        captured = datetime.now().astimezone()
        data = {"source": source, "captured_at": captured.isoformat(), **parse_status(raw, captured)}
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else render(data))
        return 0
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
