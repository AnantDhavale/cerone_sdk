# Cerone

**Check AI agent actions before they run.**

Cerone gives your agent an identity, lets you declare what it is supposed to do,
and returns a runtime decision before a tool call executes:

- `approved`
- `flagged`
- `rejected`

Use it when your agent is about to do something real:

- read or write files
- hit internal APIs
- query a database
- perform billing, support, or ops actions
- call tools on behalf of users

Cerone is built for teams that want a simple question answered at runtime:

**Should this agent be allowed to do this action right now?**

---

## Why Developers Install Cerone

- validate agent tool calls before execution
- keep your existing model stack and keys
- detect actions that do not fit the agent's declared purpose
- catch risky or suspicious action payloads early
- add identity, trust, and audit signals without rebuilding your app
- start from a hosted trial directly from the SDK

Cerone is not a model proxy. It sits around agent actions, not between you and
your LLM provider.

---

## Install

```bash
pip install cerone
```

Fastest way to verify everything works:

```bash
cerone demo
```

If your shell has not picked up the installed script yet:

```bash
python3 -m cerone demo
```

`cerone demo` bootstraps a hosted trial, creates a demo agent, runs one real
validation, and prints the result.

### Once The Trial Starts, Do This Next

Do not stop at "trial started."

Go straight to the first value path:

1. Create your first agent with a real purpose and capability set.
2. Validate one real action your app actually wants to run.
3. Look at the returned decision: `approved`, `flagged`, or `rejected`.

If you only bootstrap the trial but never create an agent or validate an
action, you have not actually tested Cerone yet.

If you only want a lightweight connectivity and hosted-trial bootstrap check:

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

If you are working from source:

```bash
git clone https://github.com/AnantDhavale/cerone_sdk.git
cd cerone_sdk
pip install -e .
```

---

## Quick Start

```python
import asyncio

from cerone import CeroneClient, infer_agent_profile_from_action


async def main():
    client = CeroneClient(
        base_url="https://api.homersemantics.com",
    )

    try:
        profile = infer_agent_profile_from_action(
            "file_read",
            {"path": "README.md"},
            workspace_target="repository files such as README.md",
        )

        agent = client.create_agent(
            purpose=profile.purpose,
            capabilities=profile.capabilities,
            environment="development",
        )

        result = await client.validate_async(
            agent_id=agent.agent_id,
            action="file_read",
            parameters={"path": "README.md"},
        )

        print("Agent:", agent.agent_id)
        print("Decision:", result.result)
        print("Trust:", result.trust_score)
        print("Alignment:", result.semantic_alignment)
    finally:
        await client.aclose()


asyncio.run(main())
```

What happens here:

1. Cerone creates an agent identity with declared purpose and capabilities.
2. Your app asks Cerone to validate a real action.
3. Cerone returns a runtime decision before that action is executed.

---

## A More Typical Sync Example

```python
from cerone import CeroneClient

client = CeroneClient()

agent = client.create_agent(
    purpose="Answer customer billing questions and look up billing records.",
    capabilities=["db_read", "billing_api"],
    environment="development",
)

result = client.validate(
    agent.agent_id,
    "database_query",
    {"table": "billing", "customer_id": "123"},
)

print(result.result, result.trust_score)
client.close()
```

The intended flow is simple:

- `approved` -> continue
- `flagged` -> review or warn according to your app policy
- `rejected` -> block execution

---

## Purpose Fidelity Matters

Cerone works best when the declared purpose actually matches what the agent is
doing.

If you are wrapping common tools like `file_read`, avoid vague purpose text.
This is better:

```python
from cerone import CeroneClient, infer_agent_profile_from_action

client = CeroneClient(integration_id="openclaw-plugin")

profile = infer_agent_profile_from_action(
    "file_read",
    {"path": "README.md"},
    workspace_target="repository files such as README.md",
)

agent = client.create_agent(
    purpose=profile.purpose,
    capabilities=profile.capabilities,
    environment="development",
)
```

Use `infer_agent_profile_from_action(...)` when you want stronger default
purpose and capability hints for common tool patterns.

---

## Single Validation vs Batch Validation

Start with `validate(...)` for one action. Use `validate_batch([...])` only when
you already have multiple validation items to send together.

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

If you call `validate_batch([])`, the SDK raises a local error before sending a
request.

---

## What Cerone Checks

Cerone is useful when permissions alone are not enough.

It helps answer questions like:

- is this action consistent with the agent's declared purpose?
- is this tool use inside the granted capability scope?
- does this payload look suspicious, evasive, or unsafe?
- should the action be allowed, flagged, or blocked?

Depending on the action and context, Cerone can help catch:

- agents drifting outside their role
- over-permitted agents doing the wrong thing
- suspicious file, API, or data access patterns
- manipulative or policy-evasive tool calls

---

## SDK Lifecycle Hooks

Cerone stays lightweight, but it can emit structured local lifecycle signals for
debugging, integration analytics, or your own telemetry sink.

```python
from cerone import CeroneClient, TelemetryEventType


def on_sdk_event(event):
    if event.event_type == TelemetryEventType.LOCAL_ERROR:
        print("Local SDK issue:", event.payload)


client = CeroneClient(
    integration_id="openclaw-plugin",
    telemetry_hook=on_sdk_event,
)
```

Current hook events:

- `client_initialized`
- `hosted_trial_started`
- `trial_token_received`
- `agent_created`
- `validation_attempted`
- `validation_result_received`
- `batch_validation_attempted`
- `local_error`

---

## Hosted Trial and Access

Cerone currently has two usage paths.

### 1. Hosted trial

- `CeroneClient()` can bootstrap an anonymous hosted trial token automatically
- includes **2,500 one-time validations**
- designed for first use, testing, and demos
- no model proxy required

### 2. Persistent access

- for POCs, pilots, and production environments
- contact us for provisioned persistent SDK access

Support and onboarding:

- [homersemantics.com](https://homersemantics.com)
- [info@homersemantics.com](mailto:info@homersemantics.com)

Hosted service terms:

- [TERMS_OF_SERVICE.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/TERMS_OF_SERVICE.md)
- [PRIVACY.md](https://github.com/AnantDhavale/cerone_sdk/blob/main/PRIVACY.md)

---

## Bring Your Own Model Key

Cerone validates agent behaviour. It does not replace your inference provider.

You keep your own OpenAI, Anthropic, or other provider key and send model calls
through your normal stack. Cerone checks intended actions and returns runtime
decisions around those actions.

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
        agent = client.create_agent(
            purpose="Summarise support tickets",
            capabilities=["read_ticket", "write_summary"],
        )

        validation = await client.validate_async(
            agent_id=agent.agent_id,
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

## Other SDKs

Current Cerone SDK surfaces:

- **Python**
  - package: `cerone`
  - repo: [github.com/AnantDhavale/cerone_sdk](https://github.com/AnantDhavale/cerone_sdk)

- **Node / JavaScript**
  - package: `agent-governance`
  - repo: [github.com/AnantDhavale/agent-governance-js](https://github.com/AnantDhavale/agent-governance-js)

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

---

## Contact

- Website: [homersemantics.com](https://homersemantics.com)
- Support: [info@homersemantics.com](mailto:info@homersemantics.com)
- Founder: [anantdhavale@gmail.com](mailto:anantdhavale@gmail.com)

If you are building with agents and want tighter control over what they are
allowed to do, reach out.
Now with advanced analytics. 
