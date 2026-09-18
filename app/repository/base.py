from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.models.point import PointRecord
from app.models.value import ValueRecord


class Repository(ABC):
    @abstractmethod
    def reset(self, points: List[PointRecord], snapshots: Dict[str, ValueRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_points(self) -> List[PointRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_point_by_web_id(self, web_id: str) -> Optional[PointRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_point_by_path(self, path: str) -> Optional[PointRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_point_by_name(self, name: str) -> Optional[PointRecord]:
        raise NotImplementedError

    @abstractmethod
    def create_point(self, point: PointRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_snapshot(self, web_id: str) -> Optional[ValueRecord]:
        raise NotImplementedError

    @abstractmethod
    def set_snapshot(self, web_id: str, value: ValueRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    def query_recorded(
        self,
        web_id: str,
        start: Optional[float],
        end: Optional[float],
        max_count: Optional[int],
    ) -> List[ValueRecord]:
        raise NotImplementedError

    @abstractmethod
    def append_recorded(self, web_id: str, values: List[ValueRecord]) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_recorded(self, web_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear_recorded(self, web_id: str) -> None:
        raise NotImplementedError
