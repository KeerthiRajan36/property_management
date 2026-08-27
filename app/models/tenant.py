from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False, index=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=False)
    identification_number = Column(String(60), unique=True, index=True, nullable=False)
    emergency_contact = Column(String(30), nullable=True)
    address = Column(String(300), nullable=True)
    # Optional link to a login-capable User account (role=tenant)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)

    user = relationship("User")
    leases = relationship("Lease", back_populates="tenant")
