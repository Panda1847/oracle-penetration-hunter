# ORACLE V4 — Complete Coder Workflow
# Deploy-Ready & Sales-Ready with NVIDIA NIM
# Owner: NULLSEC / Michael Lastovich
# Status: Production handoff document

---

## READ THIS FIRST

This document is the complete task list to take ORACLE from current state
to fully deployed and sales-ready. Every task is ordered by dependency.
Do not skip ahead. Each phase must pass its verification step before moving on.

Estimated total time: 8–12 focused developer days.

---

## PHASE 0 — Environment Baseline
### Est: 2 hours | Verify before touching any code

### 0.1 — Clean Kali VM test
Run the following on a FRESH Kali install (not your dev machine):
```bash
git clone [your-private-repo] oracle
cd oracle
python3 --version          # Must be 3.10+
go version                 # Must be 1.21+
docker --version           # Must be 24+
docker compose version     # Must be 2.x
nmap --version
gobuster version
ffuf -V
```

Document every failure. Fix before proceeding.

### 0.2 — Confirm current test suite baseline
```bash
cd oracle
pip install -r requirements.txt --break-system-packages
pip install -r requirements-dev.txt --break-system-packages
pytest tests/ -v --tb=short 2>&1 | tee baseline_test_results.txt
```

Save that output. Every task must keep tests green or add new ones.

### 0.3 — Confirm current demo runs
```bash
python oracle.py --demo --demo-speed 0.1
```
If it crashes, fix it before touching anything else. Demo must always run.

---

## PHASE 1 — NVIDIA NIM Integration
### Est: 4–6 hours | This is the new AI backend

NVIDIA NIM exposes an OpenAI-compatible API. The integration point is the
ModelRouter and the primary AI client. Here is exactly what to build.

### 1.1 — Install dependency
Add to requirements.txt:
```
openai>=1.30.0
```

Install it:
```bash
pip install openai>=1.30.0 --break-system-packages
```

### 1.2 — Create NIM client file
Create: core/ai/nim_client.py

