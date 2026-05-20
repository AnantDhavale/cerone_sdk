# Cerone — Runtime Governance and Security for AI Agents

**Install it. Create an agent. Validate a real action. See a live runtime decision in minutes.**

Cerone gives every AI agent a cryptographic identity, validates intended actions
before execution, helps detect unsafe or evasive action patterns, and returns
explicit runtime decisions:

- `approved`
- `flagged`
- `rejected`

Start immediately from the SDK with **2,500 one-time free validations**.

Cerone is a thin runtime layer: keep your own model stack, add identity,
validation, security checks, containment, and auditability around agent actions.

---

## Why Developers Use Cerone

- start immediately with hosted trial access from the SDK
- validate agent actions before they execute
- add runtime security checks without replacing the rest of your stack
- detect risky action patterns like injection, exfiltration, or policy override
- contain risky agents with explicit runtime decisions and operator controls
- keep your own OpenAI, Anthropic, or other model key
- get real decisions instead of vague policy claims
- use a lean trust layer instead of a heavy control-plane rewrite

---

## Install

```bash
pip install cerone
```

After install, you can verify connectivity and bootstrap a hosted trial from the terminal:

```bash
cerone demo
```

If your shell does not pick up the installed script immediately, this also works:

```bash
python3 -m cerone demo
```

`cerone demo` is the fastest activation path. It bootstraps a hosted trial,
creates a demo agent, runs one live validation, and prints your remaining trial
usage.

If you only want a lightweight connectivity and trial bootstrap check, use:

```bash
cerone
```

**macOS note:** if `pip install cerone` succeeds but `cerone` says `command not found`, your Python scripts directory may not be on `PATH` yet. On many macOS installs, this fixes it:

```bash
echo 'export PATH="/Library/Frameworks/Python.framework/Versions/3.10/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
hash -r
```

Then try:

```bash
cerone demo
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

Hosted service & privacy terms:

- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)
- [PRIVACY.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/PRIVACY.md)

---

## Quick Start

Terminal-first activation:

```bash
cerone demo
```

Fallback if the installed script is not on `PATH` yet:

```bash
python3 -m cerone demo
```

This runs one real hosted-trial flow end to end:
- bootstraps a trial token
- creates a demo agent
- validates one safe action
- shows the decision, trust score, latency, and remaining trial usage

Python SDK:

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

Cerone is a runtime governance, trust, and security layer for AI agents.

It:
- gives each agent a cryptographic identity
- validates intended actions against declared purpose and capability
- returns explicit runtime decisions before execution
- helps detect unsafe, manipulative, or exfiltration-oriented action payloads
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

## Why Security Teams Care

Cerone is not just a governance layer. It is also a runtime security layer for
agent actions.

That means Cerone can help with:

- interception before execution, not just detection after the fact
- context-aware validation of whether an action fits what this agent is
  supposed to be doing
- zero-trust treatment of agent tool calls until they are validated
- injection and instruction-override resistance
- secret harvesting and exfiltration detection
- explicit allow / flag / reject decisions instead of silent risk
- containment through manual kill switch and lineage-aware controls
- runtime audit trails for incident review and operator oversight

The goal is not to replace your whole security stack. The goal is to give AI
agents a thin runtime control and security layer exactly where agent misuse
happens: at action time.

In practice, Cerone's security model is:

- **interception before execution**: validate intended tool use before the tool
  runs
- **context-aware validation**: check whether an action is consistent with the
  agent's declared purpose, capability, and runtime context
- **zero-trust for agents**: do not assume a previously well-behaved agent
  should automatically be trusted on its next action

---

## Runtime Policy and Containment

Cerone is also evolving into a stronger runtime policy layer, not just an
identity and semantic-alignment layer.

The current direction includes runtime detections for patterns such as:

- prompt injection
- instruction override
- role manipulation
- policy evasion
- secret harvesting
- data exfiltration
- obfuscation and encoded payload tricks

These checks are intended to complement semantic validation:

- semantic alignment asks whether the action fits the declared purpose
- runtime policy checks ask whether the action payload itself looks unsafe,
  manipulative, evasive, or exfiltration-oriented

Cerone also has an operator-controlled containment direction:

- manual kill switch support
- soft containment
- hard containment

Important:
- detection does not automatically activate containment by default
- the intended default behavior is operator-controlled, manual activation

For integrators, the practical rule remains simple:

- `approved` -> continue
- `flagged` -> review or warn according to your app policy
- `rejected` -> block execution

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

Hosted service & privacy terms:
- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)
- [PRIVACY.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/PRIVACY.md)
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
- **security-relevant**: it helps catch misuse before tools execute
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

## Other SDKs

Cerone now has more than one SDK surface.

Current SDKs:

- **Python SDK**
  - package: `cerone`
  - repo: [github.com/AnantDhavale/cerone_sdk](https://github.com/AnantDhavale/cerone_sdk)

- **Node / JavaScript SDK**
  - package: `agent-governance`
  - repo: [github.com/AnantDhavale/agent-governance-js](https://github.com/AnantDhavale/agent-governance-js)

The product name is **Cerone** across both SDKs.  
The npm package uses the name `agent-governance` for discoverability.

If you are building in Python:

```bash
pip install cerone
```

If you are building in Node:

```bash
npm install agent-governance
```

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

By downloading this SDK user acknowledge the terms of service and privacy as mentioned here. 
