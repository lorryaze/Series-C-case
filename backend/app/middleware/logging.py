"""Request logging middleware with per-request correlation ids."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")

RequestHandler = Callable[[Request], Awaitable[Response]]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Tag each request with an id and log its method, path, status and latency."""

    async def dispatch(self, request: Request, call_next: RequestHandler) -> Response:
        """Attach a request id, time the call and log the outcome."""
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id
        logger.info(
            "%s %s -> %s in %.1fms [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


def configure_logging(debug: bool) -> None:
    """Configure root logging once at application start-up."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
