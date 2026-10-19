"""Журнал HTTP-запросов и метрики (количество, ошибки, время ответа)."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("app.http")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s logistics-app %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    for noisy in ("aiormq", "aio_pika", "httpx", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class Metrics:
    def __init__(self) -> None:
        self.started = time.time()
        self.data: dict[str, dict] = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0.0})

    def observe(self, key: str, status: int, ms: float) -> None:
        item = self.data[key]
        item["count"] += 1
        item["total_ms"] += ms
        if status >= 500:
            item["errors"] += 1

    def snapshot(self) -> dict:
        endpoints = {
            k: {"count": v["count"], "errors": v["errors"], "avg_ms": round(v["total_ms"] / v["count"], 1)}
            for k, v in sorted(self.data.items())
        }
        return {
            "uptime_s": round(time.time() - self.started),
            "requests": sum(v["count"] for v in self.data.values()),
            "errors": sum(v["errors"] for v in self.data.values()),
            "endpoints": endpoints,
        }


class RequestLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics: Metrics) -> None:
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]
        started = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = rid
        path = request.url.path
        if path not in ("/health", "/metrics"):
            route = request.scope.get("route")
            self.metrics.observe(f"{request.method} {getattr(route, 'path', path)}", response.status_code, ms)
            log.info("[%s] %s %s status=%s duration=%.0fms", rid, request.method, path, response.status_code, ms)
        return response
