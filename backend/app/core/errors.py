"""Domain Exceptions and Standard Error Codes."""

from typing import Optional, Dict, Any


class DomainException(Exception):
    """Base exception for all domain logic and operational rule failures."""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details or {}


class EntityNotFoundError(DomainException):
    """Raised when a requested domain entity does not exist."""
    def __init__(self, entity_type: str, entity_id: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=f"{entity_type.upper()}_NOT_FOUND",
            message=f"{entity_type} with identifier '{entity_id}' was not found.",
            status_code=404,
            field="id",
            details=details or {"entity_type": entity_type, "entity_id": str(entity_id)}
        )


class InvalidStateTransitionError(DomainException):
    """Raised when an illegal lifecycle state transition is requested."""
    def __init__(
        self,
        entity_type: str,
        current_state: str,
        target_state: str,
        allowed_transitions: Optional[list] = None
    ):
        super().__init__(
            code=f"{entity_type.upper()}_STATE_TRANSITION_INVALID",
            message=f"Cannot transition {entity_type} from state '{current_state}' to '{target_state}'.",
            status_code=409,
            field="status",
            details={
                "entity_type": entity_type,
                "current_state": current_state,
                "target_state": target_state,
                "allowed_transitions": allowed_transitions or []
            }
        )


class DomainValidationError(DomainException):
    """Raised when business domain invariants or parameters are violated."""
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=code or "DOMAIN_VALIDATION_FAILED",
            message=message,
            status_code=422,
            field=field,
            details=details
        )


class ConflictError(DomainException):
    """Raised when an entity uniqueness or association conflict occurs."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="RESOURCE_CONFLICT",
            message=message,
            status_code=409,
            field=field,
            details=details
        )
