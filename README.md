
# Cerone Python SDK (Beta)

Zero Trust security and production governance for AI agents.

Cerone helps teams enforce policy controls on agent actions and maintain operational accountability in production environments.  
The SDK is currently in early-access beta for selected users.  Thus, it provides Zero Trust Security Validation, Verification and Governance for AI Agents. 

## Install

```bash
pip install cerone
```

## Access (Beta)

API access is currently managed through early access:

- Request access: https://aztp.homersemantics.com/
- Receive approval and API credentials
- Review terms in `TERMS_OF_SERVICE.md`

## Quick Start

```python
import os
from cerone import CeroneClient

client = CeroneClient(api_key=os.getenv("CERONE_API_KEY"))

agent = client.create_agent(
    purpose="Approved operational workflow",
    capabilities=["approved_capability"],
)

response = client.validate(
    agent_id=agent.agent_id,
    action="approved_action",
    parameters={"key": "value"},
)

print(response.result)
```

## What the SDK Provides

- Authenticated client access to Cerone services
- Agent registration and identity-bound operations
- Sync and async validation calls
- Batch validation support
- Governance-oriented telemetry surfaces

## Usage Terms

Usage limits and commercial terms are defined in `TERMS_OF_SERVICE.md`.

Current free trial: up to 100 validations in the first 5 days.

## License

Proprietary commercial license. See `LICENSE`.

## Contact

info@homersemantics.com
```

4. Use `response.result` (matches your SDK dataclass).
