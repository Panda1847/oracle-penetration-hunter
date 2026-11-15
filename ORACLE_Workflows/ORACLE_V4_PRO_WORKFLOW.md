# ORACLE V4 Pro — Final Release Workflow for codex
# Master Prompt Sequence
### NULLSEC // Last Push to Production

---

## PHASE 1 — Codebase Audit & Gap Analysis

### Prompt 1.1 — Full System Audit

```
Perform a comprehensive audit of this ORACLE V4 codebase. I need you to:

1. Read and analyze every file in these directories:
   - core/orchestrator/
   - core/ai/
   - core/planner/
   - core/policy/
   - oracle/core/
   - oracle/plugins/
   - plugins/nmap/
   - plugins/http/
   - plugins/fuzz/
   - workers/
   - api/
   - memory/

2. For each directory produce:
   - What it does
   - What it depends on
   - Any broken imports or missing dependencies
   - Any TODOs, stubs, or unimplemented functions
   - Any hardcoded values that should be config

3. Produce a master gap list: everything that is incomplete, broken,
   or missing before this codebase is production-ready.

Do not fix anything yet. Just audit and report.
```

---

### Prompt 1.2 — Dependency & Import Validation

```
Scan every Python file in this project and:

1. List all imports that reference modules not present in the codebase
2. List all imports that reference packages not in requirements.txt
3. Identify any circular import chains
4. Check that oracle/core/engine.py compatibility wrapper correctly
   re-exports everything consumers expect from it
5. Check that all __init__.py files export the correct symbols

Generate a requirements.txt diff showing what needs to be added.
Do not fix yet — report only.
```

---

## PHASE 2 — Core Infrastructure Fixes

### Prompt 2.1 — Fix All Broken Imports

```
Fix every broken import identified in the audit. Rules:

1. Do not change any module's public API — only fix the imports
2. If a module is genuinely missing, create a minimal stub with
   a TODO comment marking it for full implementation
3. Update requirements.txt with any missing packages
4. Ensure oracle/core/engine.py compatibility wrapper works correctly
   for all consumers of MissionEngine
5. Run a final import check after fixing: every file should be
   importable without errors

Files to prioritize:
- core/orchestrator/mission_manager.py
- core/ai/council.py
- core/policy/scope_guard.py
- oracle/core/planner.py
- oracle/core/intelligence.py
- workers/agent.py
```

---

### Prompt 2.2 — MissionManager State Machine Hardening

```
Review and harden core/orchestrator/mission_manager.py:

1. Verify the state machine covers all mission lifecycle states:
   INIT → SCOPING → RECON → ANALYSIS → REPORTING → COMPLETE → FAILED → ROLLED_BACK

2. Ensure every state transition:
   - Validates scope via core/policy/scope_guard.py BEFORE executing
   - Logs the transition to the cryptographic audit chain
   - Handles failure gracefully with rollback capability
   - Emits the correct event on core/orchestrator/event_bus.py

3. Add missing transitions if any state has no failure path

4. Ensure the MissionManager is thread-safe for concurrent missions

5. Add a mission_health_check() method that returns current state,
   active agents, scope status, and audit chain integrity

Do not change the public API. Strengthen the internals.
```

---

### Prompt 2.3 — Cryptographic Audit Chain

```
Review and complete the cryptographic audit chain system.
Find all files involved in audit logging (check core/orchestrator/,
memory/provenance.py, memory/replay.py).

Ensure the audit chain:

1. Records EVERY agent decision with:
   - Timestamp (UTC, ISO 8601)
   - Agent ID and type
   - Decision made and reasoning summary
   - Confidence score
   - Scope validation result (pass/fail)
   - SHA-256 hash of the previous entry (chain integrity)
   - SHA-256 hash of this entry

2. Is written to .oracle/logs/ with filename pattern:
   mission_{mission_id}_{timestamp}.audit.jsonl

3. Has a verify_chain(mission_id) function that validates
   every hash in the chain and returns True/False + any broken links

4. Cannot be disabled — it must always be active regardless of config

5. Has an export_audit_report(mission_id) that produces a
   human-readable PDF summary via core/reporting/pdf_builder.py

Test the chain with a mock mission after implementing.
```

