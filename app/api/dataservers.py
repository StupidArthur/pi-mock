from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services import point_service

router = APIRouter(prefix="/piwebapi", tags=["dataservers"])


def server_item():
    name = settings.server_name
    web_id = point_service.server_web_id(name)
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


@router.get("/dataservers")
def list_dataservers():
    return {"Items": [server_item()]}


@router.get("/dataservers/{web_id}")
def get_dataserver(web_id: str):
    item = server_item()
    if web_id == item["WebId"] or web_id.lower() == item["Name"].lower():
        return item
    return JSONResponse(
        status_code=404, content={"Errors": ["Data Server not found."]}
    )
