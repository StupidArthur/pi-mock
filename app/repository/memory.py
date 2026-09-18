import threading
from typing import Dict, List, Optional

from app.models.point import PointRecord, normalize_path
from app.models.value import ValueRecord
from app.repository.base import Repository


class MemoryRepository(Repository):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._points: Dict[str, PointRecord] = {}
        self._snapshots: Dict[str, ValueRecord] = {}
        self._recorded: Dict[str, List[ValueRecord]] = {}

    def reset(self, points: List[PointRecord], snapshots: Dict[str, ValueRecord]) -> None:
        with self._lock:
            self._points = {point.web_id: point for point in points}
            self._snapshots = dict(snapshots)
            self._recorded = {point.web_id: [] for point in points}

    def list_points(self) -> List[PointRecord]:
        with self._lock:
            return list(self._points.values())

    def get_point_by_web_id(self, web_id: str) -> Optional[PointRecord]:
        with self._lock:
            return self._points.get(web_id)

    def get_point_by_path(self, path: str) -> Optional[PointRecord]:
        target = normalize_path(path)
        with self._lock:
            for point in self._points.values():
                if normalize_path(point.path) == target:
                    return point
            for point in self._points.values():
                if point.name.lower() == target or normalize_path(point.name) == target:
                    return point
        return None

    def get_point_by_name(self, name: str) -> Optional[PointRecord]:
        with self._lock:
            for point in self._points.values():
                if point.name.lower() == str(name).lower():
                    return point
        return None

    def create_point(self, point: PointRecord) -> None:
        with self._lock:
            self._points[point.web_id] = point
            self._recorded.setdefault(point.web_id, [])

    def get_snapshot(self, web_id: str) -> Optional[ValueRecord]:
        with self._lock:
            return self._snapshots.get(web_id)

    def set_snapshot(self, web_id: str, value: ValueRecord) -> None:
        with self._lock:
            self._snapshots[web_id] = value

    def query_recorded(
        self,
        web_id: str,
        start: Optional[float],
        end: Optional[float],
        max_count: Optional[int],
    ) -> List[ValueRecord]:
        with self._lock:
            values = list(self._recorded.get(web_id, []))
        result = []
        for item in values:
            epoch = item.epoch()
            if start is not None and epoch < start:
                continue
            if end is not None and epoch > end:
                continue
            result.append(item)
        result.sort(key=lambda item: item.epoch())
        if max_count is not None and len(result) > max_count:
            result = result[:max_count]
        return result

    def append_recorded(self, web_id: str, values: List[ValueRecord]) -> int:
        with self._lock:
            bucket = self._recorded.setdefault(web_id, [])
            bucket.extend(values)
        return len(values)

    def count_recorded(self, web_id: str) -> int:
        with self._lock:
            return len(self._recorded.get(web_id, []))

    def clear_recorded(self, web_id: str) -> None:
        with self._lock:
            self._recorded[web_id] = []
