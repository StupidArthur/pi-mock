from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Query, Response
from fastapi.responses import JSONResponse

from app.core import fault
from app.services import point_service, stream_service

router = APIRouter(prefix="/piwebapi", tags=["streams"])


def _not_found():
    return JSONResponse(status_code=404, content={"Errors": ["PI Point not found."]})


@router.get("/streams/{web_id}/value")
def get_value(web_id: str):
    point = point_service.find_point(web_id)
    if not point:
        return _not_found()
    data = stream_service.get_current_value(point)
    if data is None:
        return JSONResponse(status_code=404, content={"Errors": ["No data found."]})
    return data


@router.get("/streams/{web_id}/recorded")
def get_recorded(
    web_id: str,
    startTime: Optional[str] = Query(default=None),
    endTime: Optional[str] = Query(default=None),
    maxCount: Optional[int] = Query(default=None, ge=0),
):
    point = point_service.find_point(web_id)
    if not point:
        return _not_found()
    items = stream_service.get_recorded(point, startTime, endTime, maxCount)
    return {"Items": items}


@router.post("/streams/{web_id}/value")
def write_value(web_id: str, payload: Dict[str, Any] = Body(...)):
    point = point_service.find_point(web_id)
    if not point:
        return _not_found()
    if not isinstance(payload, dict) or "Value" not in payload:
        return JSONResponse(status_code=400, content={"Errors": ["Value is required."]})
    try:
        stream_service.write_value(point, payload.get("Timestamp"), payload.get("Value"))
    except stream_service.ValidationError as error:
        return JSONResponse(status_code=400, content={"Errors": [str(error)]})
    except (ValueError, TypeError) as error:
        return JSONResponse(status_code=400, content={"Errors": [f"Invalid timestamp: {error}"]})
    status = fault.state.config.write_status
    if status == 204:
        return Response(status_code=204)
    return Response(status_code=status)


@router.post("/streams/{web_id}/recorded")
def write_recorded(web_id: str, items: List[Dict[str, Any]] = Body(...)):
    point = point_service.find_point(web_id)
    if not point:
        return _not_found()
    if not isinstance(items, list):
        return JSONResponse(status_code=400, content={"Errors": ["Body must be an array."]})
    try:
        count = stream_service.write_recorded(point, items)
    except stream_service.ValidationError as error:
        return JSONResponse(status_code=400, content={"Errors": [str(error)]})
    except (ValueError, TypeError) as error:
        return JSONResponse(status_code=400, content={"Errors": [f"Invalid timestamp: {error}"]})
    status = fault.state.config.write_status
    if status == 204:
        return Response(status_code=204)
    return JSONResponse(status_code=status, content={"WrittenCount": count})
