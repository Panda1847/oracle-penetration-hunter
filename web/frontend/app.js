const params = new URLSearchParams(window.location.search);
const token = params.get("token");
if (token) localStorage.setItem("oracle_token", token);

const state = { tab: "command", filter: "all", graphFilter: "all", graphZoom: 1, graphPan: {x: 0, y: 0}, snapshot: {}, lastEvents: [], selected: null, streamStarted: false, streamConnected: false, streamRetry: null, streamAbort: null };
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));
const num = (value, digits = 0) => Number(value || 0).toFixed(digits);
const time = (value) => { if (!value) return "—"; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value).slice(0, 19) : date.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"}); };
const tokenHeaders = () => { const value = localStorage.getItem("oracle_token") || ""; return value ? {"X-Oracle-Token": value} : {}; };

async function api(path, options = {}) {
  const headers = {...tokenHeaders(), ...(options.headers || {})};
  const response = await fetch(path, {...options, headers});
  if (!response.ok) throw new Error(`${path} → ${response.status}`);
  return response.json();
}
function updateEventState(events) {
  state.lastEvents = events.slice(-240);
  state.snapshot.events = state.lastEvents;
  renderActivityChart(state.lastEvents);
  renderEvents(state.lastEvents);
  $("activity-count").textContent = state.lastEvents.length;
  $("last-sync").textContent = new Date().toLocaleTimeString();
}
function handleStreamEvent(eventName, payload) {
  if (eventName === "resync") {
    state.lastEvents = [];
    state.snapshot.events = [];
    renderEvents([]);
    refresh();
    return;
  }
  if (!payload || !payload.stream_id) return;
  const next = state.lastEvents.filter((item) => item.stream_id !== payload.stream_id);
  next.push(payload);
  updateEventState(next);
}
function parseSseBlock(block) {
  const fields = {};
  block.split("\n").forEach((line) => {
    const separator = line.indexOf(":");
    if (separator < 0) return;
    const key = line.slice(0, separator);
    const value = line.slice(separator + 1).trimStart();
    fields[key] = fields[key] ? `${fields[key]}\n${value}` : value;
  });
  if (!fields.data) return;
  try { handleStreamEvent(fields.event || "message", JSON.parse(fields.data)); } catch (_) { /* malformed events are ignored; polling will recover */ }
}
async function consumeEventStream() {
  const response = await fetch("/api/dashboard/events?limit=240", {headers: {...tokenHeaders(), "Accept": "text/event-stream"}, cache: "no-store"});
  if (!response.ok || !response.body) throw new Error(`event stream → ${response.status}`);
  state.streamConnected = true;
  $("connection-label").textContent = "LIVE STREAM";
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    blocks.filter((block) => block.trim() && !block.trimStart().startsWith(":" )).forEach(parseSseBlock);
  }
  throw new Error("event stream disconnected");
}
function connectEventStream() {
  if (state.streamStarted) return;
  state.streamStarted = true;
  const run = async () => {
    try { await consumeEventStream(); }
    catch (error) {
      state.streamConnected = false;
      $("connection-label").textContent = "RECONNECTING";
      if (state.streamRetry) window.clearTimeout(state.streamRetry);
      state.streamRetry = window.setTimeout(() => { state.streamStarted = false; connectEventStream(); }, 1800);
    }
  };
  run();
}
function toast(message, type = "info") { const node = $("toast"); node.textContent = message; node.className = `toast show ${type}`; window.clearTimeout(toast.timer); toast.timer = window.setTimeout(() => node.className = "toast", 3600); }
function empty(message = "No data available yet.") { return `<div class="empty-state"><span>◌</span><strong>${esc(message)}</strong></div>`; }
function pill(value, kind = "subtle") { return `<span class="pill ${kind}">${esc(value || "—")}</span>`; }
function severity(value) { const normalized = String(value || "INFO").toLowerCase(); return `<span class="severity severity-${normalized}">${esc(value || "INFO")}</span>`; }

