"""Зависимости FastAPI (Dependency Injection)."""
from __future__ import annotations

from collections.abc import Iterator

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from exceptions import AuthError, ForbiddenError
from models.user import Role, User
from repositories.user import UserRepository
from security import decode_token
from services.auth import AuthService
from services.item import ItemService

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.db.session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_item_service(request: Request, session: Session = Depends(get_session)) -> ItemService:
    return ItemService(session, request.app.state.cache)


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session)


def get_current_user(token: str = Depends(oauth2),
                     session: Session = Depends(get_session)) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise AuthError("Invalid or expired token") from None
    user = UserRepository(session).get_by_username(payload.get("sub", ""))
    if user is None:
        raise AuthError("User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role is not Role.ADMIN:
        raise ForbiddenError("Administrator role required")
    return user
