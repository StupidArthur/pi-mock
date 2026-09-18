from typing import Any, Dict

from fastapi import APIRouter, Body

from app.services import point_service, stream_service

router = APIRouter(prefix="/piwebapi", tags=["batch"])


def _parse_stream_resource(resource: str):
    parts = [part for part in str(resource).split("?")[0].split("/") if part]
    if len(parts) >= 4 and parts[0] == "piwebapi" and parts[1] == "streams":
        return parts[2], parts[3]
    return None, None


def _handle(method: str, resource: str, content: Any) -> Dict[str, Any]:
    web_id, action = _parse_stream_resource(resource)
    if not web_id:
        return {"Status": 404, "Content": {"Errors": ["Batch resource not found."]}}
    point = point_service.find_point(web_id)
    if not point:
        return {"Status": 404, "Content": {"Errors": ["PI Point not found."]}}
    if method == "GET" and action == "value":
        data = stream_service.get_current_value(point)
        return {"Status": 200 if data is not None else 404, "Content": data}
    if method == "POST" and action == "value":
        stream_service.write_value(point, content.get("Timestamp"), content.get("Value"))
        return {"Status": 202, "Content": {"Written": True}}
    if method == "POST" and action == "recorded":
        count = stream_service.write_recorded(point, content)
        return {"Status": 202, "Content": {"WrittenCount": count}}
    return {"Status": 405, "Content": {"Errors": ["Method not supported for resource."]}}


@router.post("/batch")
def batch(payload: Dict[str, Any] = Body(default_factory=dict)):
    responses = []
    for request in payload.get("Requests", []):
        try:
            result = _handle(
                str(request.get("Method", "GET")).upper(),
                request.get("Resource", ""),
                request.get("Content"),
            )
        except (ValueError, stream_service.ValidationError) as error:
            result = {"Status": 400, "Content": {"Errors": [str(error)]}}
        responses.append(result)
    return {"Responses": responses}
