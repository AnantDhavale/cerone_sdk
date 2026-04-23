
# Agent Governance Python SDK (Beta)

Zero Trust security and production governance for AI agents. 
Cryptographic identity and run-time validation for AI agents in production.

AI agents are being deployed into production systems that handle real decisions, real data, and real consequences, yet most teams have no 
runtime control over what those agents actually do. Agent Governance fixes that.

Agent Governance enforces cryptographic identity, semantic intent validation, and continuous trust scoring on every agent action; ensuring agents only 
do what they were authorized to do, and nothing else. Deploying AI agents in production without this layer of protection is an unacceptable 
operational and security risk.

The SDK is currently in early-access beta for selected teams building production AI systems that require accountability, auditability, and 
control.

## Install

```bash
pip install agent-governance
```

## Access (Beta)

API access is currently managed through early access:

- Request access: https://www.homersemantics.com/ai-agent-governance-and-oauth
- Reach out to Anant at anantdhavale@gmail.com or info@homersemantics.com
- Receive approval and API credentials
- Review terms in `TERMS_OF_SERVICE.md`

## Quick Start

```python
from agent_governance import AgentGovernanceClient
import os

client = AgentGovernanceClient(api_key=os.getenv("AGENT_GOVERNANCE_API_KEY"))

# Create agent
agent = client.create_agent(
    purpose="Email classifier",
    capabilities=["read_email", "move_email", "send_reply"]
)

# Validate action before executing
response = client.validate(
    agent_id=agent.agent_id,
    action="move_email",
    parameters={"email_id": "123", "folder": "spam"}
)

if response.result.value == "approved":
    mailbox.move_email("123", "spam")
else:
    print(f"Action rejected: {response.violations}")
```

## What the SDK Provides

- Authenticated client access to Agent Governance services
- Agent registration and identity-bound operations
- Sync and async validation calls
- Batch validation support
- Governance-oriented telemetry surfaces

## Compatibility

Existing `cerone` imports continue to work in this release. New integrations should use:

```python
from agent_governance import AgentGovernanceClient
```

## Usage Terms

Usage limits and commercial terms are defined in `TERMS_OF_SERVICE.md`.

Current free trial: up to 25 validations in the first 5 days.

## License

Proprietary commercial license. See `LICENSE`.

## Contact
- Reach out to Anant at anantdhavale@gmail.com or info@homersemantics.com
- If you are using Agent Governance, we would highly appreciate any feedback.
