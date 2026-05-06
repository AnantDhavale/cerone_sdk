# Cerone — Governance and Zero Trust Runtime for AI Agents

**Powered by AZTP (Agent Zero Trust Platform)**

Cerone gives every AI agent a cryptographic identity, validates that its
actions align with its declared purpose, and produces an auditable runtime
trail across identity, validation, governance, and delegated token exchange.

Most teams deploying agents in production still have weak runtime control over
what those agents actually do. Cerone is built to fix that.

---

## Install

The current hosted SDK package name is `cerone`.

```bash
pip install cerone
```

If you are working from source, clone this repository and install it locally:

```bash
git clone https://github.com/AnantDhavale/cerone_sdk.git
cd cerone_sdk
pip install -e .

```

---

## Get Your Free API Key

Hosted onboarding is self-serve. No waitlist and no approval step.

```bash
curl -X POST https://api.homersemantics.com/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "name": "Your Name"}'
```

You receive an `sk_free_...` key instantly. No password is required for SDK
authentication.

Free tier currently includes:

- **5,000 validations per 30-day window**
- **free for the first 30 days from signup**
- **bring your own OpenAI / Anthropic / other model-provider key**
- **Cerone does not proxy or charge for model inference**

Hosted signup and support:

- [homersemantics.com](https://homersemantics.com)
- [info@homersemantics.com](mailto:info@homersemantics.com)

Hosted service terms:

- [TERMS_OF_SERVICE.md] https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md

---

## Quick Start

```python
import asyncio

from cerone import CeroneClient


async def main():
    client = CeroneClient(
        base_url="https://api.homersemantics.com",
        api_key="sk_free_...",
    )

    try:
        health = client.health_check()
        print(f"Health: {health}")

        certificate = client.create_agent(
            purpose="Customer billing support",
            capabilities=["db_read", "billing_api"],
        )

        print(f"Agent ID: {certificate.agent_id}")
        print(f"Trust score: {certificate.trust_score}")

        result = await client.validate_async(
            agent_id=certificate.agent_id,
            action="database_query",
            parameters={"table": "billing", "customer_id": "123"},
        )
        print(f"Validation result: {result}")

        trust_score = client.get_trust_score(certificate.agent_id)
        print(f"Trust score: {trust_score}")

        audit_log = client.get_audit_log(certificate.agent_id, limit=10)
        print(f"Audit log: {audit_log}")
    finally:
        await client.aclose()


asyncio.run(main())
```

---

## What Cerone Validates

| Check | What it catches |
|---|---|
| **Cryptographic identity** | Impersonation, spoofed agents |
| **Semantic alignment** | Agents acting outside their declared purpose |
| **Trust scoring** | Behavioural drift over time |
| **Capability scope** | Agents calling tools they were never granted |
| **Lineage integrity** | Unauthorized parent-child relationships |

---

## Bring Your Own Model Key

Cerone governs agent **behaviour**, not inference.

You keep your own OpenAI, Anthropic, or other provider key and pass it directly
to your model calls. Cerone validates the agent action and records the
governance trail, but it does not sit in the middle of your model billing path.

```python
import asyncio
import openai

from cerone import CeroneClient


async def main():
    client = CeroneClient(
        base_url="https://api.homersemantics.com",
        api_key="sk_free_...",
    )
    openai_client = openai.AsyncOpenAI(api_key="sk-...")

    try:
        certificate = client.create_agent(
            purpose="Summarise support tickets",
            capabilities=["read_ticket", "write_summary"],
        )

        validation = await client.validate_async(
            agent_id=certificate.agent_id,
            action="write_summary",
            parameters={"ticket_id": "T-001"},
        )
        print(f"Validation result: {validation}")

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Summarise ticket T-001"}],
        )
        print(response)
    finally:
        await client.aclose()


asyncio.run(main())
```

---

## Validation Pattern

The current `cerone` SDK exposes validation through `CeroneClient`.
Validate the intended action before running the local tool or model call you
control.

```python
from cerone import CeroneClient

client = CeroneClient(
    base_url="https://api.homersemantics.com",
    api_key="sk_free_...",
)

certificate = client.create_agent(
    purpose="Customer data analysis",
    capabilities=["db_read", "analytics"],
)

validation = client.validate(
    agent_id=certificate.agent_id,
    action="database_query",
    parameters={"customer_id": "123"},
)
print(f"Validation result: {validation}")

# Run your local tool after validation.
customer = {"customer_id": "123", "name": "Jane Doe"}
print(customer)

client.close()
```

---

## Tiers

| | Free | Startup | Pro | Enterprise |
|---|---|---|---|---|
| Validations / 30-day window | 5,000 | 50,000 | 500,000 | Custom |
| Agents | 5 | 25 | 250 | Custom |
| Audit retention | 7 days | 30 days | 90 days | 365 days |
| Model access | BYO only | BYO only | BYO now, managed later | BYO or managed |
| Support | Community | Email | Priority | Dedicated |
| Commercial model | Free for first 30 days | Contact / self-serve pricing | Contact / self-serve pricing | Contact us |

Commercial packaging may evolve, but the current hosted free-tier limits above
match the backend configuration.

---

## Architecture

```text
Your Agent Code
      │
      ▼
  Cerone SDK  ──────────────────────────────────────────┐
      │                                                  │
      ▼                                                  ▼
AZTP Platform (api.homersemantics.com)            Your LLM Provider
  ├─ Identity Manager
  ├─ Semantic Validator
  ├─ Trust Engine
  └─ Audit Logger
```

---

## Supported Frameworks and Integrations

AZTP currently ships adapters or normalization paths for:

- CrewAI
- Google ADK
- Gemma
- Salesforce
- ServiceNow
- Slack
- Microsoft 365
- Google Workspace
- Jira

---

## Usage and Quota

```bash
curl https://api.homersemantics.com/usage \
  -H "X-API-Key: sk_free_..."
```

This returns current usage, remaining quota, reset date, free-tier expiry, and
tier feature flags.

---

## Documentation

- [TERMS_OF_SERVICE.md]https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md


---

## License

## License

This SDK repository currently uses a proprietary commercial SDK license.

The SDK source license and the hosted Cerone service terms are separate:

- SDK / package code: [LICENSE](https://github.com/AnantDhavale/cerone_sdk/blob/main/LICENSE)
- Hosted service usage: [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)

Free trial and hosted commercial terms are subject to change.


---

## Contact and Feedback

- Website: [homersemantics.com](https://homersemantics.com)
- Support: [info@homersemantics.com](mailto:info@homersemantics.com)
- Founder: [anantdhavale@gmail.com](mailto:anantdhavale@gmail.com)

If you are using Cerone, feedback is genuinely useful. POCs and design
partners are welcome.
