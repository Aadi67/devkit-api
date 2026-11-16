
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

        # Exclude health checks from rate limiting.
        if not path.startswith("/v1/") or path == "/v1/health":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        cf_ip = headers.get(b"cf-connecting-ip", b"").decode("latin-1").strip()

        client = scope.get("client")
        client_ip = cf_ip or (client[0] if client else "unknown")

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

            # Periodically remove expired client entries.
            if self.request_counter % 1000 == 0:
                self.requests = {
                    ip: value
                    for ip, value in self.requests.items()
                    if value[0] == window
                }

            allowed = count <= self.limit
            remaining = max(0, self.limit - count)

        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
        }

        if not allowed:
            retry_after = max(1, reset_at - now)
            headers["Retry-After"] = str(retry_after)

            response = JSONResponse(
                status_code=429,
                headers=headers,
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

        await self.app(scope, receive, send)