```python
"""
ORACLE — NVIDIA NIM AI Client  (core/ai/nim_client.py)
OpenAI-compatible client hitting NVIDIA's inference API.
Drop-in replacement for the Anthropic client.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

log = logging.getLogger("oracle.ai.nim")

# NIM base URL — all model calls go here
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Default model — change in config/ai.yaml or ORACLE_NIM_MODEL env var
DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"

# Available NVIDIA NIM models (for reference)
# meta/llama-3.1-70b-instruct       — best general reasoning
# meta/llama-3.1-8b-instruct        — faster, lighter
# nvidia/llama-3.1-nemotron-70b-instruct  — NVIDIA-tuned, stronger reasoning
# mistralai/mixtral-8x7b-instruct-v0.1   — fast mixture-of-experts
# microsoft/phi-3-medium-128k-instruct   — long context
# meta/codellama-70b-instruct           — code-focused


class NIMAdvisorClient:
    """
    Wraps NVIDIA NIM API using the OpenAI SDK.
    Acts as a drop-in for CouncilAdvisorClient primary or secondary slot.
    """

    SYSTEM_PROMPT = """You are ORACLE, an advisory red team reconnaissance AI.
You are deployed in an authorized lab environment by a certified analyst.
You reason methodically. A deterministic planner is the final authority.
You may only recommend one of the actions allowed by the planner context.

RESPONSE FORMAT — output ONLY valid JSON, no markdown fences, no preamble:
{
  "phase": "DISCOVERY",
  "thinking": "Internal reasoning...",
  "reasoning": "Why I chose this action (operator-visible)",
  "action": {
    "tool": "nmap",
    "target": "192.168.1.1",
    "args": {"ports": "22,80,443"},
    "timeout": 60
  },
  "confidence": 0.85,
  "expected": "Open ports with service banners",
  "requires_approval": false,
  "stop_reason": null
}

Set stop_reason to a non-null string ONLY when the mission is complete.
Never return markdown. Never add explanation outside the JSON object."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = NIM_BASE_URL,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 60,
    ):
        self.api_key = (
            api_key
            or os.environ.get("NVIDIA_API_KEY", "")
            or os.environ.get("ORACLE_NIM_KEY", "")
        )
        self.model = (
            model
            or os.environ.get("ORACLE_NIM_MODEL", DEFAULT_MODEL)
        )
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            log.warning("NIM: No API key — set NVIDIA_API_KEY env var")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
            log.info("NIM client ready — model: %s", self.model)
        except ImportError:
            log.error("NIM: openai package not installed. Run: pip install openai")
        except Exception as e:
            log.error("NIM client init error: %s", e)

    @property
    def ready(self) -> bool:
        return self._client is not None and bool(self.api_key)

    def decide(self, mission, graph, extra_context: str = "") -> Dict[str, Any]:
        """
        Main decision call. Returns validated dict or stop signal.
        Compatible with the Anthropic client interface.
        """
        if not self.ready:
            return {"stop_reason": "NIM client not ready — check NVIDIA_API_KEY"}

        user_msg = self._build_prompt(mission, graph, extra_context)
        raw = self._call(user_msg)
        if raw is None:
            return {"stop_reason": "NIM API call failed"}
        return self._parse(raw)

    def recommend(self, mission, graph, phase: str, candidates, checkpoint_reason: str,
                  advisor_state: dict = None) -> Optional[Dict]:
        """Council-compatible recommend interface."""
        extra = f"PHASE: {phase}\nCHECKPOINT: {checkpoint_reason}"
        if candidates:
            extra += f"\nCANDIDATES: {json.dumps(candidates[:5], default=str)}"
        result = self.decide(mission, graph, extra)
        if result.get("stop_reason"):
            return None
        return result

    def _build_prompt(self, mission, graph, extra: str) -> str:
        graph_summary = graph.summary() if hasattr(graph, "summary") else str(graph)
        scope = getattr(mission, "scope", [])
        return f"""MISSION: {getattr(mission, 'name', 'unknown')}
SCOPE: {', '.join(scope) if isinstance(scope, list) else scope}
OBJECTIVE: {getattr(mission, 'objective', 'Identify vulnerabilities')}
PROFILE: {getattr(mission, 'profile', 'normal')}
ITERATION: {getattr(mission, 'iterations', 0)}

KNOWLEDGE GRAPH:
{graph_summary}

{extra}

Decide the single best next action to advance the mission."""

    def _call(self, user_msg: str, retries: int = 2) -> Optional[str]:
        for attempt in range(retries + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user",   "content": user_msg},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                    stream=False,
                )
                content = completion.choices[0].message.content
                log.debug("NIM response received (%d chars)", len(content or ""))
                return (content or "").strip()

            except Exception as e:
                err_str = str(e).lower()
                log.warning("NIM call attempt %d error: %s", attempt + 1, e)
                if "401" in err_str or "unauthorized" in err_str:
                    log.error("NIM: Invalid API key")
                    return None
                if "429" in err_str or "rate" in err_str:
                    time.sleep(5 * (attempt + 1))
                elif attempt >= retries:
                    return None
                else:
                    time.sleep(2)
        return None

    def _parse(self, raw: str) -> Dict[str, Any]:
        # Strip markdown fences
        cleaned = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.MULTILINE).strip()

        # Extract JSON object
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            cleaned = m.group(0)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            log.warning("NIM malformed JSON: %s | raw: %s", e, raw[:200])
            return {"stop_reason": f"nim_malformed_json: {e}", "raw": raw[:300]}

        # Normalize args
        action = data.get("action", {})
        if isinstance(action, dict) and isinstance(action.get("args"), str):
            try:
                action["args"] = json.loads(action["args"])
            except Exception:
                action["args"] = {}

        # Fix confidence
        conf = data.get("confidence", 0.7)
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            data["confidence"] = 0.7

        return data

    def summarize(self, graph) -> str:
        """Generate executive summary from findings."""
        if not self.ready:
            return "NIM not ready — cannot generate summary."
        prompt = (
            "You are a senior penetration tester writing a professional report. "
            "Write a concise executive summary (max 400 words) of these findings. "
            "Include: scope, key services found, notable risks, top recommendations.\n\n"
            f"FINDINGS:\n{graph.summary() if hasattr(graph, 'summary') else str(graph)}"
        )
        result = self._call(prompt)
        return result or "Summary generation failed."
```

### 1.3 — Add NIM to ModelRouter
In core/ai/model_router.py, make these exact changes:

CHANGE 1 — Add import at top:
```python
from .nim_client import NIMAdvisorClient
```

CHANGE 2 — Update VALID_BACKENDS:
```python
VALID_BACKENDS = {"auto", "anthropic", "ollama", "council", "deterministic", "nim"}
```

CHANGE 3 — Add NIM init in __init__ after self.ollama line:
```python
self.nim = self._build_nim_client()
```

