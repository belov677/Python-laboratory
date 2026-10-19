"""Исследование CDN: заголовки, время ответа, первый и повторные запросы, cache busting."""
import time

import requests

ORIGIN = "http://127.0.0.1:5000"
CDN = "http://127.0.0.1:8090"
RESOURCES = ["/static/images/notebook.png", "/static/images/mouse.png",
             "/static/images/paper.png", "/static/css/style.css", "/static/js/app.js"]
HEADERS = ("Content-Type", "Content-Length", "Cache-Control", "Age", "X-Cache", "X-Edge")


def fetch(url: str) -> tuple[requests.Response, float]:
    start = time.perf_counter()
    response = requests.get(url, timeout=5)
    return response, (time.perf_counter() - start) * 1000


def main() -> None:
    print("=== Заголовки ответа: origin и CDN ===")
    for base, title in ((ORIGIN, "origin"), (CDN, "CDN")):
        response, ms = fetch(base + RESOURCES[0])
        print(f"[{title}] GET {base}{RESOURCES[0]} → {response.status_code}, {ms:.1f} мс")
        for h in HEADERS:
            if h in response.headers:
                print(f"    {h}: {response.headers[h]}")
    print("\n=== Первый и повторные запросы через CDN ===")
    print(f"{'ресурс':32} {'запрос':>6} {'X-Cache':>8} {'Age':>4} {'мс':>7} {'байт':>7}")
    for path in RESOURCES[1:]:
        for attempt in (1, 2, 3):
            response, ms = fetch(CDN + path)
            print(f"{path:32} {attempt:>6} {response.headers['X-Cache']:>8} "
                  f"{response.headers['Age']:>4} {ms:7.1f} {len(response.content):7}")
            time.sleep(1 if attempt == 2 else 0)
    print("\n=== Средняя задержка, 20 запросов ===")
    for base, title in ((ORIGIN, "origin напрямую"), (CDN, "через CDN (кэш)")):
        times = [fetch(base + RESOURCES[1])[1] for _ in range(20)]
        print(f"{title:18} среднее {sum(times) / len(times):6.2f} мс, мин {min(times):5.2f} мс")
    print("\n=== Cache busting: версионирование имени файла ===")
    for path in ("/static/css/style.v1.css", "/static/css/style.v1.css", "/static/css/style.v2.css"):
        response, ms = fetch(CDN + path)
        first_line = response.text.splitlines()[0]
        print(f"{path:26} {response.headers['X-Cache']:5} {first_line}")


if __name__ == "__main__":
    main()
