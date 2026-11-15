# ORACLE v4 release status

Each item lists the test or check that proves it. Items marked OPEN are not done.

## Done (verified by tests)

- **Python suite:** 187 passed, 0 failed, 0 collection errors; also clean with
  `-W error::DeprecationWarning`. Run: `python -m pytest -q`.
- **Queue shadowing bug fixed:** top-level `queue/` package removed (it shadowed
  the stdlib `queue` and broke 5 modules). Verified by full-suite collection.
- **Worker secret not shipped:** `config/workers.yaml` has `shared_secret: ""`.
  Test: `tests/unit/test_startup_preflight.py::test_fresh_clone_default_config_refuses_to_start`.
- **Committed secret refused:** a rejected or committed secret is a *required*
  preflight failure. Tests: `test_committed_secret_is_refused_even_if_strong`,
  and `test_runtime_config_validator.py`.
- **Worker replay protection:** signatures bind a live timestamp with a skew
  window. Tests: `tests/unit/test_worker_auth_hardening.py` (stale, future,
  tampered, non-integer timestamps rejected).
- **Empty scope fails closed:** `tests/test_safety.py::test_empty_scope_fails_closed_by_default`.
- **Engagement contract gating:** only signed, unexpired engagements or
  loopback `--lab` produce a live scope. Tests: `tests/unit/test_engagement.py`
  (signature, tamper, expiry, not-yet-active, profile ceiling, bare constructor
  blocked, forgery, lab loopback-only).
- **Engagement audit trail:** `engagement_verified` is written to the mission's
  single audit log. Test: `test_valid_engagement_is_recorded_in_audit_log`;
  lab runs write none: `test_lab_run_writes_no_engagement_event`.
- **Engagement revocation:** revoked contracts rejected after signature and expiry
  checks; unreadable list fails closed. Tests: `test_revoked_contract_is_rejected`,
  `test_unrevoked_contract_still_passes`, `test_unreadable_revocation_file_fails_closed`.
- **No ScopeGuard bypass in the live path:** `_resolve_scope_guard` refuses
  non-loopback targets without authorization. Tests:
  `test_live_entrypoint_refuses_non_loopback_without_authorization`,
  `test_live_entrypoint_refuses_engagement_without_pubkey`. `run_demo` is
  loopback-only and never builds a ScopeGuard.
- **NIM fallback order enforced:** NIM → Anthropic → Ollama → deterministic.
  Tests: `tests/unit/test_ai_fallback_order.py` (4 cases).
- **Go CI version aligned:** CI and `runtime-go/go.mod` both use Go 1.26.
- **core/ vs oracle/core split documented:** `docs/architecture.md`, section
  "Package split".
- **Denylist limitation documented:** `docs/security.md`.
- **Key custody runbook:** `docs/key_custody.md` (authority private key never on
  an ORACLE host; rotation and revocation procedure).
- **Dashboard copy:** "No high-risk paths identified" and "Verified lab nodes"
  do not exist in this tree; no screenshots are shipped.

## OPEN (not done, must be finished before release)

- **Go build with gRPC not verified.** `runtime-go/grpc_server.go` imports
  grpc v1.72.1 / protobuf v1.36.6, which could not be downloaded in the build
  environment. With that file stubbed, `go vet` and `go test` pass. Required:
  `cd runtime-go && go mod tidy && go vet ./... && go test ./...` on a networked
  machine must exit 0. Target: `make ci`.
- **`make ci` not run end to end** (needs the Go step above).
- **Engagement audit wiring is partial for the CLI:** the event is written by
  `record_engagement_verified()`, which is unit-tested, but the full `run_live`
  path has not been executed end to end with a real engagement file.
- **Shell denylist** (`BLOCKED_PATTERNS`) is a known denylist; per-binary
  allowlist is planned, not built.
