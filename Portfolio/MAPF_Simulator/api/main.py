"""FastAPI control and streaming service for isolated SUMO sessions."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import (
    ActionsRequest, ActionsResponse, CreateSessionRequest, CreateSessionResponse,
    HealthResponse, MetricsResponse, ObservationResponse, SessionStatusResponse,
    StepRequest, StepResponse, StopSessionResponse, VehicleResponse,
)
from api.session_manager import ROOT, SessionManager
from api.ws_stream import WebSocketBroadcaster


STATIC = Path(__file__).resolve().parent / "static"
DEFAULTS = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
manager = SessionManager()
broadcaster = WebSocketBroadcaster()


def _json_schema(value: Any) -> dict[str, Any]:
    """Build a compact JSON schema from the current nested default configuration."""
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {key: _json_schema(item) for key, item in value.items()},
            "additionalProperties": False,
        }
    if isinstance(value, bool):
        return {"type": "boolean", "default": value}
    if isinstance(value, int):
        return {"type": "integer", "default": value}
    if isinstance(value, float):
        return {"type": "number", "default": value}
    if isinstance(value, list):
        return {"type": "array", "default": value}
    return {"type": "string", "default": value}


def _session(session_id: str) -> Any:
    """Resolve a session and translate missing identifiers to HTTP 404."""
    try:
        return manager.get(session_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run idle cleanup in the background and close SUMO on shutdown."""
    async def cleanup_loop() -> None:
        while True:
            await asyncio.sleep(float(DEFAULTS["api"]["cleanup_interval_s"]))
            await asyncio.to_thread(manager.cleanup_idle)

    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await asyncio.to_thread(manager.close_all)


app = FastAPI(title="Joint AV-Signal Simulator", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Open the interactive local viewer by default."""
    return RedirectResponse("/viewer")


@app.get("/viewer", include_in_schema=False)
async def viewer() -> FileResponse:
    """Serve the dependency-free browser experiment viewer."""
    return FileResponse(STATIC / "viewer.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return service liveness/readiness."""
    return HealthResponse()


@app.get("/config/schema")
async def config_schema() -> dict[str, Any]:
    """Expose the schema and defaults for every settable configuration value."""
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **_json_schema(DEFAULTS)}


@app.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create one seeded, isolated SUMO session."""
    try:
        session = await asyncio.to_thread(
            manager.create,
            scenario=request.scenario,
            penetration_rate=request.penetration_rate,
            seed=request.seed,
            mode=request.mode,
            config_overrides=request.config_overrides,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return CreateSessionResponse(session_id=session.session_id)


@app.get("/sessions/{session_id}", response_model=SessionStatusResponse)
async def session_status(session_id: str) -> SessionStatusResponse:
    """Return status and immutable experiment metadata."""
    session = _session(session_id)
    return SessionStatusResponse(
        session_id=session.session_id,
        sim_time=session.sim_time,
        running=not session.done,
        scenario=session.scenario,
        penetration_rate=session.penetration_rate,
    )


@app.delete("/sessions/{session_id}", response_model=StopSessionResponse)
async def delete_session(session_id: str) -> StopSessionResponse:
    """Stop SUMO and remove a session from the registry."""
    _session(session_id)
    await asyncio.to_thread(manager.stop, session_id)
    return StopSessionResponse(stopped=True)


@app.get("/sessions/{session_id}/observations", response_model=ObservationResponse)
async def observations(session_id: str) -> ObservationResponse:
    """Return observations only for agents active at the current boundary."""
    return ObservationResponse(**_session(session_id).observations())


@app.post("/sessions/{session_id}/actions", response_model=ActionsResponse)
async def actions(session_id: str, request: ActionsRequest) -> ActionsResponse:
    """Submit every role's actions in one batched REST request."""
    session = _session(session_id)
    await asyncio.to_thread(
        session.submit_actions,
        request.av_actions,
        request.signal_actions,
        request.region_actions,
    )
    return ActionsResponse(accepted=True)


@app.post("/sessions/{session_id}/step", response_model=StepResponse)
async def step(session_id: str, request: StepRequest) -> StepResponse:
    """Advance one or more ticks and broadcast every resulting state frame."""
    result: dict[str, float | bool] = {"sim_time": 0.0, "done": False}
    for _ in range(request.n_steps):
        session = _session(session_id)
        result = await asyncio.to_thread(session.step)
        await broadcaster.broadcast(session_id, session.stream_frame())
        if bool(result["done"]):
            break
    return StepResponse(sim_time=float(result["sim_time"]), done=bool(result["done"]))


@app.get("/sessions/{session_id}/metrics", response_model=MetricsResponse)
async def metrics(session_id: str) -> MetricsResponse:
    """Return cumulative research metrics for a session."""
    return MetricsResponse(**_session(session_id).metrics())


@app.get("/sessions/{session_id}/vehicles", response_model=list[VehicleResponse])
async def vehicles(session_id: str) -> list[VehicleResponse]:
    """Return live vehicle state for external visualization clients."""
    return [VehicleResponse(**item) for item in _session(session_id).vehicles()]


@app.websocket("/sessions/{session_id}/stream")
async def stream(
    websocket: WebSocket,
    session_id: str,
    every_n: int = Query(default=1, ge=1),
) -> None:
    """Push read-only state frames to one of multiple simultaneous subscribers."""
    try:
        session = manager.get(session_id)
    except KeyError:
        await websocket.close(code=4404)
        return
    await broadcaster.connect(session_id, websocket, every_n)
    await websocket.send_json(session.stream_frame())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(session_id, websocket)
