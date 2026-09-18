import json
import sqlite3
import threading
from typing import Dict, List, Optional

from app.models.point import PointRecord, normalize_path
from app.models.value import ValueRecord
from app.repository.base import Repository

SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    web_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    descriptor TEXT,
    point_type TEXT,
    engineering_units TEXT,
    zero REAL,
    span REAL,
    digital_set_name TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
    web_id TEXT PRIMARY KEY,
    ts REAL,
    value TEXT,
    good INTEGER,
    questionable INTEGER,
    substituted INTEGER,
    raw_ts TEXT,
    null_ts INTEGER
);
CREATE TABLE IF NOT EXISTS recorded (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    web_id TEXT NOT NULL,
    ts REAL,
    value TEXT,
    good INTEGER,
    questionable INTEGER,
    substituted INTEGER,
    raw_ts TEXT,
    null_ts INTEGER
);
CREATE INDEX IF NOT EXISTS idx_recorded_webid_ts ON recorded (web_id, ts);
"""


def _dump_value(value) -> str:
    return json.dumps(value)


def _load_value(text):
    if text is None:
        return None
    return json.loads(text)


class SQLiteRepository(Repository):
    def __init__(self, path: str) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def reset(self, points: List[PointRecord], snapshots: Dict[str, ValueRecord]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM points")
            self._conn.execute("DELETE FROM snapshots")
            self._conn.execute("DELETE FROM recorded")
            for point in points:
                self._insert_point(point)
            for web_id, value in snapshots.items():
                self._upsert_snapshot(web_id, value)
            self._conn.commit()

    def _point_from_row(self, row) -> PointRecord:
        return PointRecord(
            web_id=row["web_id"],
            name=row["name"],
            path=row["path"],
            descriptor=row["descriptor"] or "",
            point_type=row["point_type"] or "Float32",
            engineering_units=row["engineering_units"] or "",
            zero=row["zero"] or 0,
            span=row["span"] or 0,
            digital_set_name=row["digital_set_name"],
        )

    def _value_from_row(self, row) -> ValueRecord:
        from datetime import datetime, timezone

        ts = row["ts"]
        timestamp = None
        if ts is not None:
            timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
        return ValueRecord(
            timestamp=timestamp,
            value=_load_value(row["value"]),
            good=bool(row["good"]),
            questionable=bool(row["questionable"]),
            substituted=bool(row["substituted"]),
            raw_timestamp=row["raw_ts"],
            null_timestamp=bool(row["null_ts"]),
        )

    def list_points(self) -> List[PointRecord]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM points").fetchall()
        return [self._point_from_row(row) for row in rows]

    def get_point_by_web_id(self, web_id: str) -> Optional[PointRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM points WHERE web_id = ?", (web_id,)
            ).fetchone()
        return self._point_from_row(row) if row else None

    def get_point_by_path(self, path: str) -> Optional[PointRecord]:
        target = normalize_path(path)
        with self._lock:
            rows = self._conn.execute("SELECT * FROM points").fetchall()
        for row in rows:
            if normalize_path(row["path"]) == target:
                return self._point_from_row(row)
        for row in rows:
            if str(row["name"]).lower() == target or normalize_path(row["name"]) == target:
                return self._point_from_row(row)
        return None

    def get_point_by_name(self, name: str) -> Optional[PointRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM points WHERE lower(name) = ?", (str(name).lower(),)
            ).fetchone()
        return self._point_from_row(row) if row else None

    def _insert_point(self, point: PointRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO points "
            "(web_id, name, path, descriptor, point_type, engineering_units, zero, span, digital_set_name) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                point.web_id,
                point.name,
                point.path,
                point.descriptor,
                point.point_type,
                point.engineering_units,
                point.zero,
                point.span,
                point.digital_set_name,
            ),
        )

    def create_point(self, point: PointRecord) -> None:
        with self._lock:
            self._insert_point(point)
            self._conn.commit()

    def get_snapshot(self, web_id: str) -> Optional[ValueRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM snapshots WHERE web_id = ?", (web_id,)
            ).fetchone()
        return self._value_from_row(row) if row else None

    def _upsert_snapshot(self, web_id: str, value: ValueRecord) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO snapshots "
            "(web_id, ts, value, good, questionable, substituted, raw_ts, null_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                web_id,
                value.timestamp.timestamp() if value.timestamp else None,
                _dump_value(value.value),
                int(value.good),
                int(value.questionable),
                int(value.substituted),
                value.raw_timestamp,
                int(value.null_timestamp),
            ),
        )

    def set_snapshot(self, web_id: str, value: ValueRecord) -> None:
        with self._lock:
            self._upsert_snapshot(web_id, value)
            self._conn.commit()

    def query_recorded(
        self,
        web_id: str,
        start: Optional[float],
        end: Optional[float],
        max_count: Optional[int],
    ) -> List[ValueRecord]:
        query = "SELECT * FROM recorded WHERE web_id = ?"
        params: list = [web_id]
        if start is not None:
            query += " AND ts >= ?"
            params.append(start)
        if end is not None:
            query += " AND ts <= ?"
            params.append(end)
        query += " ORDER BY ts ASC, id ASC"
        if max_count is not None:
            query += " LIMIT ?"
            params.append(max_count)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._value_from_row(row) for row in rows]

    def append_recorded(self, web_id: str, values: List[ValueRecord]) -> int:
        if not values:
            return 0
        payload = [
            (
                web_id,
                value.timestamp.timestamp() if value.timestamp else None,
                _dump_value(value.value),
                int(value.good),
                int(value.questionable),
                int(value.substituted),
                value.raw_timestamp,
                int(value.null_timestamp),
            )
            for value in values
        ]
        with self._lock:
            self._conn.executemany(
                "INSERT INTO recorded "
                "(web_id, ts, value, good, questionable, substituted, raw_ts, null_ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                payload,
            )
            self._conn.commit()
        return len(payload)

    def count_recorded(self, web_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS total FROM recorded WHERE web_id = ?", (web_id,)
            ).fetchone()
        return int(row["total"]) if row else 0

    def clear_recorded(self, web_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM recorded WHERE web_id = ?", (web_id,))
            self._conn.commit()
