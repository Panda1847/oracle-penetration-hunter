<div align="center">

# ORACLE

### Mission orchestration for authorized security testing

Scope-controlled execution, advisory AI, evidence intelligence, replayable missions, and professional reporting in one operator-focused platform.

[![License](https://img.shields.io/badge/license-MIT-1f2937.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org/)
[![Release](https://img.shields.io/badge/release-v4.0.0-7c3aed.svg)](RELEASE_STATUS.md)
[![CI](https://github.com/Panda1847/oracle-penetration-hunter/actions/workflows/ci.yml/badge.svg)](https://github.com/Panda1847/oracle-penetration-hunter/actions/workflows/ci.yml)

</div>

> **Authorized use only.** ORACLE is intended for engagements with written authorization, internal environments owned by the operator, and isolated research labs. Read [SECURITY.md](SECURITY.md) before use.

## Overview

ORACLE is a distributed mission-orchestration platform for repeatable security operations. It combines a deterministic planner with an advisory AI layer, isolated workers, plugin-driven reconnaissance, evidence provenance, operator approvals, telemetry, replay, and report generation.

The core design principle is simple: **policy and scope remain authoritative**. AI recommendations are advisory, every action is evaluated against policy, and missions can continue with deterministic fallbacks when an AI backend is unavailable.

![ORACLE control plane](assets/oracle_social_preview.png)

## Capabilities

- **Mission control plane** — Launch, monitor, pause, resume, and review missions through the CLI and web gateway.
- **Scope and engagement controls** — Enforce target scope, approvals, risk ceilings, and signed engagement records.
- **Advisory AI with deterministic fallback** — Route recommendations through configured providers without allowing model output to bypass guardrails.
- **Evidence intelligence** — Track findings, confidence, provenance, contradictions, and relationships in an evidence graph.
- **Replayable operations** — Preserve decisions, events, artifacts, and operator actions for review and reporting.
- **Worker isolation** — Dispatch execution through authenticated workers and an optional Go runtime.
- **Plugin architecture** — Add capabilities through manifest-driven plugins instead of hard-coded workflows.
- **Reporting and export** — Produce structured JSON and operator-facing summaries from the mission record.
- **Telemetry** — Expose health, metrics, tracing, and dashboard configuration for operational visibility.

## Quick start

```bash
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m oracle --demo --web --web-port 5000
```

Open `http://127.0.0.1:5000` for the local control plane. For a complete setup, see [docs/QUICKSTART.md](docs/QUICKSTART.md) and [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Advisory AI

ORACLE keeps the planner authoritative and treats external model output as untrusted advice. Configure an approved backend in `config/ai.yaml` or use deterministic mode for a fully local run. Ollama is supported for local advisory inference; if no backend is available, the platform records the fallback and continues with deterministic planning.

Never place provider secrets in source control. Use environment variables or the deployment secret store described in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Signed engagements

For non-lab operations, use the offline engagement-issuance workflow. The authoring utility creates an Ed25519-signed record; the runtime verifies it with a public key and fails closed on malformed, expired, revoked, or tampered records.

```bash
python scripts/issue_engagement.py genkey \
  --out-private authority.key --out-public authority.pub
python scripts/issue_engagement.py issue \
  --private-key authority.key \
  --contract-id CONTRACT-2026-0142 \
  --client "Example Client" \
  --scope 192.0.2.10 \
  --issued-by "security@example.com" \
  --out engagement.json
```

Keep the private authority key offline and outside the ORACLE runtime. See [docs/key_custody.md](docs/key_custody.md).

## Architecture

```text
Operator / CLI / Web UI
          |
      API gateway
          |
  Mission manager + policy
     /       |       \
 Planner   Evidence   Event bus
    |          |          |
 Workers   Reporting   Replay store
    |
 Optional Go execution runtime
```

The main source areas are:

| Area | Responsibility |
| --- | --- |
| `core/` | Planning, policy, orchestration, AI routing, and reporting |
| `oracle/runtime/` | Runtime safety, sessions, audit, configuration, and execution |
| `workers/` | Worker registration, authentication, heartbeats, and callbacks |
| `plugins/` | Capability discovery, validation, and plugin registry |
| `security/` | Signing, vault, mTLS, sandboxing, and engagement verification |
| `api/` and `web/` | Operator APIs and the control-plane gateway |
| `telemetry/` | Health checks, metrics, tracing, and dashboards |
| `runtime-go/` | Concurrent isolated execution support |
| `tests/` | Unit, integration, and resilience coverage |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API.md](docs/API.md), and [docs/security.md](docs/security.md) for deeper detail.

## Verification

```bash
make ci
```

The CI workflow compiles the Python packages, runs Python tests, and runs the Go runtime tests when the Go toolchain is available. `make verify` performs environment checks without starting a mission.

## Project documentation

- [Release status](RELEASE_STATUS.md)
- [Installation](docs/INSTALLATION.md)
- [Quick start](docs/QUICKSTART.md)
- [Configuration](docs/CONFIGURATION.md)
- [Mission lifecycle](docs/mission_lifecycle.md)
- [Plugin SDK](docs/plugin_sdk.md)
- [Security model](docs/security.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

ORACLE is released under the [MIT License](LICENSE). It is not a substitute for authorization, rules of engagement, or professional judgment.
