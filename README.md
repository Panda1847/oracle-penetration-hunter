<div align="center">

# ORACLE

## Oracle Penetration Hunter

### The hardened mission control plane for authorized security operations.

ORACLE turns scoped security testing into a controlled, observable, replayable operation: deterministic planning, advisory AI, signed engagements, isolated workers, evidence intelligence, live operator control, and executive-grade reporting in one command center.

[![License](https://img.shields.io/badge/license-MIT-1f2937.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org/)
[![Release](https://img.shields.io/badge/release-v4.0.0-7c3aed.svg)](RELEASE_STATUS.md)
[![Tests](https://img.shields.io/badge/tests-197%20passing-16a34a.svg)](tests/)
[![CI](https://github.com/Panda1847/oracle-penetration-hunter/actions/workflows/ci.yml/badge.svg)](https://github.com/Panda1847/oracle-penetration-hunter/actions/workflows/ci.yml)

[Dashboard](#the-control-plane) · [Quick start](#quick-start) · [Security model](#security-model) · [Architecture](#architecture)

</div>

> **Authorized use only.** ORACLE is built for signed engagements, internal environments owned by the operator, isolated research labs, and explicitly permitted competitions. It is not a permission system and it must never be used against systems without written authorization. Read [SECURITY.md](SECURITY.md) before running a mission.

![ORACLE control plane](assets/oracle_social_preview.png)

## The short version

ORACLE is not a loose collection of scanners. It is a **security operations control plane** that keeps the mission, policy, evidence, operators, workers, and outputs connected from preflight to final report.

It gives an operator one place to:

- define the mission objective and authorized scope;
- enforce lab or signed-engagement authorization before execution;
- observe decisions, actions, findings, and workers as they happen;
- pause, resume, or stop a live mission through a manager-owned state machine;
- gate sensitive actions behind explicit approvals;
- correlate hosts, services, findings, evidence, and attack paths;
- inspect findings, confidence, CVEs, assets, and evidence references;
- replay a mission and reconstruct what happened;
- export structured artifacts and professional reports.

**The AI can advise. The policy engine decides. The operator remains in control.**

## What ORACLE brings to the fight

### Mission command, not terminal chaos

The ORACLE runtime organizes work into explicit missions with objectives, profiles, iteration limits, phases, status transitions, audit records, and durable artifacts. The CLI is the authoritative launch surface; the web dashboard is the operator command center.

### Scope enforcement that fails closed

Loopback lab missions can run through the local lab guard. Non-loopback missions require a verified signed engagement record and trusted public key. Engagement validation covers expiry, revocation, scope, profile ceilings, and signature integrity. Invalid, expired, revoked, tampered, or out-of-scope authorization is rejected before the mission starts.

### A deterministic core with an AI edge

ORACLE's planner and policy engine remain authoritative. Advisory AI can rank or explain candidate actions, but it cannot invent an action outside the candidate set, bypass scope, override approvals, or replace deterministic fallback behavior. Malformed and out-of-range advisory responses are rejected.

Supported advisory paths include configured NIM and Ollama integrations, council-style recommendation review, local deterministic fallback, confidence gates, structured response validation, and prompt boundaries that treat tool output and evidence as untrusted data.

### Live operator control

The dashboard is a live control plane, not a static report page. Authenticated server-sent events provide bounded replay, keepalives, resynchronization, deduplication, and polling fallback. Operators can see the mission timeline and issue manager-backed pause, resume, and stop commands with actor, reason, version, and audit metadata.

### Approval gates for consequential actions

Actions that require human authorization become visible approval requests. Operators can approve, deny with a reason, or defer. Decisions are validated, idempotent, timestamped, emitted to the event stream, and recorded in the audit trail.

### Evidence that stays connected

ORACLE builds an evidence graph instead of leaving findings as disconnected text. Findings retain severity, confidence, affected assets, CVE references, evidence references, provenance, contradictions, and relationships to hosts, services, actions, and candidate attack paths.

### Attack-surface intelligence

The interactive attack graph visualizes hosts, services, findings, weighted relationships, risk-colored nodes, and top paths. Operators can filter node types, pan and zoom, inspect nodes with the keyboard, and move from graph context into the evidence inspector.

### Worker-aware execution

The dispatcher and worker registry expose authenticated worker identity, roles, capabilities, transport, heartbeat freshness, health score, and inflight jobs. The dashboard makes unsupported operations explicit rather than pretending that drain or quarantine controls exist when the runtime does not provide them.

### Replayable, reportable, reviewable

Every serious operation should be explainable after the fact. ORACLE preserves events, decisions, artifacts, audit records, reports, evidence packages, and replay data so a mission can be reviewed, exported, and reconstructed instead of trusted on memory alone.

## The control plane

The dashboard is organized around the operator's real workflow:

| Surface | What it does |
| --- | --- |
| **Command center** | Mission posture, phase progress, risk score, AI council posture, top findings, system health, and live controls. |
| **Live activity** | Streaming actions, findings, decisions, approvals, operator events, filters, and event inspection. |
| **Findings** | Ranked findings with severity, affected asset, confidence, CVEs, evidence, analyst status, and remediation notes. |
| **Attack graph** | Interactive hosts/services/findings graph with risk weighting, filters, paths, pan, zoom, and keyboard inspection. |
| **Workers** | Health, heartbeat age, inflight load, role, transport, and capability coverage. |
| **Evidence** | Provenance-aware evidence ledger, confidence signals, contradictions, and chain-of-custody context. |
| **Approvals** | Human authorization queue with approve, deny, defer, reason capture, and audit emission. |
| **Reports** | Mission summaries, intelligence reports, evidence exports, replay files, and packaged artifacts. |
| **Telemetry** | Health components, counters, gauges, traces, events-per-minute, and opt-in browser alerts. |

The launcher performs a preflight review before any runtime action. Dashboard launch is intentionally limited to loopback lab scope; signed live engagements use the authorized CLI workflow.

## Quick start: enter the lab

```bash
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

Run the safe simulated experience with the live control plane:

```bash
python -m oracle --demo --web --web-port 5000
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The demo path is the recommended first run. It exercises the dashboard, event stream, mission controls, findings, graph, telemetry, approvals, reports, and replay surfaces without launching a real target mission.

For environment diagnostics and readiness checks:

```bash
python -m oracle --doctor
python -m oracle --selftest
python -m oracle --list-plugins
python -m oracle --version
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md), [docs/INSTALLATION.md](docs/INSTALLATION.md), and [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the complete setup path.

## Authorized mission launch

### Local lab mode

For a loopback-only lab, make the authorization boundary explicit:

```bash
python -m oracle \
  --lab \
  --scope 127.0.0.1 \
  --mission-name lab-baseline \
  --objective "Map the local lab surface and identify observable misconfigurations" \
  --profile normal \
  --max-iter 10 \
  --web \
  --web-port 8088 \
  --report \
  --audit-log
```

### Signed engagement mode

For non-loopback scope, issue and verify a signed engagement artifact. Keep the private authority key offline and outside the ORACLE runtime:

```bash
python scripts/issue_engagement.py genkey \
  --out-private authority.key \
  --out-public authority.pub

python scripts/issue_engagement.py issue \
  --private-key authority.key \
  --contract-id CONTRACT-2026-0142 \
  --client "Example Client" \
  --scope 192.0.2.10 \
  --issued-by "security@example.com" \
  --out engagement.json
```

Then launch only with the signed record and its trusted public key:

```bash
python -m oracle \
  --engagement engagement.json \
  --engagement-pubkey authority.pub \
  --mission-name authorized-baseline \
  --objective "Assess the explicitly authorized environment" \
  --profile normal \
  --max-iter 20 \
  --web \
  --web-port 8088 \
  --report \
  --audit-log
```

Read [docs/key_custody.md](docs/key_custody.md) and [docs/security.md](docs/security.md) before using signed engagements.

## Operator workflows

### Advisory AI and council review

Configure an approved advisory backend in `config/ai.yaml`. ORACLE can use NIM or Ollama when configured, but the mission remains functional with deterministic planning when an AI backend is unavailable. AI output is normalized into a narrow recommendation schema, checked against allowed candidates, confidence-gated, and logged with the reason it was accepted or rejected.

```bash
# Inspect the current AI configuration.
cat config/ai.yaml

# Use deterministic behavior by disabling advisory providers in your deployment config.
# Never commit provider secrets; use environment variables or a secret store.
```

### Plugins and capability discovery

Plugins are manifest-driven and registered through the plugin system. Review available capabilities before a mission:

```bash
python -m oracle --list-plugins
```

The repository includes plugin and worker documentation in [docs/plugin_sdk.md](docs/plugin_sdk.md) and [docs/worker_deploy.md](docs/worker_deploy.md).

### Replay and post-mission review

Inspect mission snapshots and replay artifacts without starting a new mission:

```bash
python -m oracle --list-missions
python -m oracle --replay MISSION_NAME --list-replays
python -m oracle --replay MISSION_NAME --replay-id REPLAY_ID --replay-json
```

Replay and export behavior is documented in [docs/API.md](docs/API.md) and [docs/EXAMPLES.md](docs/EXAMPLES.md).

### Reports and exports

ORACLE produces operator-facing summaries, intelligence reports, evidence packages, structured JSON, replay artifacts, and downloadable dashboard exports. Reports are derived from the mission record so the narrative, evidence, and machine-readable package remain connected.

## Architecture

```text
                         Operator
                    CLI / Web / API client
                              |
                    Authenticated control plane
                              |
                 Mission manager + policy authority
                    /          |          \
             Planner       Event bus       Audit
                |              |             |
        AI advisor/council  Live SSE      Replay store
                |              |             |
        Deterministic gate  Dashboard    Artifacts
                |
        Dispatcher + approvals
             /          \
       Workers       Local executor
             |
       Plugins / tools / optional Go runtime
                              |
             Evidence graph + reporting pipeline
```

| Source area | Responsibility |
| --- | --- |
| `core/` | Planning, policy, orchestration, AI routing, graph correlation, and reporting. |
| `oracle/core/` | Mission and action models, engine lifecycle, and runtime-facing contracts. |
| `oracle/runtime/` | Execution safety, sessions, audit, configuration, and subprocess control. |
| `oracle/queue/` | Event streams, approvals, replay, and bounded queue behavior. |
| `workers/` | Registration, authentication, heartbeats, health, and callbacks. |
| `plugins/` | Capability discovery, manifests, validation, and plugin registry. |
| `security/` | Engagement signing, verification, vault, mTLS, sandboxing, and scope boundaries. |
| `api/` and `web/` | Operator APIs, dashboard gateway, serializers, SSE, and static control-plane UI. |
| `dashboard/` and `telemetry/` | Live event normalization, health, metrics, traces, and observability surfaces. |
| `runtime-go/` | Optional concurrent isolated execution support. |
| `tests/` | Unit, integration, security-boundary, resilience, and contract coverage. |

## Security model

ORACLE is designed around defense in depth:

1. **Authorization first** — lab mode or a verified signed engagement.
2. **Scope guard** — every target is checked against the authorized scope.
3. **Policy authority** — risk ceilings, profiles, approvals, and transition rules are deterministic.
4. **Advisory isolation** — model output is untrusted advice, never final authority.
5. **Operator gates** — sensitive actions can require an explicit decision.
6. **Authenticated control** — dashboard and worker control surfaces support authentication boundaries.
7. **Auditability** — operator actions, decisions, findings, and outcomes are recorded.
8. **Fail closed** — malformed authorization, invalid recommendations, and illegal state transitions are rejected.

No dashboard feature bypasses signed engagement verification. No AI feature bypasses deterministic policy. No worker feature should be treated as proof of authorization.

## Verification

Run the full project checks before shipping changes:

```bash
make ci
```

Useful focused checks:

```bash
python3 -m pytest -q
python3 -m compileall -q web api core oracle
python3 -m ruff check . --select E9,F63,F7,F82
node --check web/frontend/app.js
python3 -m oracle --doctor
python3 -m oracle --selftest
```

The current control-plane baseline includes **197 passing Python tests**, JavaScript syntax validation, Python compilation checks, Ruff correctness checks, and clean diff validation.

## Documentation map

- [Release status](RELEASE_STATUS.md)
- [Installation](docs/INSTALLATION.md)
- [Quick start](docs/QUICKSTART.md)
- [Configuration](docs/CONFIGURATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Mission lifecycle](docs/mission_lifecycle.md)
- [Plugin SDK](docs/plugin_sdk.md)
- [Worker deployment](docs/worker_deploy.md)
- [Security model](docs/security.md)
- [Key custody](docs/key_custody.md)
- [Examples](docs/EXAMPLES.md)
- [FAQ](docs/FAQ.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

ORACLE is released under the [MIT License](LICENSE). It is not a substitute for authorization, rules of engagement, legal advice, or professional judgment.