---

## PHASE 3 — AI Council Completion

### Prompt 3.1 — Council Voting System

```
Review core/ai/council.py and core/ai/council_review.py.

Complete the AI council voting system so it:

1. Runs exactly 5 agents for every major decision point:
   - ReconAgent: evaluates target surface
   - RiskAgent: classifies risk level
   - ScopeAgent: validates scope compliance
   - StrategyAgent: recommends next action
   - ValidationAgent: cross-checks other agents for contradictions

2. Voting protocol:
   - Each agent votes PROCEED / HOLD / ABORT with confidence 0.0-1.0
   - Minimum 4/5 votes to PROCEED on any destructive or active action
   - Any ABORT vote triggers immediate mission pause
   - ScopeAgent ABORT is always final — cannot be overridden

3. Contradiction detection:
   - If ValidationAgent detects contradictions between agents,
     trigger a council_review cycle using council_review.py
   - Log all contradictions to the audit chain

4. Every vote must be logged to the audit chain with full reasoning

5. Connect to memory/contradiction_detector.py for cross-mission
   contradiction detection

Use core/ai/model_router.py to route agent calls to the
correct model (Ollama local or API).
```

---

### Prompt 3.2 — Model Router & Fallback

```
Complete core/ai/model_router.py and core/ai/local_fallback.py:

1. Model router priority order:
   - Primary: Anthropic Claude API (if ANTHROPIC_API_KEY set)
   - Secondary: Ollama local (if OLLAMA_HOST reachable)
   - Tertiary: local_fallback.py (always available, limited capability)

2. The router must:
   - Auto-detect available models on startup
   - Health-check models every 60 seconds
   - Fail over automatically without breaking active missions
   - Log all model switches to the audit chain
   - Respect rate limits with exponential backoff

3. local_fallback.py must:
   - Work completely offline with no external calls
   - Provide reduced but functional council decisions
   - Clearly mark all fallback decisions in the audit chain
   - Never claim higher confidence than 0.6 in fallback mode

4. Add a model_status() endpoint accessible via the API that
   shows which models are active and their health status.
```

---

## PHASE 4 — Plugin System

### Prompt 4.1 — Plugin Registry & Validation

```
Review oracle/plugins/ and plugins/ directories.
Complete the plugin system:

1. Plugin registry must:
   - Auto-discover plugins in both plugins/ and oracle/plugins/
   - Validate each plugin against a schema before loading
   - Reject plugins that don't declare their scope requirements
   - Maintain a plugin health status

2. Every plugin must implement this interface:
   class OraclePlugin:
       name: str
       version: str
       capabilities: List[str]
       requires_scope: bool = True
       risk_level: str  # "passive", "active", "destructive"
       
       async def execute(self, target, scope, context) -> PluginResult
       async def validate_scope(self, target, scope) -> bool
       async def health_check(self) -> bool

3. Scope validation must run BEFORE every plugin execution.
   If scope validation fails, the plugin must not execute.

4. Plugin results must be routed through:
   core/orchestrator/artifact_router.py → memory/evidence_linker.py
   → memory/graph_store.py

5. Review and complete these existing plugins:
   - plugins/nmap/ — port scanning, service detection
   - plugins/http/ — HTTP probing, header analysis, endpoint discovery
   - plugins/fuzz/ — directory and parameter fuzzing
   
   Each must fully implement the OraclePlugin interface.
```

---

### Prompt 4.2 — Nmap Plugin Hardening

```
Complete plugins/nmap/ to production standard:

1. Implement full nmap integration:
   - Service and version detection (-sV)
   - OS detection (-O) where authorized
   - Script scanning for common vulns (--script vuln) where authorized
   - Rate limiting to avoid detection and network disruption
   - XML output parsing into structured PluginResult

2. Every scan must:
   - Validate target is within scope FIRST
   - Log start/end/results to audit chain
   - Handle network timeouts gracefully
   - Store results in memory/graph_store.py with TTL

3. CVE correlation:
   - Match discovered services/versions against oracle/data/
     CVE database
   - For each CVE match, create an evidence node in the graph
   - Attach CVSS score, description, and remediation notes

4. Do NOT implement exploit execution — discovery and correlation only.
   When a critical CVE is found, emit an event on event_bus.py
   with type "critical_vulnerability_found" for the Pro gate to handle.
```

