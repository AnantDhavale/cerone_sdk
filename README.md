# Ceron (Beta) - Zero Trust Security and Production governance for AI Agents : Python SDK 


Ceron gives every AI agents a verifiable identity, enforces runtime policy checks on high-risk actions, and continuously adjusts control posture based on observed behavior. It helps teams keep autonomous systems inside approved boundaries in production.  Result: safer agent operations with clear governance, accountability, and enforcement.

Ceron helps teams enforce policy controls on agent actions and maintain operational accountability in production environments. Thus, it provides Zero Trust Security Validation, Verification and Governance for AI Agents. 

Ceron SDK is currently in early-access beta for selected users.

https://aztp.homersemantics.com/

## Install

```bash
pip install ceron
Access
API access (Beta) is currently managed through early access:
•	Request: https://aztp.homersemantics.com/
•	Receive approval and API credentials
•	Review terms in TERMS_OF_SERVICE.md
Quick Start
import os
from ceron import CeronClient

client = CeronClient(api_key=os.getenv("CERON_API_KEY"))

agent = client.create_agent(
    purpose="Approved operational workflow",
    capabilities=["approved_capability"],
)

response = client.validate(
    agent_id=agent.agent_id,
    action="approved_action",
    parameters={"key": "value"},
)

print(response.status)

What the SDK Provides
•	Authenticated client access to Ceron services
•	Agent registration and identity-bound operations
•	Sync/async validation calls
•	Batch validation support
•	Governance-oriented telemetry surfaces

Usage Terms
Usage limits and commercial terms are defined in TERMS_OF_SERVICE.md.

Current free trial: up to 100 validations in the first 5 days.

License
Proprietary commercial license. See LICENSE.

Contact
info@homersemantics.com

<img width="472" height="647" alt="image" src="https://github.com/user-attachments/assets/016a2b84-286c-41b8-98eb-aef335cada5d" />



