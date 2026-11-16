
import threading
import time

from starlette.responses import JSONResponse


class RateLimitMiddleware:
    """
    Process-local fixed-window rate limiter.

    Limits requests to 60 per minute per client IP.
    Intended for a single-instance MVP deployment.
    """

    def __init__(self, app, limit=60, window_seconds=60):
        self.app = app
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = {}
        self.lock = threading.Lock()
        self.request_counter = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Exclude non-API routes and health checks.
        if not path.startswith("/v1/") or path == "/v1/health":
            await self.app(scope, receive, send)
            return

        # Identify the client IP.
        request_headers = dict(scope.get("headers", []))
        cf_ip = (
            request_headers.get(b"cf-connecting-ip", b"")
            .decode("latin-1")
            .strip()
        )

        client = scope.get("client")
        client_ip = cf_ip or (client[0] if client else "unknown")

        # Calculate fixed time window.
        now = int(time.time())
        window = now // self.window_seconds
        reset_at = (window + 1) * self.window_seconds

        with self.lock:
            entry = self.requests.get(client_ip)

            if entry is None or entry[0] != window:
                count = 1
            else:
                count = entry[1] + 1

            self.requests[client_ip] = (window, count)
            self.request_counter += 1

            # Periodically remove expired entries.
            if self.request_counter % 1000 == 0:
                self.requests = {
                    ip: value
                    for ip, value in self.requests.items()
                    if value[0] == window
                }

            allowed = count <= self.limit
            remaining = max(0, self.limit - count)

        # Standard rate-limit response headers.
        rate_limit_headers = [
            (b"x-ratelimit-limit", str(self.limit).encode()),
            (b"x-ratelimit-remaining", str(remaining).encode()),
            (b"x-ratelimit-reset", str(reset_at).encode()),
        ]

        if not allowed:
            retry_after = max(1, reset_at - now)

            response = JSONResponse(
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_at),
                    "Retry-After": str(retry_after),
                },
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later."
                    }
                }
            )

            await response(scope, receive, send)
            return

        # Add rate-limit headers to successful responses.
        async def send_with_rate_limit_headers(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.extend(rate_limit_headers)
                message["headers"] = response_headers

            await send(message)

        await self.app(scope, receive, send_with_rate_limit_headers)
