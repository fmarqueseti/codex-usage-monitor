from datetime import datetime, timedelta

from poc.backend.app.domain.models import UsageSnapshot, UsageWindow
from .base import UsageProvider


class MockUsageProvider(UsageProvider):
    def get_usage(self) -> UsageSnapshot:
        now = datetime.now().astimezone()
        five_reset = now + timedelta(hours=2)
        week_reset = now + timedelta(days=4)
        return UsageSnapshot(
            "mock",
            now,
            UsageWindow("5-hour", 75, 25, five_reset, 7200, five_reset.strftime("%H:%M")),
            UsageWindow("Weekly", 82, 18, week_reset, 345600, week_reset.strftime("%H:%M on %-d %b")),
        )
