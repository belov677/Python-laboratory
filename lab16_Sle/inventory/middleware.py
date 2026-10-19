import logging
import time

log = logging.getLogger("inventory.requests")


class RequestLogMiddleware:
    """Логирует метод, путь, пользователя, статус и время обработки запроса."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        ms = (time.perf_counter() - started) * 1000
        user = request.user.username if getattr(request, "user", None) and \
            request.user.is_authenticated else "anonymous"
        log.info("%s %s [%s] -> %s (%.1f мс)", request.method, request.get_full_path(), user,
                 response.status_code, ms)
        return response
