from typing import Generic, List, TypeVar

from pydantic import BaseModel
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

T = TypeVar("T")


class PageParams:

    def __init__(
        self,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "id",
        sort_order: str = "asc",
    ):
        self.page = max(page, 1)
        self.limit = min(max(limit, 1), 200)
        self.sort_by = sort_by
        self.sort_order = sort_order


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    limit: int
    pages: int
    items: List[T]


def apply_sort(query: Query, model, sort_by: str, sort_order: str) -> Query:
    column = getattr(model, sort_by, None)
    if column is None:
        column = getattr(model, "id")
    return query.order_by(desc(column) if sort_order == "desc" else asc(column))


def paginate(query: Query, model, params: PageParams) -> dict:
    query = apply_sort(query, model, params.sort_by, params.sort_order)
    total = query.count()
    items = query.offset((params.page - 1) * params.limit).limit(params.limit).all()
    pages = (total + params.limit - 1) // params.limit if params.limit else 1
    return {
        "total": total,
        "page": params.page,
        "limit": params.limit,
        "pages": pages,
        "items": items,
    }
