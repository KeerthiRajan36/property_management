from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError
from app.models.building import Building
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.building import BuildingCreate, BuildingUpdate, BuildingOut
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/buildings", tags=["Buildings"])


def get_repo(db: Session = Depends(get_db)) -> BaseRepository:
    return BaseRepository(db, Building)


@router.post("", response_model=BuildingOut, status_code=status.HTTP_201_CREATED)
def create_building(
    payload: BuildingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    building = repo.create(payload.model_dump())
    write_audit_log(db, current_user.id, "CREATE", "Building", building.id)
    return building


@router.get("", response_model=PaginatedResponse[BuildingOut])
def list_buildings(
    property_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    query = repo.query()
    if property_id:
        query = query.filter(Building.property_id == property_id)
    return paginate(query, Building, PageParams(page, limit, sort_by, sort_order))


@router.get("/{building_id}", response_model=BuildingOut)
def get_building(
    building_id: int,
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    building = repo.get(building_id)
    if not building:
        raise NotFoundError("Building not found")
    return building


@router.put("/{building_id}", response_model=BuildingOut)
def update_building(
    building_id: int,
    payload: BuildingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    building = repo.get(building_id)
    if not building:
        raise NotFoundError("Building not found")
    building = repo.update(building, payload.model_dump(exclude_unset=True))
    write_audit_log(db, current_user.id, "UPDATE", "Building", building.id)
    return building
