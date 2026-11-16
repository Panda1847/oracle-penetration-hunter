# Oracle Penetration Hunter Control Plane Upgrade Implementation Plan

> **For agentic workers:** Execute this plan task-by-task. Each task is independently testable and should be committed as a focused change.

**Goal:** Make the Oracle Penetration Hunter web console a genuinely live, operator-complete control plane with runtime-connected controls, interactive evidence workflows, and production-grade polish.

**Architecture:** Keep the existing Flask gateway and static frontend. Add a server-sent event stream backed by the existing event bus, explicit mission-control and approval APIs backed by the mission manager/policy layer, and a small client-side state store that renders the existing dashboard tabs from one normalized snapshot. Preserve loopback/auth defaults and fail closed for operator actions.

**Tech Stack:** Python 3.11+, Flask, existing event bus and mission/policy modules, vanilla JavaScript, CSS, SVG/Canvas primitives, EventSource with polling fallback, existing pytest/Ruff checks.

**Spec:** User request in conversation: add the recommended improvements starting with real-time streaming and continue through runtime controls, interactive attack graph, approvals, mission launcher, findings workflow, worker operations, telemetry, UX/accessibility, and security hardening.

## Global Constraints

- The deterministic planner, policy engine, and scope guard remain authoritative.
- AI recommendations remain advisory and cannot bypass scope, engagement, approval, or risk checks.
- The dashboard remains loopback-only by default and must preserve token/basic-auth behavior.
- Every operator action must be auditable and visible in the timeline.
- No credentials, signed private keys, or generated runtime artifacts enter source control.
- The frontend must work with JavaScript disabled only for a readable shell/error message; operational controls require authenticated JavaScript requests.
- Do not introduce n8n workflow nodes because this repository contains no n8n runtime; use the same progressive-disclosure principle for mission-launch configuration.
- Do not add GSAP merely for decoration; use short CSS transform/opacity transitions unless a real graph interaction requires a plugin.

## Review Focus

- Event-stream disconnects must fall back to bounded polling without duplicate event rendering.
- Pause/resume/stop must change runtime behavior, not only mission metadata.
- Approval, control, launcher, and worker mutation routes must reject malformed or unauthorized requests.
- Mission launch must require explicit scope/engagement validation before dispatch.
- Large event/evidence datasets must remain bounded and responsive.
- Motion must honor reduced-motion preferences and avoid layout-property animation.

---

### Task 1: Real-time event streaming

**Files:**
- Modify: `web/backend_gateway.py`
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/index.html`
- Modify: `web/frontend/styles.css`
- Test: `tests/integration/test_control_plane_gateway.py`

**Interfaces:**
- Produces `GET /api/dashboard/events` as an authenticated `text/event-stream` endpoint with bounded keepalive and event payloads.
- Frontend consumes EventSource and falls back to the current 3.5-second refresh loop on disconnect.

- [ ] Add an authenticated SSE route that serializes recent event-bus entries and emits keepalive comments.
- [ ] Add a frontend event-stream controller that updates only affected panels, deduplicates by trace/event ID, and switches to polling on error.
- [ ] Add connected/reconnecting/offline UI states.
- [ ] Test authenticated access, content type, keepalive/event framing, and fallback-safe behavior.

### Task 2: Runtime-connected mission controls

**Files:**
- Modify: `core/orchestrator/mission_manager.py`
- Modify: `core/orchestrator/dispatcher.py`
- Modify: `web/backend_gateway.py`
- Modify: `tests/integration/test_control_plane_gateway.py`
- Test: `tests/unit/test_mission_controls.py`

**Interfaces:**
- Add a mission-manager control method such as `request_control(action: str, actor: str) -> dict`.
- Gateway control route delegates to the mission manager when present and returns the resulting state.

- [ ] Write failing tests for pause, resume, and stop behavior, including queued-job handling and audit directives.
- [ ] Implement state transitions and dispatcher behavior: pause blocks new dispatch, resume reopens eligible work, stop cancels queued work and marks the mission stopped.
- [ ] Preserve safe idempotency for repeated controls and reject invalid transitions with 409.
- [ ] Update UI controls to show pending/confirmed state and disable invalid actions.

### Task 3: Interactive attack graph

**Files:**
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/styles.css`
- Modify: `web/frontend/index.html`
- Test: `tests/unit/test_dashboard_serializers.py` if serializer gaps are found.

**Interfaces:**
- Use `overview.attack_graph` nodes/edges/top paths already exposed by the API.
- Selecting a node opens the inspector and filters related findings/evidence.

- [ ] Render a bounded SVG graph with pan/zoom controls, severity/risk colors, and accessible node buttons.
- [ ] Add node selection, reset view, and risk/phase filtering.
- [ ] Connect graph selections to the existing inspector and evidence tabs.
- [ ] Respect reduced motion and avoid layout-property animations.

### Task 4: Actionable approvals

