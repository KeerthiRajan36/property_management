import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
):
    """Persist an audit trail entry. Called from services after any
    create/update/delete/login action (Level 15 - Audit Logs)."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details, default=str) if details else None,
    )
    db.add(log)
    db.commit()
