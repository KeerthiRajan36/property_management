from fastapi import Depends
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import AuthError, PermissionError_
from app.models.user import User, UserRole
from app.utils.security import decode_token

oauth2_scheme = HTTPBearer()


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = cred.credentials
    if not token:
        raise AuthError("Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise AuthError("Invalid or expired access token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_deleted.is_(False)).first()
    if not user:
        raise AuthError("User not found")
    if not user.is_active:
        raise AuthError("Account is deactivated")
    return user


def require_roles(*roles: UserRole):


    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise PermissionError_(
                f"Role '{current_user.role.value}' is not permitted to perform this action"
            )
        return current_user

    return checker


# Convenience shorthands used across routes
require_super_admin = require_roles(UserRole.SUPER_ADMIN)
require_admin_or_manager = require_roles(UserRole.SUPER_ADMIN, UserRole.PROPERTY_MANAGER)
require_staff = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.PROPERTY_MANAGER,
    UserRole.FACILITY_MANAGER,
    UserRole.MAINTENANCE_STAFF,
    UserRole.SECURITY_STAFF,
)
