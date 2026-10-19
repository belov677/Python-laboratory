from __future__ import annotations

from sqlalchemy.orm import Session

from exceptions import AuthError, ConflictError
from models.user import Role, User
from repositories.user import UserRepository
from security import create_token, hash_password, verify_password


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = UserRepository(session)

    def register(self, username: str, password: str, role: Role = Role.USER) -> User:
        if self.repo.get_by_username(username):
            raise ConflictError(f"User {username} already exists")
        user = self.repo.add(User(username=username, password_hash=hash_password(password),
                                  role=role))
        self.session.commit()
        return user

    def login(self, username: str, password: str) -> str:
        user = self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Incorrect username or password")
        return create_token(user.username, user.role.value)

    def ensure_admin(self, username: str, password: str) -> None:
        if self.repo.get_by_username(username) is None:
            self.register(username, password, Role.ADMIN)
