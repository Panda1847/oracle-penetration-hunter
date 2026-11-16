"""SOC-grade dashboard backend gateway and static frontend server."""

from __future__ import annotations

import base64
from collections import defaultdict, deque
from dataclasses import asdict
import json
from queue import Empty, Full, Queue
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory, stream_with_context

from api.evidence import evidence_snapshot
from api.approvals import ApprovalQueue
from api.missions import mission_snapshot, mission_timeline
from api.plugins import plugin_snapshot
from api.reports import report_snapshot
from dashboard.live_stream import build_live_item, build_live_stream
from api.workers import worker_snapshot
from telemetry.health import GLOBAL_HEALTH
from telemetry.metrics import GLOBAL_METRICS
from telemetry.tracing import GLOBAL_TRACES


def _frontend_dir() -> Path:
    return Path(__file__).resolve().parent / "frontend"


def create_gateway(
    *,
    mission=None,
    manager=None,
    graph=None,
    dispatcher=None,
    plugin_registry=None,
    event_bus=None,
    approvals=None,
    artifact_router=None,
    metrics=None,
    health=None,
    tracer=None,
    auth_token: str = "",
    auth_user: str = "",
    auth_pass: str = "",
):
    app = Flask(__name__, static_folder=str(_frontend_dir()), static_url_path="/assets")
    metrics = metrics or GLOBAL_METRICS
    health = health or GLOBAL_HEALTH
    tracer = tracer or GLOBAL_TRACES
    auth_token = str(auth_token or "").strip()
    auth_user = str(auth_user or "").strip()
    auth_pass = str(auth_pass or "")
    rate_windows = {
        "default": {"max_requests": 180, "window_seconds": 60},
        "/api/dashboard/export": {"max_requests": 20, "window_seconds": 60},
    }
    request_buckets: dict[str, deque[float]] = defaultdict(deque)
    rate_lock = threading.RLock()
    approvals = approvals or ApprovalQueue()

    def _client_addr() -> str:
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
        remote = forwarded or (request.remote_addr or "")
        return remote.strip().lower()

    def _is_loopback_client() -> bool:
        client = _client_addr()
        return client in {"127.0.0.1", "::1", "localhost"} or client.startswith("::ffff:127.0.0.1")

    def _enforce_rate_limit():
        if not request.path.startswith("/api/dashboard/"):
            return None
        policy = rate_windows.get(request.path, rate_windows["default"])
        now = time.monotonic()
        key = f"{_client_addr()}::{request.path}"
        with rate_lock:
            bucket = request_buckets[key]
            cutoff = now - float(policy["window_seconds"])
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= int(policy["max_requests"]):
                return jsonify({"error": "rate_limited"}), 429
            bucket.append(now)
        return None

    def _authed() -> bool:
        # Token auth via header.
        if auth_token:
            provided = (request.headers.get("X-Oracle-Token") or "").strip()
            if not provided:
                provided = (request.cookies.get("oracle_token") or "").strip()
            return bool(provided) and provided == auth_token
        # Basic auth via Authorization header.
        if auth_user and auth_pass:
            header = request.headers.get("Authorization") or ""
            if not header.startswith("Basic "):
                return False
            try:
                raw = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8", errors="replace")
            except Exception:
                return False
            if ":" not in raw:
                return False
            user, pw = raw.split(":", 1)
            return user == auth_user and pw == auth_pass
        # Secure default: if no credentials configured, only loopback clients are allowed.
        return _is_loopback_client()

    def _require_auth():
        rate_error = _enforce_rate_limit()
        if rate_error is not None:
            return rate_error
        if _authed():
            return None
        hint = "Use --web-auth-token or --web-auth-user/--web-auth-pass when exposing dashboard outside localhost."
        return jsonify({"error": "unauthorized", "hint": hint}), 401

    @app.get("/")
    def index():
        response = send_from_directory(_frontend_dir(), "index.html")
        token_query = (request.args.get("token") or "").strip()
        if auth_token and token_query and token_query == auth_token:
            response.set_cookie("oracle_token", auth_token, httponly=True, samesite="Lax")
        return response

    @app.get("/healthz")
    def healthz():
        return jsonify(health.summary())

    @app.get("/api/dashboard/overview")
    def overview():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify(mission_snapshot(mission, graph, event_bus=event_bus, plugin_registry=plugin_registry))

    @app.get("/api/dashboard/timeline")
    def timeline():
        auth = _require_auth()
        if auth is not None:
            return auth
        limit = int(request.args.get("limit", 200) or 200)
        return jsonify({"items": mission_timeline(mission, graph, event_bus=event_bus, limit=limit)})

    @app.get("/api/dashboard/live-stream")
    def live_stream():
        auth = _require_auth()
        if auth is not None:
            return auth
        limit = int(request.args.get("limit", 200) or 200)
        return jsonify(build_live_stream(mission=mission, graph=graph, event_bus=event_bus, limit=limit))

    @app.get("/api/dashboard/events")
    def dashboard_events():
        auth = _require_auth()
        if auth is not None:
            return auth
        if event_bus is None:
            return jsonify({"error": "event stream unavailable"}), 503

        max_replay = 240
        try:
            requested_limit = int(request.args.get("limit", max_replay) or max_replay)
        except (TypeError, ValueError):
            requested_limit = max_replay
        limit = max(1, min(requested_limit, max_replay))
        last_event_id = (request.headers.get("Last-Event-ID") or "").strip()
        pending: Queue = Queue(maxsize=256)
        overflowed = threading.Event()

        def on_event(message):
            try:
                pending.put_nowait(message)
            except Full:
                overflowed.set()

        unsubscribe = event_bus.subscribe_envelopes(on_event)
        replay = event_bus.timeline(limit=limit)
        replay_ids = {str(item.get("event_id", "")) for item in replay}
        replay_start = 0
        if last_event_id:
            for index, item in enumerate(replay):
                if str(item.get("event_id", "")) == last_event_id:
                    replay_start = index + 1
                    break
            else:
                replay = []

        def frame(data, *, event=None, event_id=None):
            lines = []
            if event_id:
                lines.append(f"id: {event_id}")
            if event:
                lines.append(f"event: {event}")
            lines.append(f"data: {json.dumps(data, sort_keys=True, separators=(',', ':'))}")
            return "\n".join(lines) + "\n\n"

        @stream_with_context
        def generate():
            sent_ids = set()
            try:
                if last_event_id and not replay and last_event_id not in replay_ids:
                    yield frame({"reason": "event_id_outside_replay_window"}, event="resync")
                else:
                    for raw in replay[replay_start:]:
                        event_id = str(raw.get("event_id", ""))
                        if event_id:
                            sent_ids.add(event_id)
                        item = build_live_item(raw)
                        yield frame(item, event=item["event_type"], event_id=event_id)

                while True:
                    if overflowed.is_set():
                        overflowed.clear()
                        yield frame({"reason": "subscriber_queue_overflow"}, event="resync")
                    try:
                        message = pending.get(timeout=15)
                    except Empty:
                        yield ": keepalive\n\n"
                        continue
                    raw = message.to_dict()
                    event_id = str(raw.get("event_id", ""))
                    if event_id in sent_ids:
                        continue
                    sent_ids.add(event_id)
                    item = build_live_item(raw)
                    yield frame(item, event=item["event_type"], event_id=event_id)
            finally:
                unsubscribe()

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/dashboard/workers")
    def workers():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify({"items": worker_snapshot(dispatcher)})

    @app.get("/api/dashboard/plugins")
    def plugins():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify({"items": plugin_snapshot(plugin_registry)})

    @app.get("/api/dashboard/evidence")
    def evidence():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify(evidence_snapshot(graph))

    @app.get("/api/dashboard/telemetry")
    def telemetry():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify(
            {
                "metrics": metrics.snapshot(),
                "health": health.summary(),
                "traces": tracer.snapshot(),
            }
        )

    @app.get("/api/dashboard/artifacts")
    def artifacts():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify({"items": report_snapshot(artifact_router, download_prefix="/api/dashboard/artifacts/download")})

    @app.get("/api/dashboard/artifacts/download/<path:artifact_path>")
    def artifact_download(artifact_path: str):
        auth = _require_auth()
        if auth is not None:
            return auth
        if artifact_router is None:
            return jsonify({"error": "artifact router unavailable"}), 503
        resolved = artifact_router.resolve(artifact_path)
        if resolved is None:
            abort(404)
        return send_file(resolved, as_attachment=True, download_name=resolved.name)

    @app.get("/api/dashboard/approvals")
    def approval_items():
        auth = _require_auth()
        if auth is not None:
            return auth
        return jsonify({"items": approvals.pending()})

    @app.post("/api/dashboard/approvals")
    def create_approval():
        auth = _require_auth()
        if auth is not None:
            return auth
        if mission is None:
            return jsonify({"error": "mission unavailable"}), 503
        payload = request.get_json() or {}
        action = payload.get("action")
        if not isinstance(action, dict) or not action:
            return jsonify({"error": "action object is required"}), 400
        item = approvals.submit(
            requested_by=str(payload.get("requested_by", "operator")),
            requested_role=str(payload.get("requested_role", "operator")),
            mission_id=str(getattr(mission, "name", "")),
            action=action,
        )
        if event_bus is not None:
            event_bus.publish("approval_required", {"type": "approval_required", **asdict(item)}, trace_id="dashboard-approval")
        return jsonify(asdict(item)), 201

    @app.post("/api/dashboard/approvals/<approval_id>")
    def decide_approval(approval_id: str):
        auth = _require_auth()
        if auth is not None:
            return auth
        payload = request.get_json() or {}
        try:
            item = approvals.decide(
                approval_id,
                actor=str(payload.get("actor", "operator")),
                decision=str(payload.get("decision", "")),
                reason=str(payload.get("reason", "")),
            )
        except KeyError:
            return jsonify({"error": "approval not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        result = asdict(item)
        if event_bus is not None:
            event_bus.publish("approval_decided", {"type": "approval_decided", **result}, trace_id="dashboard-approval")
        return jsonify(result)

    @app.get("/api/dashboard/chat")
    def chat_history():
        auth = _require_auth()
        if auth is not None:
            return auth
        if graph is None:
            return jsonify({"messages": []})
        return jsonify({"messages": graph.recent_chat(100)})

    @app.post("/api/dashboard/chat")
    def post_chat():
        auth = _require_auth()
        if auth is not None:
            return auth
        if graph is None:
            return jsonify({"error": "graph unavailable"}), 503
        payload = request.get_json() or {}
        message = graph.add_chat_message(
            user=str(payload.get("user", "operator")),
            text=str(payload.get("text", "")),
            ts=str(payload.get("ts", "")),
        )
        return jsonify(message), 201

    @app.post("/api/dashboard/directives")
    def post_directive():
        auth = _require_auth()
        if auth is not None:
            return auth
        if graph is None:
            return jsonify({"error": "graph unavailable"}), 503
        payload = request.get_json() or {}
        text = str(payload.get("text", "")).strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        graph.add_directive(text)
        return jsonify({"ok": True, "text": text}), 201

    @app.post("/api/dashboard/control")
    def mission_control():
        auth = _require_auth()
        if auth is not None:
            return auth
        if mission is None or graph is None:
            return jsonify({"error": "mission unavailable"}), 503
        payload = request.get_json() or {}
        action = str(payload.get("action", "")).strip().lower()
        transitions = {"pause": "paused", "resume": "running", "stop": "stopped"}
        if action not in transitions:
            return jsonify({"error": "action must be pause, resume, or stop"}), 400
        if manager is not None and hasattr(manager, "request_control"):
            try:
                result = manager.request_control(
                    action,
                    actor=str(payload.get("actor", "operator")),
                    reason=str(payload.get("reason", "")),
                    command_id=payload.get("command_id"),
                    expected_version=payload.get("expected_version"),
                )
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            except RuntimeError as exc:
                return jsonify({"error": str(exc)}), 409
            return jsonify({"ok": True, **result}), 200
        mission.status = transitions[action]
        graph.add_directive(f"Operator command: {action}")
        return jsonify({"ok": True, "action": action, "status": mission.status}), 200

    @app.get("/api/dashboard/export")
    def export_snapshot():
        auth = _require_auth()
        if auth is not None:
            return auth
        snapshot = {
            "overview": mission_snapshot(mission, graph, event_bus=event_bus, plugin_registry=plugin_registry),
            "timeline": mission_timeline(mission, graph, event_bus=event_bus, limit=500),
            "live_stream": build_live_stream(mission=mission, graph=graph, event_bus=event_bus, limit=500),
            "workers": worker_snapshot(dispatcher),
            "plugins": plugin_snapshot(plugin_registry),
            "evidence": evidence_snapshot(graph),
            "artifacts": report_snapshot(artifact_router, download_prefix="/api/dashboard/artifacts/download"),
        }
        return app.response_class(json.dumps(snapshot, sort_keys=True), mimetype="application/json")

    return app


def run_gateway(
    graph,
    mission,
    *,
    manager=None,
    dispatcher=None,
    plugin_registry=None,
    event_bus=None,
    approvals=None,
    artifact_router=None,
    port: int = 5000,
):
    app = create_gateway(
        mission=mission,
        manager=manager,
        graph=graph,
        dispatcher=dispatcher,
        plugin_registry=plugin_registry,
        event_bus=event_bus,
        approvals=approvals,
        artifact_router=artifact_router,
    )
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