CHANGE 4 — Add _build_nim_client method:
```python
def _build_nim_client(self) -> NIMAdvisorClient:
    nim_cfg = self.config.get("nim", {}) if isinstance(self.config.get("nim"), dict) else {}
    return NIMAdvisorClient(
        api_key=self.env.get("NVIDIA_API_KEY") or self.env.get("ORACLE_NIM_KEY") or nim_cfg.get("api_key", ""),
        model=self.env.get("ORACLE_NIM_MODEL") or nim_cfg.get("model", "meta/llama-3.1-70b-instruct"),
        temperature=float(nim_cfg.get("temperature", 0.1)),
        max_tokens=int(nim_cfg.get("max_tokens", 1024)),
        timeout=int(nim_cfg.get("timeout", 60)),
    )
```

CHANGE 5 — Update _select_active to handle nim backend:
```python
def _select_active(self):
    if self.backend == "deterministic":
        return self.local
    if self.backend == "nim":
        return self.nim if self._is_ready(self.nim) else self.local
    if self.backend == "anthropic":
        return self.client if self._is_ready(self.client) else self.local
    if self.backend == "ollama":
        return self.ollama if self._is_ready(self.ollama) else self.local
    if self.backend == "council":
        return self.council if self._is_ready(self.council) else self.local
    # auto — try nim first, then anthropic, then ollama, then local
    if self._is_ready(self.nim):
        return self.nim
    if self._is_ready(self.client):
        return self.client
    if self._is_ready(self.ollama):
        return self.ollama
    return self.local
```

CHANGE 6 — Update council to use NIM as secondary:
```python
self.council = CouncilAdvisorClient(
    primary_client=self.nim if self._is_ready(self.nim) else self.client,
    secondary_client=self.ollama,
)
```

### 1.4 — Update config/ai.yaml
Add this NIM section:
```yaml
nim:
  enabled: true
  model: meta/llama-3.1-70b-instruct
  temperature: 0.1
  max_tokens: 1024
  timeout: 60
  # Available models:
  # meta/llama-3.1-70b-instruct        (best quality)
  # meta/llama-3.1-8b-instruct         (faster/cheaper)
  # nvidia/llama-3.1-nemotron-70b-instruct (NVIDIA-tuned)
  # mistralai/mixtral-8x7b-instruct-v0.1  (mixture of experts)

advisor:
  enabled: true
  backend: nim  # CHANGED from auto to nim
  min_confidence_default: 0.6
  fallback_to_deterministic: true
```

### 1.5 — Update .env.example
```bash
# NVIDIA NIM (primary AI backend)
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ORACLE_NIM_MODEL=meta/llama-3.1-70b-instruct
ORACLE_AI_BACKEND=nim

# Anthropic (optional fallback)
ORACLE_API_KEY=sk-ant-api03-xxxxxxxxxx

# Oracle config
ORACLE_ENV=production
ORACLE_SCOPE=192.168.1.0/24
```

### 1.6 — Update docker-compose.yml
Add NIM env vars to oracle-control-plane service:
```yaml
environment:
  - ORACLE_API_KEY=${ORACLE_API_KEY:-}
  - NVIDIA_API_KEY=${NVIDIA_API_KEY:-}
  - ORACLE_NIM_MODEL=${ORACLE_NIM_MODEL:-meta/llama-3.1-70b-instruct}
  - ORACLE_AI_BACKEND=${ORACLE_AI_BACKEND:-nim}
  - ORACLE_ENV=production
```

