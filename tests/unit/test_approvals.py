import pytest

from api.approvals import ApprovalQueue


def test_approval_decisions_validate_reason_and_are_idempotent():
    queue = ApprovalQueue()
    item = queue.submit("planner", "operator", "mission-1", {"tool": "demo"})

    with pytest.raises(ValueError, match="reason is required"):
        queue.decide(item.approval_id, "alice", "deny")
    with pytest.raises(ValueError, match="decision must be"):
        queue.decide(item.approval_id, "alice", "maybe")

    decided = queue.decide(item.approval_id, "alice", "approve")
    assert decided.status == "approved"
    assert decided.decision == "approve"
    assert decided.decided_at
    assert queue.decide(item.approval_id, "alice", "approve") is decided

    with pytest.raises(RuntimeError, match="already been decided"):
        queue.decide(item.approval_id, "bob", "deny", reason="not safe")


def test_approval_queue_rejects_unknown_ids():
    queue = ApprovalQueue()
    with pytest.raises(KeyError):
        queue.decide("missing", "alice", "approve")
