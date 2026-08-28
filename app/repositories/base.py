from typing import Generic, Type, TypeVar, Optional, List

from sqlalchemy.orm import Session, Query

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):

    def __init__(self, db: Session, model: Type[ModelType]):
        self.db = db
        self.model = model

    def _base_query(self) -> Query:
        query = self.db.query(self.model)
        if hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted.is_(False))
        return query

    def get(self, id_: int) -> Optional[ModelType]:
        return self._base_query().filter(self.model.id == id_).first()

    def list(self) -> List[ModelType]:
        return self._base_query().all()

    def query(self) -> Query:
        """Expose a filtered (soft-delete aware) query for further chaining
        by services that need custom filters/pagination."""
        return self._base_query()

    def create(self, obj_in: dict) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType, obj_in: dict) -> ModelType:
        for field, value in obj_in.items():
            if value is not None:
                setattr(obj, field, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def soft_delete(self, obj: ModelType) -> ModelType:
        if hasattr(obj, "is_deleted"):
            obj.is_deleted = True
            self.db.commit()
            self.db.refresh(obj)
        else:
            self.db.delete(obj)
            self.db.commit()
        return obj

    def hard_delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
