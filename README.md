# Cerone — Governance and Zero Trust Runtime for AI Agents

**Powered by AZTP (Agent Zero Trust Platform)**

Cerone gives every AI agent a cryptographic identity, validates that its
actions align with its declared purpose, and produces an auditable runtime
trail across identity, validation, governance, and delegated token exchange.

Most teams deploying agents in production still have weak runtime control over
what those agents actually do. Cerone is built to fix that.

Why developers try Cerone:
- add governance without replacing the rest of the agent stack
- keep your own model-provider key and model spend
- get explicit `approved`, `flagged`, or `rejected` runtime decisions
- use a lean runtime trust layer instead of a heavy control-plane rewrite

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

## Access Modes

Cerone now has two usage paths:

1. **Hosted API trial**
   - the hosted AZTP backend supports an anonymous evaluation flow
   - that trial currently lives at the API layer
   - if you are testing the raw hosted API, contact us for the latest trial guidance

2. **Python SDK usage**
   - the current `cerone` Python package still expects an API key
   - for SDK use in demos, POCs, or production, email us for a provisioned key

Hosted signup and support:

- [homersemantics.com](https://homersemantics.com)
- [info@homersemantics.com](mailto:info@homersemantics.com)

Hosted service terms:

- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)

---

## Quick Start

```python
import asyncio

from cerone import CeroneClient


async def main():
    client = CeroneClient(
        base_url="https://aztp-homer-semantics.onrender.com",
        api_key="sk_startup_...",
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
        base_url="https://aztp-homer-semantics.onrender.com",
        api_key="sk_startup_...",
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
    base_url="https://aztp-homer-semantics.onrender.com",
    api_key="sk_startup_...",
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

| | Trial | Startup | Pro | Enterprise |
|---|---|---|---|---|
| Validations / 30-day window | Hosted evaluation flow | 50,000 | 500,000 | Custom |
| Agents | Limited | 25 | 250 | Custom |
| Audit retention | Limited | 30 days | 90 days | 365 days |
| Model access | BYO | BYO | BYO now, managed later | BYO or managed |
| Support | — | Email | Priority | Dedicated |
| Commercial model | Evaluation | Contact us | Contact us | Contact us |

Current commercial motion:
- evaluate first
- contact us for provisioned persistent SDK access

---

## Architecture

```text
Your Agent Code
      │
      ▼
  Cerone SDK  ──────────────────────────────────────────┐
      │                                                  │
      ▼                                                  ▼
AZTP Platform (aztp-homer-semantics.onrender.com)  Your LLM Provider
  ├─ Identity Manager
  ├─ Semantic Validator
  ├─ Trust Engine
  └─ Audit Logger
```

---

## Integration Direction

Cerone is being shaped to govern:
- agent frameworks
- custom tool-calling runtimes
- business workflows that need identity, validation, and audit

If you want a specific framework or business-system integration, contact us directly.

---

## Usage and Quota

```bash
curl https://aztp-homer-semantics.onrender.com/usage \
  -H "X-API-Key: sk_startup_..."
```

This returns current usage, remaining quota, reset date, and tier feature flags.

---

## Documentation

- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)


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
