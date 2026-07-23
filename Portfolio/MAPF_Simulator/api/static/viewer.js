"use strict";

const state = { session: null, socket: null, running: false, timer: null, frame: null };
const $ = (id) => document.getElementById(id);
const canvas = $("map");
const ctx = canvas.getContext("2d");

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response.json();
}

function setError(error = "") { $("error").textContent = error; }
function setControls(active) {
  ["run", "pause", "single", "reset", "stop"].forEach((id) => $(id).disabled = !active);
  $("create").disabled = active;
}

async function createSession() {
  setError();
  try {
    const result = await api("/sessions", {
      method: "POST",
      body: JSON.stringify({
        scenario: $("scenario").value,
        penetration_rate: Number($("penetration").value),
        seed: Number($("seed").value),
        config_overrides: {},
        mode: $("mode").value,
      }),
    });
    state.session = result.session_id;
    $("sessionId").textContent = state.session.slice(0, 12);
    $("connection").textContent = "Connected";
    $("connection").className = "pill online";
    setControls(true);
    connectSocket();
  } catch (error) { setError(error.message); }
}

function connectSocket() {
  if (state.socket) state.socket.close();
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${scheme}://${location.host}/sessions/${state.session}/stream`);
  state.socket.onmessage = (event) => render(JSON.parse(event.data));
  state.socket.onerror = () => setError("WebSocket stream disconnected");
}

async function neutralActions() {
  const observations = await api(`/sessions/${state.session}/observations`);
  return {
    av_actions: Object.fromEntries(Object.keys(observations.av_agents).map((id) => [id, [0, 0]])),
    signal_actions: Object.fromEntries(Object.keys(observations.signal_agents).map((id) => [id, 0])),
    region_actions: Object.fromEntries(Object.keys(observations.region_agents).map((id) => [id, [.5, .5, .5, .5]])),
  };
}

async function stepOnce() {
  if (!state.session) return;
  try {
    const actions = await neutralActions();
    await api(`/sessions/${state.session}/actions`, { method: "POST", body: JSON.stringify(actions) });
    const result = await api(`/sessions/${state.session}/step`, { method: "POST", body: JSON.stringify({ n_steps: 1 }) });
    if (Math.round(result.sim_time) % 10 === 0) updateMetrics();
    if (result.done) pause();
  } catch (error) { pause(); setError(error.message); }
}

function schedule() {
  if (!state.running) return;
  stepOnce().finally(() => { state.timer = setTimeout(schedule, Number($("delay").value)); });
}
function run() { if (!state.running) { state.running = true; schedule(); } }
function pause() { state.running = false; clearTimeout(state.timer); }

async function stopSession() {
  pause();
  if (state.socket) state.socket.close();
  if (state.session) {
    try { await api(`/sessions/${state.session}`, { method: "DELETE" }); } catch (_) { /* already gone */ }
  }
  state.session = null;
  state.frame = null;
  $("connection").textContent = "No session";
  $("connection").className = "pill offline";
  $("sessionId").textContent = "—";
  setControls(false);
  drawMap({ vehicles: [], signals: [] });
}
async function resetSession() { await stopSession(); await createSession(); }

async function updateMetrics() {
  const metrics = await api(`/sessions/${state.session}/metrics`);
  for (const [key, value] of Object.entries(metrics)) {
    const element = $(key); if (!element) continue;
    const suffix = key === "co2_kg" ? " kg" : key === "fuel_l" ? " L" : key === "throughput" ? " /h" : key.includes("time") ? " s" : "";
    element.textContent = typeof value === "number" ? `${value.toFixed(key === "fairness_index" ? 3 : 2)}${suffix}` : value;
  }
}

function render(frame) {
  state.frame = frame;
  $("simTime").textContent = `${frame.sim_time.toFixed(0)} s`;
  $("vehicleCount").textContent = frame.vehicles.length;
  $("rewards").textContent = JSON.stringify(frame.active_agent_rewards, null, 2);
  drawMap(frame);
  if (Math.round(frame.sim_time) % 10 === 0) updateMetrics().catch((error) => setError(error.message));
}

function drawMap(frame) {
  const width = canvas.clientWidth * devicePixelRatio;
  const height = canvas.clientHeight * devicePixelRatio;
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  ctx.clearRect(0, 0, width, height);
  const margin = 70 * devicePixelRatio;
  const map = (x, y) => [margin + ((x + 200) / 1000) * (width - 2 * margin), height - margin - ((y + 200) / 1000) * (height - 2 * margin)];
  ctx.lineWidth = 13 * devicePixelRatio; ctx.strokeStyle = "#1d3347"; ctx.lineCap = "round";
  for (let i = 0; i < 4; i++) {
    const coordinate = i * 200;
    let a = map(-200, coordinate), b = map(800, coordinate); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
    a = map(coordinate, -200); b = map(coordinate, 800); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
  }
  const signals = new Map((frame.signals || []).map((item) => [item.intersection_id, item]));
  for (let col = 0; col < 4; col++) for (let row = 0; row < 4; row++) {
    const id = String.fromCharCode(65 + col) + row; const [x, y] = map(col * 200, row * 200); const signal = signals.get(id);
    ctx.beginPath(); ctx.arc(x, y, 8 * devicePixelRatio, 0, Math.PI * 2);
    ctx.fillStyle = signal && [0, 2, 5, 7].includes(signal.current_phase_id) ? "#53ec9b" : "#ff6b6b"; ctx.fill();
    ctx.fillStyle = "#7f96ad"; ctx.font = `${10 * devicePixelRatio}px system-ui`; ctx.fillText(id, x + 11 * devicePixelRatio, y - 9 * devicePixelRatio);
  }
  for (const vehicle of frame.vehicles || []) {
    const [x, y] = map(vehicle.x, vehicle.y); ctx.beginPath(); ctx.arc(x, y, (vehicle.type === "AV" ? 4.5 : 3.2) * devicePixelRatio, 0, Math.PI * 2);
    ctx.fillStyle = vehicle.type === "AV" ? "#ffad4d" : "#5ea4ff"; ctx.fill();
  }
}

$("create").onclick = createSession;
$("run").onclick = run;
$("pause").onclick = pause;
$("single").onclick = stepOnce;
$("reset").onclick = resetSession;
$("stop").onclick = stopSession;
$("delay").oninput = () => $("delayValue").textContent = `${$("delay").value} ms`;
window.addEventListener("resize", () => drawMap(state.frame || { vehicles: [], signals: [] }));
drawMap({ vehicles: [], signals: [] });

const attachedSession = new URLSearchParams(location.search).get("session");
if (attachedSession) {
  state.session = attachedSession;
  $("sessionId").textContent = state.session.slice(0, 12);
  $("connection").textContent = "External policy replay";
  $("connection").className = "pill online";
  ["create", "run", "pause", "single", "reset", "stop"].forEach((id) => $(id).disabled = true);
  connectSocket();
}
