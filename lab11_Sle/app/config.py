import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://lab:lab@localhost:5432/warehouse")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))
API_KEY = os.getenv("API_KEY", "secret-key")
