import threading
from collections import deque
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class MockConfig(BaseModel):
    delay_ms: int = Field(default=0, ge=0, le=120000)
    force_status: Optional[int] = Field(default=None, ge=100, le=599)
    drop_connection: bool = False
    invalid_json: bool = False
    omit_fields: List[str] = Field(default_factory=list)
    history_order: str = "asc"
    write_status: int = 202
    auth_enabled: bool = False
    auth_type: str = "basic"
    username: str = "piuser"
    password: str = "password123"


class EndpointFault(BaseModel):
    method: str = "GET"
    path: str
    status: Optional[int] = Field(default=None, ge=100, le=599)
    delay_ms: Optional[int] = Field(default=None, ge=0, le=120000)
    times: Optional[int] = None


class MockState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.config = MockConfig()
            self.faults: List[EndpointFault] = []
            self.quality: dict = {}
            self.requests: deque = deque(maxlen=20000)
            self.request_seq = 0

    def patch_config(self, patch: dict) -> MockConfig:
        with self.lock:
            data = self.config.model_dump()
            for key, value in patch.items():
                if value is not None:
                    data[key] = value
            self.config = MockConfig(**data)
            return self.config

    def add_fault(self, method: str, path: str, status, delay_ms, times=None) -> EndpointFault:
        fault = EndpointFault(method=method.upper(), path=path, status=status, delay_ms=delay_ms, times=times)
        with self.lock:
            self.faults.append(fault)
        return fault

    def match_fault(self, method: str, path: str) -> Optional[EndpointFault]:
        with self.lock:
            for fault in list(self.faults):
                if fault.method == method.upper() and fault.path == path:
                    if fault.times is not None:
                        fault.times -= 1
                        if fault.times <= 0:
                            self.faults.remove(fault)
                    return fault
        return None

    def clear_faults(self) -> None:
        with self.lock:
            self.faults = []

    def set_quality(self, key: str, good: bool, questionable: bool, substituted: bool) -> dict:
        record = {"good": good, "questionable": questionable, "substituted": substituted}
        with self.lock:
            self.quality[key.lower()] = record
        return record

    def get_quality(self, keys) -> Optional[dict]:
        with self.lock:
            for key in keys:
                if key and key.lower() in self.quality:
                    return dict(self.quality[key.lower()])
        return None

    def clear_quality(self) -> None:
        with self.lock:
            self.quality = {}

    def next_request_id(self) -> int:
        with self.lock:
            self.request_seq += 1
            return self.request_seq

    def record_request(self, entry: dict) -> None:
        with self.lock:
            self.requests.append(entry)

    def list_requests(self) -> List[dict]:
        with self.lock:
            return list(self.requests)

    def clear_requests(self) -> None:
        with self.lock:
            self.requests.clear()


state = MockState()
