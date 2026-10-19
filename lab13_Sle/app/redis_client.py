import redis

from config import REDIS_URL


def get_redis(url: str = REDIS_URL) -> redis.Redis:
    return redis.Redis.from_url(url, decode_responses=True, socket_timeout=1,
                                socket_connect_timeout=1)
