# Gyroscope Live — Meta-Architect Engine

Gyroscope is a multi-layer meta-cognitive system designed to run projects, systems, and tasks in a way that is:

- consistent,
- auditable,
- reproducible,
- resilient to both human and AI errors.

The system is composed of layers (BIOS → Kernel → Delta → Session) that handle operational memory, stabilization, planning, critique, and final outputs.

## Core Roles

### Architect
Generates the plan — a blueprint. This is the high-level structure of the task.

### Critic
Evaluates errors, gaps, risks, and inconsistencies.

### Implementer
Translates the blueprint into real code, structures, or documents.

### Governor (optional)
Supervisory layer for multi-agent coordination and governance.

## Cognitive Governance & I.I.L

Gyroscope is governed by the **Cognitive Governance Protocol (v0.1)** and grounded in the  
**Interference Intelligence Layer (I.I.L) Manifest v0.1**:

- [I.I.L Manifest v0.1](./MANIFESTO.md)
- [Cognitive Governance Protocol v0.1](./docs/CognitiveGovernanceProtocol.md)

These documents define:
- how human–AI collaboration should work,
- how roles are separated (Architect / Critic / Implementer / Governor),
- how we ensure auditability, safety, and reproducibility.

## How to run the project

```bash
# create and activate venv
python -m venv venv
source venv/bin/activate

# install dependencies (when we add requirements.txt)
pip install -r requirements.txt

# run local meta-architect stub/proxy
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# test streaming client
python test_client.py --prompt "Explain what Gyroscope middleware does in two sentences."