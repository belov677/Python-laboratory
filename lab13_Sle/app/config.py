import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "warehouse")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
CACHE_TTL = int(os.getenv("CACHE_TTL", "120"))
