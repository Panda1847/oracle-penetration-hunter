# ORACLE V4 Pro — Repo-Aligned Definitive Execution Plan

This document supersedes `ORACLE_V4_PRO_WORKFLOW.md` for this repository state.

## Architecture Lock (Do Not Change)

- State machine: `INIT -> DISCOVERY -> ENUMERATION -> VALIDATION -> EXPLOIT_ANALYSIS -> POST_PROCESS -> REPORTING -> COMPLETE | FAILED | PAUSED`
- Council model: `proposer / critic / verifier` with deterministic confidence-gate fallback
- Plugin execution contract: sync `ToolPlugin.build()` / `ToolPlugin.parse()` plus manifest-driven registry

## Status Legend

- `[DONE]` implemented and working in current codebase
- `[PARTIAL]` implemented but incomplete, fragile, or missing required hardening
- `[MISSING]` not implemented in current codebase

## Phase 1 — Codebase Audit and Dependency Hygiene

- `[DONE]` Deterministic mission architecture is in place and wired end-to-end. Evidence: `core/orchestrator/mission_manager.py`, `core/planner/*`, `oracle/core/engine.py`.
- `[DONE]` Import sanity has baseline protection through CI compile step. Evidence: `.github/workflows/ci.yml` (`python -m compileall ...`).
- `[PARTIAL]` Structured architecture docs exist but are not a strict release gate. Evidence: `README.md`, `docs/architecture.md`.
- `[MISSING]` Automated broken-import inventory report (all files + ownership + fix diff) is not present.
- `[MISSING]` Automated circular-import detection/report is not present.
- `[PARTIAL]` Requirements alignment exists but no generated dependency diff workflow. Evidence: `requirements.txt`, `requirements-dev.txt`.

## Phase 2 — Runtime and Orchestration Hardening

- `[DONE]` Mission lifecycle and legal transitions are enforced by state machine. Evidence: `core/planner/state_machine.py`.
- `[DONE]` Planner checkpoints and progression are deterministic. Evidence: `core/planner/transition_rules.py`, `core/planner/phase_controller.py`.
- `[DONE]` Scope/safety check is enforced before execution. Evidence: `core/orchestrator/mission_manager.py` (`safety.validate(...)`), `oracle/runtime/safety.py`.
- `[DONE]` Decision gating is deterministic and can override advisor safely. Evidence: `core/planner/confidence_gate.py`.
- `[DONE]` Internal phases (`EXPLOIT_ANALYSIS`, `POST_PROCESS`, `REPORTING`) are implemented without advisor dependency. Evidence: `_handle_internal_phase` in `core/orchestrator/mission_manager.py`.
- `[PARTIAL]` Mission rollback support exists via storage backup CLI flow but is not a full transactional rollback engine. Evidence: `oracle/cli/rollback.py`, `oracle/memory/storage.py`.
- `[PARTIAL]` Thread safety is mixed: graph storage has locks, mission manager does not expose explicit multi-mission synchronization primitives.
- `[MISSING]` `mission_health_check()` API on mission manager is not implemented as a dedicated method.

## Phase 3 — AI Council and Model Routing

- `[DONE]` 3-role council (`proposer/critic/verifier`) with arbiter logic is implemented. Evidence: `core/ai/council.py`.
- `[DONE]` Advisor remains non-authoritative; deterministic candidate set is always final authority. Evidence: `core/ai/advisor.py`, `core/planner/confidence_gate.py`.
- `[DONE]` Recommendation schema validation and candidate-set enforcement are implemented. Evidence: `core/ai/response_validator.py`, mission manager schema-repair flow.
- `[PARTIAL]` Council drift/override analytics exist for telemetry/reporting but are not used to trigger active control loops. Evidence: `core/ai/council_review.py`, `api/missions.py`, `dashboard/live_stream.py`.
- `[DONE]` Multi-backend router exists (`nim`, `anthropic`, `ollama`, `council`, `deterministic`). Evidence: `core/ai/model_router.py`, `core/ai/nim_client.py`, `core/ai/ollama_client.py`.
- `[PARTIAL]` Failover behavior exists at call time but no 60-second active health scheduler with explicit switch audit events.
- `[MISSING]` Dedicated model-status endpoint is not exposed in API/dashboard surfaces.
- `[PARTIAL]` Local fallback exists and is offline-safe, but fallback-confidence ceiling policy (for example max `0.6`) is not enforced. Evidence: `core/ai/local_fallback.py`.

## Phase 4 — Plugin System and Tooling

- `[DONE]` Manifest-driven enterprise plugin registry is implemented. Evidence: `plugins/registry.py`.
- `[DONE]` Legacy compatibility loader is present for `oracle/plugins/*.py`. Evidence: `oracle/plugins/base.py`.
- `[DONE]` Plugin health checks for required binaries are implemented in registry snapshots and doctor/selftest paths.
- `[DONE]` Strict parse-contract validation and quarantine are implemented. Evidence: `plugins/result_validator.py`, mission manager `parse_quarantined` path.
- `[PARTIAL]` Plugin interface is sync `build()/parse()` as required, but no `validate_scope()` method on plugin classes; scope is centralized in runtime safety.
- `[PARTIAL]` `nmap/http/fuzz` plugins are functional, but nmap parser is regex stdout-based (no XML parser).
- `[PARTIAL]` Nmap advanced modes from original workflow (`-O`, `--script vuln`, explicit rate-control profiles) are not fully implemented in plugin surface.
- `[DONE]` CVE enrichment pipeline exists (offline + optional online) and is linked into graph ingestion. Evidence: `oracle/core/intelligence.py`, `oracle/memory/graph.py`.
- `[MISSING]` Event `critical_vulnerability_found` for license-gate interception is not emitted.

