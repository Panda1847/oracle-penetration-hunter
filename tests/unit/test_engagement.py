"""Contract-gating tests for security/engagement.py and ScopeGuard.

Covers the eight verification cases listed in TODO_BEFORE_RELEASE.md:
valid accepted, tampered rejected, expired rejected, not-yet-active
rejected, profile-ceiling violation rejected, bare constructor blocked,
wrong-key forgery rejected, lab mode loopback-only.
"""
import json
import time

import pytest

from core.policy.scope_guard import ScopeGuard
from security.engagement import (
    EngagementError,
    EngagementRecord,
    EngagementVerifier,
    generate_authority_keypair,
    sign_engagement,
)


@pytest.fixture
def keys():
    return generate_authority_keypair()  # (private_pem, public_pem)


@pytest.fixture
def verifier(keys):
    return EngagementVerifier(keys[1])


def _record(**overrides):
    now = time.time()
    base = dict(
        contract_id="CONTRACT-TEST-1",
        client="Test Client",
        authorized_scope=["192.168.56.0/24"],
        not_before=now - 60,
        not_after=now + 3600,
        issued_by="ops@example.test",
        max_profile="normal",
    )
    base.update(overrides)
    return EngagementRecord(**base)


def _artifact(keys, **overrides):
    return sign_engagement(_record(**overrides), keys[0])


def test_valid_engagement_is_accepted(keys, verifier):
    guard = ScopeGuard.from_engagement(_artifact(keys), verifier=verifier)
    assert guard.validator.in_scope("192.168.56.50")
    assert not guard.validator.in_scope("10.0.0.1")


def test_tampered_scope_is_rejected(keys, verifier):
    artifact = _artifact(keys)
    artifact["record"]["authorized_scope"] = ["0.0.0.0/0"]  # widen scope after signing
    with pytest.raises(EngagementError, match="signature verification failed"):
        ScopeGuard.from_engagement(artifact, verifier=verifier)


def test_expired_engagement_is_rejected(keys, verifier):
    artifact = _artifact(keys, not_before=time.time() - 7200, not_after=time.time() - 3600)
    with pytest.raises(EngagementError, match="expired"):
        ScopeGuard.from_engagement(artifact, verifier=verifier)


def test_not_yet_active_engagement_is_rejected(keys, verifier):
    artifact = _artifact(keys, not_before=time.time() + 3600, not_after=time.time() + 7200)
    with pytest.raises(EngagementError, match="not yet active"):
        ScopeGuard.from_engagement(artifact, verifier=verifier)


def test_profile_ceiling_violation_is_rejected(keys, verifier):
    artifact = _artifact(keys, max_profile="normal")
    with pytest.raises(EngagementError, match="exceeds the profile"):
        ScopeGuard.from_engagement(artifact, verifier=verifier, requested_profile="aggressive")


def test_bare_constructor_is_blocked():
    with pytest.raises(EngagementError, match="cannot be constructed directly"):
        ScopeGuard(["192.168.56.0/24"])


def test_wrong_key_forgery_is_rejected(keys):
    attacker_private, _ = generate_authority_keypair()
    forged = sign_engagement(_record(), attacker_private)
    trusted = EngagementVerifier(keys[1])  # only the real authority's public key
    with pytest.raises(EngagementError, match="signature verification failed"):
        ScopeGuard.from_engagement(forged, verifier=trusted)


def test_lab_mode_is_loopback_only():
    guard = ScopeGuard.for_lab()
    assert guard.validator.in_scope("127.0.0.1")
    assert guard.validator.in_scope("localhost")
    assert not guard.validator.in_scope("192.168.56.50")
    assert guard.engagement is None


def test_verify_from_file_round_trip(tmp_path, keys, verifier):
    path = tmp_path / "engagement.json"
    path.write_text(json.dumps(_artifact(keys)), encoding="utf-8")
    guard = ScopeGuard.from_engagement(path, verifier=verifier)
    assert guard.engagement.contract_id == "CONTRACT-TEST-1"


# ── Revocation ────────────────────────────────────────────────────────────

def test_revoked_contract_is_rejected(tmp_path, keys):
    from security.engagement import load_revoked_contract_ids  # noqa: F401

    rev = tmp_path / "revoked.txt"
    rev.write_text("CONTRACT-TEST-1  # client asked us to stop\n", encoding="utf-8")
    verifier = EngagementVerifier(keys[1], revoked_contract_ids=load_revoked_contract_ids(rev))
    with pytest.raises(EngagementError, match="has been revoked"):
        ScopeGuard.from_engagement(_artifact(keys), verifier=verifier)


def test_unrevoked_contract_still_passes(tmp_path, keys):
    from security.engagement import load_revoked_contract_ids

    rev = tmp_path / "revoked.txt"
    rev.write_text("CONTRACT-OTHER-9\n", encoding="utf-8")
    verifier = EngagementVerifier(keys[1], revoked_contract_ids=load_revoked_contract_ids(rev))
    guard = ScopeGuard.from_engagement(_artifact(keys), verifier=verifier)
    assert guard.engagement.contract_id == "CONTRACT-TEST-1"


