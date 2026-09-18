from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app import repository
from app.services import point_service

router = APIRouter(prefix="/piwebapi", tags=["points"])


@router.get("/points")
def list_points(path: Optional[str] = Query(default=None)):
    repo = repository.get_repo()
    if path:
        point = repo.get_point_by_path(path)
        if not point:
            return JSONResponse(
                status_code=404, content={"Errors": ["PI Point not found."]}
            )
        return point.to_dict()
    return {"Items": [point.to_dict() for point in repo.list_points()]}


@router.get("/points/{web_id}")
def get_point(web_id: str):
    point = point_service.find_point(web_id)
    if not point:
        return JSONResponse(
            status_code=404, content={"Errors": ["PI Point not found."]}
        )
    return point.to_dict()
