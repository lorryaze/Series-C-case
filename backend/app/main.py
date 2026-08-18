"""FastAPI application factory."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware, configure_logging
from app.routers import audit, auth, feature_flags, kyc, refunds
from app.schemas.common import ErrorResponse

API_PREFIX = "/api"

DESCRIPTION = """
Shared platform behind three internal tools — **KYC review queue**, **refunds
dashboard** and **feature flags admin** — replacing low-code tooling with
maintainable, typed services.

Every tool reuses the same foundation: JWT auth with role-based access control,
an append-only audit trail, generic repositories and a single structured error
envelope, so adding a fourth tool costs a router, a service and a page.

**Roles**: `admin` (everything), `reviewer` (approve/reject/assign), `viewer`
(read-only). Sign in at `POST /api/auth/login`, then send
`Authorization: Bearer <token>`.
"""

TAGS_METADATA: list[dict[str, str]] = [
    {"name": "auth", "description": "Sign-in, current user and user provisioning."},
    {"name": "kyc", "description": "Compliance review queue with a full audit trail."},
    {"name": "refunds", "description": "Refund approvals plus dashboard metrics."},
    {"name": "feature-flags", "description": "Flag definitions and per-environment rollout."},
    {"name": "audit", "description": "Read the shared, append-only audit trail."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        responses={
            400: {"model": ErrorResponse, "description": "Business rule violation"},
            401: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
            403: {"model": ErrorResponse, "description": "Role lacks the required permission"},
            404: {"model": ErrorResponse, "description": "Entity not found"},
            409: {"model": ErrorResponse, "description": "Conflicting state"},
            422: {"model": ErrorResponse, "description": "Payload failed validation"},
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    api_router = APIRouter(prefix=API_PREFIX)
    api_router.include_router(auth.router)
    api_router.include_router(kyc.router)
    api_router.include_router(refunds.router)
    api_router.include_router(feature_flags.router)
    api_router.include_router(audit.router)
    app.include_router(api_router)

    @app.get(
        "/api/health",
        tags=["health"],
        summary="Liveness probe",
        description="Returns the service name, version and environment.",
    )
    def health() -> dict[str, str]:
        """Report that the API is up."""
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return app


app = create_app()