function selectItem(title, data, kind = "event") {
  state.selected = {title, data, kind};
  $("inspector-title").textContent = title;
  $("inspector-content").innerHTML = `<div class="inspector-kicker">${esc(kind.toUpperCase())}</div><div class="inspector-json"><pre>${esc(JSON.stringify(data, null, 2))}</pre></div><button class="button ghost full" id="copy-inspector">Copy raw JSON</button>`;
  $("copy-inspector").onclick = async () => { await navigator.clipboard?.writeText(JSON.stringify(data, null, 2)); toast("Inspector payload copied", "success"); };
}
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((node) => node.classList.toggle("active", node.dataset.panel === tab));
  $("breadcrumb-tab").textContent = tab.replace("-", " ").toUpperCase();
}
function renderPhase(phase) {
  const phases = ["INIT", "DISCOVERY", "ENUMERATION", "ANALYSIS", "REPORTING"];
  const index = Math.max(0, phases.indexOf(String(phase || "INIT").toUpperCase()));
  document.querySelectorAll(".phase-step").forEach((node) => { const step = phases.indexOf(node.dataset.phase); node.classList.toggle("active", step === index); node.classList.toggle("complete", step < index); });
  $("phase-progress").innerHTML = phases.map((item, i) => `<span class="progress-node ${i < index ? "complete" : ""} ${i === index ? "current" : ""}"><i>${i + 1}</i><b>${item}</b></span>`).join('<span class="progress-line"></span>');
}
function renderHealth(health, targetId = "health-summary") {
  const components = Object.values(health?.components || {});
  $(targetId).innerHTML = components.length ? components.map((item) => `<div class="health-row"><span class="status-dot ${item.status === "ok" ? "live" : "warn"}"></span><span>${esc(item.component)}</span><b>${esc(item.status)}</b></div>`).join("") : empty("No health signals reported");
}
function renderActivityChart(events) {
  const buckets = Array.from({length: 24}, () => 0);
  events.slice(-240).forEach((item, i) => { buckets[i % buckets.length] += 1; });
  const max = Math.max(1, ...buckets);
  $("activity-chart").innerHTML = buckets.map((value, i) => `<span class="chart-bar" style="height:${Math.max(8, value / max * 92)}%" title="${value} events"></span>`).join("");
}
function findingScore(items) { return items.reduce((sum, item) => sum + Math.min(1, Number(item.confidence || 0)) * ({critical:1, high:.82, medium:.58, low:.3, info:.12}[String(item.severity || "info").toLowerCase()] || .12), 0); }
function renderOverview(overview, workers, evidence, telemetry, events) {
  const stats = overview.stats || {};
  const findings = overview.analyst_findings || [];
  const score = Math.min(100, Math.round(findingScore(findings) * 18));
  const critical = findings.filter((x) => String(x.severity).toLowerCase() === "critical").length;
  const elevated = findings.filter((x) => ["high", "medium"].includes(String(x.severity).toLowerCase())).length;
  $("side-mission").textContent = overview.name || "Unnamed mission";
  $("side-status").textContent = overview.status || "unknown";
  $("metric-phase").textContent = overview.phase || "INIT";
  $("metric-status").textContent = overview.status || "unknown";
  $("metric-hosts").textContent = stats.hosts || 0;
  $("metric-findings").textContent = findings.length;
  $("metric-workers").textContent = workers.length;
  $("metric-evidence").textContent = evidence.items?.length || 0;
  $("metric-objective").textContent = overview.objective || "No objective configured";
  $("mission-title").textContent = overview.name || "Unnamed mission";
  $("mission-objective").textContent = overview.objective || "—";
  $("mission-scope").textContent = (overview.scope || []).join(", ") || "loopback / lab";
  $("mission-iteration").textContent = overview.iterations || 0;
  $("mission-pill").textContent = String(overview.status || "unknown").toUpperCase();
  $("mission-pill").className = `pill ${overview.status === "running" ? "success" : overview.status === "paused" ? "warning" : "subtle"}`;
  $("threat-score").textContent = score;
  $("critical-count").textContent = critical;
  $("elevated-count").textContent = elevated;
  $("graph-count").textContent = overview.attack_graph?.nodes || 0;
  $("finding-count").textContent = findings.length;
  $("worker-count").textContent = workers.length;
  $("evidence-count").textContent = evidence.items?.length || 0;
  $("version-chip").textContent = `v${overview.build_identity?.semantic_version || "4.0.0"}`;
  renderPhase(overview.phase);
  renderActivityChart(events);
  renderCommandFindings(findings);
  renderCouncil(overview.council || {});
  renderHealth(telemetry.health);
  renderGraph(overview.attack_graph || {});
}
function renderCommandFindings(items) {
  $("command-findings").innerHTML = items.length ? items.slice(0, 5).map((item) => `<button class="compact-row" data-inspect="finding" data-index="${items.indexOf(item)}"><span class="severity-dot ${String(item.severity || "info").toLowerCase()}"></span><span class="grow"><strong>${esc(item.title || "Untitled finding")}</strong><small>${esc(item.host || "unknown host")}${item.port ? `:${item.port}` : ""}</small></span>${severity(item.severity)}</button>`).join("") : empty("No findings ranked yet");
  $("command-findings").querySelectorAll("[data-inspect]").forEach((node) => node.onclick = () => selectItem(items[node.dataset.index].title || "Finding", items[node.dataset.index], "finding"));
}
function renderCouncil(item) {
  $("council-mode").textContent = String(item.mode || "deterministic").toUpperCase();
  $("council-summary").innerHTML = `<div class="insight-row"><span>Backend</span><strong>${esc(item.backend || "unknown")}</strong></div><div class="insight-row"><span>Recommendations</span><strong>${item.recommendations_seen || 0}</strong></div><div class="insight-row"><span>Accepted / fallback</span><strong>${item.accepted_count || 0} / ${item.fallback_count || 0}</strong></div><div class="insight-row"><span>Consensus</span><strong>${item.agreement_count || 0}/${item.eligible_votes || 0}</strong></div><div class="insight-callout">${esc(item.last_gate_reason || item.last_recommendation_reasoning || "Deterministic policy is authoritative when no advisory signal is available.")}</div>`;
}
function renderEvents(items) {
  const filtered = state.filter === "all" ? items : items.filter((item) => String(item.event_type || item.type || item.topic || "").toLowerCase().includes(state.filter));
  $("event-total").textContent = `${filtered.length} events`;
  $("event-table").innerHTML = filtered.length ? `<div class="table-head"><span>TIME</span><span>TYPE</span><span>CHANNEL</span><span>SUMMARY</span><span>STATUS</span></div>` + filtered.slice().reverse().map((item, i) => { const payload = item.payload || item; const type = payload.type || item.event_type || item.topic || "event"; return `<button class="table-row event-row" data-event-index="${items.indexOf(item)}"><span class="mono muted">${time(payload.created_at || item.created_at)}</span><span class="event-type">${esc(type)}</span><span>${esc(payload.phase || payload.channel || item.topic || "system")}</span><span class="grow"><strong>${esc(payload.headline || payload.tool || payload.title || type)}</strong><small>${esc(payload.summary || payload.target || payload.narrative || "Event received")}</small></span><span>${payload.returncode === 0 ? pill("success", "success") : pill(payload.status || "logged", "subtle")}</span></button>`; }).join("") : empty("No matching events");
  $("event-table").querySelectorAll("[data-event-index]").forEach((node) => node.onclick = () => selectItem("Live event", items[node.dataset.eventIndex], "event"));
}
function renderFindings(items) {
  const counts = items.reduce((out, item) => { const key = String(item.severity || "INFO").toLowerCase(); out[key] = (out[key] || 0) + 1; return out; }, {});
  $("finding-summary").innerHTML = ["critical", "high", "medium", "low"].map((key) => `<div class="summary-chip"><span class="severity-dot ${key}"></span><strong>${counts[key] || 0}</strong><small>${key}</small></div>`).join("");
  $("finding-table").innerHTML = items.length ? `<div class="table-head finding-head"><span>RISK</span><span>FINDING</span><span>ASSET</span><span>CONFIDENCE</span><span>PLUGIN</span></div>` + items.map((item, i) => `<button class="table-row finding-row" data-finding-index="${i}"><span>${severity(item.severity)}</span><span class="grow"><strong>${esc(item.title || "Untitled finding")}</strong><small>${esc((item.cves || []).join(", ") || "No CVE reference")}</small></span><span class="mono">${esc(item.host || "unknown")}${item.port ? `:${item.port}` : ""}</span><span><div class="confidence"><i style="width:${Math.min(100, Number(item.confidence || 0) * 100)}%"></i></div>${num(Number(item.confidence || 0) * 100)}%</span><span class="mono muted">${esc(item.plugin || "—")}</span></button>`).join("") : empty("No findings collected");
  $("finding-table").querySelectorAll("[data-finding-index]").forEach((node) => node.onclick = () => selectItem(items[node.dataset.findingIndex].title || "Finding", items[node.dataset.findingIndex], "finding"));
}
function renderGraph(graph) {
  const nodes = (graph.top_nodes || []).filter((node) => state.graphFilter === "all" || String(node.kind || "").toLowerCase() === state.graphFilter);
  const allNodes = graph.top_nodes || []; const edges = graph.top_edges || []; const paths = graph.top_paths || [];
  $("graph-pill").textContent = `${graph.nodes || 0} nodes · ${graph.edges || 0} edges`;
  const width = 700; const height = 300; const centerX = width / 2; const centerY = height / 2;
  const positions = Object.fromEntries(allNodes.map((node, index) => { const angle = (Math.PI * 2 * index / Math.max(1, allNodes.length)) - Math.PI / 2; return [node.id, {x: centerX + Math.cos(angle) * 220, y: centerY + Math.sin(angle) * 92}]; }));
  const visibleIds = new Set(nodes.map((node) => node.id));
  const edgeMarkup = edges.filter((edge) => positions[edge.from] && positions[edge.to] && visibleIds.has(edge.from) && visibleIds.has(edge.to)).map((edge) => `<line class="graph-edge" x1="${positions[edge.from].x}" y1="${positions[edge.from].y}" x2="${positions[edge.to].x}" y2="${positions[edge.to].y}" stroke-width="${Math.max(1, Math.min(4, Number(edge.weight || 1)))}"></line>`).join("");
  const nodeMarkup = nodes.map((node) => { const point = positions[node.id] || {x: centerX, y: centerY}; const risk = Number(node.risk_score || 0); const tone = risk >= .75 ? "critical" : risk >= .45 ? "high" : "medium"; return `<g class="graph-node ${tone}" tabindex="0" role="button" aria-label="Inspect ${esc(node.label || node.id)}" data-node-id="${esc(node.id)}" transform="translate(${point.x} ${point.y})"><circle r="${Math.max(14, Math.min(24, 14 + risk * 10))}"></circle><text y="38" text-anchor="middle">${esc((node.label || node.id || "node").slice(0, 18))}</text></g>`; }).join("");
  $("graph-view").innerHTML = nodes.length ? `<svg class="attack-graph-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Interactive attack graph"><g class="graph-canvas" transform="translate(${state.graphPan.x} ${state.graphPan.y}) scale(${state.graphZoom})">${edgeMarkup}${nodeMarkup}</g></svg><div class="graph-caption">Select a node to inspect correlated evidence. Drag to pan; use the controls to zoom.</div>` : empty("Attack paths will appear as evidence is correlated");
  $("risk-nodes").innerHTML = nodes.length ? nodes.map((node, index) => `<button class="risk-row" data-risk-index="${index}"><span class="node-icon">◈</span><span class="grow"><strong>${esc(node.label || node.id)}</strong><small>${esc(node.kind || "node")}</small></span><b>${num(node.risk_score, 2)}</b></button>`).join("") : empty("No weighted nodes yet");
  $("risk-nodes").querySelectorAll("[data-risk-index]").forEach((node) => node.onclick = () => selectItem("Risk node", nodes[node.dataset.riskIndex], "attack graph"));
  $("graph-view").querySelectorAll("[data-node-id]").forEach((node) => { const inspect = () => { const selected = allNodes.find((item) => item.id === node.dataset.nodeId); if (selected) selectItem(selected.label || selected.id, selected, "attack graph node"); }; node.onclick = inspect; node.onkeydown = (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); inspect(); } }; });
  const svg = $("graph-view").querySelector("svg"); if (svg) { const canvas = svg.querySelector(".graph-canvas"); let drag; const applyPan = () => canvas.setAttribute("transform", `translate(${state.graphPan.x} ${state.graphPan.y}) scale(${state.graphZoom})`); svg.onpointerdown = (event) => { drag = {x: event.clientX, y: event.clientY, pan: {...state.graphPan}}; svg.setPointerCapture(event.pointerId); }; svg.onpointermove = (event) => { if (!drag) return; state.graphPan = {x: drag.pan.x + (event.clientX - drag.x) / 2, y: drag.pan.y + (event.clientY - drag.y) / 2}; applyPan(); }; svg.onpointerup = () => { drag = null; }; svg.onpointercancel = () => { drag = null; }; }
  $("graph-paths").innerHTML = paths.length ? paths.slice(0, 5).map((path) => `<div class="path-row"><span class="path-score">${num(path.score, 2)}</span><div class="path-line">${(path.path || []).map((part, i) => `<span class="path-node">${esc(part)}</span>${i < path.path.length - 1 ? '<i>→</i>' : ''}`).join("")}</div></div>`).join("") : empty("Attack paths will appear as evidence is correlated");
}
function renderWorkers(items) {
  $("worker-grid").innerHTML = items.length ? items.map((worker) => `<button class="worker-card" data-worker-index="${items.indexOf(worker)}"><div class="worker-card-head"><span class="worker-orb ${worker.health_score > .7 ? "healthy" : "degraded"}">⊙</span><span>${pill(worker.role || "worker", worker.health_score > .7 ? "success" : "warning")}</span></div><strong>${esc(worker.worker_id)}</strong><small>${esc(worker.endpoint || worker.transport || "local runtime")}</small><div class="worker-meter"><i style="width:${Math.min(100, Number(worker.health_score || 0) * 100)}%"></i></div><div class="worker-foot"><span>health ${num(Number(worker.health_score || 0) * 100)}%</span><span>${esc((worker.capabilities || []).join(" · ") || "no capabilities")}</span></div></button>`).join("") : empty("No registered workers");
  $("worker-grid").querySelectorAll("[data-worker-index]").forEach((node) => node.onclick = () => selectItem("Worker", items[node.dataset.workerIndex], "worker"));
}
function renderEvidence(data) {
  const items = data.items || []; const stats = data.stats || {};
  $("evidence-table").innerHTML = items.length ? `<div class="table-head"><span>ID</span><span>TYPE</span><span>CONTENT</span><span>CONFIDENCE</span></div>` + items.slice().reverse().map((item, i) => `<button class="table-row" data-evidence-index="${items.length - 1 - i}"><span class="mono muted">${esc(item.id || `EV-${i + 1}`)}</span><span>${esc(item.kind || item.type || "observation")}</span><span class="grow"><strong>${esc(item.title || item.summary || item.value || "Evidence item")}</strong><small>${esc(item.source || item.plugin || "runtime")}</small></span><span>${num(Number(item.confidence || 0) * 100)}%</span></button>`).join("") : empty("No evidence collected");
  $("evidence-quality").innerHTML = `<div class="quality-score">${num(Number(stats.average_confidence || stats.mean_confidence || 0) * 100)}<small>%</small></div><p>average confidence</p><div class="quality-line"><span>items</span><b>${items.length}</b></div><div class="quality-line"><span>contradictions</span><b class="${(data.contradictions || []).length ? "red-text" : "green-text"}">${(data.contradictions || []).length}</b></div>`;
  $("evidence-table").querySelectorAll("[data-evidence-index]").forEach((node) => node.onclick = () => selectItem("Evidence item", items[node.dataset.evidenceIndex], "evidence"));
}
function renderApprovals(items) { $("approval-count").textContent = items.length; $("approval-table").innerHTML = items.length ? items.map((item, i) => `<button class="approval-card" data-approval-index="${i}"><div><span class="approval-icon">✓</span><span><strong>${esc(item.approval_id || "Approval request")}</strong><small>${esc(item.requested_by || "operator")} · ${esc(item.status || "pending")}</small></span></div><code>${esc(JSON.stringify(item.action || {}, null, 2))}</code><div class="approval-actions"><span class="pill warning">requires review</span><span class="text-button">Inspect →</span></div></button>`).join("") : empty("No actions are waiting for approval"); $("approval-table").querySelectorAll("[data-approval-index]").forEach((node) => node.onclick = () => selectItem("Approval request", items[node.dataset.approvalIndex], "approval")); }
function renderReports(items) { $("report-table").innerHTML = items.length ? `<div class="table-head"><span>ARTIFACT</span><span>TYPE</span><span>CREATED</span><span>ACTION</span></div>` + items.map((item, i) => `<div class="table-row"><span class="file-icon">▤</span><span class="grow"><strong>${esc(item.name || item.path || "artifact")}</strong><small class="mono">${esc(item.relative_path || item.path || "")}</small></span><span>${esc(item.artifact_type || item.content_type || "file")}</span><span>${item.download_url ? `<a class="button small ghost" href="${esc(item.download_url)}">Download ↗</a>` : pill("local", "subtle")}</span></div>`).join("") : empty("Reports will appear after mission output is generated"); }
function renderTelemetry(data) { renderHealth(data.health, "telemetry-health"); const metrics = {...(data.metrics?.counters || {}), ...(data.metrics?.gauges || {})}; $("telemetry-metrics").innerHTML = Object.keys(metrics).length ? Object.entries(metrics).slice(0, 24).map(([key, value]) => `<div class="metric-card"><span class="mono">${esc(key)}</span><strong>${typeof value === "number" ? num(value, 2) : esc(value)}</strong></div>`).join("") : empty("No metrics emitted yet"); const traces = data.traces || []; $("trace-table").innerHTML = traces.length ? traces.slice(-20).reverse().map((trace) => `<div class="table-row"><span class="mono muted">${time(trace.created_at || trace.ts)}</span><span class="grow"><strong>${esc(trace.name || trace.operation || "trace")}</strong><small>${esc(trace.trace_id || trace.message || "")}</small></span><span>${pill(trace.status || "recorded", "subtle")}</span></div>`).join("") : empty("No traces buffered"); }