### 1.7 — Write NIM tests
Create tests/unit/test_nim_client.py:
```python
"""Tests for NVIDIA NIM client integration."""
import json
import pytest
from unittest.mock import MagicMock, patch
from core.ai.nim_client import NIMAdvisorClient


def _good_response():
    return json.dumps({
        "phase": "DISCOVERY",
        "thinking": "Port scanning first",
        "reasoning": "Need to discover open services",
        "action": {"tool": "nmap", "target": "192.168.1.1",
                   "args": {"ports": "22,80,443"}, "timeout": 60},
        "confidence": 0.85,
        "expected": "Open ports",
        "requires_approval": False,
        "stop_reason": None
    })


def test_nim_parse_valid():
    client = NIMAdvisorClient()
    result = client._parse(_good_response())
    assert result.get("phase") == "DISCOVERY"
    assert result["action"]["tool"] == "nmap"


def test_nim_parse_strips_markdown():
    client = NIMAdvisorClient()
    wrapped = f"```json\n{_good_response()}\n```"
    result = client._parse(wrapped)
    assert result.get("phase") == "DISCOVERY"


def test_nim_parse_malformed():
    client = NIMAdvisorClient()
    result = client._parse("this is not json {{{{")
    assert "stop_reason" in result
    assert result["stop_reason"] is not None


def test_nim_ready_without_key():
    client = NIMAdvisorClient(api_key="")
    assert client.ready is False


def test_nim_ready_with_key():
    with patch("core.ai.nim_client.OpenAI"):
        client = NIMAdvisorClient(api_key="nvapi-test")
        assert client.ready is True


def test_nim_decide_no_key():
    client = NIMAdvisorClient(api_key="")
    result = client.decide(MagicMock(), MagicMock())
    assert "stop_reason" in result


def test_nim_confidence_clamped():
    client = NIMAdvisorClient()
    data = json.loads(_good_response())
    data["confidence"] = 99.0
    result = client._parse(json.dumps(data))
    assert result["confidence"] == 0.7


def test_nim_string_args_normalized():
    client = NIMAdvisorClient()
    data = json.loads(_good_response())
    data["action"]["args"] = '{"ports": "80"}'
    result = client._parse(json.dumps(data))
    assert isinstance(result["action"]["args"], dict)
```

### 1.8 — Verify NIM integration
```bash
# Set your NVIDIA API key
export NVIDIA_API_KEY="nvapi-your-key-here"
export ORACLE_AI_BACKEND="nim"

# Run NIM tests
pytest tests/unit/test_nim_client.py -v

# Quick live test
python3 -c "
from core.ai.nim_client import NIMAdvisorClient
client = NIMAdvisorClient()
print('NIM ready:', client.ready)
print('Model:', client.model)
"

# Run full demo to confirm no regressions
python oracle.py --demo --demo-speed 0.1
```

PASS CRITERIA:
- test_nim_client.py: all green
- demo runs clean
- NIM ready: True printed

---

## PHASE 2 — Critical Fixes
### Est: 1.5 days | These are blocking issues for any demo or sale

### 2.1 — Add missing prometheus.yml
The docker-compose mounts ./telemetry as Prometheus config but
prometheus.yml does not exist. Create telemetry/prometheus.yml:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: oracle
    static_configs:
      - targets: ['oracle-control-plane:8000']
    metrics_path: /metrics

  - job_name: redis
    static_configs:
      - targets: ['redis:6379']
```

### 2.2 — Validate install.sh end-to-end
Run this on a clean Kali VM (not dev machine):
```bash
# On clean Kali
sudo apt update && sudo apt install -y git python3-pip golang nmap gobuster ffuf curl
git clone [repo] oracle
cd oracle
chmod +x scripts/install.sh
./scripts/install.sh
```

Fix every failure. The install must complete with zero errors.
Add these checks to install.sh if missing:
```bash
# Check Python version
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"

# Check required binaries
for bin in nmap curl; do
    command -v $bin >/dev/null 2>&1 || { echo "Missing: $bin"; exit 1; }
done

# Install Python deps
pip3 install -r requirements.txt --break-system-packages

# Verify import works
python3 -c "import oracle; print('ORACLE', oracle.__version__, 'installed OK')"

echo ""
echo "Installation complete."
echo "Next: export NVIDIA_API_KEY=your-key && python oracle.py --demo"
```

### 2.3 — Fix the plugin dual-system conflict
oracle/plugins/ (flat files) and plugins/ (structured with manifest.yaml)
both exist. The registry needs to load the structured plugins correctly.

In plugins/registry.py, verify it loads from plugins/ directory
(the structured one with manifest.yaml), NOT oracle/plugins/.

Add a deprecation shim in oracle/plugins/base.py:
```python
# Shim — delegates to structured plugin registry
import warnings
warnings.warn(
    "oracle.plugins.base is deprecated. Use plugins.registry instead.",
    DeprecationWarning, stacklevel=2
)
```

Then update oracle/cli/main.py import to use plugins.registry.

### 2.4 — Validate the Go runtime builds
```bash
cd runtime-go
go mod tidy
go build ./...
go test ./...
```

Fix any build errors. The Go executor must compile clean.
If tests fail due to missing gRPC deps:
```bash
go get google.golang.org/grpc
go mod tidy
```

### 2.5 — Confirm Redis connection is optional
ORACLE should start and run in demo/standalone mode WITHOUT Redis.
In oracle/queue/redis_bus.py, confirm there is graceful degradation:
```python
try:
    import redis
    self._client = redis.Redis(...)
    self._client.ping()
