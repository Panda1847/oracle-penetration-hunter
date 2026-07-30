<div align="center">

# 🔮 ORACLE Penetration Hunter

### The AI Penetration Hunter Your Infrastructure Fears

*Distributed Autonomous Mission Orchestration*

**Automated attack surface discovery, vulnerability hunting, and red team orchestration.**
**Free Community Edition. Scope-Controlled. Evidence-Tracked.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](.github/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Made for Red Teamers](https://img.shields.io/badge/made%20for-red%20teamers-red.svg)](#)

[Screenshots](#-see-it-in-action) •
[Quickstart](#-quickstart) •
[Features](#-features) •
[Architecture](#-architecture) •
[Examples](docs/EXAMPLES.md) •
[Docs](docs/) •
[Contributing](CONTRIBUTING.md)

</div>

---

> ⚠️ **Authorized Use Only.** ORACLE is built for penetration testers, red teamers, and
> security researchers operating **within written authorization and defined scope.**
> See [SECURITY.md](SECURITY.md) and [Responsible Use](#-responsible-use) before running
> this against any target. Unauthorized use against systems you do not own or have
> explicit permission to test is illegal.

## What is ORACLE?

ORACLE is an AI-assisted mission orchestration platform for authorized security testing.
It automates the grind of reconnaissance and attack-surface mapping, keeps every action
**inside a defined scope**, and builds an **evidence graph** as it goes — so your findings
are reproducible, explainable, and ready for reporting, not buried in fifty terminal tabs.

Point it at a scope and an objective, and ORACLE runs an autonomous mission loop: a
planner and mission manager evaluate the next move each iteration, an **AI Council**
reviews candidate actions against a canonical attack graph, and every decision — accepted,
overridden, or deferred to a deterministic fallback — is written to the timeline. Nothing
executes outside the scope you define, and the entire run is replayable afterward from
its own evidence artifacts.

It's built by a red teamer, for red teamers: `I built ORACLE because manual attack surface mapping is too slow for modern CI/CD. It automates the tedious recon and vulnerability chaining, letting red teams focus on creative exploitation.
what problem it solved for you personally — this is the most convincing line in the
whole README, write it in your own voice]`.

## 🎯 Features

- **🕹️ Live Mission Control Plane** — A real-time web dashboard (default `:8088`) showing
  mission phase, workers, findings, approvals, artifacts, and operator notes in one place —
  not a folder of scattered logs.
- **🧠 AI Council Advisory Layer** — Named model backends propose actions; a confidence
  gate decides whether to accept, fall back to deterministic logic, or flag for operator
  review. Every recommendation, acceptance, override, and drift event is recorded.
- **🕸️ Attack Graph & Risk Scoring** — Hosts, services, and findings are correlated into a
  live attack graph with per-node risk scores and highlighted candidate attack paths.
- **⏪ Full Mission Replay** — Every mission writes replay artifacts, so a completed run
  can be stepped back through phase-by-phase for review, training, or reporting.
- **🛡️ Scope-Guarded by Design** — Every action is checked against an explicit,
  operator-defined scope before it runs. Nothing touches what isn't authorized, and if the
  AI backend is unreachable, ORACLE falls back to deterministic guardrails rather than
  guessing.
- **🌐 Topology Mapping** — Discovered subnets, hosts, and services are assembled into a
  live topology graph as the mission runs.
- **🔌 Plugin-Based Tooling** — Reconnaissance capability ships as plugins (`nmap`, `http`,
  `fuzz` out of the box) that orchestrate your existing tools rather than replacing them.
- **📊 Reporting Built-In** — Every mission produces a Markdown + HTML executive summary
  with graphed findings, automatically, on completion.

## 🖥️ See It In Action

**A live mission, end to end** — from CLI launch to the AI Council reasoning about its
next move, to attack graph risk scoring, to a finished replayable mission.

### Launching a mission

ORACLE boots with a startup preflight, loads its plugins, and starts the mission loop —
falling back to deterministic logic automatically when no AI backend is reachable:

![ORACLE CLI mission run](assets/screenshots/04-cli-mission-run.png)

### Live Mission Control Plane

The web dashboard tracks phase, hosts, findings, and workers in real time:

![ORACLE Control Plane overview](assets/screenshots/01-control-plane-overview.png)

### AI Council + Attack Graph

Every candidate action is reasoned about against the attack graph before it's accepted,
overridden, or deferred to a deterministic fallback — with full agreement/drift tracking:

![Attack graph, replay, and AI Council](assets/screenshots/03-attack-graph-ai-council.png)

### Timeline, Topology & Artifacts

Every reasoning step, decision, and discovered topology node is logged — and every
mission produces downloadable artifacts (evidence, intelligence, packaged reports):

![Timeline, topology, and artifacts](assets/screenshots/02-timeline-artifacts-notes.png)

---

### Detailed Mission Walkthrough (9 Frames)

<details>
<summary>Frame 1: CLI Startup & Preflight</summary>

![CLI startup with ORACLE ASCII banner and startup preflight checks](assets/screenshots/05-cli-startup-preflight.png)

The mission boots with a startup preflight (checking plugin availability, AI backend
connectivity, falling back to deterministic logic if needed), then loads plugins
and begins the mission loop.

</details>

<details>
<summary>Frame 2: Mission Complete — Initial Findings</summary>

![Mission completion screen showing 1 host discovered, 1 critical finding](assets/screenshots/06-mission-complete-findings.png)

After the first iterations, the knowledge graph has 1 host and 1 finding (a
TCP-wrapped service on port 8888). The AI Council reasons about next steps and
the report is being generated automatically.

</details>

<details>
<summary>Frame 3: AI Council Reasoning & Action Feed</summary>

![Detailed view of AI reasoning, last action taken, and action feed timeline](assets/screenshots/07-ai-reasoning-action-feed.png)

The left panel ("Intel / Operator") shows the AI's reasoning ("Local fallback selected
the highest-confidence allowed action during..."). The right "Action Feed" shows each
tool invocation (nmap, http, etc.) with timestamps and response codes.

</details>

<details>
<summary>Frame 4: Discovery Phase — Port Mapping</summary>

![Discovery phase with large port range scan active, showing pending work](assets/screenshots/08-discovery-phase-mapping.png)

The mission enters the DISCOVERY phase. The AI is reasoning about the next action, and
the last action was an nmap with a large port range. The Knowledge Graph shows ports
being enumerated against the target.

</details>

<details>
<summary>Frame 5: AI Pending Work — Reasoning in Progress</summary>

![AI still thinking, with discovery scan ports showing in output](assets/screenshots/09-ai-pending-scan-work.png)

The AI Council continues evaluating candidate actions. The discovery phase is still
active with pending scan work — the planner is deciding whether to continue enumeration,
pivot to deeper scanning, or move to the next phase.

</details>

### Live mission from start to finish

Watch a real mission run from startup preflight, through the AI Council reasoning loop,
to completion — 68 seconds that show scope enforcement, live reasoning, and findings
being assembled into the knowledge graph:

<video width="100%" controls>
  <source src="assets/demo.mp4" type="video/mp4">
  Your browser does not support the video tag. <a href="assets/demo.mp4">Download demo.mp4</a>
</video>

## 🚀 Quickstart

```bash
# Clone the repository
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter

# Install dependencies
pip install -r requirements.txt

# Launch a mission against your lab scope, with the live dashboard enabled
python3 -m oracle \
  --scope 10.0.0.2 10.0.0.3 10.0.0.4 \
  --mission-name enterprise-demo \
  --objective "Enumerate CI/DB/web tier, identify exposed credentials and misconfigurations" \
  --profile normal \
  --max-iter 20 \
  --web --web-port 8088 \
  --report \
  --audit-log
```

Open `http://127.0.0.1:8088` to watch the mission run live in the Control Plane. On
completion, ORACLE writes a Markdown + HTML executive summary report automatically.

> By default the dashboard binds to loopback and blocks non-local clients unless
> credentials are configured — see [docs/CONFIGURATION.md](docs/CONFIGURATION.md) before
> exposing it beyond `127.0.0.1`.

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a full walkthrough and
[docs/INSTALLATION.md](docs/INSTALLATION.md) for platform-specific setup
(Kali Linux, Docker, and manual installs).

## 🏗️ Architecture

ORACLE is organized into five cooperating layers:

| Layer | Responsibility |
|---|---|
| `oracle/core` | Mission state, scope enforcement, configuration |
| `oracle/reconnaissance` | Passive/active discovery pipelines |
| `oracle/scanning` | Vulnerability and service scanning orchestration |
| `oracle/exploitation` | Controlled, opt-in exploitation workflow chaining |
| `oracle/reporting` | Evidence graph → structured report generation |

Full diagrams and data flow in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 📦 Comparison

| | ORACLE | Traditional Toolchains |
|---|---|---|
| Scope enforcement | Built-in, mandatory | Manual discipline |
| Evidence tracking | Automatic graph + replay artifacts | Manual notes / screenshots |
| AI-assisted triage | AI Council with confidence gating + deterministic fallback | ❌ |
| Attack path analysis | Live attack graph with per-node risk scoring | Manual correlation |
| Mission review | Full step-by-step replay | Reconstructed from logs/memory |
| Reporting | Auto-generated Markdown + HTML on completion | Written from scratch |
| Tool orchestration | Unified mission model, plugin-based | Separate tabs/scripts |

`Compared to traditional scanners like Nessus, ORACLE doesn't just find vulnerabilities; it reasons about attack paths and chains findings to demonstrate real impact.
actually used side-by-side) once you have a fair, specific basis for it — precise,
falsifiable claims build more trust with technical readers than broad category
comparisons alone.]`

## 🗺️ Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for what's shipped, in progress, and planned —
including community-requested features.

## 🤝 Contributing

Contributions are welcome — from bug reports to new reconnaissance modules. Read
[CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) to get
started.

## 🔒 Responsible Use

ORACLE is a Free Community Edition tool intended **exclusively** for:

- Authorized penetration testing engagements with signed scope/rules of engagement
- Red team operations within your own organization
- Security research in isolated lab environments you own or control
- CTFs and other explicitly permitted testing environments

Do not use ORACLE against any system without explicit, written authorization. See
[SECURITY.md](SECURITY.md) for responsible disclosure and reporting.

## 📄 License

Released under the [MIT License](LICENSE).

---

<div align="center">

**Built by [Panda1847](https://github.com/Panda1847) / NULLSEC**

If ORACLE is useful to your work, consider giving it a ⭐ — it genuinely helps other
red teamers find the project.

</div>
