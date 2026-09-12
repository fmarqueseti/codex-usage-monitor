from datetime import datetime

from poc.codex_usage import UsageProvider as LegacyProvider, parse_status
from poc.backend.app.domain.models import UsageSnapshot, UsageWindow
from .base import UsageProvider


class LegacyAdapter(UsageProvider):
    def __init__(self, provider: LegacyProvider):
        self.provider = provider

    def get_usage(self) -> UsageSnapshot:
        source, raw = self.provider.read()
        captured = datetime.now().astimezone()
        data = parse_status(raw, captured)
        return UsageSnapshot(source, captured, _window(data["five_hour"]), _window(data["weekly"]))


def _window(data: dict) -> UsageWindow:
    return UsageWindow(
        data["name"], data["remaining_percent"], data["used_percent"],
        datetime.fromisoformat(data["reset_at"]), data["seconds_until_reset"], data["reset_text"],
    )