## Phase 5 — API and Control Plane Hardening

- `[DONE]` Operator API with RBAC/JWT/session ownership exists. Evidence: `api/app.py`, `api/auth.py`, `storage/sessions.py`.
- `[DONE]` SOC dashboard gateway exists with auth controls, rate limiting, and export endpoints. Evidence: `web/backend_gateway.py`.
- `[DONE]` Mission, evidence, plugin, worker, report serializers are implemented. Evidence: `api/missions.py`, `api/evidence.py`, `api/plugins.py`, `api/workers.py`, `api/reports.py`.
- `[PARTIAL]` REST surface differs from original workflow spec (no exact `POST /missions`, `DELETE /missions/{id}`, etc. in `api/app.py` contract).
- `[MISSING]` Request ID propagation in all responses is not implemented.
- `[MISSING]` Pydantic request models and standardized schema validation are not implemented.
- `[PARTIAL]` Evidence endpoint pagination is not implemented (full snapshot returns).

## Phase 6 — Worker System Hardening

- `[DONE]` Worker agent can accept jobs and callback results. Evidence: `workers/agent.py`, `workers/result_callback.py`.
- `[DONE]` Worker auth with signed requests and shared-secret hardening exists. Evidence: `workers/auth.py`.
- `[DONE]` Worker registry and health scoring exist. Evidence: `workers/registration.py`, `workers/heartbeat.py`.
- `[DONE]` Dispatcher local fallback and remote dispatch path are implemented. Evidence: `core/orchestrator/dispatcher.py`.
- `[DONE]` Queue dead-letter behavior exists for subscriber failures. Evidence: `oracle/queue/deadletter.py`, `oracle/queue/redis_bus.py`.
- `[PARTIAL]` Graceful signal-driven worker shutdown handling is limited (server stop exists, but explicit SIGTERM lifecycle orchestration is minimal).
- `[PARTIAL]` Worker registration lifecycle is implemented but not yet exposed via a full operator management API workflow.

## Phase 7 — Audit Chain and Evidence Integrity

- `[DONE]` Hash-chained runtime audit logger exists. Evidence: `oracle/runtime/audit.py`.
- `[DONE]` Actor audit chain with verification exists for operator actions. Evidence: `security/audit_chain.py`.
- `[PARTIAL]` Audit logging in mission runtime is optional (`--audit-log`) rather than always-on.
- `[PARTIAL]` Replay artifacts are rich and include decision context, council round, before/after snapshots. Evidence: `memory/replay.py`, mission manager checkpoint paths.
- `[MISSING]` Unified mission audit-chain verify command for runtime audit files is not implemented.
- `[MISSING]` Audit-to-PDF dedicated report generator is not implemented as a first-class command.

## Phase 8 — Demo and Operator UX

- `[DONE]` Demo mode exists and runs without API keys/tools. Evidence: `oracle/demos/demo_mission.py`, `oracle/cli/main.py --demo`.
- `[PARTIAL]` Demo scenario is simulated and useful, but not yet fully V4-native mission-manager path with council checkpoints and license-gate showcase.
- `[PARTIAL]` Dashboard live-stream and council telemetry are strong, but operator workflow polish is still needed for release demos.

## Phase 9 — Testing and CI

- `[DONE]` Large unit/integration suite exists across planner, council, reporting, control plane, workers, replay.
- `[DONE]` CI runs compile checks + Go tests + Python tests. Evidence: `.github/workflows/ci.yml`.
- `[PARTIAL]` CI does not yet include lint and security scan jobs requested in original workflow.
- `[DONE]` Critical mission-manager integration tests pass in current workspace (`tests/integration/test_mission_manager.py`).
- `[PARTIAL]` Coverage target tracking/reporting is not enforced in CI.

## Phase 10 — Release Engineering and Documentation

- `[DONE]` Core README exists and installation path is documented.
- `[PARTIAL]` Root `.gitignore` covers many artifacts but omits `.oracle/` mission runtime dir.
- `[MISSING]` `CHANGELOG.md` is not present.
- `[MISSING]` `LICENSE.md`, `TERMS_OF_SERVICE.md`, and `ACCEPTABLE_USE_POLICY.md` are not present in root.
- `[MISSING]` Root `SECURITY.md` and `CONTRIBUTING.md` are not present.

## Definitive Pre-Release Priority Queue (Pro)

- `[P0][MISSING]` Implement always-on runtime audit logging with chain verification command.
- `[P0][MISSING]` Implement license gate module in `core/policy/license_gate.py` and event wiring for critical findings.
- `[P0][PARTIAL]` Add request IDs + strict API input validation on operator endpoints.
- `[P0][PARTIAL]` Harden worker lifecycle (explicit graceful shutdown orchestration and operator visibility).
- `[P1][PARTIAL]` Add model status endpoint + explicit backend health scheduler/switch telemetry.
- `[P1][PARTIAL]` Upgrade nmap plugin capability depth (XML parse path, constrained advanced scan modes).
- `[P1][MISSING]` Add release artifacts/docs: `CHANGELOG.md`, legal docs, security/contributing docs.
- `[P2][PARTIAL]` Expand CI to include lint/security gates and optional coverage thresholds.