**Files:**
- Modify: `api/approvals.py`
- Modify: `web/backend_gateway.py`
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/index.html`
- Test: `tests/unit/test_approvals_api.py`
- Test: `tests/integration/test_control_plane_gateway.py`

**Interfaces:**
- Add authenticated `POST /api/dashboard/approvals/<approval_id>` with `{decision: approve|deny|defer, reason}`.
- Delegate to the existing approval engine and emit an audit event.

- [ ] Add failing tests for valid decisions, missing reason on denial, unknown IDs, and unauthorized clients.
- [ ] Implement fail-closed approval mutation and timeline/audit emission.
- [ ] Add approve/deny/defer UI with confirmation and reason capture.

### Task 5: Mission launcher

**Files:**
- Modify: `web/backend_gateway.py`
- Modify: `web/frontend/index.html`
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/styles.css`
- Test: `tests/integration/test_control_plane_gateway.py`

**Interfaces:**
- Add a guided launcher payload validated by the same CLI/config/policy rules used by missions.
- Do not dispatch until scope/engagement preflight passes.

- [ ] Add a launcher drawer with objective, scope, engagement artifact/public key, profile, iteration limit, AI backend, and report options.
- [ ] Add a preflight review step showing scope and authorization before submit.
- [ ] Return structured validation errors without starting a mission.
- [ ] Add tests proving invalid or unsigned non-loopback scope is rejected.

### Task 6: Findings workflow

**Files:**
- Modify: `web/frontend/index.html`
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/styles.css`
- Modify: `web/backend_gateway.py` only if a read/update endpoint is missing.
- Test: `tests/integration/test_control_plane_gateway.py` only if backend routes change.

- [ ] Add finding detail inspector with status, notes, evidence references, CVEs, confidence, and affected asset.
- [ ] Add analyst status labels and local filter/search state.
- [ ] Add remediation note capture through the existing directive/chat/audit mechanisms unless a dedicated persisted finding mutation is already available.
- [ ] Ensure all content is escaped before insertion into HTML.

### Task 7: Worker operations

**Files:**
- Modify: `api/workers.py`
- Modify: `web/backend_gateway.py`
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/index.html`
- Test: `tests/unit/test_worker_control.py`

- [ ] Expose worker health, heartbeat age, inflight jobs, capability filters, and status in the UI.
- [ ] Add safe drain/quarantine controls only if the dispatcher exposes corresponding operations; otherwise show read-only state and an explicit unavailable reason.
- [ ] Add tests for capability filtering and unauthorized mutation attempts.

### Task 8: Telemetry and notifications

**Files:**
- Modify: `web/frontend/app.js`
- Modify: `web/frontend/styles.css`
- Modify: `web/frontend/index.html`
- Modify: `web/backend_gateway.py` only if telemetry payloads need bounded history.

- [ ] Add charts for events/minute, worker health, severity distribution, and advisor/fallback counts using existing metrics/event data.
- [ ] Add critical-finding and approval-request browser notifications only after explicit user opt-in.
- [ ] Add bounded client history to prevent memory growth.

### Task 9: Prompt and configuration quality

**Files:**
- Review: `core/ai/prompt_templates.py`, `core/ai/response_validator.py`, `config/ai.yaml`
- Modify only where needed.
- Test: existing AI tests plus focused prompt/validation tests.

- [ ] Review prompts against the prompt-engineer checklist: explicit role, scope, allowed output schema, refusal behavior, and deterministic fallback.
- [ ] Add/strengthen structured-output validation and prompt-injection-resistant handling of tool/data content.
- [ ] Preserve token/latency budgets and document known limitations.

### Task 10: Visual system, animation, and accessibility QA

**Files:**
- Modify: `web/frontend/styles.css`
- Modify: `web/frontend/app.js` only for focus/keyboard behavior.
- Test: static syntax checks and accessibility-oriented DOM assertions where practical.

- [ ] Document the chosen palette based on the existing Oracle cyan brand token and verify contrast for text, controls, borders, severity states, and focus rings.
- [ ] Add keyboard navigation, visible focus states, ARIA labels, skip navigation, and reduced-motion CSS.
- [ ] Review all transitions against the animation checklist: transform/opacity only, under 300ms, interruptible, no `transition: all`, and hover motion gated for fine pointers.
- [ ] Keep GSAP out unless a concrete interaction requires it; if introduced, register plugins once and test teardown.

### Task 11: Final review and release

**Files:**
- Modify: `README.md` and `docs/` with operator-control documentation.
- Create: `docs/superpowers/plans/2026-11-15-control-plane-upgrade.md` (this plan).

- [ ] Run full Python tests, compile checks, Ruff correctness checks, and JavaScript syntax checks.
- [ ] Run a code-review pass focused on XSS, auth, CSRF, event duplication, unbounded memory, and state transitions.
- [ ] Verify generated artifacts and secrets are absent.
- [ ] Commit each coherent task and publish when GitHub authentication is available.
