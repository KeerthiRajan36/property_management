import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """Records who did what, to which entity, and when. Used for security & compliance."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)  # CREATE / UPDATE / DELETE / LOGIN etc.
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    user = relationship("User")


class Notification(Base):
    """Lightweight in-app notification log (rent due, maintenance updates, etc.).
    A real deployment would fan these out over email/SMS/push; here they are
    persisted and can be listed via the API, and are also written to the
    application log by the notification service."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    message = Column(String(500), nullable=False)
    is_read = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