async function refresh() {
  try {
    const liveRequest = state.streamConnected ? Promise.resolve({items: state.lastEvents}) : api("/api/dashboard/live-stream?limit=240");
    const [overview, workersData, evidence, artifacts, approvals, live, telemetry] = await Promise.all([api("/api/dashboard/overview"), api("/api/dashboard/workers"), api("/api/dashboard/evidence"), api("/api/dashboard/artifacts"), api("/api/dashboard/approvals"), liveRequest, api("/api/dashboard/telemetry")]);
    const events = live.items || [];
    state.snapshot = {overview, workers: workersData.items || [], evidence, artifacts: artifacts.items || [], approvals: approvals.items || [], events, telemetry}; state.lastEvents = events;
    renderOverview(overview, state.snapshot.workers, evidence, telemetry, events); renderEvents(events); renderFindings(overview.analyst_findings || []); renderWorkers(state.snapshot.workers); renderEvidence(evidence); renderApprovals(state.snapshot.approvals); renderReports(state.snapshot.artifacts); renderTelemetry(telemetry);
    $("activity-count").textContent = events.length; $("connection-label").textContent = state.streamConnected ? "LIVE STREAM" : "LIVE"; $("last-sync").textContent = new Date().toLocaleTimeString();
    connectEventStream();
  } catch (error) { $("connection-label").textContent = "OFFLINE"; toast(`Dashboard connection lost: ${error.message}`, "error"); }
}
async function control(action) { try { const result = await api("/api/dashboard/control", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({action})}); toast(`Mission ${action} command accepted`, "success"); await refresh(); selectItem("Mission control", result, "operator action"); } catch (error) { toast(`Control failed: ${error.message}`, "error"); } }
async function post(path, payload, label) { try { await api(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}); toast(label, "success"); await refresh(); } catch (error) { toast(error.message, "error"); } }

