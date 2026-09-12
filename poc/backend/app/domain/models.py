from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UsageWindow:
    name: str
    remaining_percent: int
    used_percent: int
    reset_at: datetime
    seconds_until_reset: int
    reset_text: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "remaining_percent": self.remaining_percent,
            "used_percent": self.used_percent,
            "reset_text": self.reset_text,
            "reset_at": self.reset_at.isoformat(),
            "seconds_until_reset": self.seconds_until_reset,
        }


@dataclass(frozen=True)
class UsageSnapshot:
    source: str
    captured_at: datetime
    five_hour: UsageWindow
    weekly: UsageWindow

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "captured_at": self.captured_at.isoformat(),
            "five_hour": self.five_hour.to_dict(),
            "weekly": self.weekly.to_dict(),
        }
