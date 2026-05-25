"""Cerone Python SDK."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import platform
import secrets
import warnings
from pathlib import Path
import time
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

import requests

try:
    import aiohttp

    _AIOHTTP_AVAILABLE = True
    _AIOHTTP_CLIENT_ERROR = aiohttp.ClientError
except ModuleNotFoundError:
    aiohttp = None
    _AIOHTTP_AVAILABLE = False

    class _AiohttpClientError(Exception):
        pass

    _AIOHTTP_CLIENT_ERROR = _AiohttpClientError

# Keep runtime version aligned with package metadata.
__version__ = "1.1.22"
__author__ = "Anant Dhavale"
ACCESS_URL = "https://www.homersemantics.com/ai-agent-governance-and-oauth"
SDK_NAME = "cerone-python-sdk"
SDK_RUNTIME = "python"

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])

# F18: maximum entries in the in-process validation cache (prevents unbounded growth)
_CACHE_MAX_SIZE = 1000


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ValidationResult(Enum):
    """Validation result enum."""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED  = "flagged"
    ERROR    = "error"


class InteractionMode(Enum):
    """High-level SDK interaction mode for telemetry and correlation."""

    CLIENT_LIFECYCLE = "client_lifecycle"
    TRIAL_BOOTSTRAP = "trial_bootstrap"
    AGENT_CREATE = "agent_create"
    SINGLE_VALIDATION = "single_validation"
    BATCH_VALIDATION = "batch_validation"
    TRUST_LOOKUP = "trust_lookup"
    AUDIT_LOOKUP = "audit_lookup"
    PRIVATE_REQUEST = "private_request"


class TelemetryEventType(Enum):
    """Observable SDK lifecycle and validation events."""

    CLIENT_INITIALIZED = "client_initialized"
    HOSTED_TRIAL_STARTED = "hosted_trial_started"
    TRIAL_TOKEN_RECEIVED = "trial_token_received"
    AGENT_CREATED = "agent_created"
    VALIDATION_ATTEMPTED = "validation_attempted"
    VALIDATION_RESULT_RECEIVED = "validation_result_received"
    BATCH_VALIDATION_ATTEMPTED = "batch_validation_attempted"
    LOCAL_ERROR = "local_error"


class LocalErrorCategory(Enum):
    """Structured local error categories before requests reach the backend."""

    MISSING_TOKEN = "missing_token"
    MISSING_AGENT_ID = "missing_agent_id"
    EMPTY_BATCH = "empty_batch"
    SERIALIZATION_ERROR = "serialization_error"
    INVALID_ACTION_SHAPE = "invalid_action_shape"
    WRAPPER_MISUSE = "wrapper_misuse"
    UNSUPPORTED_PATH = "unsupported_path"


@dataclass
class SDKTelemetryEvent:
    """Structured SDK-side telemetry event."""

    event_type: TelemetryEventType
    timestamp: str
    sdk_name: str
    sdk_version: str
    runtime: str
    client_session_id: str
    integration_id: Optional[str]
    auth_session_id: Optional[str]
    payload: Dict[str, Any]


@dataclass
class InferredAgentProfile:
    """A minimally inferred purpose/capability profile for agent creation."""

    purpose: str
    capabilities: List[str]
    inferred: bool
    action: Dict[str, Any]


@dataclass
class CeroneResponse:
    """Response from Cerone validation."""
    result: ValidationResult
    semantic_alignment: float
    trust_score: float
    violations: List[str]
    agent_id: str
    action: str
    timestamp: str
    latency_ms: int
    policy_families: List[str]
    matched_rule_ids: List[str]
    recommended_action: Optional[str] = None


@dataclass
class AgentCertificate:
    """Agent identity certificate."""
    agent_id: str
    purpose: str
    capabilities: List[str]
    trust_score: float
    signature: str
    created_at: str
    declared_purpose: Optional[str] = None
    declared_capabilities: Optional[List[str]] = None
    environment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CeroneException(Exception):
    """Base exception for Cerone SDK."""


class AuthenticationError(CeroneException):
    """Raised when API key is invalid."""


class ValidationError(CeroneException):
    """Raised when validation fails."""


class RateLimitError(CeroneException):
    """Raised when rate limit is exceeded."""


class LocalValidationError(ValidationError):
    """Raised for locally classified client-side issues before a request is sent."""

    def __init__(
        self,
        message: str,
        category: LocalErrorCategory,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.category = category
        self.details = details or {}


class _ClientRequestError(ValidationError):
    """Raised for non-retryable 4xx request errors."""


class _ServerError(ValidationError):
    """Raised for retryable 5xx server errors."""


def _normalize_tool_name(tool_name: Any) -> str:
    return tool_name.strip().lower() if isinstance(tool_name, str) else ""


def _infer_capability_from_tool(tool_name: str) -> str:
    normalized = _normalize_tool_name(tool_name)
    if normalized.startswith("database_") or normalized.startswith("db_"):
        return "db_write" if any(word in normalized for word in ("write", "update", "insert", "delete", "create")) else "db_read"
    if normalized.startswith("file_"):
        return "file_write" if any(word in normalized for word in ("write", "update", "create", "delete")) else "file_read"
    if normalized.startswith("api_") or normalized.endswith("_api"):
        return "api_call"
    if any(word in normalized for word in ("http", "fetch", "browse", "search", "network")):
        return "network_access"
    return normalized


def _describe_workspace_target(workspace_target: Optional[str]) -> str:
    if isinstance(workspace_target, str) and workspace_target.strip():
        return workspace_target.strip()
    return "source code, configuration, and project structure"


def _infer_purpose(required_capability: str, tool_name: str, workspace_target: str) -> str:
    if required_capability == "file_read":
        return (
            f"Perform {tool_name} operations to read files from a codebase and inspect {workspace_target} "
            "for source code analysis, configuration review, debugging, and implementation planning."
        )
    if required_capability == "file_write":
        return (
            f"Perform {tool_name} operations to update project files within {workspace_target} "
            "for software engineering changes, fixes, and implementation tasks."
        )
    if required_capability == "api_call":
        return (
            f"Perform {tool_name} operations to call development and service APIs needed for "
            "software engineering workflows, diagnostics, and implementation tasks."
        )
    if required_capability == "network_access":
        return (
            f"Perform {tool_name} operations to access network resources related to {workspace_target} "
            "for software engineering research, dependency inspection, and debugging."
        )
    if required_capability == "db_read":
        return (
            f"Perform {tool_name} operations to read database records needed for debugging, "
            "system analysis, and software engineering investigation."
        )
    if required_capability == "db_write":
        return (
            f"Perform {tool_name} operations to update database records required for controlled "
            "software engineering workflows and operational fixes."
        )
    return (
        f"Perform {tool_name} operations to work with {workspace_target} "
        "for software engineering, debugging, and workflow tasks."
    )


def infer_agent_profile_from_action(
    action: Any,
    parameters: Optional[Dict[str, Any]] = None,
    *,
    purpose: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    workspace_target: Optional[str] = None,
) -> InferredAgentProfile:
    """Infer a lightweight purpose/capability profile from a validation action."""

    if isinstance(action, dict):
        tool_name = action.get("tool")
        action_parameters = action.get("parameters", parameters or {})
    else:
        tool_name = action
        action_parameters = parameters or {}

    if not isinstance(tool_name, str) or not tool_name.strip():
        raise LocalValidationError(
            "Action must be a non-empty string or an action dict with a non-empty 'tool' field.",
            LocalErrorCategory.INVALID_ACTION_SHAPE,
            {"action": action},
        )
    if not isinstance(action_parameters, dict):
        raise LocalValidationError(
            "Action parameters must be a dictionary.",
            LocalErrorCategory.INVALID_ACTION_SHAPE,
            {"action": action},
        )

    required_capability = _infer_capability_from_tool(tool_name)
    resolved_capabilities = list(capabilities) if capabilities else [required_capability]
    resolved_purpose = (
        purpose.strip()
        if isinstance(purpose, str) and purpose.strip()
        else _infer_purpose(required_capability, tool_name, _describe_workspace_target(workspace_target))
    )
    inferred = not (isinstance(purpose, str) and purpose.strip()) and not capabilities

    return InferredAgentProfile(
        purpose=resolved_purpose,
        capabilities=resolved_capabilities,
        inferred=inferred,
        action={"tool": tool_name, "parameters": action_parameters},
    )


class CeroneClient:
    """Cerone API client for validating AI agent actions."""

    _IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.homersemantics.com",
        timeout: int = 30,
        max_retries: int = 3,
        enable_cache: bool = False,
        retry_non_idempotent: bool = False,
        integration_id: Optional[str] = None,
        client_session_id: Optional[str] = None,
        telemetry_hook: Optional[Callable[[SDKTelemetryEvent], None]] = None,
        telemetry_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Cerone client.

        Args:
            api_key: Your Cerone API key. If omitted, the client will attempt
                to bootstrap an anonymous hosted trial token automatically.
            base_url: API endpoint (default: production).
            timeout: Request timeout in seconds.
            max_retries: Number of retry attempts for eligible requests.
            enable_cache: Enable local caching of high-trust validations.
                          Cache is bounded to 1,000 entries (LRU eviction).
            retry_non_idempotent: Retry POST/PUT/PATCH/DELETE on transport
                errors. Defaults to False to avoid duplicate side effects.
            integration_id: Optional stable identifier for the host integration,
                wrapper, or app embedding this SDK.
            client_session_id: Optional caller-provided local run/session id.
                If omitted, the SDK creates one.
            telemetry_hook: Optional callback invoked with structured SDK-side
                lifecycle and validation events.
            telemetry_metadata: Optional static metadata merged into emitted
                SDK telemetry events.
        """
        self.api_key = None
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.enable_cache = enable_cache
        self.retry_non_idempotent = retry_non_idempotent
        self.integration_id = integration_id
        self.client_session_id = client_session_id or f"csn_{secrets.token_hex(8)}"
        self.telemetry_hook = telemetry_hook
        self.telemetry_metadata = dict(telemetry_metadata or {})
        self._trial_token_path = Path.home() / ".cerone" / "trial_token"
        self._auth_session_id: Optional[str] = None
        self._request_sequence = 0

        # F18: bounded LRU cache — plain dict grows unboundedly in long-running
        # processes; OrderedDict with a size cap gives O(1) eviction.
        self._cache: Optional[OrderedDict] = OrderedDict() if enable_cache else None

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": f"{SDK_NAME}/{__version__}",
                "X-Cerone-SDK-Name": SDK_NAME,
                "X-Cerone-SDK-Version": __version__,
                "X-Cerone-Runtime": SDK_RUNTIME,
                "X-Cerone-Platform": platform.system().lower(),
                "X-Cerone-Python-Version": platform.python_version(),
                "X-Cerone-Client-Session": self.client_session_id,
            }
        )
        self._async_session: Optional[Any] = None
        if self.integration_id:
            self._session.headers["X-Cerone-Integration-Id"] = self.integration_id
        if api_key:
            self._apply_api_key(api_key)

        self._emit_event(
            TelemetryEventType.CLIENT_INITIALIZED,
            base_url=self.base_url,
            has_api_key=bool(api_key),
            integration_id=self.integration_id,
        )

    # ------------------------------------------------------------------
    # Certificate / agent management
    # ------------------------------------------------------------------

    def create_agent(
        self,
        purpose: str,
        capabilities: Optional[List[str]] = None,
        environment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentCertificate:
        """Create a new agent with cryptographic identity."""
        declared_purpose = purpose
        declared_capabilities = list(capabilities or [])
        payload: Dict[str, Any] = {
            "purpose": declared_purpose,
            "capabilities": declared_capabilities,
        }
        if environment:
            payload["environment"] = environment
        if metadata:
            payload["metadata"] = metadata
        response = self._request(
            "POST",
            "/v1/certificates",
            **self._request_kwargs(
                "sdk_create_agent_called",
                InteractionMode.AGENT_CREATE,
                json=payload,
                _allow_private_request=True,
            ),
        )

        # AZTP canonical response:
        # {
        #   "certificate": {"agent_id", "purpose", "capabilities", "signature", "issued_at", ...},
        #   "trust_score": ...
        # }
        # Keep backwards compatibility with older flat responses.
        cert_data = response.get("certificate") if isinstance(response, dict) else None
        if not isinstance(cert_data, dict):
            cert_data = response

        agent_id = cert_data.get("agent_id") or response.get("agent_id")
        if not agent_id:
            raise ValidationError("Missing agent_id in create_agent response")

        certificate = AgentCertificate(
            agent_id=agent_id,
            purpose=cert_data.get("purpose", declared_purpose),
            capabilities=cert_data.get("capabilities", declared_capabilities),
            trust_score=response.get("trust_score", cert_data.get("trust_score", 0.0)),
            signature=cert_data.get("signature", response.get("signature", "")),
            created_at=cert_data.get(
                "issued_at",
                response.get("created_at", response.get("issued_at", "")),
            ),
            declared_purpose=declared_purpose,
            declared_capabilities=declared_capabilities,
            environment=environment,
            metadata=metadata,
        )
        self._emit_event(
            TelemetryEventType.AGENT_CREATED,
            agent_id=certificate.agent_id,
            declared_purpose=declared_purpose,
            declared_capabilities=declared_capabilities,
            effective_purpose=certificate.purpose,
            effective_capabilities=certificate.capabilities,
            environment=environment,
        )
        return certificate

    def create_agent_for_action(
        self,
        action: Any,
        parameters: Optional[Dict[str, Any]] = None,
        *,
        purpose: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        workspace_target: Optional[str] = None,
        environment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentCertificate:
        """Create an agent using a purpose/capability profile inferred from an action."""

        profile = infer_agent_profile_from_action(
            action,
            parameters,
            purpose=purpose,
            capabilities=capabilities,
            workspace_target=workspace_target,
        )
        return self.create_agent(
            profile.purpose,
            profile.capabilities,
            environment=environment,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        agent_id: str,
        action: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> CeroneResponse:
        """Validate an agent action in real-time."""
        normalized_agent_id = self._normalize_agent_id(agent_id)
        action_payload = self._normalize_action_payload(action, parameters)
        tool_name = action_payload["tool"]
        tool_parameters = action_payload["parameters"]

        if self._cache is not None:
            cache_key = self._cache_key(normalized_agent_id, tool_name, tool_parameters)
            cached = self._cache.get(cache_key)
            if cached and time.time() - cached["timestamp"] < 300:
                if cached["trust_score"] > 0.95:
                    logger.debug("Cache hit for %s", cache_key)
                    # Move to end (most recently used)
                    self._cache.move_to_end(cache_key)
                    return cast(CeroneResponse, cached["response"])

        start_time = time.time()
        payload = {"agent_id": normalized_agent_id, "action": action_payload}
        self._emit_event(
            TelemetryEventType.VALIDATION_ATTEMPTED,
            interaction_mode=InteractionMode.SINGLE_VALIDATION.value,
            agent_id=normalized_agent_id,
            tool=tool_name,
            capability_hint=_infer_capability_from_tool(tool_name),
        )
        response = self._request(
            "POST",
            "/v1/validate",
            **self._request_kwargs(
                "sdk_validate_called",
                InteractionMode.SINGLE_VALIDATION,
                json=payload,
                _allow_private_request=True,
            ),
        )
        latency_ms = int((time.time() - start_time) * 1000)

        result_value = str(response.get("result", "error")).lower()
        cerone_response = CeroneResponse(
            result=self._parse_validation_result(result_value),
            semantic_alignment=float(response.get("semantic_alignment", 0.0) or 0.0),
            trust_score=float(response.get("trust_score", 0.0) or 0.0),
            violations=response.get("violations", []),
            agent_id=normalized_agent_id,
            action=tool_name,
            timestamp=str(response.get("timestamp", "")),
            latency_ms=latency_ms,
            policy_families=response.get("policy_families", []),
            matched_rule_ids=response.get("matched_rule_ids", []),
            recommended_action=response.get("recommended_action"),
        )

        if (
            self._cache is not None
            and cerone_response.result == ValidationResult.APPROVED
            and cerone_response.trust_score > 0.95
        ):
            cache_key = self._cache_key(normalized_agent_id, tool_name, tool_parameters)
            self._cache[cache_key] = {
                "response": cerone_response,
                "trust_score": cerone_response.trust_score,
                "timestamp": time.time(),
            }
            self._cache.move_to_end(cache_key)
            # F18: evict oldest entries if cache is full
            while len(self._cache) > _CACHE_MAX_SIZE:
                self._cache.popitem(last=False)

        self._emit_event(
            TelemetryEventType.VALIDATION_RESULT_RECEIVED,
            interaction_mode=InteractionMode.SINGLE_VALIDATION.value,
            agent_id=normalized_agent_id,
            tool=tool_name,
            result=cerone_response.result.value,
            semantic_alignment=cerone_response.semantic_alignment,
            trust_score=cerone_response.trust_score,
            policy_families=cerone_response.policy_families,
            matched_rule_ids=cerone_response.matched_rule_ids,
            latency_ms=cerone_response.latency_ms,
        )
        return cerone_response

    async def validate_async(
        self,
        agent_id: str,
        action: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> CeroneResponse:
        """Async version of validate() for high-throughput scenarios."""
        if not _AIOHTTP_AVAILABLE:
            raise ValidationError(
                "aiohttp is required for async methods. "
                "Install with: pip install aiohttp"
            )

        start_time = time.time()
        normalized_agent_id = self._normalize_agent_id(agent_id)
        action_payload = self._normalize_action_payload(action, parameters)
        payload = {"agent_id": normalized_agent_id, "action": action_payload}
        self._emit_event(
            TelemetryEventType.VALIDATION_ATTEMPTED,
            interaction_mode=InteractionMode.SINGLE_VALIDATION.value,
            agent_id=normalized_agent_id,
            tool=action_payload["tool"],
            capability_hint=_infer_capability_from_tool(action_payload["tool"]),
        )
        data = await self._request_async(
            "POST",
            "/v1/validate",
            **self._request_kwargs(
                "sdk_validate_called",
                InteractionMode.SINGLE_VALIDATION,
                json=payload,
                _allow_private_request=True,
            ),
        )
        latency_ms = int((time.time() - start_time) * 1000)

        result_value = str(data.get("result", "error")).lower()
        cerone_response = CeroneResponse(
            result=self._parse_validation_result(result_value),
            semantic_alignment=float(data.get("semantic_alignment", 0.0) or 0.0),
            trust_score=float(data.get("trust_score", 0.0) or 0.0),
            violations=data.get("violations", []),
            agent_id=normalized_agent_id,
            action=action_payload["tool"],
            timestamp=str(data.get("timestamp", "")),
            latency_ms=latency_ms,
            policy_families=data.get("policy_families", []),
            matched_rule_ids=data.get("matched_rule_ids", []),
            recommended_action=data.get("recommended_action"),
        )
        self._emit_event(
            TelemetryEventType.VALIDATION_RESULT_RECEIVED,
            interaction_mode=InteractionMode.SINGLE_VALIDATION.value,
            agent_id=normalized_agent_id,
            tool=action_payload["tool"],
            result=cerone_response.result.value,
            semantic_alignment=cerone_response.semantic_alignment,
            trust_score=cerone_response.trust_score,
            policy_families=cerone_response.policy_families,
            matched_rule_ids=cerone_response.matched_rule_ids,
            latency_ms=cerone_response.latency_ms,
        )
        return cerone_response

    def validate_batch(self, validations: List[Dict[str, Any]]) -> List[CeroneResponse]:
        """
        Validate multiple actions in a single request.

        Each dict in ``validations`` must contain:
            agent_id   (str)
            action     (dict with ``tool`` and ``parameters`` keys)
        """
        if not validations:
            self._raise_local_error(
                LocalErrorCategory.EMPTY_BATCH,
                "validate_batch requires at least one validation item. "
                "Use validate(...) for a single action, or validate_batch([...]) with one or more items."
            )
        # F3: build properly shaped ValidationRequest objects for the backend
        requests_payload = []
        for v in validations:
            normalized_agent_id = self._normalize_agent_id(v["agent_id"])
            requests_payload.append({
                "agent_id": normalized_agent_id,
                "action": v["action"],   # must be {"tool": str, "parameters": dict}
            })

        self._emit_event(
            TelemetryEventType.BATCH_VALIDATION_ATTEMPTED,
            interaction_mode=InteractionMode.BATCH_VALIDATION.value,
            validation_count=len(requests_payload),
            agent_ids=[item["agent_id"] for item in requests_payload],
        )
        response = self._request(
            "POST",
            "/v1/validate/batch",
            **self._request_kwargs(
                "sdk_validate_batch_called",
                InteractionMode.BATCH_VALIDATION,
                json={"validations": requests_payload},
                _allow_private_request=True,
            ),
        )

        return [
            CeroneResponse(
                result=self._parse_validation_result(r.get("result", "error")),
                semantic_alignment=r.get("semantic_alignment", 0.0),
                trust_score=r.get("trust_score", 0.0),
                violations=r.get("violations", []),
                agent_id=r.get("agent_id", ""),
                action=r.get("action", {}).get("tool", "") if isinstance(r.get("action"), dict) else str(r.get("action", "")),
                timestamp=r.get("timestamp", ""),
                latency_ms=r.get("latency_ms", 0),
                policy_families=r.get("policy_families", []),
                matched_rule_ids=r.get("matched_rule_ids", []),
                recommended_action=r.get("recommended_action"),
            )
            for r in response["results"]
        ]

    # ------------------------------------------------------------------
    # Trust / audit
    # ------------------------------------------------------------------

    def get_trust_score(self, agent_id: str) -> Dict[str, Any]:
        """Get current trust score and history for an agent."""
        normalized_agent_id = self._normalize_agent_id(agent_id)
        return self._request(
            "GET",
            f"/v1/trust/{normalized_agent_id}",
            **self._request_kwargs(
                "sdk_get_trust_score_called",
                InteractionMode.TRUST_LOOKUP,
                _allow_private_request=True,
            ),
        )

    @staticmethod
    def _parse_validation_result(value: Any) -> ValidationResult:
        """
        Parse backend result safely.

        Supports newly introduced states (e.g. "flagged") and falls back to
        ERROR for forward-compatibility instead of raising ValueError.
        """
        raw = str(value).lower()
        try:
            return ValidationResult(raw)
        except ValueError:
            logger.warning("unknown_validation_result value=%s, defaulting=error", raw)
            return ValidationResult.ERROR

    def get_audit_log(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit log events for an agent.

        Returns a list of event dicts.  Each dict contains at minimum:
            timestamp, agent_id, action, result, change_reason
        """
        normalized_agent_id = self._normalize_agent_id(agent_id)
        # F4: backend returns {"events": [...], ...} — read the correct key
        params = {"limit": limit, "offset": offset}
        response = self._request(
            "GET",
            f"/v1/audit/agent/{normalized_agent_id}",
            **self._request_kwargs(
                "sdk_get_audit_log_called",
                InteractionMode.AUDIT_LOOKUP,
                params=params,
                _allow_private_request=True,
            ),
        )
        return response["events"]

    # ------------------------------------------------------------------
    # Health / lifecycle
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.json()
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def close(self) -> None:
        """Close the underlying synchronous HTTP session."""
        self._session.close()

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP session if initialized."""
        if self._async_session is not None and not self._async_session.closed:
            await self._async_session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_key(self, agent_id: str, action: str, parameters: Dict[str, Any]) -> str:
        serialized = json.dumps(parameters, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{agent_id}:{action}:{digest}"

    def _emit_event(self, event_type: TelemetryEventType, **payload: Any) -> None:
        if self.telemetry_hook is None:
            return
        event_payload = dict(self.telemetry_metadata)
        event_payload.update(payload)
        event = SDKTelemetryEvent(
            event_type=event_type,
            timestamp=_utc_now_iso(),
            sdk_name=SDK_NAME,
            sdk_version=__version__,
            runtime=SDK_RUNTIME,
            client_session_id=self.client_session_id,
            integration_id=self.integration_id,
            auth_session_id=self._auth_session_id,
            payload=event_payload,
        )
        try:
            self.telemetry_hook(event)
        except Exception as exc:  # pragma: no cover - defensive hook isolation
            logger.warning("telemetry_hook_failed error=%s", exc)

    def _raise_local_error(
        self,
        category: LocalErrorCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        event_details = dict(details or {})
        event_details["category"] = category.value
        self._emit_event(TelemetryEventType.LOCAL_ERROR, **event_details)
        raise LocalValidationError(message, category, details)

    @staticmethod
    def _fingerprint_token(token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"auth_{digest[:12]}"

    def _next_request_sequence(self) -> int:
        self._request_sequence += 1
        return self._request_sequence

    def _request_kwargs(
        self,
        intent: str,
        interaction_mode: InteractionMode,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["X-Cerone-Client-Intent"] = intent
        headers["X-Cerone-Interaction-Mode"] = interaction_mode.value
        kwargs["headers"] = headers
        return kwargs

    def _prepare_request_headers(self, headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prepared = dict(headers or {})
        prepared.setdefault("X-Cerone-SDK-Name", SDK_NAME)
        prepared.setdefault("X-Cerone-SDK-Version", __version__)
        prepared.setdefault("X-Cerone-Runtime", SDK_RUNTIME)
        prepared.setdefault("X-Cerone-Client-Session", self.client_session_id)
        prepared["X-Cerone-Request-Sequence"] = str(self._next_request_sequence())
        if self.integration_id:
            prepared.setdefault("X-Cerone-Integration-Id", self.integration_id)
        if self._auth_session_id:
            prepared["X-Cerone-Auth-Session"] = self._auth_session_id
        return prepared

    def _normalize_agent_id(self, agent_id: Any) -> str:
        if not isinstance(agent_id, str):
            self._raise_local_error(
                LocalErrorCategory.MISSING_AGENT_ID,
                "agent_id must be a non-empty string",
                {"agent_id": repr(agent_id)},
            )
        normalized = agent_id.strip()
        if not normalized:
            self._raise_local_error(
                LocalErrorCategory.MISSING_AGENT_ID,
                "agent_id must be a non-empty string",
            )
        if normalized.startswith("<") or "MagicMock" in normalized:
            self._raise_local_error(
                LocalErrorCategory.MISSING_AGENT_ID,
                "agent_id must be a real Cerone agent ID, not a mock object representation",
                {"agent_id": normalized},
            )
        return normalized

    def _load_cached_trial_token(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        try:
            if self._trial_token_path.exists():
                token = self._trial_token_path.read_text(encoding="utf-8").strip()
                if token.startswith("sk_trial_"):
                    return token
        except Exception:
            logger.warning("trial_token_cache_read_failed")
        return None

    def _persist_trial_token(self, token: str) -> None:
        try:
            self._trial_token_path.parent.mkdir(parents=True, exist_ok=True)
            self._trial_token_path.write_text(token, encoding="utf-8")
        except Exception:
            logger.warning("trial_token_cache_write_failed")

    def _apply_api_key(self, token: str) -> None:
        self.api_key = token
        self._auth_session_id = self._fingerprint_token(token)
        self._session.headers["X-API-Key"] = token
        self._session.headers["X-Cerone-Auth-Session"] = self._auth_session_id
        if self._async_session is not None and not self._async_session.closed:
            self._async_session.headers["X-API-Key"] = token
            self._async_session.headers["X-Cerone-Auth-Session"] = self._auth_session_id

    def _clear_trial_token(self) -> None:
        if self.api_key and self.api_key.startswith("sk_trial_"):
            self.api_key = None
            self._auth_session_id = None
            self._session.headers.pop("X-API-Key", None)
            self._session.headers.pop("X-Cerone-Auth-Session", None)
            if self._async_session is not None and not self._async_session.closed:
                self._async_session.headers.pop("X-API-Key", None)
                self._async_session.headers.pop("X-Cerone-Auth-Session", None)
            try:
                if self._trial_token_path.exists():
                    self._trial_token_path.unlink()
            except Exception:
                logger.warning("trial_token_cache_delete_failed")

    def _ensure_api_key(self) -> None:
        if self.api_key:
            return
        cached = self._load_cached_trial_token()
        if cached:
            self._apply_api_key(cached)
            self._emit_event(TelemetryEventType.TRIAL_TOKEN_RECEIVED, source="cache")
            return
        self._emit_event(TelemetryEventType.HOSTED_TRIAL_STARTED, base_url=self.base_url)
        bootstrap_headers = self._prepare_request_headers(
            self._request_kwargs(
                "sdk_trial_bootstrap_called",
                InteractionMode.TRIAL_BOOTSTRAP,
            )["headers"]
        )
        response = self._session.request(
            "POST",
            f"{self.base_url}/trial/session",
            timeout=self.timeout,
            json={},
            headers=bootstrap_headers,
        )
        self._raise_for_status(response.status_code, response.text)
        payload = response.json()
        trial_token = payload.get("trial_token")
        if not isinstance(trial_token, str) or not trial_token:
            self._raise_local_error(
                LocalErrorCategory.MISSING_TOKEN,
                "Hosted trial response did not include a valid trial token.",
                {"payload_keys": list(payload.keys()) if isinstance(payload, dict) else []},
            )
        self._apply_api_key(trial_token)
        self._persist_trial_token(trial_token)
        self._emit_event(
            TelemetryEventType.TRIAL_TOKEN_RECEIVED,
            source="network",
            auth_session_id=self._auth_session_id,
        )

    async def _ensure_api_key_async(self) -> None:
        if self.api_key:
            return
        cached = self._load_cached_trial_token()
        if cached:
            self._apply_api_key(cached)
            self._emit_event(TelemetryEventType.TRIAL_TOKEN_RECEIVED, source="cache")
            return
        self._emit_event(TelemetryEventType.HOSTED_TRIAL_STARTED, base_url=self.base_url)
        session = await self._get_async_session()
        bootstrap_headers = self._prepare_request_headers(
            self._request_kwargs(
                "sdk_trial_bootstrap_called",
                InteractionMode.TRIAL_BOOTSTRAP,
            )["headers"]
        )
        async with session.request(
            "POST",
            f"{self.base_url}/trial/session",
            json={},
            headers=bootstrap_headers,
        ) as response:
            body_text = await response.text()
            self._raise_for_status(response.status, body_text)
            payload = json.loads(body_text)
        trial_token = payload.get("trial_token")
        if not isinstance(trial_token, str) or not trial_token:
            self._raise_local_error(
                LocalErrorCategory.MISSING_TOKEN,
                "Hosted trial response did not include a valid trial token.",
                {"payload_keys": list(payload.keys()) if isinstance(payload, dict) else []},
            )
        self._apply_api_key(trial_token)
        self._persist_trial_token(trial_token)
        self._emit_event(
            TelemetryEventType.TRIAL_TOKEN_RECEIVED,
            source="network",
            auth_session_id=self._auth_session_id,
        )

    def _normalize_action_payload(
        self,
        action: Any,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Normalize validation payload into AZTP contract:
            {"tool": <str>, "parameters": <dict>}

        Supports legacy SDK call shape:
            validate(agent_id=..., action="tool_name", parameters={...})
        """
        if isinstance(action, dict):
            tool = action.get("tool")
            params = action.get("parameters", parameters or {})
            if not isinstance(tool, str) or not tool:
                self._raise_local_error(
                    LocalErrorCategory.INVALID_ACTION_SHAPE,
                    "Action dict must include a non-empty 'tool' field",
                    {"action": action},
                )
            if not isinstance(params, dict):
                self._raise_local_error(
                    LocalErrorCategory.INVALID_ACTION_SHAPE,
                    "Action parameters must be a dictionary",
                    {"action": action},
                )
            return {"tool": tool, "parameters": params}

        if not isinstance(action, str) or not action:
            self._raise_local_error(
                LocalErrorCategory.INVALID_ACTION_SHAPE,
                "Action must be a non-empty string or an action dict",
                {"action": action},
            )

        params = parameters or {}
        if not isinstance(params, dict):
            self._raise_local_error(
                LocalErrorCategory.INVALID_ACTION_SHAPE,
                "Parameters must be a dictionary",
                {"action": action},
            )
        return {"tool": action, "parameters": params}

    def _can_retry(self, method: str) -> bool:
        return method.upper() in self._IDEMPOTENT_METHODS or self.retry_non_idempotent

    @staticmethod
    def _raise_for_status(status_code: int, body_text: str) -> None:
        if 200 <= status_code < 300:
            return
        if status_code == 401:
            raise AuthenticationError(
                f"Invalid or missing API key. See access options at {ACCESS_URL}"
            )
        if status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded. See plan options at {ACCESS_URL}"
            )
        if status_code >= 500:
            raise _ServerError(f"Server error: {status_code}")
        raise _ClientRequestError(f"Request failed: {status_code} - {body_text}")

    @staticmethod
    def _guard_empty_batch_request(endpoint: str, kwargs: Dict[str, Any]) -> None:
        if endpoint != "/v1/validate/batch":
            return
        payload = kwargs.get("json")
        if not isinstance(payload, dict):
            return
        validations = payload.get("validations")
        if validations == []:
            raise LocalValidationError(
                "validate_batch requires at least one validation item. "
                "Use validate(...) for a single action, or validate_batch([...]) with one or more items."
                ,
                LocalErrorCategory.EMPTY_BATCH,
            )

    def _warn_private_request_usage(self, endpoint: str, allow_private_request: bool) -> None:
        if allow_private_request:
            return
        if not endpoint.startswith("/"):
            return
        self._emit_event(
            TelemetryEventType.LOCAL_ERROR,
            category=LocalErrorCategory.WRAPPER_MISUSE.value,
            endpoint=endpoint,
            reason="private_request_usage",
        )
        warnings.warn(
            "_request() is a private method. Use the public SDK methods instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Internal request with bounded retries."""
        allow_private_request = bool(kwargs.pop("_allow_private_request", False))
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            self._raise_local_error(
                LocalErrorCategory.UNSUPPORTED_PATH,
                "Endpoint must be an absolute path starting with '/'.",
                {"endpoint": endpoint},
            )
        if endpoint != "/trial/session":
            self._ensure_api_key()
        self._warn_private_request_usage(endpoint, allow_private_request)
        try:
            self._guard_empty_batch_request(endpoint, kwargs)
        except LocalValidationError as exc:
            self._emit_event(TelemetryEventType.LOCAL_ERROR, category=exc.category.value, endpoint=endpoint)
            raise
        url = f"{self.base_url}{endpoint}"
        kwargs["headers"] = self._prepare_request_headers(kwargs.get("headers"))
        if "json" in kwargs:
            try:
                json.dumps(kwargs["json"])
            except TypeError as exc:
                self._raise_local_error(
                    LocalErrorCategory.SERIALIZATION_ERROR,
                    "Request payload is not JSON serializable.",
                    {"endpoint": endpoint, "error": str(exc)},
                )
        can_retry = self._can_retry(method)
        attempts = (self.max_retries + 1) if can_retry else 1

        for attempt in range(attempts):
            try:
                response = self._session.request(method, url, timeout=self.timeout, **kwargs)
                self._raise_for_status(response.status_code, response.text)
                try:
                    return response.json()
                except ValueError as exc:
                    raise ValidationError("Invalid JSON response from server") from exc
            except AuthenticationError:
                if self.api_key and self.api_key.startswith("sk_trial_") and attempt < attempts - 1:
                    self._clear_trial_token()
                    self._ensure_api_key()
                    continue
                raise
            except (RateLimitError, _ClientRequestError):
                raise
            except _ServerError:
                if attempt < attempts - 1:
                    wait = 2 ** attempt
                    logger.warning("Server error, retrying in %ss…", wait)
                    time.sleep(wait)
                    continue
                raise
            except requests.exceptions.Timeout:
                if attempt < attempts - 1:
                    logger.warning("Request timeout, retrying…")
                    continue
                raise ValidationError("Request timeout")
            except requests.exceptions.RequestException as exc:
                if attempt < attempts - 1:
                    logger.warning("Request failed: %s, retrying…", exc)
                    continue
                raise ValidationError(f"Request failed: {exc}")

        raise ValidationError("Max retries exceeded")

    async def _get_async_session(self) -> Any:
        if not _AIOHTTP_AVAILABLE:
            raise ValidationError(
                "aiohttp is required for async methods. "
                "Install with: pip install aiohttp"
            )
        if self._async_session is None or self._async_session.closed:
            self._async_session = aiohttp.ClientSession(
                headers=dict(self._session.headers),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._async_session

    async def _request_async(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Async request helper with bounded retries."""
        allow_private_request = bool(kwargs.pop("_allow_private_request", False))
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            self._raise_local_error(
                LocalErrorCategory.UNSUPPORTED_PATH,
                "Endpoint must be an absolute path starting with '/'.",
                {"endpoint": endpoint},
            )
        if endpoint != "/trial/session":
            await self._ensure_api_key_async()
        self._warn_private_request_usage(endpoint, allow_private_request)
        try:
            self._guard_empty_batch_request(endpoint, kwargs)
        except LocalValidationError as exc:
            self._emit_event(TelemetryEventType.LOCAL_ERROR, category=exc.category.value, endpoint=endpoint)
            raise
        url = f"{self.base_url}{endpoint}"
        kwargs["headers"] = self._prepare_request_headers(kwargs.get("headers"))
        if "json" in kwargs:
            try:
                json.dumps(kwargs["json"])
            except TypeError as exc:
                self._raise_local_error(
                    LocalErrorCategory.SERIALIZATION_ERROR,
                    "Request payload is not JSON serializable.",
                    {"endpoint": endpoint, "error": str(exc)},
                )
        can_retry = self._can_retry(method)
        attempts = (self.max_retries + 1) if can_retry else 1

        for attempt in range(attempts):
            try:
                session = await self._get_async_session()
                async with session.request(method, url, **kwargs) as response:
                    body_text = await response.text()
                    self._raise_for_status(response.status, body_text)
                    try:
                        return json.loads(body_text)
                    except json.JSONDecodeError as exc:
                        raise ValidationError("Invalid JSON response from server") from exc
            except AuthenticationError:
                if self.api_key and self.api_key.startswith("sk_trial_") and attempt < attempts - 1:
                    self._clear_trial_token()
                    await self._ensure_api_key_async()
                    continue
                raise
            except (RateLimitError, _ClientRequestError):
                raise
            except _ServerError:
                if attempt < attempts - 1:
                    wait = 2 ** attempt
                    logger.warning("Async server error, retrying in %ss…", wait)
                    await asyncio.sleep(wait)
                    continue
                raise
            except asyncio.TimeoutError:
                if attempt < attempts - 1:
                    logger.warning("Async timeout, retrying…")
                    continue
                raise ValidationError("Request timeout")
            except _AIOHTTP_CLIENT_ERROR as exc:
                if attempt < attempts - 1:
                    logger.warning("Async request failed: %s, retrying…", exc)
                    continue
                raise ValidationError(f"Request failed: {exc}")

        raise ValidationError("Max retries exceeded")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if self._async_session is not None and not self._async_session.closed:
            logger.warning(
                "Async session still open. "
                "Use 'async with CeroneClient(...)' or await client.aclose()."
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
        self.close()


class AgentWrapper:
    """Wrapper that automatically validates all agent actions via a decorator."""

    def __init__(self, cerone_client: CeroneClient, agent_id: str):
        self.client = cerone_client
        self.agent_id = agent_id

    def validate_action(self, func: F) -> F:
        """Decorator that validates a function call through Cerone before executing it."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            action = func.__name__
            parameters = {"args": args, "kwargs": kwargs}

            result = self.client.validate(
                agent_id=self.agent_id,
                action=action,
                parameters=parameters,
            )

            if result.result == ValidationResult.APPROVED:
                logger.info(
                    "Action '%s' approved (alignment: %.2f)",
                    action,
                    result.semantic_alignment,
                )
                return func(*args, **kwargs)

            logger.warning("Action '%s' blocked: %s", action, result.violations)
            raise PermissionError(f"Cerone blocked action: {', '.join(result.violations)}")

        return cast(F, wrapper)


__all__ = [
    "CeroneClient",
    "AgentWrapper",
    "CeroneResponse",
    "AgentCertificate",
    "InferredAgentProfile",
    "SDKTelemetryEvent",
    "ValidationResult",
    "InteractionMode",
    "TelemetryEventType",
    "LocalErrorCategory",
    "CeroneException",
    "AuthenticationError",
    "ValidationError",
    "LocalValidationError",
    "RateLimitError",
    "infer_agent_profile_from_action",
]
