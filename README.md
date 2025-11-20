
# AgentDNA

AgentDNA is a package that helps in auditing and verifiability of Agents within a multi-agent communication system.


## Key Features
- **Unified trust layer** for multi-agent systems  
- Automatically manages:
  - DID setup  
  - Signing traces of conversation  
  - Verification of Agent conversation  
- Immutable audit logging
- Fully compatible with:
  - Google A2A protocol 
  - ADK, Crew and LangGraph frameworks 

## Installation
```
# Installation via pip
pip install agentdna

# Installation via uv
uv add agentdna
```

## Architecture
AgentDNA internally wraps several layers to keep agent developers free from Rubix-specific complexity.

```
┌─────────────────────────┐
│      Agent Developer    │
│  dna.build() / handle() │
└─────────────┬───────────┘
              │
┌─────────────────────────┐
│       AgentDNA          │
│ role = "host" | "remote"│
└─────────────┬───────────┘
              │
┌─────────────────────────┐
│   RubixMessageHandler   |
│ - build host/agent msgs │
│ - parse & verify inbound│
│ - NFT execution (host)  │
└─────────────┬───────────┘
              │
┌───────────────────────────┐
│    RubixTrustService      │
│ - DID management          │
│ - sign_envelope()         │
│ - verify_envelope()       │
│ - verify_message_payload()│
└─────────────┬─────────────┘
              │
┌─────────────────────────┐
│       rubix-py SDK      │
│ RubixClient             │
│ Signer                  │
│ Querier                 │
└─────────────────────────┘
```

## Agent Roles
AgentDNA supports two roles:

### **Host Agent**
Responsible for:
- Signing and sending outgoing **host_request**
- Verifying inbound **agent_response**
- Optional **NFT execution** for audit logging

### **Remote Agent**
Responsible for:
- Verifying inbound **host_request**
- Signing outbound **agent_response**

## Quick Start Example
### **Initializing**
```python
from agentdna import AgentDNA

dna = AgentDNA(alias="<agent alias>", role="<host/remote>")

```
### **Remote Agents**
```python
verify_info = await dna.handle(raw_text=raw_message, verify_mode="<light/heavy>")

reply = run_llm(original_msg)

built = dna.build(
    original_message=original_msg,
    response=reply,
    host_block=host_block,
)
```

### **Host Agent**
```python
outbound = dna.build(
    original_message="Are you free tomorrow?",
    state={"task_id": tid, "context_id": cid}
)

result = await self.dna.handle(
    resp_parts=resp_parts,
    original_task=task,
    remote_name=agent_name,
)
```

## Project Structure
```
agentdna/
 ├── core.py
 ├── handler.py
 ├── trust.py
 ├── node_client.py
 └── ...
```

## Examples
Full Host, ADK, and LangGraph examples can be found inside `examples/`.

## License
MIT
