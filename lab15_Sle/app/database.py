from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from models.models import Base


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, pool_pre_ping=True)
        self.session = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))

    def init(self, drop: bool = False) -> None:
        if drop:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
