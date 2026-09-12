import unittest
from datetime import datetime, timedelta, timezone

from poc.backend.app.domain.models import UsageSnapshot, UsageWindow
from poc.backend.app.services.usage_service import UsageService
from poc.backend.app.providers.mock import MockUsageProvider


def snapshot():
    now = datetime.now(timezone.utc)
    return UsageSnapshot(
        "test", now,
        UsageWindow("5-hour", 80, 20, now + timedelta(hours=1), 3600),
        UsageWindow("Weekly", 70, 30, now + timedelta(days=1), 86400),
    )


class CountingProvider:
    def __init__(self): self.calls = 0
    def get_usage(self): self.calls += 1; return snapshot()


class MvpTests(unittest.TestCase):
    def test_service_caches_provider(self):
        provider = CountingProvider()
        service = UsageService(provider, cache_ttl=60)
        service.get_usage(); service.get_usage()
        self.assertEqual(provider.calls, 1)

    def test_mock_provider_returns_both_windows(self):
        result = MockUsageProvider().get_usage()
        self.assertEqual(result.five_hour.used_percent, 25)
        self.assertEqual(result.weekly.remaining_percent, 82)

    def test_service_rejects_inconsistent_percentages(self):
        now = datetime.now(timezone.utc)
        bad = UsageSnapshot("test", now, UsageWindow("5-hour", 80, 0, now, 0), UsageWindow("Weekly", 70, 30, now, 0))
        with self.assertRaises(ValueError):
            UsageService(type("Provider", (), {"get_usage": lambda _: bad})(), 60).get_usage()


if __name__ == "__main__": unittest.main()
