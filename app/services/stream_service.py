import random
from typing import Any, List, Optional

from app.core import fault
from app.models.point import PointRecord
from app.models.value import ValueRecord, parse_timestamp
from app.services import point_service


class ValidationError(ValueError):
    pass


def coerce_value(point_type: str, value: Any):
    if value is None:
        raise ValidationError("Value must not be null.")
    if point_type in ("Float32", "Float64"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f"Value is not valid for point type {point_type}.")
        return float(value)
    if point_type in ("Int16", "Int32"):
        if isinstance(value, bool):
            raise ValidationError("Value is not valid for an integer point.")
        if isinstance(value, int):
            result = int(value)
        elif isinstance(value, float) and value.is_integer():
            result = int(value)
        else:
            raise ValidationError(f"Value is not valid for point type {point_type}.")
        if point_type == "Int16" and not (-32768 <= result <= 32767):
            raise ValidationError("Value is out of range for Int16.")
        return result
    if point_type == "Boolean":
        if not isinstance(value, bool):
            raise ValidationError("Value is not valid for a Boolean point.")
        return value
    if point_type == "String":
        if not isinstance(value, str):
            raise ValidationError("Value is not valid for a String point.")
        return value
    return value


def apply_quality(point: PointRecord, value: ValueRecord) -> ValueRecord:
    override = fault.state.get_quality(point_service.point_quality_keys(point))
    if override:
        value.good = override["good"]
        value.questionable = override["questionable"]
        value.substituted = override["substituted"]
    return value


def omit_fields(data: dict) -> dict:
    omit = fault.state.config.omit_fields
    if not omit:
        return data
    return {key: value for key, value in data.items() if key not in omit}


def value_response(point: PointRecord, value: ValueRecord) -> dict:
    return omit_fields(value.to_stream_dict(point.engineering_units))


def get_current_value(point: PointRecord) -> Optional[dict]:
    from app import repository

    snapshot = repository.get_repo().get_snapshot(point.web_id)
    if snapshot is None:
        return None
    snapshot = apply_quality(point, snapshot)
    return value_response(point, snapshot)


def get_recorded(
    point: PointRecord,
    start: Optional[str],
    end: Optional[str],
    max_count: Optional[int],
) -> List[dict]:
    from app import repository

    try:
        start_dt = parse_timestamp(start) if start else None
    except ValueError as error:
        raise ValueError(f"Invalid startTime: {error}") from error
    try:
        end_dt = parse_timestamp(end) if end else None
    except ValueError as error:
        raise ValueError(f"Invalid endTime: {error}") from error
    start_epoch = start_dt.timestamp() if start_dt else None
    end_epoch = end_dt.timestamp() if end_dt else None
    values = repository.get_repo().query_recorded(
        point.web_id, start_epoch, end_epoch, max_count
    )
    order = fault.state.config.history_order
    if order == "desc":
        values = list(reversed(values))
    elif order == "random":
        values = list(values)
        random.shuffle(values)
    return [value_response(point, apply_quality(point, value)) for value in values]


def write_value(point: PointRecord, timestamp: Any, value: Any) -> ValueRecord:
    from app import repository

    record = ValueRecord(
        timestamp=parse_timestamp(timestamp) if timestamp else None,
        value=coerce_value(point.point_type, value),
    )
    repo = repository.get_repo()
    repo.set_snapshot(point.web_id, record)
    repo.append_recorded(point.web_id, [record])
    return record


def write_recorded(point: PointRecord, items: List[dict]) -> int:
    from app import repository

    records = []
    for item in items:
        records.append(
            ValueRecord(
                timestamp=parse_timestamp(item.get("Timestamp")) if item.get("Timestamp") else None,
                value=coerce_value(point.point_type, item.get("Value")),
            )
        )
    repo = repository.get_repo()
    count = repo.append_recorded(point.web_id, records)
    if records:
        repo.set_snapshot(point.web_id, records[-1])
    return count