def test_missing_revocation_file_means_no_revocations(tmp_path):
    from security.engagement import load_revoked_contract_ids

    assert load_revoked_contract_ids(tmp_path / "does-not-exist.txt") == frozenset()


def test_unreadable_revocation_file_fails_closed(tmp_path):
    from security.engagement import load_revoked_contract_ids

    # A directory where a file is expected: read_text raises OSError.
    bad = tmp_path / "revoked_dir"
    bad.mkdir()
    with pytest.raises(EngagementError, match="cannot read revocation list"):
        load_revoked_contract_ids(bad)


# ── Audit trail ───────────────────────────────────────────────────────────

def test_valid_engagement_is_recorded_in_audit_log(tmp_path, keys, verifier):
    import json as _json
    from oracle.cli.main import record_engagement_verified
    from oracle.runtime.audit import AuditConfig, AuditLogger
    from oracle.core.models import Mission

    guard = ScopeGuard.from_engagement(_artifact(keys), verifier=verifier)
    log_path = tmp_path / "mission_audit.jsonl"
    audit = AuditLogger(AuditConfig(path=log_path))
    mission = Mission(name="m-test", profile="normal", scope=[])

    assert record_engagement_verified(audit, guard, mission) is True

    events = [_json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    engagement_events = [e for e in events if e.get("event") == "engagement_verified"]
    assert len(engagement_events) == 1
    payload = engagement_events[0]["payload"]
    assert payload["contract_id"] == "CONTRACT-TEST-1"
    assert payload["client"] == "Test Client"
    assert payload["scope"] == ["192.168.56.0/24"]
    assert payload["max_profile"] == "normal"
    assert payload["issued_by"] == "ops@example.test"


def test_lab_run_writes_no_engagement_event(tmp_path):
    from oracle.cli.main import record_engagement_verified
    from oracle.runtime.audit import AuditConfig, AuditLogger
    from oracle.core.models import Mission

    log_path = tmp_path / "lab_audit.jsonl"
    audit = AuditLogger(AuditConfig(path=log_path))
    mission = Mission(name="lab", profile="normal", scope=[])
    assert record_engagement_verified(audit, ScopeGuard.for_lab(), mission) is False
    assert not log_path.exists() or "engagement_verified" not in log_path.read_text()


# ── No bypass of the scope choke point ────────────────────────────────────

class _Args:
    """Minimal stand-in for argparse output used by _resolve_scope_guard."""

    def __init__(self, engagement=None, engagement_pubkey=None, lab=False):
        self.engagement = engagement
        self.engagement_pubkey = engagement_pubkey
        self.lab = lab


def test_live_entrypoint_refuses_non_loopback_without_authorization():
    from oracle.cli.main import _resolve_scope_guard
    from oracle.core.models import Mission

    mission = Mission(name="live", profile="normal", scope=["10.0.0.5"])
    with pytest.raises(EngagementError, match="No scope authorization provided"):
        _resolve_scope_guard(mission, _Args())


def test_live_entrypoint_refuses_engagement_without_pubkey(tmp_path, keys, monkeypatch):
    from oracle.cli.main import _resolve_scope_guard
    from oracle.core.models import Mission

    monkeypatch.delenv("ORACLE_ENGAGEMENT_PUBKEY", raising=False)
    eng = tmp_path / "eng.json"
    eng.write_text(json.dumps(_artifact(keys)), encoding="utf-8")
    mission = Mission(name="live", profile="normal", scope=["192.168.56.1"])
    with pytest.raises(EngagementError, match="no trusted public key"):
        _resolve_scope_guard(mission, _Args(engagement=str(eng)))


def test_live_entrypoint_accepts_valid_engagement(tmp_path, keys):
    from oracle.cli.main import _resolve_scope_guard
    from oracle.core.models import Mission

    eng = tmp_path / "eng.json"
    eng.write_text(json.dumps(_artifact(keys)), encoding="utf-8")
    pub = tmp_path / "authority.pub"
    pub.write_bytes(keys[1])
    mission = Mission(name="live", profile="normal", scope=[])
    guard = _resolve_scope_guard(mission, _Args(engagement=str(eng), engagement_pubkey=str(pub)))
    assert guard.engagement is not None
    assert mission.scope == ["192.168.56.0/24"]


def test_lab_entrypoint_pins_loopback_only():
    from oracle.cli.main import _resolve_scope_guard
    from oracle.core.models import Mission

    mission = Mission(name="lab", profile="normal", scope=["10.0.0.5"])
    guard = _resolve_scope_guard(mission, _Args(lab=True))
    assert mission.scope == ["localhost", "127.0.0.1", "::1"]
    assert not guard.validator.in_scope("10.0.0.5")
