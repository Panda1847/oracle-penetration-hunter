import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.core.engine import MissionEngine
from oracle.core.models import Mission, ActionResult, Action
from oracle.memory.graph import KnowledgeGraph
from oracle.memory.storage import Storage


class _StubAI:
    def __init__(self):
        self.calls = 0

    def decide(self, mission, graph, extra=""):
        self.calls += 1
        return {"stop_reason": "ok"}


class _StubExecutor:
    def build_command(self, action):
        return "echo stub"

    def run(self, action):
        return ActionResult(action=action, stdout="", stderr="", returncode=0, duration=0.0, parsed={})


class _StubSafety:
    def validate(self, action, cmd):
        return True, "OK"


def test_engine_pause_resume_does_not_complete(tmp_path):
    mission = Mission(name="m", scope=["127.0.0.1"], max_iterations=5)
    mission.status = "paused"

    graph = KnowledgeGraph(mission.name, Storage(tmp_path))
    engine = MissionEngine(
        mission=mission,
        graph=graph,
        ai=_StubAI(),
        executor=_StubExecutor(),
        safety=_StubSafety(),
    )

    it = engine.run()
    assert next(it)["type"] == "start"
    assert next(it)["type"] == "paused"

    mission.status = "running"
    e = next(it)
    assert e["type"] in ("thinking", "stopped"), e
    # drain until stopped
    for e in it:
        if e["type"] == "stopped":
            break

    assert mission.status == "stopped"


def test_engine_control_state_machine_is_idempotent_and_fail_closed(tmp_path):
    mission = Mission(name="control", scope=["127.0.0.1"], max_iterations=1)
    graph = KnowledgeGraph(mission.name, Storage(tmp_path))
    engine = MissionEngine(
        mission=mission,
        graph=graph,
        ai=_StubAI(),
        executor=_StubExecutor(),
        safety=_StubSafety(),
    )

    paused = engine.request_control("pause", actor="alice", reason="review")
    assert paused["outcome"] == "applied"
    assert paused["status"] == "paused"
    assert engine.request_control("pause")["outcome"] == "already_applied"
    assert engine.request_control("resume")["status"] == "running"
    stopped = engine.request_control("stop", command_id="cmd-1")
    assert stopped["status"] == "stopped"
    assert stopped["control_version"] == 3

    try:
        engine.request_control("resume")
    except RuntimeError as exc:
        assert "invalid transition" in str(exc)
    else:
        raise AssertionError("resume after stop must be rejected")
