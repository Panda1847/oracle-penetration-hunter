"""Worker control-plane serializers."""

from __future__ import annotations

import time
from typing import Any, Dict, List


def worker_snapshot(dispatcher) -> List[Dict[str, Any]]:
    if dispatcher is None or not getattr(dispatcher, "registry", None):
        return []
    items: List[Dict[str, Any]] = []
    for record in dispatcher.registry.all().values():
        heartbeat_age = max(0.0, time.time() - float(record.heartbeat.last_seen))
        status = "healthy" if heartbeat_age <= 15 and record.health_score >= 0.7 else "degraded" if heartbeat_age <= 45 else "offline"
        items.append(
            {
                "worker_id": record.worker_id,
                "endpoint": record.endpoint,
                "capabilities": list(record.capabilities),
                "transport": record.transport,
                "role": record.role,
                "health_score": round(record.health_score, 3),
                "inflight_jobs": record.inflight_jobs,
                "heartbeat_age_seconds": round(heartbeat_age, 1),
                "status": status,
                "operations": {"drain": False, "quarantine": False, "reason": "dispatcher exposes read-only worker registry"},
                "metadata": dict(record.metadata),
            }
        )
    return items
