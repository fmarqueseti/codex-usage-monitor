from abc import ABC, abstractmethod

from poc.backend.app.domain.models import UsageSnapshot


class UsageProvider(ABC):
    @abstractmethod
    def get_usage(self) -> UsageSnapshot:
        raise NotImplementedError
