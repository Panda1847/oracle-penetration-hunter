"""Approval queue and decision workflow."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4


@dataclass
class ApprovalRequest:
    approval_id: str
    requested_by: str
    requested_role: str
    action: dict
    mission_id: str
    status: str = "pending"
    decided_by: str = ""
    decision: str = ""
    reason: str = ""
    decided_at: str = ""


class ApprovalQueue:
    """In-memory approval workflow for operator actions."""

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}

    def submit(self, requested_by: str, requested_role: str, mission_id: str, action: dict) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=uuid4().hex,
            requested_by=requested_by,
            requested_role=requested_role,
            mission_id=mission_id,
            action=dict(action),
        )
        self._requests[request.approval_id] = request
        return request

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(approval_id)

    def decide(self, approval_id: str, actor: str, decision: str, reason: str = "") -> ApprovalRequest:
        request = self._requests.get(approval_id)
        if request is None:
            raise KeyError(approval_id)
        decision = str(decision or "").strip().lower()
        if decision not in {"approve", "deny", "defer"}:
            raise ValueError("decision must be approve, deny, or defer")
        reason = str(reason or "").strip()
        if decision == "deny" and not reason:
            raise ValueError("reason is required when denying an approval")
        if request.status != "pending":
            if request.decision == decision and request.decided_by == actor:
                return request
            raise RuntimeError("approval has already been decided")
        request.status = {"approve": "approved", "deny": "denied", "defer": "deferred"}[decision]
        request.decided_by = str(actor or "operator")
        request.decision = decision
        request.reason = reason
        request.decided_at = datetime.now(timezone.utc).isoformat()
        return request

    def pending(self) -> list[dict]:
        return [asdict(request) for request in self._requests.values() if request.status == "pending"]