---

## PHASE 5 — API & Workers

### Prompt 5.1 — API Hardening

```
Review and harden all files in api/:

1. Authentication (api/auth.py):
   - JWT token validation on every endpoint
   - API key support for programmatic access
   - Rate limiting: 100 req/min per token
   - All auth failures logged to audit chain

2. Mission endpoints (api/missions.py):
   - POST /missions — create with scope validation
   - GET /missions/{id} — status with audit trail
   - DELETE /missions/{id} — abort with rollback
   - GET /missions/{id}/graph — evidence graph export
   - GET /missions/{id}/report — full report

3. Evidence endpoints (api/evidence.py):
   - GET /evidence/{mission_id} — paginated evidence list
   - GET /evidence/{id} — single evidence node with provenance

4. Plugin endpoints (api/plugins.py):
   - GET /plugins — list available with health status
   - POST /plugins/{name}/run — execute with scope check

5. All endpoints must:
   - Return consistent JSON error format
   - Include request ID in all responses
   - Log to audit chain for any state-changing operation
   - Validate input with Pydantic models

6. Fix api/workers.py to correctly interface with workers/agent.py
```

---

### Prompt 5.2 — Worker System

```
Complete the worker system in workers/:

1. workers/agent.py — the core worker:
   - Must accept tasks from the queue system
   - Execute plugins within scope constraints
   - Report results back via workers/result_callback.py
   - Heartbeat every 30 seconds via workers/heartbeat.py
   - Graceful shutdown on SIGTERM

2. workers/registration.py:
   - Workers must register with the orchestrator on startup
   - De-register cleanly on shutdown
   - Support multiple workers running simultaneously

3. workers/auth.py:
   - Worker-to-orchestrator authentication
   - Each worker has a unique identity token
   - Tokens logged in audit chain

4. Queue integration:
   - Connect workers to oracle/queue/ system
   - Implement dead letter queue for failed tasks
   - Failed tasks must not silently disappear

5. Add a worker_status API endpoint showing:
   active workers, queue depth, tasks completed, tasks failed
```

---

## PHASE 6 — Pro License Gate (The Taste Feature)

### Prompt 6.1 — License Gate System

```
Implement the ORACLE Pro license gate system. This is a critical
feature that gates active exploit execution behind a license check.

Create: core/policy/license_gate.py

The gate must intercept the "critical_vulnerability_found" event
from event_bus.py and:

1. Display a terminal UI panel showing:
   ┌─────────────────────────────────────────────────────┐
   │  ORACLE // EXPLOIT MODULE — PRO LICENSE REQUIRED    │
   ├─────────────────────────────────────────────────────┤
   │  Target:    [discovered target]                     │
   │  CVE:       [CVE ID]                                │
   │  Type:      [vulnerability type]                    │
   │  Severity:  [CRITICAL/HIGH] (CVSS: [score])        │
   │  Status:    Exploit pathway generated. Awaiting.    │
   │                                                     │
   │  ORACLE has identified an exploitable attack path.  │
   │  Execution requires an active Pro license with      │
   │  scope verification.                                │
   │                                                     │
   │  [ nullsec.io/pro ]  [ VIEW CVE DETAILS ]          │
   └─────────────────────────────────────────────────────┘

2. The full exploit pathway IS generated and stored (encrypted)
   in .oracle/artifacts/ — it just isn't executed.

3. Log the gate trigger to audit chain with:
   - CVE ID and CVSS score
   - That an exploit pathway was generated but gated
   - That no execution occurred

4. In Pro mode (valid LICENSE_KEY env var):
   - Validate license key against a local license file
   - If valid, unlock execution and proceed
   - Log license validation to audit chain

5. The gate CANNOT be bypassed by config. It must be in the
   critical path before any active execution.

Integrate into core/policy/policy_engine.py as a required step.
```

---

## PHASE 7 — Demo Mode

### Prompt 7.1 — V4-Native Demo Mode

