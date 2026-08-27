import datetime

from sqlalchemy.orm import Session

from app.exceptions import AuthError, ConflictError
from app.models.user import User, RefreshToken
from app.schemas.auth import UserRegister
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.utils.audit import write_audit_log


def register_user(db: Session, payload: UserRegister) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ConflictError("A user with this email already exists")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit_log(db, user.id, "CREATE", "User", user.id, {"email": user.email})
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")
    if not user.is_active:
        raise AuthError("Account is deactivated")
    return user


def issue_token_pair(db: Session, user: User) -> dict:
    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id))
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    db.add(RefreshToken(user_id=user.id, token=refresh, expires_at=expires_at))
    db.commit()
    write_audit_log(db, user.id, "LOGIN", "User", user.id)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthError("Invalid or expired refresh token")
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == refresh_token, RefreshToken.revoked.is_(False))
        .first()
    )
    if not stored:
        raise AuthError("Refresh token has been revoked or does not exist")
    if stored.expires_at < datetime.datetime.utcnow():
        raise AuthError("Refresh token has expired")
    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")
    new_access = create_access_token(str(user.id), user.role.value)
    return {"access_token": new_access, "refresh_token": refresh_token, "token_type": "bearer"}


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.hashed_password):
        raise AuthError("Old password is incorrect")
    user.hashed_password = hash_password(new_password)
    db.commit()
    write_audit_log(db, user.id, "UPDATE", "User", user.id, {"action": "password_change"})
