import time

import pytest

from workers.auth import WorkerAuth


def test_worker_auth_rejects_weak_default_secret():
    with pytest.raises(ValueError):
        WorkerAuth("oracle-worker-secret")


def test_worker_auth_rejects_short_secret():
    with pytest.raises(ValueError):
        WorkerAuth("shortsecret")


def test_worker_auth_reads_env_secret(monkeypatch):
    monkeypatch.setenv("ORACLE_WORKER_SECRET", "very-strong-worker-secret-123")
    auth = WorkerAuth(None)
    signed = auth.sign({"ok": True})
    assert auth.verify({"ok": True}, signed)


def test_worker_auth_allows_insecure_only_when_flag_enabled(monkeypatch):
    monkeypatch.setenv("ORACLE_ALLOW_INSECURE_WORKER_SECRET", "1")
    auth = WorkerAuth("")
    signed = auth.sign({"ok": True})
    assert auth.verify({"ok": True}, signed)


def test_verify_rejects_tampered_payload():
    auth = WorkerAuth("very-strong-worker-secret-123")
    signed = auth.sign({"ok": True})
    assert not auth.verify({"ok": False}, signed)


def test_verify_rejects_stale_timestamp_replay():
    auth = WorkerAuth("very-strong-worker-secret-123", max_clock_skew_seconds=300)
    stale = str(int(time.time()) - 3600)
    signed = auth.sign({"ok": True}, timestamp=stale)
    assert not auth.verify({"ok": True}, signed)


def test_verify_rejects_future_timestamp():
    auth = WorkerAuth("very-strong-worker-secret-123", max_clock_skew_seconds=300)
    future = str(int(time.time()) + 3600)
    signed = auth.sign({"ok": True}, timestamp=future)
    assert not auth.verify({"ok": True}, signed)


def test_verify_rejects_non_integer_timestamp():
    auth = WorkerAuth("very-strong-worker-secret-123")
    signed = auth.sign({"ok": True}, timestamp="not-a-number")
    assert not auth.verify({"ok": True}, signed)
