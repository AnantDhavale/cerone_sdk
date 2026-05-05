# Cerone — Governance and Zero Trust Runtime for AI Agents

**Powered by AZTP (Agent Zero Trust Platform)**

Cerone gives every AI agent a cryptographic identity, validates that its actions align with its declared purpose, and produces an auditable runtime trail across identity, validation, governance, and delegated token exchange.

Most teams deploying agents in production still have weak runtime control over what those agents actually do. Cerone is built to fix that.

---

## Install

The current SDK/package name in this repo is `aztp`.

```bash
pip install git+https://github.com/AnantDhavale/AZTP.git
```

If you are working locally:

```bash
git clone https://github.com/AnantDhavale/AZTP.git
cd AZTP
pip install -e .
```

---

## Get Your Free API Key

Self-serve signup. No waitlist and no approval step.

```bash
curl -X POST https://aztp-homer-semantics.onrender.com/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-secure-password", "name": "Your Name"}'
```

You receive an `sk_free_...` key instantly.

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
from aztp.sdk import AZTPClient, AZTPAgent

async def main():
    client = AZTPClient(
        api_url="https://aztp-homer-semantics.onrender.com",
        api_key="sk_free_...",
    )

    agent = AZTPAgent(
        purpose="Customer billing support",
        capabilities=["db_read", "billing_api"],
        client=client,
    )
    await agent.initialize()

    print(f"Agent ID: {agent.agent_id}")
    print(f"Trust score: {agent.certificate.trust_score}")

    result = await agent.validate_and_execute(
        tool="database_query",
        parameters={"table": "billing", "customer_id": "123"},
        execute_fn=lambda: {"amount": 99.99, "status": "paid"},
    )
    print(f"Result: {result}")

    child = await agent.spawn(
        purpose="Verify roaming charges",
        capabilities=["network_api"],
    )

    await agent.terminate()
    await client.close()

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
import openai
from aztp.sdk import AZTPClient, AZTPAgent

client = AZTPClient(
    api_url="https://aztp-homer-semantics.onrender.com",
    api_key="sk_free_...",
)
openai_client = openai.AsyncOpenAI(api_key="sk-...")  # your key, your spend

agent = AZTPAgent(
    purpose="Summarise support tickets",
    capabilities=["read_ticket", "write_summary"],
    client=client,
)
await agent.initialize()

await agent.validate_and_execute(
    tool="write_summary",
    parameters={"ticket_id": "T-001"},
    execute_fn=lambda: openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Summarise ticket T-001"}],
    ),
)
```

---

## Decorator Pattern

```python
agent = AZTPAgent(
    purpose="Customer data analysis",
    capabilities=["db_read", "analytics"],
    client=client,
)
await agent.initialize()

@agent.action("database_query")
async def query_customers(customer_id: str):
    return {"customer_id": customer_id, "name": "Jane Doe"}

customer = await query_customers("123")
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
- Issues: [github.com/AnantDhavale/AZTP/issues](https://github.com/AnantDhavale/AZTP/issues)

If you are using Cerone, feedback is genuinely useful. I am doing some additions/ changes, please do reach out if you face any issues.
