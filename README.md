# Ceron Python SDK

Zero Trust Security for AI Agents

Ceron gives every AI agent a verifiable identity, enforces runtime policy checks on high-risk actions, and continuously adjusts control posture based on observed behavior.  
It helps teams keep autonomous systems inside approved boundaries in production.  
Result: safer agent operations with clear governance, accountability, and enforcement.


[![PyPI version](https://badge.fury.io/py/ceron.svg)](https://badge.fury.io/py/ceron)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)

## What is Ceron?

Ceron validates that AI agents stay aligned with their declared purpose using semantic analysis. Unlike traditional security that checks permissions, Ceron checks **purpose** - ensuring agents don't drift from their intended behavior.

## Installation

```bash
pip install ceron
```

## Getting API Access (Early Access)

1. Request early access: https://aztp.homersemantics.com/
2. Wait for approval and API key issuance.
3. Set your key in your environment:

```bash
export CERON_API_KEY="your_key_here"
```

## Quick Start

```python
import os
from ceron import CeronClient, ValidationResult

# Initialize client
client = CeronClient(api_key=os.getenv("CERON_API_KEY"))

# Create an agent with declared purpose
agent = client.create_agent(
    purpose="Customer support agent for billing inquiries",
    capabilities=["database_read", "send_email"]
)

# Validate agent actions in real-time
result = client.validate(
    agent_id=agent.agent_id,
    action="database_query",
    parameters={"query": "SELECT * FROM billing WHERE customer_id = ?"}
)

# Execute only if approved
if result.result == ValidationResult.APPROVED:
    execute_query()
else:
    log_blocked_action(result.violations)
```

## Core Concepts

### 1. Verified Agent Identity
Each agent is issued a verifiable identity tied to its declared role and policy scope. This allows Ceron to attribute actions to the correct agent and enforce policy consistently across environments.

### 2. Runtime Policy Validation
Before sensitive operations execute, Ceron evaluates requested actions against the agent’s declared intent, permissions, and active policy controls. Actions that do not meet policy are blocked or flagged according to your enforcement settings.

### 3. Continuous Trust and Control
Ceron continuously monitors behavior over time and updates enforcement posture based on observed risk signals. Teams can apply graduated controls (allow, monitor, restrict, revoke) to keep production agents within approved operating boundaries.

## API Reference

### CeronClient

#### `__init__(api_key, base_url, timeout, max_retries, enable_cache)`

Initialize Ceron client.

**Parameters:**
- `api_key` (str): Your Ceron API key
- `base_url` (str): API endpoint (default: https://api.homersemantics.com)
- `timeout` (int): Request timeout in seconds (default: 30)
- `max_retries` (int): Number of retry attempts (default: 3)
- `enable_cache` (bool): Enable local caching (default: False)

#### `create_agent(purpose, capabilities) -> AgentCertificate`

Create a new agent with cryptographic identity.

**Parameters:**
- `purpose` (str): Clear description of agent's intended purpose
- `capabilities` (List[str], optional): List of allowed capabilities

**Returns:** `AgentCertificate` with agent_id and signature

#### `validate(agent_id, action, parameters) -> CeronResponse`

Validate an agent action in real-time.

**Parameters:**
- `agent_id` (str): Agent identifier
- `action` (str): Action type
- `parameters` (dict): Action parameters

**Returns:** `CeronResponse` with validation result

#### `validate_async(agent_id, action, parameters) -> CeronResponse`

Async version of validate() for high-throughput scenarios.

#### `validate_batch(validations) -> List[CeronResponse]`

Validate multiple actions in a single request.

**Parameters:**
- `validations` (List[dict]): List of validation requests

**Returns:** List of `CeronResponse` objects

#### `get_trust_score(agent_id) -> dict`

Get current trust score and history for an agent.

**Returns:** Dict with current_score, tier, total_actions, violations

#### `get_audit_log(agent_id, limit, offset) -> List[dict]`

Retrieve audit log for an agent.

**Parameters:**
- `agent_id` (str): Agent identifier
- `limit` (int): Number of records (default: 100)
- `offset` (int): Pagination offset (default: 0)

**Returns:** List of audit events

### AgentWrapper

#### `validate_action(func)`

Decorator that validates function calls through Ceron.

```python
agent = AgentWrapper(ceron_client=client, agent_id="agt_123")

@agent.validate_action
def sensitive_operation(param1, param2):
    # Automatically validated before execution
    return execute(param1, param2)
```

## Response Objects

### CeronResponse

```python
@dataclass
class CeronResponse:
    result: ValidationResult          # APPROVED | REJECTED | ERROR
    semantic_alignment: float         # 0.0 to 1.0
    trust_score: float               # Current agent trust (0.0 to 1.0)
    violations: List[str]            # List of violations if rejected
    agent_id: str                    # Agent identifier
    action: str                      # Action type
    timestamp: str                   # ISO 8601 timestamp
    latency_ms: int                  # Validation latency in milliseconds
```

### AgentCertificate

```python
@dataclass
class AgentCertificate:
    agent_id: str                    # Unique agent identifier
    purpose: str                     # Declared purpose
    capabilities: List[str]          # Allowed capabilities
    trust_score: float              # Initial trust (1.0)
    signature: str                  # Ed25519 signature
    created_at: str                 # ISO 8601 timestamp
```

## Error Handling

```python
from ceron import (
    CeronClient,
    AuthenticationError,
    ValidationError,
    RateLimitError
)

client = CeronClient(api_key="sk_...")

try:
    result = client.validate(agent_id, action, parameters)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError:
    print("Rate limit exceeded")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Performance Considerations

### Latency
- Typical validation: 50-100ms
- With caching enabled: 1-5ms (cached hits)
- Async validation: Process multiple in parallel

### Rate Limits
- 100 100 validations in first 5 days
- Use batch validation for high-throughput
- Enable caching for repeated actions

### Best Practices

1. **Use async for high-frequency operations:**
```python
results = await asyncio.gather(
    client.validate_async(agent_id, action1, params1),
    client.validate_async(agent_id, action2, params2),
    client.validate_async(agent_id, action3, params3)
)
```

2. **Enable caching for trusted agents:**
```python
client = CeronClient(api_key="sk_...", enable_cache=True)
```

3. **Use batch validation when possible:**
```python
results = client.validate_batch(multiple_validations)
```

4. **Implement graceful degradation:**
```python
try:
    result = client.validate(agent_id, action, parameters)
except ValidationError:
    # Fall back to safe mode or human approval
    escalate_to_human()
```

## Integration Patterns

### Pattern 1: Pre-Flight Validation
```python
def agent_action(action, params):
    # Validate BEFORE executing
    result = client.validate(agent_id, action, params)
    if result.result == ValidationResult.APPROVED:
        return execute_action(action, params)
    else:
        raise PermissionError(result.violations)
```

### Pattern 2: Wrapper/Decorator
```python
agent = AgentWrapper(ceron_client=client, agent_id="agt_123")

@agent.validate_action
def protected_function(param):
    return sensitive_operation(param)
```

### Pattern 3: Async Fire-and-Forget
```python
async def fast_execution(action, params):
    # Execute immediately
    result = execute_action(action, params)
    
    # Validate asynchronously for monitoring
    asyncio.create_task(
        client.validate_async(agent_id, action, params)
    )
    
    return result
```

## Testing

```bash
# Install dev dependencies
pip install ceron[dev]

# Run tests
pytest tests/

# Run with coverage
pytest --cov=ceron tests/
```

## Support

- **Documentation:** https://docs.homersemantics.com/ceron
- **Email:** support@homersemantics.com
- **Issues:** https://github.com/homer-semantics/ceron-python/issues

## License

Ceron SDK Commercial License - see LICENSE file for details

## Terms of Service

Use of Ceron APIs is also governed by TERMS_OF_SERVICE.md.

Free trial: up to 100 validations in the first 5 days. See TERMS_OF_SERVICE.md.


## Changelog

### v1.0.0 (2026-02-28)
- Initial release
- Synchronous and async validation
- Batch validation support
- Trust score tracking
- Audit logging
- Local caching option