except Exception as e:
    log.warning("Redis unavailable — running in-process queue mode: %s", e)
    self._client = None
```

If it hard-crashes without Redis, add this guard.

### 2.6 — Run full test suite and fix failures
```bash
pytest tests/ -v --tb=short 2>&1 | tee test_results.txt
grep -E "FAILED|ERROR" test_results.txt
```

All failures must be fixed before Phase 3.

---

## PHASE 3 — Demo Upgrade
### Est: 1 day | Your most important sales asset

The current demo was built before the council, AIL, and evidence graph existed.
It must be rewritten to show V4's actual differentiators.

### 3.1 — Rewrite oracle/demos/demo_mission.py
The new demo must show all of these in sequence:
- 3 hosts discovered with realistic port data
- Council voting round (proposer picks nmap, critic challenges it, verifier confirms)
- Attack graph building (edges forming between hosts and services)
- Evidence confidence scores updating
- AIL detecting a repeated pattern and flagging it
- Phase transition from DISCOVERY to ENUMERATION
- Web path found with MEDIUM severity finding
- Final stats: 3 hosts, 8 findings, 1 AIL event

Structure:
```python
DEMO_HOSTS = [...]             # 3 hosts with realistic port data
DEMO_COUNCIL_ROUNDS = [...]    # 3 rounds of council votes
DEMO_AIL_EVENT = {...}         # 1 AIL repetition detection
DEMO_FINDINGS = [...]          # 8 findings across severity levels
DEMO_ATTACK_PATHS = [...]      # 2 attack paths with scores

class DemoRunner:
    def run(self) -> Generator[Dict, None, None]:
        # Phase: INIT
        # Phase: DISCOVERY — 3 hosts, nmap results
        # Council rounds — visible votes per iteration
        # Phase: ENUMERATION — web fuzzing
        # AIL event — repetition flag
        # Phase: POST_PROCESS — attack graph synthesis
        # Final stats
```

### 3.2 — Update CLI demo handler in oracle/cli/main.py
In run_demo(), consume these new event types:
- "council_round" — show proposer/critic/verifier votes in Rich panel
- "ail_event" — show governance flag in yellow warning panel
- "attack_path" — show path score in graph panel
- "phase_transition" — show phase change banner

### 3.3 — Demo must complete in under 90 seconds at speed 1.0
Time it:
```bash
time python oracle.py --demo --demo-speed 1.0
```

If over 90 seconds, reduce sleep delays in DemoRunner.run().

### 3.4 — Demo with web dashboard must work
```bash
python oracle.py --demo --demo-speed 1.5 --web --web-port 5000
# Open browser, verify:
# - Hosts panel populates
# - Findings panel updates
# - Action feed scrolls
# - No console errors
```

Fix any WebSocket disconnects or empty panels.

---

## PHASE 4 — Frontend-Backend Bridge
### Est: 1 day | Makes the command center real

### 4.1 — Start both servers and verify they connect
```bash
# Terminal 1 — API backend
python -m uvicorn web.backend_gateway:app --port 8000 --reload

# Terminal 2 — check it responds
curl http://localhost:8000/health
curl http://localhost:8000/api/missions
curl http://localhost:8000/api/graph
```

Fix any 404s, 500s, or import errors in web/backend_gateway.py.

### 4.2 — Audit every API endpoint in web/frontend/app.js
Read web/frontend/app.js and list every fetch() call.
For each one, verify the corresponding route exists in web/backend_gateway.py.
Build a simple test script:

```bash
cat > /tmp/test_endpoints.sh << 'EOF'
BASE="http://localhost:8000"
for endpoint in /health /api/missions /api/graph /api/findings /api/workers /api/approvals; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE$endpoint)
    echo "$STATUS  $endpoint"
