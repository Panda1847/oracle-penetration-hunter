import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workers.registration import WorkerRegistry
from api.workers import worker_snapshot


def test_worker_registry_tracks_health_and_selection():
    registry = WorkerRegistry(heartbeat_timeout_seconds=60)
    registry.register("local-node", "local://executor", ["*"], transport="local", role="local")
    registry.register("remote-a", "http://127.0.0.1:9999", ["nmap"], transport="http", role="remote")

    registry.acknowledge("remote-a")
    registry.complete("remote-a", True)

    best = registry.healthiest("nmap")

    assert best is not None
    assert best.worker_id == "remote-a"
    assert best.health_score > 0


def test_worker_snapshot_exposes_freshness_and_read_only_operations():
    registry = WorkerRegistry()
    registry.register("local-node", "local://executor", ["http"], transport="local", role="local")

    snapshot = worker_snapshot(SimpleNamespace(registry=registry))

    assert snapshot[0]["status"] == "healthy"
    assert snapshot[0]["heartbeat_age_seconds"] >= 0
    assert snapshot[0]["operations"]["drain"] is False
