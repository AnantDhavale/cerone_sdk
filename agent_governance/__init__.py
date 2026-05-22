"""Backward-compatible alias for the Cerone Python SDK."""

from cerone import (
    AgentCertificate,
    AgentWrapper,
    AuthenticationError,
    CeroneClient,
    CeroneException,
    CeroneResponse,
    InferredAgentProfile,
    InteractionMode,
    LocalErrorCategory,
    LocalValidationError,
    RateLimitError,
    SDKTelemetryEvent,
    TelemetryEventType,
    ValidationError,
    ValidationResult,
    __author__,
    __version__,
    infer_agent_profile_from_action,
)

AgentGovernanceClient = CeroneClient
AgentGovernanceResponse = CeroneResponse
AgentGovernanceException = CeroneException

__all__ = [
    "AgentGovernanceClient",
    "AgentGovernanceResponse",
    "AgentGovernanceException",
    "AgentCertificate",
    "AgentWrapper",
    "InferredAgentProfile",
    "SDKTelemetryEvent",
    "AuthenticationError",
    "InteractionMode",
    "LocalErrorCategory",
    "LocalValidationError",
    "RateLimitError",
    "TelemetryEventType",
    "ValidationError",
    "ValidationResult",
    "CeroneClient",
    "CeroneResponse",
    "CeroneException",
    "infer_agent_profile_from_action",
    "__author__",
    "__version__",
]
