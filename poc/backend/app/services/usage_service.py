import logging
import threading
import time

from poc.backend.app.domain.models import UsageSnapshot

logger = logging.getLogger(__name__)


class UsageService:
    def __init__(self, provider, cache_ttl: float = 60):
        self.provider = provider
        self.cache_ttl = cache_ttl
        self._cached: UsageSnapshot | None = None
        self._cached_at = 0.0
        self._lock = threading.Lock()

    def get_usage(self) -> UsageSnapshot:
        with self._lock:
            age = time.monotonic() - self._cached_at
            if self._cached is not None and age < self.cache_ttl:
                logger.info("usage cache hit")
                return self._cached
            logger.info("usage cache miss; querying provider")
            started = time.monotonic()
            snapshot = self.provider.get_usage()
            _validate(snapshot)
            self._cached, self._cached_at = snapshot, time.monotonic()
            logger.info("usage query completed in %.3fs", time.monotonic() - started)
            return snapshot


def _validate(snapshot: UsageSnapshot) -> None:
    for window in (snapshot.five_hour, snapshot.weekly):
        if not 0 <= window.remaining_percent <= 100:
            raise ValueError("Percentual restante inválido")
        if window.used_percent != 100 - window.remaining_percent:
            raise ValueError("Percentuais de uso e restante inconsistentes")
        if window.reset_at.tzinfo is None:
            raise ValueError("reset_at precisa ser timezone-aware")
