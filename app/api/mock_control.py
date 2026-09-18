from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app import repository
from app.core import config as config_module
from app.core import fault
from app.models.mock import (
    EndpointFaultIn,
    GenerateRequest,
    MockConfigPatch,
    QualityPatch,
    TagCreate,
)
from app.models.point import POINT_TYPES, PointRecord, build_path
from app.models.value import ValueRecord
from app.services import data_generator, point_service, stream_service

router = APIRouter(prefix="/mock", tags=["mock"])


@router.get("/config")
def get_config():
    return fault.state.config.model_dump()


@router.post("/config")
def set_config(patch: MockConfigPatch = Body(default_factory=MockConfigPatch)):
    data = patch.model_dump(exclude_none=True)
    if "history_order" in data and data["history_order"] not in ("asc", "desc", "random"):
        return JSONResponse(
            status_code=400,
            content={"Errors": ["history_order must be asc, desc or random."]},
        )
    if "write_status" in data and data["write_status"] not in (202, 204):
        return JSONResponse(
            status_code=400, content={"Errors": ["write_status must be 202 or 204."]}
        )
    if "auth_type" in data and data["auth_type"] not in ("basic",):
        return JSONResponse(
            status_code=400,
            content={"Errors": ["auth_type must be 'basic'."]},
        )
    config = fault.state.patch_config(data)
    return config.model_dump()


@router.post("/reset")
def reset():
    point_service.reset_to_defaults(config_module.settings)
    return {"success": True}


@router.post("/fault")
def add_fault(fault_in: EndpointFaultIn = Body(...)):
    created = fault.state.add_fault(
        fault_in.method, fault_in.path, fault_in.status, fault_in.delay_ms, fault_in.times
    )
    return created.model_dump()


@router.get("/faults")
def list_faults():
    return {"Items": [item.model_dump() for item in fault.state.faults]}


@router.delete("/faults")
def clear_faults():
    fault.state.clear_faults()
    return {"success": True}


@router.post("/tags")
def create_tag(payload: TagCreate = Body(...)):
    repo = repository.get_repo()
    if payload.point_type not in POINT_TYPES:
        return JSONResponse(
            status_code=400, content={"Errors": ["Unsupported PointType."]}
        )
    web_id = payload.web_id or ("POINT_" + payload.name.upper().replace(" ", "_"))
    point = PointRecord(
        web_id=web_id,
        name=payload.name,
        path=payload.path or build_path(config_module.settings.server_name, payload.name),
        descriptor=payload.descriptor,
        point_type=payload.point_type,
        engineering_units=payload.engineering_units,
        zero=payload.zero,
        span=payload.span,
        digital_set_name=payload.digital_set_name,
    )
    conflict = repo.find_point_conflict(point)
    if conflict:
        return JSONResponse(
            status_code=409,
            content={"Errors": [f"PI Point {conflict} already exists."]},
        )
    repo.create_point(point)
    if payload.snapshot is not None:
        value = stream_service.coerce_value(point.point_type, payload.snapshot)
        repo.set_snapshot(web_id, ValueRecord(value=value, good=payload.good))
    return point.to_dict()


@router.post("/tags/{tag}/quality")
def set_quality(tag: str, payload: QualityPatch = Body(...)):
    point = point_service.find_point(tag)
    if not point:
        return JSONResponse(
            status_code=404, content={"Errors": ["PI Point not found."]}
        )
    return fault.state.set_quality(
        point.name, payload.good, payload.questionable, payload.substituted
    )


@router.post("/data/generate")
def generate_data(request: GenerateRequest = Body(...)):
    point = point_service.find_point(request.tag)
    if not point:
        return JSONResponse(
            status_code=404, content={"Errors": ["PI Point not found."]}
        )
    records = data_generator.generate(point, request)
    repository.get_repo().append_recorded(point.web_id, records)
    return {"Generated": len(records), "Tag": point.name, "WebId": point.web_id}


@router.get("/requests")
def list_requests(limit: Optional[int] = None):
    items = fault.state.list_requests()
    if limit is not None:
        items = items[-limit:]
    return {"Items": items}


@router.delete("/requests")
def clear_requests():
    fault.state.clear_requests()
    return {"success": True}
