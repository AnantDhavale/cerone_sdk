# Cerone — Runtime Governance for AI Agents

**Install it. Create an agent. Validate a real action. See a live governance decision in minutes.**

Cerone gives every AI agent a cryptographic identity, validates intended actions
before execution, and returns explicit runtime decisions:

- `approved`
- `flagged`
- `rejected`

Start immediately from the SDK with **2,500 one-time free validations**.

**Powered by AZTP (Agent Zero Trust Platform)**

---

## Why Developers Use Cerone

- start immediately with hosted trial access from the SDK
- validate agent actions before they execute
- keep your own OpenAI, Anthropic, or other model key
- add runtime governance without replacing the rest of your stack
- get real decisions instead of vague policy claims
- use a lean trust layer instead of a heavy control-plane rewrite

---

## Install

```bash
pip install cerone
```

After install, you can verify connectivity and bootstrap a hosted trial from the terminal:

```bash
cerone
```

If your shell does not pick up the installed script immediately, this also works:

```bash
python3 -m cerone
```

**macOS note:** if `pip install cerone` succeeds but `cerone` says `command not found`, your Python scripts directory may not be on `PATH` yet. On many macOS installs, this fixes it:

```bash
echo 'export PATH="/Library/Frameworks/Python.framework/Versions/3.10/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
hash -r
```

Then try:

```bash
cerone
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
   - `CeroneClient()` can bootstrap an anonymous hosted trial token automatically
   - the current hosted trial is designed for evaluation and demo use
   - if the trial is exhausted, contact us for persistent access

2. **Python SDK usage**
   - use `CeroneClient()` with no key for hosted trial bootstrap
   - use a provisioned key for persistent POCs or production environments

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
        base_url="https://api.homersemantics.com",
    )

    try:
        certificate = client.create_agent(
            purpose="Customer billing support",
            capabilities=["db_read", "billing_api"],
        )

        result = await client.validate_async(
            agent_id=certificate.agent_id,
            action="database_query",
            parameters={"table": "billing", "customer_id": "123"},
        )

        print("Agent:", certificate.agent_id)
        print("Decision:", result.result)
        print("Trust:", result.trust_score)
    finally:
        await client.aclose()


asyncio.run(main())
```

---

## Single Action vs Batch Validation

Start with `validate(...)` for a single action. Use `validate_batch([...])` only
when you already have two or more validation items to send together.

Single action:

```python
from cerone import CeroneClient

client = CeroneClient()

agent = client.create_agent(
    purpose="Customer billing support",
    capabilities=["db_read", "billing_api"],
)

result = client.validate(
    agent.agent_id,
    "database_query",
    {"table": "billing", "customer_id": "123"},
)

print(result.result, result.trust_score)
client.close()
```

Batch validation:

```python
from cerone import CeroneClient

client = CeroneClient()

results = client.validate_batch([
    {
        "agent_id": "agt_123",
        "action": {
            "tool": "database_query",
            "parameters": {"table": "billing", "customer_id": "123"},
        },
    },
    {
        "agent_id": "agt_456",
        "action": {
            "tool": "refund_lookup",
            "parameters": {"refund_id": "rf_789"},
        },
    },
])

for item in results:
    print(item.agent_id, item.result, item.trust_score)

client.close()
```

If you call `validate_batch([])`, the SDK raises a local error before making a
request.

---

## What Cerone Does

Cerone is a runtime trust and governance layer for AI agents.

It:
- gives each agent a cryptographic identity
- validates intended actions against declared purpose and capability
- returns explicit runtime decisions before execution
- records audit and trust signals across agent activity
- preserves lineage and delegation boundaries where applicable

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

## Trial and Access

Cerone currently has two usage paths:

### 1. Hosted Trial
- `CeroneClient()` can bootstrap an anonymous hosted trial token automatically
- includes **2,500 one-time successful validations**
- no manual signup required to begin evaluation
- intended for initial testing and demos

### 2. Persistent Access
- for POCs, pilots, and production usage
- contact us for provisioned persistent SDK access

Support and contact:
- [homersemantics.com](https://homersemantics.com)
- [info@homersemantics.com](mailto:info@homersemantics.com)

Hosted service terms:
- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)

---

## Bring Your Own Model Key

Cerone governs agent **behaviour**, not inference.

You keep your own OpenAI, Anthropic, or other provider key and pass it directly
to your model calls. Cerone validates the intended action and records the
governance trail, but it does not sit in the middle of your model billing path.

```python
import asyncio
import openai

from cerone import CeroneClient


async def main():
    client = CeroneClient(
        base_url="https://api.homersemantics.com",
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
        print("Decision:", validation.result)

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

## Why Cerone Is Different

Many vendors talk about agentic governance. Very few have something real you
can install, run, and demo.

Cerone is different because it is:
- **runtime-real**: it makes live governance decisions in the execution path
- **lean**: it adds trust and control without demanding a full platform rewrite
- **developer-usable**: installable, callable, and demoable now
- **business-aware**: designed to support workflow-aware governance, not just technical checks

Most of the category still looks theoretical. Cerone is meant to be used.

---

## Architecture

```text
Your Agent Code
      │
      ▼
  Cerone SDK  ──────────────────────────────────────────┐
      │                                                  │
      ▼                                                  ▼
AZTP Platform (api.homersemantics.com)  Your LLM Provider
  ├─ Identity Manager
  ├─ Semantic Validator
  ├─ Trust Engine
  └─ Audit Logger
```

Cerone is distributed by design: a thin SDK on the client side and centralized
identity, validation, governance, and audit logic on the server side.

---

## License

This SDK repository currently uses a proprietary commercial SDK license.

The SDK source license and the hosted Cerone service terms are separate:

- SDK / package code: [LICENSE](https://github.com/AnantDhavale/cerone_sdk/blob/main/LICENSE)
- Hosted service usage: [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)

Free trial and hosted commercial terms are subject to change.

Homer Semantics and Anant Dhavale are not liable for losses, damages, business
interruption, model outputs, workflow outcomes, or downstream actions arising
from use of the SDK or hosted service. Use Cerone at your own discretion and risk.

---

## Contact

- Website: [homersemantics.com](https://homersemantics.com)
- Support: [info@homersemantics.com](mailto:info@homersemantics.com)
- Founder: [anantdhavale@gmail.com](mailto:anantdhavale@gmail.com)

If you are building with agents and want runtime governance that is actually
usable, reach out.