done
EOF
bash /tmp/test_endpoints.sh
```

All endpoints must return 200 or 404 (not 500).

### 4.3 — Verify WebSocket events reach the frontend
In web/frontend/app.js, find the WebSocket connection.
In web/backend_gateway.py, confirm it emits:
- mission_update
- finding_added
- host_discovered
- worker_status
- council_vote (new — add if missing)
- ail_event (new — add if missing)

### 4.4 — Add council_vote WebSocket event
In web/backend_gateway.py, after each council round, emit:
```python
socketio.emit("council_vote", {
    "iteration": mission.iterations,
    "proposer": council_result["proposer"],
    "critic": council_result["critic"],
    "verifier": council_result["verifier"],
    "arbiter": council_result["chosen"],
    "confidence": council_result["confidence"],
})
```

In web/frontend/app.js, consume it:
```javascript
socket.on("council_vote", (data) => {
    updateCouncilPanel(data);
});
```

### 4.5 — Static assets check
```bash
# All these must resolve with 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/assets/styles.css
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/assets/app.js
```

---

## PHASE 5 — Docker Deployment
### Est: 4 hours | One-command launch

### 5.1 — Test full docker-compose stack
```bash
export NVIDIA_API_KEY="nvapi-your-key"
export ORACLE_SCOPE="192.168.1.0/24"
export ORACLE_AI_BACKEND="nim"

docker compose build
docker compose up -d

# Wait 30 seconds, then check
docker compose ps
curl http://localhost:5000/health
curl http://localhost:9090  # Prometheus
curl http://localhost:3000  # Grafana
```

Fix every container that isn't healthy.

### 5.2 — Fix Go runtime container
The current docker-compose runs `go run .` which recompiles every time.
Change to:
```yaml
oracle-runtime-go:
  build:
    context: runtime-go
    dockerfile: Dockerfile.go
  container_name: oracle-runtime-go
  ports:
    - "9001:9001"
```

Create runtime-go/Dockerfile.go:
```dockerfile
FROM golang:1.24-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN go build -o oracle-executor .

FROM alpine:latest
RUN apk --no-cache add nmap curl
COPY --from=builder /app/oracle-executor .
EXPOSE 9001
CMD ["./oracle-executor"]
```

### 5.3 — Create docker compose demo profile
Add to docker-compose.yml:
```yaml
  oracle-demo:
    build: .
    container_name: oracle-demo
    environment:
      - NVIDIA_API_KEY=${NVIDIA_API_KEY:-}
      - ORACLE_AI_BACKEND=nim
    ports:
      - "5001:5000"
    command: --demo --web --web-port 5000 --demo-speed 1.5
    profiles:
      - demo
```

Demo launch becomes:
```bash
docker compose --profile demo up oracle-demo
# Open http://localhost:5001
```

### 5.4 — Validate clean teardown
```bash
docker compose down -v
docker compose up -d
# Must come up clean with no state issues
```

---

## PHASE 6 — CLI Doctor and Selftest
### Est: 3 hours | Operator confidence

### 6.1 — Verify oracle --doctor works
```bash
python oracle.py --doctor
```

Output must show:
- Python version check
- Required binary checks (nmap, curl, gobuster/ffuf)
- NVIDIA_API_KEY present/absent
- Redis reachable/unreachable
- Go executor reachable/unreachable
- Wordlist presence
- All pass/warn/fail with color

If --doctor is not implemented, add it to oracle/cli/main.py:
```python
elif args.subcommand == "doctor":
    from oracle.cli.doctor import run_doctor
    run_doctor()
```

### 6.2 — Verify oracle --selftest works
```bash
python oracle.py --selftest
```

Must run through: config load, safety gate, plugin load, AI client init,
graph init, demo mission (3 iterations). All green.

### 6.3 — Verify oracle --replay works
```bash
# Use an existing mission artifact
python oracle.py --replay --mission enterprise
```

Must replay the mission step by step through the Rich dashboard.

---

## PHASE 7 — README and Documentation
### Est: 1 day | Non-negotiable for sales

### 7.1 — README.md minimum required sections

The README must contain ALL of the following with real content:

```
1. ORACLE logo / banner (ASCII or image)
2. One-line description
3. Badges (CI, Python version, License, Docker)
4. What is ORACLE (3 sentences max)
5. What makes it different (comparison table)
6. Architecture diagram (ASCII or SVG)
7. Quickstart (3 commands to first output)
8. Full CLI reference (every flag documented)
9. NVIDIA NIM configuration section
10. Plugin system (how to write a plugin)
11. Licensing table (Community vs Pro vs Enterprise)
12. Security notice (authorized environments only)
13. Built by NULLSEC (with certifications)
```

The current README.md has 2 lines. This is the #1 sales blocker.

### 7.2 — Add NVIDIA NIM quickstart section to README
```markdown
## AI Backend — NVIDIA NIM

ORACLE uses NVIDIA NIM as its primary AI reasoning engine.
Get your API key at https://integrate.nvidia.com

