"""Подключение к MongoDB."""
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import MONGO_DB, MONGO_URL
from exceptions import StorageUnavailableError


def get_database(url: str = MONGO_URL, name: str = MONGO_DB):
    client = MongoClient(url, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
    except PyMongoError as error:
        raise StorageUnavailableError(f"MongoDB недоступна: {error}") from None
    return client[name]
