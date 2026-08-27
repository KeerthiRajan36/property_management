import enum
import datetime

from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    PROPERTY_MANAGER = "property_manager"
    FACILITY_MANAGER = "facility_manager"
    MAINTENANCE_STAFF = "maintenance_staff"
    SECURITY_STAFF = "security_staff"
    TENANT = "tenant"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.TENANT, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")
