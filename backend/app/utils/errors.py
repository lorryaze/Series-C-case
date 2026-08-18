"""Application error hierarchy.

Services raise these instead of ``HTTPException`` so business logic stays
independent of the transport layer; ``app.middleware.error_handler`` maps them to
the structured HTTP error envelope.
"""


class AppError(Exception):
    """Base class for all expected, client-facing failures."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    """A referenced entity does not exist."""

    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    """The request is well-formed but violates a business rule."""

    status_code = 422
    code = "validation_error"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"


class AuthenticationError(AppError):
    """Credentials are missing or invalid."""

    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(AppError):
    """The caller is authenticated but lacks the required role."""

    status_code = 403
    code = "permission_denied"
