import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.point import PointRecord, build_path, normalize_path
from app.models.value import ValueRecord

DEFAULT_TAGS = [
    ("sinusoid", "POINT_SIN_001", "Mock sinusoid", "Float32", "", 0, 100, 25.0, True),
    ("temperature", "POINT_TEMP_001", "Mock temperature", "Float32", "degC", 0, 100, 25.5, True),
    ("pressure", "POINT_PRESS_001", "Mock pressure", "Float32", "kPa", 0, 200, 101.3, True),
    ("flow", "POINT_FLOW_001", "Mock flow", "Float32", "L/min", 0, 200, 50.0, True),
    ("status", "POINT_STATUS_001", "Mock status", "String", "", 0, 0, "RUNNING", True),
    ("counter", "POINT_COUNT_001", "Mock counter", "Int32", "count", 0, 1000000, 100, True),
    ("bad_quality", "POINT_BAD_001", "Mock bad quality", "Float32", "degC", 0, 100, 23.5, False),
    ("empty_tag", "POINT_EMPTY", "Mock empty tag", "Float32", "degC", 0, 100, None, True),
]

DEFAULT_BAD_QUALITY_KEYS = ["bad_quality", "point_bad_001"]


def server_web_id(server_name: str) -> str:
    return "SERVER_" + server_name.replace("-", "_").replace(" ", "_").upper()


def server_path(server_name: str) -> str:
    return "\\\\" + server_name


def default_points(server_name: str) -> List[PointRecord]:
    points = []
    for name, web_id, descriptor, point_type, units, zero, span, _value, _good in DEFAULT_TAGS:
        points.append(
            PointRecord(
                web_id=web_id,
                name=name,
                path=build_path(server_name, name),
                descriptor=descriptor,
                point_type=point_type,
                engineering_units=units,
                zero=zero,
                span=span,
                digital_set_name=None,
            )
        )
    return points


def default_snapshots(points: List[PointRecord]) -> Dict[str, ValueRecord]:
    from datetime import datetime, timezone

    by_name = {point.name: point.web_id for point in points}
    now = datetime.now(timezone.utc)
    snapshots: Dict[str, ValueRecord] = {}
    for name, web_id, _descriptor, _point_type, _units, _zero, _span, value, good in DEFAULT_TAGS:
        if value is None:
            continue
        target = by_name.get(name, web_id)
        snapshots[target] = ValueRecord(timestamp=now, value=value, good=good)
    return snapshots


def load_example(path: str, server_name: str) -> Optional[Tuple[List[PointRecord], Dict[str, ValueRecord]]]:
    from datetime import datetime, timezone

    example = Path(path)
    if not example.exists():
        return None
    with example.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    now = datetime.now(timezone.utc)
    points: List[PointRecord] = []
    snapshots: Dict[str, ValueRecord] = {}
    for item in data.get("points", []):
        name = item["name"]
        web_id = item.get("web_id") or ("POINT_" + name.upper())
        point = PointRecord(
            web_id=web_id,
            name=name,
            path=item.get("path") or build_path(server_name, name),
            descriptor=item.get("descriptor", ""),
            point_type=item.get("point_type", "Float32"),
            engineering_units=item.get("engineering_units", ""),
            zero=item.get("zero", 0),
            span=item.get("span", 100),
            digital_set_name=item.get("digital_set_name"),
        )
        points.append(point)
        if item.get("snapshot") is not None:
            snapshots[web_id] = ValueRecord(
                timestamp=now, value=item["snapshot"], good=item.get("good", True)
            )
    if not points:
        return None
    return points, snapshots


def seed_data(server_name: str, example_path: Optional[str] = None):
    loaded = load_example(example_path, server_name) if example_path else None
    if loaded:
        return loaded
    points = default_points(server_name)
    return points, default_snapshots(points)


def find_point(identifier: str) -> Optional[PointRecord]:
    from app import repository

    repo = repository.get_repo()
    if not identifier:
        return None
    point = repo.get_point_by_web_id(identifier)
    if point:
        return point
    point = repo.get_point_by_path(identifier)
    if point:
        return point
    return repo.get_point_by_name(identifier)


def point_quality_keys(point: PointRecord) -> List[str]:
    return [point.web_id, point.name, normalize_path(point.path)]


def bootstrap(settings) -> None:
    from app import repository
    from app.core import fault

    points, snapshots = seed_data(settings.server_name, settings.example_data_path)
    fault.state.reset()
    repository.get_repo().reset(points, snapshots)
    for key in DEFAULT_BAD_QUALITY_KEYS:
        fault.state.set_quality(key, False, True, False)
