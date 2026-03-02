# Ceron Python SDK

Zero Trust Security for AI Agents

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

### 1. Agent Identity
Every agent gets a cryptographic certificate with its declared purpose:

```python
agent = client.create_agent(
    purpose="Autonomous trading agent for cryptocurrency markets",
    capabilities=["market_read", "trade_execute"]
)
# Returns: AgentCertificate with agent_id and Ed25519 signature
```

### 2. Semantic Validation
Actions are validated against the agent's purpose using semantic embeddings:

```python
# This will be APPROVED (aligned with trading purpose)
result = client.validate(
    agent_id=agent.agent_id,
    action="trade_execute",
    parameters={"symbol": "BTC/USD", "side": "buy"}
)

# This will be REJECTED (not aligned with trading purpose)
result = client.validate(
    agent_id=agent.agent_id,
    action="send_email_marketing",
    parameters={"recipients": "all_customers"}
)
```

### 3. Adaptive Trust Scoring
Trust increases with aligned behavior, decreases with drift:

```python
trust = client.get_trust_score(agent.agent_id)
print(f"Trust: {trust['current_score']:.2f}")
print(f"Tier: {trust['tier']}")  # Trusted | Monitored | Restricted | Revoked
```

## Usage Examples

### Example 1: Trading Agent

```python
from ceron import CeronClient, ValidationResult

client = CeronClient(api_key="sk_...")

# Register trading agent
trading_agent = client.create_agent(
    purpose="Execute cryptocurrency trades based on market signals",
    capabilities=["market_read", "trade_execute"]
)

def execute_trade(symbol, side, quantity):
    """Execute trade with Ceron validation"""
    
    # Validate BEFORE executing
    result = client.validate(
        agent_id=trading_agent.agent_id,
        action="trade_execute",
        parameters={
            "symbol": symbol,
            "side": side,
            "quantity": quantity
        }
    )
    
    if result.result == ValidationResult.APPROVED:
        # Aligned with purpose → Execute
        broker.execute_trade(symbol, side, quantity)
        print(f"✓ Trade executed (alignment: {result.semantic_alignment:.2f})")
    else:
        # Drift detected → Block
        print(f"✗ Trade blocked: {result.violations}")
        alert_compliance_team(result)
```

### Example 2: Customer Support Agent

```python
from ceron import CeronClient, AgentWrapper, ValidationResult

client = CeronClient(api_key="sk_...")

# Create agent
support_agent = client.create_agent(
    purpose="Handle customer billing inquiries and process refunds",
    capabilities=["database_read", "send_email", "process_refund"]
)

# Use wrapper for automatic validation
agent = AgentWrapper(
    ceron_client=client,
    agent_id=support_agent.agent_id
)

# Decorator automatically validates before execution
@agent.validate_action
def process_refund(customer_id, amount):
    """Process refund - automatically validated by Ceron"""
    return billing_system.refund(customer_id, amount)

@agent.validate_action
def access_customer_data(customer_id):
    """Access customer data - validated before execution"""
    return database.query("SELECT * FROM customers WHERE id = ?", customer_id)

# Usage
try:
    # This will be validated and executed if aligned
    process_refund(customer_id="12345", amount=50.00)
except PermissionError as e:
    print(f"Action blocked by Ceron: {e}")
```

### Example 3: Streaming Data Processing

```python
import asyncio
from ceron import CeronClient, ValidationResult

client = CeronClient(api_key="sk_...")

# Register data processing agent
data_agent = client.create_agent(
    purpose="Analyze customer churn data and send retention offers",
    capabilities=["database_read", "send_email"]
)

async def process_customer_stream(customer_stream):
    """Process streaming data with async validation"""
    
    async for customer in customer_stream:
        if customer.churn_risk > 0.8:
            # Validate action asynchronously
            result = await client.validate_async(
                agent_id=data_agent.agent_id,
                action="send_retention_offer",
                parameters={
                    "customer_id": customer.id,
                    "offer_type": "discount"
                }
            )
            
            if result.result == ValidationResult.APPROVED:
                await send_offer(customer)
            else:
                await log_blocked_offer(customer, result.violations)

# Run async processing
asyncio.run(process_customer_stream(customer_stream))
```

### Example 4: Batch Validation

```python
from ceron import CeronClient, ValidationResult

client = CeronClient(api_key="sk_...")

# Validate multiple actions at once
validations = [
    {
        "agent_id": "agt_123",
        "action": "query_database",
        "parameters": {"table": "customers"}
    },
    {
        "agent_id": "agt_123",
        "action": "send_email",
        "parameters": {"to": "customer@example.com"}
    },
    {
        "agent_id": "agt_123",
        "action": "update_record",
        "parameters": {"id": 456, "status": "processed"}
    }
]

results = client.validate_batch(validations)

# Process results
for result in results:
    if result.result == ValidationResult.APPROVED:
        execute_action(result.action, result.agent_id)
    else:
        print(f"Blocked: {result.action} - {result.violations}")
```

### Example 5: High-Throughput with Caching

```python
from ceron import CeronClient, ValidationResult

# Enable caching for high-trust actions
client = CeronClient(
    api_key="sk_...",
    enable_cache=True  # Cache approvals with trust > 0.95 for 5 minutes
)

agent = client.create_agent(
    purpose="Process payment transactions",
    capabilities=["payment_gateway"]
)

# First call: Full validation (~50ms)
result1 = client.validate(agent.agent_id, "process_payment", {...})

# Subsequent calls: Cached if high trust (~1ms)
result2 = client.validate(agent.agent_id, "process_payment", {...})
result3 = client.validate(agent.agent_id, "process_payment", {...})
```

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
- 100 requests/minute per API key
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

## Changelog

### v1.0.0 (2026-02-28)
- Initial release
- Synchronous and async validation
- Batch validation support
- Trust score tracking
- Audit logging
- Local caching option
