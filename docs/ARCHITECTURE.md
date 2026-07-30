# Architecture

## Overview

ORACLE is organized around a **mission** as the core unit of work: a scoped,
authorized engagement that flows through discovery, analysis, and reporting
while every action is checked against scope and logged to an evidence graph.

```
                         ┌─────────────────────┐
                         │   Operator (CLI)    │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   oracle/core       │
                         │  Mission state,     │
                         │  scope enforcement  │
                         └──────────┬──────────┘
                                    │
        ┌───────────────┬──────────┼──────────┬───────────────┐
        │               │                     │               │
┌───────▼──────┐ ┌───────▼───────┐ ┌───────────▼─────────┐ ┌───▼────────────┐
│reconnaissance│ │   scanning    │ │    exploitation      │ │   reporting    │
│  (discovery) │ │ (vuln/service │ │ (opt-in, controlled  │ │ (evidence →    │
│              │ │   scanning)   │ │  workflow chaining)  │ │  report)       │
└───────┬──────┘ └───────┬───────┘ └───────────┬──────────┘ └───┬────────────┘
        │                │                     │                │
        └────────────────┴──────────┬──────────┴────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   Evidence Graph       │
                         │ (networkx-backed store)│
                         └────────────────────────┘
```

## Observed Components (Confirmed)

The following components are confirmed present in the running system (visible in the
Control Plane dashboard and CLI output) and should anchor the rest of this document as
it's filled in against the real codebase:

- **Control Plane** — web dashboard (default port `8088`) showing mission phase, hosts,
  findings, workers, approvals, artifacts, and operator notes
- **Planner / Mission Manager** — evaluates the next action each iteration against
  deterministic guardrails
- **AI Council** — named advisor backend(s) (e.g. `nim`) that propose actions; decisions
  are accepted, overridden, or deferred based on a confidence gate, with agreement/drift
  tracked over time
- **Attack Graph** — nodes/edges built from discovered hosts/services/findings, with
  per-node risk scoring and correlated path candidates
- **Timeline** — a stream of reasoning steps, decisions, and system events for the mission
- **Topology** — discovered subnets/hosts/services assembled into a graph
- **Replay System** — writes replay artifacts per mission so a run can be stepped through
  after the fact
- **Plugin System** — `nmap` (TCP port scan + service/version detection), `http` (single
  request, status/headers/body preview), `fuzz` (directory enumeration via gobuster/ffuf)
  confirmed as built-in plugins
- **Deterministic Fallback** — when no AI backend is reachable, the mission continues
  using deterministic logic rather than stopping or guessing

`The architecture consists of a core engine (planner, intelligence, reporting), a plugin system (nmap, fuzz, http, dependency_check), and a runtime layer for task execution.
boundaries once cross-referenced against the codebase — the above list is grounded in
observed dashboard/CLI behavior, but the internal file/module layout may differ from the
five-layer sketch that follows.]`

## Core Concepts

### Mission
A mission binds a **scope**, a set of **modules** to run, and produces an
**evidence graph** as output. Missions are resumable and auditable.

### Scope Guard
Every module call passes through `oracle/core/scope_guard.py` (or your
equivalent), which checks the target against the active scope definition
before any network action is taken. Actions outside scope are rejected and
logged, not silently skipped.

### Evidence Graph
Rather than free-text logs, findings are stored as nodes/edges (hosts,
services, vulnerabilities, credentials, relationships between them) using
`networkx`. This is what lets `oracle report generate` build a structured
report automatically instead of requiring manual write-up.

### AI Advisory Layer
The advisory layer reads the current evidence graph and surfaces
**suggestions** — likely attack paths, priority findings, missing coverage —
but never executes an action autonomously. The operator approves every step.
This is a deliberate design choice: ORACLE augments a red teamer's judgment,
it doesn't replace it.

## Module Interface

New reconnaissance/scanning/exploitation modules implement a common interface
so they can be orchestrated uniformly:

```python
class OracleModule(Protocol):
    name: str
    requires: list[str]          # external tool dependencies

    def run(self, target: ScopedTarget, context: MissionContext) -> Findings:
        ...
```

`Plugins are defined by a manifest.yaml and a Python class implementing the Plugin interface, handling scanning and result validation.
finalized — this is illustrative scaffolding, not the shipped implementation.]`

## Data Flow

1. Operator defines scope → `oracle scope add`
2. Operator starts mission → `oracle mission start`
3. Core dispatches enabled modules, each checked against scope guard
4. Module findings are normalized and written to the evidence graph
5. AI advisory layer annotates the graph with triage notes
6. Reporting layer renders the graph into the requested output format
