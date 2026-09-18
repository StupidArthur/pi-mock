import fnmatch
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app import repository
from app.core import config as config_module
from app.services import point_service

router = APIRouter(prefix="/piwebapi", tags=["dataservers"])


def server_web_id() -> str:
    return point_service.server_web_id(config_module.settings.server_name)


def server_item():
    name = config_module.settings.server_name
    web_id = server_web_id()
    path = point_service.server_path(name)
    return {
        "WebId": web_id,
        "Name": name,
        "Path": path,
        "Links": {
            "Points": "/piwebapi/dataservers/" + web_id + "/points",
            "Self": "/piwebapi/dataservers/" + web_id,
        },
    }


def _match_server(value: str) -> bool:
    item = server_item()
    target = value.strip().lower()
    return target in (item["WebId"].lower(), item["Name"].lower(), item["Path"].lower())


@router.get("/dataservers")
def list_dataservers(
    name: Optional[str] = Query(default=None),
    path: Optional[str] = Query(default=None),
):
    if name is not None or path is not None:
        target = name if name is not None else path
        if _match_server(target):
            return server_item()
        return JSONResponse(
            status_code=404, content={"Errors": ["Data Server not found."]}
        )
    return {"Items": [server_item()]}


@router.get("/dataservers/{web_id}/points")
def list_server_points(
    web_id: str,
    nameFilter: Optional[str] = Query(default=None),
    maxCount: Optional[int] = Query(default=None, ge=0),
):
    item = server_item()
    if web_id.lower() not in (item["WebId"].lower(), item["Name"].lower()):
        return JSONResponse(
            status_code=404, content={"Errors": ["Data Server not found."]}
        )
    points = repository.get_repo().list_points()
    if nameFilter:
        pattern = nameFilter.lower()
        points = [point for point in points if fnmatch.fnmatch(point.name.lower(), pattern)]
    if maxCount is not None:
        points = points[:maxCount]
    return {"Items": [point.to_summary_dict() for point in points]}


@router.get("/dataservers/{web_id}")
def get_dataserver(web_id: str):
    if _match_server(web_id):
        return server_item()
    return JSONResponse(
        status_code=404, content={"Errors": ["Data Server not found."]}
    )