```
Rewrite oracle/demos/demo_mission.py to be fully V4-native.

The current demo predates V4 architecture. Replace it entirely with:

1. A self-contained demo that:
   - Targets a built-in mock network (no real targets needed)
   - Runs the complete V4 stack: MissionManager → Council → Plugins → Graph
   - Uses local_fallback.py so no API keys needed
   - Completes in under 5 minutes on CPU-only hardware
   - Produces a real audit chain and evidence graph

2. Demo scenarios (user can choose):
   a. "Quick Scan" — single host recon, 60 seconds
   b. "Network Survey" — mock subnet, 3 minutes  
   c. "Full Mission" — complete recon + analysis + report, 5 minutes

3. The demo must trigger the license gate at least once to showcase
   the Pro upsell feature naturally

4. Output a demo report to .oracle-artifacts/reports/demo_report.pdf

5. Add a --demo flag to oracle/cli/main.py that launches this

The demo is what potential customers and Anthropic will see first.
Make it impressive.
```

---

## PHASE 8 — Testing

### Prompt 8.1 — Fix & Complete Test Suite

```
Review all test files in tests/. 

1. Fix every failing test — run pytest and resolve all errors
2. For any test marked as skip or xfail, either fix or document why
3. Ensure test coverage for:
   - Scope guard cannot be bypassed (tests/unit/test_security_controls.py)
   - Audit chain integrity verification
   - Council voting with 5 agents
   - License gate activation on critical CVE
   - Plugin scope validation
   - Mission state machine all transitions
   - API authentication

4. Add integration test: tests/integration/test_full_mission.py
   - Full mission lifecycle using demo mock network
   - Verifies audit chain integrity at end
   - Verifies evidence graph has nodes
   - Verifies scope was never violated

5. Run the full test suite and confirm 0 failures:
   pytest tests/ -v --tb=short

Report coverage percentage when done.
```

---

## PHASE 9 — Documentation & Final Polish

### Prompt 9.1 — README

```
Create a professional README.md for ORACLE V4 Pro in the project root.

Include:
1. Header with ORACLE name, tagline, and badges (Python, License, Version)
2. One-paragraph description of what ORACLE is
3. Key capabilities list (bullet points, no more than 8)
4. Architecture diagram in ASCII art showing:
   CLI/API → MissionManager → AI Council → Plugin System → Evidence Graph
5. Quick start (5 commands from clone to first demo)
6. Configuration reference (key environment variables)
7. Plugin development guide (2 paragraphs)
8. License section referencing BUSL 1.1
9. NULLSEC attribution and contact

Tone: professional, technical, confident. Not marketing fluff.
This is read by senior security engineers. Write accordingly.
```

---

### Prompt 9.2 — Final Pre-Release Checklist

```
Perform final pre-release validation:

1. Run: python -c "import oracle; import core; import api; import workers"
   Fix any import errors.

2. Run: pytest tests/ -v
   Fix any failing tests.

3. Check for any hardcoded credentials, API keys, or secrets:
   grep -r "sk-" . --include="*.py"
   grep -r "password" . --include="*.py"
   grep -r "secret" . --include="*.py"
   Remove or move to environment variables.

4. Verify .gitignore includes:
   .oracle/logs/
   .oracle/missions/
   .oracle-artifacts/
   .env
   *.key
   *.pem

5. Verify LICENSE.md exists in project root
6. Verify TERMS_OF_SERVICE.md exists in project root
7. Verify ACCEPTABLE_USE_POLICY.md exists in project root

8. Create a CHANGELOG.md with V4 release notes

9. Tag the release:
   git add -A
   git commit -m "feat: ORACLE V4 Pro — production release"
   git tag -a v4.0.0 -m "ORACLE V4 Pro Release"

Report: READY FOR RELEASE or list of remaining blockers.
```

---

## PHASE 10 — Launch Commands

After Codex completes all phases:

```bash
# Verify everything runs
python -m oracle.cli.main --version
python -m oracle.cli.main --demo

# Run tests one final time
pytest tests/ -v --tb=short

# Push to GitHub
git push origin release/v4-pro
git push origin v4.0.0
```

---

*NULLSEC // ORACLE V4 Pro — Final Release Workflow*
*Document Version 1.0 // Use with Claude Code (claude-sonnet-4-5)*