```bash
export NVIDIA_API_KEY="nvapi-your-key-here"
export ORACLE_AI_BACKEND="nim"

# Verify connection
python oracle.py --doctor

# Run demo with NIM (no network target required)
python oracle.py --demo

# Live mission
python oracle.py --scope 192.168.1.0/24 --profile normal
```

Available NIM models:
| Model | Use Case | Speed |
|---|---|---|
| meta/llama-3.1-70b-instruct | Best reasoning | Medium |
| meta/llama-3.1-8b-instruct | Testing/dev | Fast |
| nvidia/llama-3.1-nemotron-70b-instruct | Complex engagements | Medium |
| mistralai/mixtral-8x7b-instruct-v0.1 | Balanced | Fast |

Set model: `export ORACLE_NIM_MODEL="model-name-here"`
```

### 7.3 — CHANGELOG.md
Write a real changelog. Minimum V4.0.0 entry:
```
## [4.0.0] — 2026-05
### Added
- NVIDIA NIM AI backend (OpenAI-compatible)
- AI council voting system (proposer/critic/verifier/arbiter)
- Deterministic mission planner with phase state machine
- SHA-256 chained cryptographic audit log
- Evidence intelligence graph (TTL decay, contradiction detection)
- Live attack graph engine with path scoring
- AIL governance layer (pause/quarantine/rollback)
- Go runtime executor with process sandboxing
- Redis-backed event bus
- Full REST API with WebSocket streaming
- Mission replay and forensic browser
- PDF report builder with audit hash
- Prometheus + Grafana telemetry
- oracle --doctor diagnostic command
- oracle --replay mission forensics
- oracle --rollback mission cleanup
```

---

## PHASE 8 — Report Quality
### Est: 4 hours | The artifact that justifies the price

### 8.1 — Verify PDF generation works
```bash
# Run a demo mission that produces a report
python oracle.py --demo --demo-speed 0.1
ls ~/.oracle/reports/
```

If no PDF is produced:
```bash
pip install reportlab weasyprint --break-system-packages
```

Then verify core/reporting/pdf_builder.py is called at mission end.

### 8.2 — PDF report must contain these sections
Open the generated PDF and verify:

Page 1: Cover — mission name, date, operator (NULLSEC), classification
Page 2: Executive Summary — 3 paragraphs, risk score, key numbers
Page 3: Attack Surface — host table with ports
Page 4+: Findings — severity badge, title, host, evidence, remediation
Last page: Audit chain hash — proves tamper-evidence

If any section is missing, add it to core/reporting/pdf_builder.py.

### 8.3 — The audit hash footer
Every report must end with:
```
ORACLE V4 — Mission: [name] — Generated: [datetime]
Audit Chain Hash: [sha256 of final audit log entry]
Verify: oracle --verify-report [report-file]
```

This is the feature that justifies enterprise pricing. It must be there.

---

## PHASE 9 — Sales Demo Recording
### Est: 3 hours | Your primary marketing asset

### 9.1 — Install recording tool
```bash
pip install asciinema --break-system-packages
# or
sudo apt install asciinema
```

### 9.2 — Record the demo
```bash
asciinema rec oracle-demo.cast -t "ORACLE V4 — Autonomous AI Red Team Intelligence"

# Inside the recording, run:
python oracle.py --demo --demo-speed 1.2

# Let it complete fully
# Then Ctrl+D to stop recording
```

### 9.3 — Convert to GIF
```bash
pip install agg --break-system-packages
agg oracle-demo.cast oracle-demo.gif --theme monokai
```

This GIF goes at the top of the README and on the website.
It is your single most important marketing asset.

### 9.4 — Record the live dashboard
Start a demo with --web, open browser, screen-record it.
Show: hosts populating, council voting panel, findings feed, attack graph.
This goes in the "Command Center" section of README.

---

## PHASE 10 — Final QA Checklist
### Run before any external demo or investor/customer meeting

```
INSTALLATION
[ ] Fresh Kali VM: ./scripts/install.sh completes with zero errors
[ ] python oracle.py --version prints correctly
[ ] python oracle.py --doctor all green or yellow (no red)
[ ] python oracle.py --list-plugins shows nmap, http, fuzz

DEMO MODE
[ ] python oracle.py --demo completes in <90s
[ ] python oracle.py --demo --web -- web-port 5000 — browser shows live data
[ ] Demo shows council votes in dashboard
[ ] Demo shows attack graph building
[ ] Demo shows AIL event
[ ] Demo produces report artifact

