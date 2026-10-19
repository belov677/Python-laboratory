from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_all(self, drop: bool = False) -> None:
        import models.item  # noqa: F401  — регистрация моделей
        import models.user  # noqa: F401
        if drop:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
