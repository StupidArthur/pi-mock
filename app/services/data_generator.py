import math
import random
from datetime import datetime, timedelta, timezone
from typing import List

from app.models.point import PointRecord
from app.models.value import EPOCH, ValueRecord, parse_timestamp


def _numeric(request, index: int) -> float:
    generator = (request.generator or "sin").lower()
    base = request.base
    amplitude = request.amplitude
    period = max(request.period, 1)
    if generator in ("constant", "const"):
        if request.value is not None:
            try:
                return float(request.value)
            except (TypeError, ValueError):
                return base
        return base
    if generator in ("linear", "ramp"):
        return base + request.slope * index
    if generator == "random":
        return base + random.uniform(-amplitude, amplitude)
    if generator == "step":
        return base + (amplitude if (index // period) % 2 else 0.0)
    return base + amplitude * math.sin(2 * math.pi * index / period)


def _value_for(point: PointRecord, request, index: int):
    point_type = point.point_type
    if point_type == "String":
        if (request.generator or "").lower() == "status":
            return "RUNNING" if index % 2 == 0 else "STOPPED"
        return f"VALUE_{index}"
    if point_type == "Boolean":
        return index % 2 == 0
    raw = _numeric(request, index)
    if point_type in ("Int16", "Int32"):
        return int(round(raw))
    return round(float(raw), 4)


def _timestamp_record(dt: datetime, mode: str) -> ValueRecord:
    mode = (mode or "normal").lower()
    if mode == "epoch":
        return ValueRecord(timestamp=EPOCH)
    if mode == "future":
        return ValueRecord(timestamp=dt + timedelta(days=365 * 100))
    if mode == "no_tz":
        text = dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{dt.microsecond // 1000:03d}"
        return ValueRecord(timestamp=dt, raw_timestamp=text)
    if mode == "bad_format":
        return ValueRecord(timestamp=dt, raw_timestamp="not-a-timestamp")
    if mode == "null":
        return ValueRecord(timestamp=dt, null_timestamp=True)
    return ValueRecord(timestamp=dt)


def generate(point: PointRecord, request) -> List[ValueRecord]:
    if request.start:
        start = parse_timestamp(request.start) or datetime.now(timezone.utc)
    else:
        start = datetime.now(timezone.utc)
    records: List[ValueRecord] = []
    previous = None
    for index in range(request.count):
        dt = start + timedelta(milliseconds=request.interval_ms * index)
        if request.duplicate_every and index > 0 and index % request.duplicate_every == 0 and previous:
            dt = previous
        previous = dt
        record = _timestamp_record(dt, request.timestamp_mode)
        record.value = _value_for(point, request, index)
        records.append(record)
    return records
