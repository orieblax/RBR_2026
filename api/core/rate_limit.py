import time
from typing import Dict, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter middleware for FastAPI serverless endpoints.
    Allows up to max_requests within window_seconds per client IP.
    """
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.client_records: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Exclude static/health/docs checks from strict rate limiting
        path = request.url.path
        if path.startswith("/api/py/docs") or path.startswith("/api/py/openapi.json") or path == "/api/py/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - self.window_seconds

        # Clean timestamps older than window
        timestamps = self.client_records.get(client_ip, [])
        valid_timestamps = [t for t in timestamps if t > window_start]

        if len(valid_timestamps) >= self.max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Límite de solicitudes excedido. Por favor intenta de nuevo en unos segundos."
                },
                headers={"Retry-After": str(self.window_seconds)}
            )

        valid_timestamps.append(now)
        self.client_records[client_ip] = valid_timestamps

        response = await call_next(request)
        return response
