
import time

from prometheus_client import Counter, Histogram, make_asgi_app

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)
)

metrics_app = make_asgi_app()


async def record_metrics(request, call_next):
    if request.url.path.startswith("/metrics"):
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or "unmatched"

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
