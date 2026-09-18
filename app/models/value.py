from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z") or text.endswith("z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    dt = dt.astimezone(timezone.utc)
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{dt.microsecond // 1000:03d}Z"


@dataclass
class ValueRecord:
    timestamp: Optional[datetime] = None
    value: Any = None
    good: bool = True
    questionable: bool = False
    substituted: bool = False
    raw_timestamp: Optional[str] = None
    null_timestamp: bool = False

    def epoch(self) -> float:
        if self.timestamp is None:
            return 0.0
        return self.timestamp.timestamp()

    def timestamp_text(self) -> Any:
        if self.null_timestamp:
            return None
        if self.raw_timestamp is not None:
            return self.raw_timestamp
        return format_timestamp(self.timestamp)

    def to_stream_dict(self, units: str = "") -> dict:
        return {
            "Timestamp": self.timestamp_text(),
            "Value": self.value,
            "UnitsAbbreviation": units,
            "Good": self.good,
            "Questionable": self.questionable,
            "Substituted": self.substituted,
        }
