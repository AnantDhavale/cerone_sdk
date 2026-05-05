# Cerone — Governance and Zero Trust Runtime for AI Agents

**Powered by AZTP (Agent Zero Trust Platform)**

Cerone gives every AI agent a cryptographic identity, validates that its actions align with its declared purpose, and produces an auditable runtime trail across identity, validation, governance, and delegated token exchange.

Most teams deploying agents in production still have weak runtime control over what those agents actually do. Cerone is built to fix that.

---

## Install

The current PyPI package name is `cerone`.

```bash
pip install cerone
```

The SDK repository is `cerone-sdk`.

If you are working locally:

```bash
git clone https://github.com/AnantDhavale/cerone-sdk.git
cd cerone-sdk
pip install -e .
```

---

## Get Your Free API Key

Self-serve signup. No waitlist and no approval step.

```bash
curl -X POST https://aztp-homer-semantics.onrender.com/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "name": "Your Name"}'
```

You receive an `sk_free_...` key instantly. No password is required for SDK authentication.

Free tier currently includes:
- **5,000 validations per 30-day window**
- **free for the first 30 days from signup**
- **bring your own OpenAI / Anthropic / other model-provider key**
- **Cerone does not proxy or charge for model inference**

Hosted signup and support:
- [homersemantics.com](https://homersemantics.com)
- [info@homersemantics.com](mailto:info@homersemantics.com)

Hosted service terms:
- [HOSTED_TERMS.md](HOSTED_TERMS.md)

---

## Quick Start

```python
import asyncio
from cerone import CeroneClient

async def main():
    client = CeroneClient(
        api_url="https://aztp-homer-semantics.onrender.com",
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

You keep your own OpenAI, Anthropic, or other provider key and pass it directly to your model calls. Cerone validates the agent action and records the governance trail, but it does not sit in the middle of your model billing path.

```python
import asyncio
import openai
from cerone import CeroneClient

async def main():
    client = CeroneClient(
        api_url="https://aztp-homer-semantics.onrender.com",
        api_key="sk_free_...",
    )
    openai_client = openai.AsyncOpenAI(api_key="sk-...")  # your key, your spend

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

The current `cerone` PyPI SDK exposes validation through `CeroneClient`.
Validate the intended action before running the local tool or model call you control.

```python
from cerone import CeroneClient

client = CeroneClient(
    api_url="https://aztp-homer-semantics.onrender.com",
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
| Price | Free for first 30 days | Contact / self-serve pricing | Contact / self-serve pricing | Contact us |

If you want fixed public pricing in this README, update this table once the commercial page is final.

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

## Supported Frameworks and Integrations

Cerone currently ships adapters or normalization paths for:

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
curl https://aztp-homer-semantics.onrender.com/usage \
  -H "X-API-Key: sk_free_..."
```

This returns current usage, remaining quota, reset date, free-tier expiry, and tier feature flags.

---

## Documentation

- [SDK Onboarding Guide](SDK_ONBOARDING_GUIDE.md)
- [Hosted Service Terms](HOSTED_TERMS.md)
- [Render Environment Changes](RENDER_ENV_CHANGES.md)

Live API docs:
- [aztp-homer-semantics.onrender.com/docs](https://aztp-homer-semantics.onrender.com/docs)

---

## License

Current repository/package metadata is **MIT**.

The open-source repository license and the hosted Cerone service terms are separate:
- repository/package code: **MIT**
- hosted service usage: [HOSTED_TERMS.md](HOSTED_TERMS.md)
Free trial is subject to change. Use the software at your own risk. 

---

## Contact and Feedback

- Website: [homersemantics.com](https://homersemantics.com)
- API docs: [aztp-homer-semantics.onrender.com/docs](https://aztp-homer-semantics.onrender.com/docs)
- Support: [info@homersemantics.com](mailto:info@homersemantics.com)
- Founder: [anantdhavale@gmail.com](mailto:anantdhavale@gmail.com)
- Issues: [github.com/AnantDhavale/cerone-sdk/issues](https://github.com/AnantDhavale/cerone-sdk/issues)

If you are using Cerone, feedback is genuinely useful. I am doing some additions/ changes, please do reach out if you face any issues. POCs and design partners welcome.