NIM INTEGRATION
[ ] export NVIDIA_API_KEY=... && python oracle.py --doctor shows NIM ready
[ ] NIM test suite passes: pytest tests/unit/test_nim_client.py -v
[ ] Live mission with NIM: first 5 iterations run clean with council visible
[ ] Fallback to deterministic works when key is unset

DOCKER
[ ] docker compose up starts all containers healthy
[ ] curl localhost:5000 returns control plane
[ ] curl localhost:9090 returns Prometheus
[ ] curl localhost:3000 returns Grafana login
[ ] docker compose --profile demo up oracle-demo shows demo in browser
[ ] docker compose down -v cleans up completely

REPORTING
[ ] PDF report generates at mission end
[ ] PDF contains: cover, executive summary, findings, audit hash
[ ] Audit hash is present and correct on final page

API
[ ] All endpoints return 200 or expected response
[ ] WebSocket connects and emits events in browser console
[ ] council_vote events visible in frontend

TESTS
[ ] pytest tests/ — zero failures, zero errors
[ ] pytest tests/ --cov=. --cov-report=term-missing — coverage >70%

SECURITY
[ ] Safety gate blocks out-of-scope targets
[ ] Destructive command blocklist works
[ ] No API keys hardcoded anywhere in codebase
[ ] git log — no secrets in commit history
```

---

## ENVIRONMENT VARIABLES — Complete Reference

```bash
# ── AI Backend ──────────────────────────────────────────────────
NVIDIA_API_KEY=nvapi-xxxx           # NVIDIA NIM API key (primary)
ORACLE_NIM_MODEL=meta/llama-3.1-70b-instruct  # NIM model
ORACLE_AI_BACKEND=nim               # nim | anthropic | ollama | deterministic | auto
ORACLE_API_KEY=sk-ant-xxxx          # Anthropic fallback (optional)

# ── Mission ─────────────────────────────────────────────────────
ORACLE_SCOPE=192.168.1.0/24         # Default scope for Docker
ORACLE_ENV=production               # production | development
ORACLE_MAX_ITER=30                  # Max AI iterations

# ── Infrastructure ───────────────────────────────────────────────
REDIS_URL=redis://localhost:6379    # Redis connection
ORACLE_GO_EXECUTOR=http://localhost:9001  # Go runtime endpoint
ORACLE_DB_PATH=/root/.oracle/oracle.db   # SQLite database

# ── Telemetry ───────────────────────────────────────────────────
ORACLE_METRICS_PORT=8000            # Prometheus scrape port
ORACLE_LOG_LEVEL=INFO               # DEBUG | INFO | WARNING

# ── Webhooks (optional) ──────────────────────────────────────────
ORACLE_WEBHOOK_URL=https://hooks.slack.com/xxx
ORACLE_WEBHOOK_SECRET=xxxx
```

---

## NVIDIA NIM — Getting Your API Key

1. Go to https://integrate.nvidia.com
2. Create account or log in
3. Navigate to API Keys → Generate Key
4. Key starts with: nvapi-
5. Free tier: 1,000 requests/day (enough for testing)
6. Paid: Pay-per-token, roughly $0.0007 per 1K tokens
7. One live ORACLE mission ≈ $0.05–$0.30 depending on iterations

For testing, use:
- meta/llama-3.1-8b-instruct (fastest, cheapest)

For live engagements, use:
- meta/llama-3.1-70b-instruct (best reasoning quality)
- nvidia/llama-3.1-nemotron-70b-instruct (NVIDIA-optimized, best for security tasks)

---

## PRIORITY ORDER SUMMARY

If time-constrained, do these in exact order. Each one unlocks the next.

```
Day 1:  Phase 0 + Phase 1  — baseline + NIM integration
Day 2:  Phase 2            — critical fixes
Day 3:  Phase 3            — demo upgrade
Day 4:  Phase 4            — frontend-backend bridge
Day 5:  Phase 5 + 6        — Docker + doctor/selftest
Day 6:  Phase 7            — README (cannot skip)
Day 7:  Phase 8 + 9        — reports + demo recording
Day 8:  Phase 10           — full QA pass
```

Do not show this to any customer or investor until Phase 10 is complete.
The QA checklist is the bar. Everything above that checklist is preparation for it.

---

## CONTACT

Owner: Michael Lastovich — NULLSEC
Certifications: CRTA (Cyberwarfare Labs), IBM Cybersecurity Analyst
Company EIN: 41-3768483

All work performed on this codebase is proprietary.
Do not commit secrets. Do not push to public repos.
All features must be tested before marking complete.
