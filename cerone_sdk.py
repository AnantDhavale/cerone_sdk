"""
Cerone Python SDK
Zero Trust Security for AI Agents

Installation:
    pip install cerone

Usage:
    from cerone import CeroneClient

    client = CeroneClient(api_key="your_api_key")
    result = client.validate(agent_id="agt_123", action="trade_execute", parameters={...})
"""

import asyncio
import hashlib
import json
import logging
import time
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

__version__ = "1.0.0"
__author__ = "Homer Semantics"
EARLY_ACCESS_URL = "https://aztp.homersemantics.com/"

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


class ValidationResult(Enum):
    """Validation result enum."""

    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


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


@dataclass
class AgentCertificate:
    """Agent identity certificate."""

    agent_id: str
    purpose: str
    capabilities: List[str]
    trust_score: float
    signature: str
    created_at: str


class CeroneException(Exception):
    """Base exception for Cerone SDK."""


class AuthenticationError(CeroneException):
    """Raised when API key is invalid."""


class ValidationError(CeroneException):
    """Raised when validation fails."""


class RateLimitError(CeroneException):
    """Raised when rate limit is exceeded."""


class _ClientRequestError(ValidationError):
    """Raised for non-retryable 4xx request errors."""


class _ServerError(ValidationError):
    """Raised for retryable 5xx server errors."""


