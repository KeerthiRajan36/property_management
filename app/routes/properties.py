from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin_or_manager
from app.exceptions import NotFoundError
from app.models.property import Property, PropertyType, PropertyStatus
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.property import PropertyCreate, PropertyUpdate, PropertyOut
from app.utils.audit import write_audit_log
from app.utils.pagination import PageParams, PaginatedResponse, paginate

router = APIRouter(prefix="/properties", tags=["Properties"])


def get_repo(db: Session = Depends(get_db)) -> BaseRepository:
    return BaseRepository(db, Property)


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    prop = repo.create(payload.model_dump())
    write_audit_log(db, current_user.id, "CREATE", "Property", prop.id)
    return prop


@router.get("", response_model=PaginatedResponse[PropertyOut])
def list_properties(
    property_type: Optional[PropertyType] = None,
    city: Optional[str] = None,
    status_: Optional[PropertyStatus] = Query(None, alias="status"),
    page: int = 1,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    query = repo.query()
    if property_type:
        query = query.filter(Property.property_type == property_type)
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if status_:
        query = query.filter(Property.status == status_)
    return paginate(query, Property, PageParams(page, limit, sort_by, sort_order))


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    repo: BaseRepository = Depends(get_repo),
):
    prop = repo.get(property_id)
    if not prop:
        raise NotFoundError("Property not found")
    return prop


@router.put("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    prop = repo.get(property_id)
    if not prop:
        raise NotFoundError("Property not found")
    prop = repo.update(prop, payload.model_dump(exclude_unset=True))
    write_audit_log(db, current_user.id, "UPDATE", "Property", prop.id)
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
    repo: BaseRepository = Depends(get_repo),
):
    prop = repo.get(property_id)
    if not prop:
        raise NotFoundError("Property not found")
    repo.soft_delete(prop)
    write_audit_log(db, current_user.id, "DELETE", "Property", property_id)
    return None