document.querySelectorAll(".nav-item").forEach((node) => node.onclick = () => setTab(node.dataset.tab));
document.querySelectorAll("[data-tab-jump]").forEach((node) => node.onclick = () => setTab(node.dataset.tabJump));
document.querySelectorAll("[data-control]").forEach((node) => node.onclick = () => control(node.dataset.control));
document.querySelectorAll(".filter").forEach((node) => node.onclick = () => { state.filter = node.dataset.filter; document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active", item === node)); renderEvents(state.lastEvents); });
$("refresh-button").onclick = refresh;
$("graph-filter").onchange = (event) => { state.graphFilter = event.target.value; renderGraph(state.snapshot.overview?.attack_graph || {}); };
$("graph-zoom-in").onclick = () => { state.graphZoom = Math.min(2.4, state.graphZoom + .2); renderGraph(state.snapshot.overview?.attack_graph || {}); };
$("graph-zoom-out").onclick = () => { state.graphZoom = Math.max(.6, state.graphZoom - .2); renderGraph(state.snapshot.overview?.attack_graph || {}); };
$("graph-zoom-reset").onclick = () => { state.graphZoom = 1; state.graphPan = {x: 0, y: 0}; renderGraph(state.snapshot.overview?.attack_graph || {}); };
$("export-button").onclick = () => { window.location.href = `/api/dashboard/export${token ? `?token=${encodeURIComponent(token)}` : ""}`; };
$("close-inspector").onclick = () => { $("inspector-title").textContent = "Select an event"; $("inspector-content").innerHTML = `<div class="empty-inspector"><span class="empty-icon">◈</span><strong>Nothing selected</strong><p>Click a finding, event, worker, or evidence item to inspect its details.</p></div>`; };
$("directive-form").onsubmit = (event) => { event.preventDefault(); const input = $("directive-input"); const text = input.value.trim(); if (text) { post("/api/dashboard/directives", {text}, "Directive recorded"); input.value = ""; } };
$("note-form").onsubmit = (event) => { event.preventDefault(); const input = $("note-input"); const text = input.value.trim(); if (text) { post("/api/dashboard/chat", {user:"operator", text}, "Note posted"); input.value = ""; } };
refresh();
window.setInterval(refresh, 3500);
