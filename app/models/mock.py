from typing import Any, List, Optional

from pydantic import BaseModel, Field


class MockConfigPatch(BaseModel):
    delay_ms: Optional[int] = Field(default=None, ge=0, le=120000)
    force_status: Optional[int] = Field(default=None, ge=100, le=599)
    drop_connection: Optional[bool] = None
    invalid_json: Optional[bool] = None
    omit_fields: Optional[List[str]] = None
    history_order: Optional[str] = None
    write_status: Optional[int] = None
    auth_enabled: Optional[bool] = None
    auth_type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class EndpointFaultIn(BaseModel):
    method: str = "GET"
    path: str
    status: Optional[int] = Field(default=None, ge=100, le=599)
    delay_ms: Optional[int] = Field(default=None, ge=0, le=120000)
    times: Optional[int] = Field(default=None, ge=1)


class QualityPatch(BaseModel):
    good: bool = True
    questionable: bool = False
    substituted: bool = False


class GenerateRequest(BaseModel):
    tag: str
    start: Optional[str] = None
    count: int = Field(ge=1, le=1000000)
    interval_ms: int = Field(default=1000, ge=1)
    generator: str = "sin"
    base: float = 50.0
    amplitude: float = 40.0
    period: int = 100
    slope: float = 1.0
    value: Optional[Any] = None
    timestamp_mode: str = "normal"
    duplicate_every: Optional[int] = Field(default=None, ge=2)
    end: Optional[str] = None


class TagCreate(BaseModel):
    name: str
    web_id: Optional[str] = None
    path: Optional[str] = None
    descriptor: str = ""
    point_type: str = "Float32"
    engineering_units: str = ""
    zero: float = 0
    span: float = 100
    digital_set_name: Optional[str] = None
    snapshot: Optional[Any] = None
    good: bool = True