class CeroneClient:
    """Cerone API client for validating AI agent actions."""

    _IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.homersemantics.com",
        timeout: int = 30,
        max_retries: int = 3,
        enable_cache: bool = False,
        retry_non_idempotent: bool = False,
    ):
        """
        Initialize Cerone client.

        Args:
            api_key: Your Cerone API key.
            base_url: API endpoint (default: production).
            timeout: Request timeout in seconds.
            max_retries: Number of retry attempts for eligible requests.
                Total attempts = 1 + max_retries.
            enable_cache: Enable local caching of high-trust validations.
            retry_non_idempotent: Retry POST/PUT/PATCH/DELETE on transport errors.
                Defaults to False to avoid duplicate side effects.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.enable_cache = enable_cache
        self.retry_non_idempotent = retry_non_idempotent
        self._cache = {} if enable_cache else None

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": f"cerone-python-sdk/{__version__}",
            }
        )

        self._async_session: Optional[Any] = None

    def create_agent(self, purpose: str, capabilities: Optional[List[str]] = None) -> AgentCertificate:
        """Create a new agent with cryptographic identity."""
        payload = {
            "purpose": purpose,
            "capabilities": capabilities or [],
        }

        response = self._request("POST", "/v1/certificates", json=payload)

        return AgentCertificate(
            agent_id=response["agent_id"],
            purpose=purpose,
            capabilities=capabilities or [],
            trust_score=response["trust_score"],
            signature=response["signature"],
            created_at=response["created_at"],
        )

    def validate(self, agent_id: str, action: str, parameters: Dict[str, Any]) -> CeroneResponse:
        """Validate an agent action in real-time."""
        if self._cache is not None:
            cache_key = self._cache_key(agent_id, action, parameters)
            cached = self._cache.get(cache_key)
            if cached and time.time() - cached["timestamp"] < 300:
                if cached["trust_score"] > 0.95:
                    logger.debug("Cache hit for %s", cache_key)
                    return cast(CeroneResponse, cached["response"])

        start_time = time.time()

        payload = {
            "agent_id": agent_id,
            "action": action,
            "parameters": parameters,
        }

        response = self._request("POST", "/v1/validate", json=payload)

        latency_ms = int((time.time() - start_time) * 1000)

        cerone_response = CeroneResponse(
            result=ValidationResult(response["result"]),
            semantic_alignment=response["semantic_alignment"],
            trust_score=response["trust_score"],
            violations=response.get("violations", []),
            agent_id=agent_id,
            action=action,
            timestamp=response["timestamp"],
            latency_ms=latency_ms,
        )

        if self._cache is not None and cerone_response.result == ValidationResult.APPROVED:
            if cerone_response.trust_score > 0.95:
                cache_key = self._cache_key(agent_id, action, parameters)
                self._cache[cache_key] = {
                    "response": cerone_response,
                    "trust_score": cerone_response.trust_score,
                    "timestamp": time.time(),
                }

        return cerone_response

    async def validate_async(self, agent_id: str, action: str, parameters: Dict[str, Any]) -> CeroneResponse:
        """Async version of validate() for high-throughput scenarios."""
        if not _AIOHTTP_AVAILABLE:
            raise ValidationError("aiohttp is required for async methods. Install with: pip install aiohttp")

        start_time = time.time()

        payload = {
            "agent_id": agent_id,
            "action": action,
            "parameters": parameters,
        }

        data = await self._request_async("POST", "/v1/validate", json=payload)

        latency_ms = int((time.time() - start_time) * 1000)

        return CeroneResponse(
            result=ValidationResult(data["result"]),
            semantic_alignment=data["semantic_alignment"],
            trust_score=data["trust_score"],
            violations=data.get("violations", []),
            agent_id=agent_id,
            action=action,
            timestamp=data["timestamp"],
            latency_ms=latency_ms,
        )

    def validate_batch(self, validations: List[Dict[str, Any]]) -> List[CeroneResponse]:
        """Validate multiple actions in a single request."""
        response = self._request("POST", "/v1/validate/batch", json={"validations": validations})

        return [
            CeroneResponse(
                result=ValidationResult(r["result"]),
                semantic_alignment=r["semantic_alignment"],
                trust_score=r["trust_score"],
                violations=r.get("violations", []),
                agent_id=r["agent_id"],
                action=r["action"],
                timestamp=r["timestamp"],
                latency_ms=r.get("latency_ms", 0),
            )
            for r in response["results"]
        ]

    def get_trust_score(self, agent_id: str) -> Dict[str, Any]:
        """Get current trust score and history for an agent."""
        return self._request("GET", f"/v1/trust/{agent_id}")

    def get_audit_log(self, agent_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve audit log for an agent."""
        params = {"limit": limit, "offset": offset}
        response = self._request("GET", f"/v1/audit/agent/{agent_id}", params=params)
        return response["events"]

    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.json()
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def close(self) -> None:
        """Close underlying synchronous HTTP session."""
        self._session.close()

    async def aclose(self) -> None:
        """Close underlying asynchronous HTTP session if initialized."""
        if self._async_session is not None and not self._async_session.closed:
            await self._async_session.close()

    def _cache_key(self, agent_id: str, action: str, parameters: Dict[str, Any]) -> str:
        """Create a stable cache key including parameters."""
        serialized = json.dumps(parameters, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{agent_id}:{action}:{digest}"

    def _can_retry(self, method: str) -> bool:
        method = method.upper()
        return method in self._IDEMPOTENT_METHODS or self.retry_non_idempotent

    @staticmethod
    def _raise_for_status(status_code: int, body_text: str) -> None:
        if 200 <= status_code < 300:
            return
        if status_code == 401:
            raise AuthenticationError(
                f"Invalid or missing API key. Request early access at {EARLY_ACCESS_URL}"
            )
        if status_code == 429:
            raise RateLimitError(
                "Rate limit exceeded. If you need higher limits, request access/upgrade via "
                f"{EARLY_ACCESS_URL}"
            )
        if status_code >= 500:
            raise _ServerError(f"Server error: {status_code}")
        raise _ClientRequestError(f"Request failed: {status_code} - {body_text}")

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Internal method for API requests with bounded retries."""
        url = f"{self.base_url}{endpoint}"
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
            except (AuthenticationError, RateLimitError, _ClientRequestError):
                raise
            except _ServerError:
                if attempt < attempts - 1:
                    wait_time = 2**attempt
                    logger.warning("Request failed with server error, retrying in %ss...", wait_time)
                    time.sleep(wait_time)
                    continue
                raise
            except requests.exceptions.Timeout:
                if attempt < attempts - 1:
                    logger.warning("Request timeout, retrying...")
                    continue
                raise ValidationError("Request timeout")
            except requests.exceptions.RequestException as exc:
                if attempt < attempts - 1:
                    logger.warning("Request failed: %s, retrying...", exc)
                    continue
                raise ValidationError(f"Request failed: {exc}")

        raise ValidationError("Max retries exceeded")

    async def _get_async_session(self) -> Any:
        if not _AIOHTTP_AVAILABLE:
            raise ValidationError("aiohttp is required for async methods. Install with: pip install aiohttp")
        if self._async_session is None or self._async_session.closed:
            self._async_session = aiohttp.ClientSession(
                headers=dict(self._session.headers),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._async_session

    async def _request_async(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        """Async API request helper with bounded retries."""
        url = f"{self.base_url}{endpoint}"
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
            except (AuthenticationError, RateLimitError, _ClientRequestError):
                raise
            except _ServerError:
                if attempt < attempts - 1:
                    wait_time = 2**attempt
                    logger.warning("Async request failed with server error, retrying in %ss...", wait_time)
                    await self._async_sleep(wait_time)
                    continue
                raise
            except asyncio.TimeoutError:
                if attempt < attempts - 1:
                    logger.warning("Async request timeout, retrying...")
                    continue
                raise ValidationError("Request timeout")
            except _AIOHTTP_CLIENT_ERROR as exc:
                if attempt < attempts - 1:
                    logger.warning("Async request failed: %s, retrying...", exc)
                    continue
                raise ValidationError(f"Request failed: {exc}")

        raise ValidationError("Max retries exceeded")

    async def _async_sleep(self, seconds: int) -> None:
        await asyncio.sleep(seconds)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if self._async_session is not None and not self._async_session.closed:
            logger.warning(
                "Async session is still open. Use 'async with CeroneClient(...)' or await client.aclose()."
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
        self.close()


class AgentWrapper:
    """Wrapper class that automatically validates all agent actions."""

    def __init__(self, cerone_client: CeroneClient, agent_id: str):
        self.client = cerone_client
        self.agent_id = agent_id

    def validate_action(self, func: F) -> F:
        """Decorator that validates function calls through Cerone."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            action = func.__name__
            parameters = {"args": args, "kwargs": kwargs}

            result = self.client.validate(agent_id=self.agent_id, action=action, parameters=parameters)

            if result.result == ValidationResult.APPROVED:
                logger.info("Action '%s' approved (alignment: %.2f)", action, result.semantic_alignment)
                return func(*args, **kwargs)

            logger.warning("Action '%s' blocked: %s", action, result.violations)
            raise PermissionError(f"Cerone blocked action: {', '.join(result.violations)}")

        return cast(F, wrapper)


__all__ = [
    "CeroneClient",
    "AgentWrapper",
    "CeroneResponse",
    "AgentCertificate",
    "ValidationResult",
    "CeroneException",
    "AuthenticationError",
    "ValidationError",
    "RateLimitError",
]
