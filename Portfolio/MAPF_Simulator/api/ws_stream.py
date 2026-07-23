"""Multiple-subscriber WebSocket broadcasting for simulator state frames."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketBroadcaster:
    """Track and broadcast to any number of viewers per simulation session."""

    def __init__(self) -> None:
        """Initialize an empty subscriber mapping."""
        self._clients: dict[str, dict[WebSocket, int]] = defaultdict(dict)

    async def connect(self, session_id: str, websocket: WebSocket, every_n: int) -> None:
        """Accept and register a read-only subscriber."""
        await websocket.accept()
        self._clients[session_id][websocket] = max(1, every_n)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a subscriber without affecting other viewers."""
        clients = self._clients.get(session_id)
        if clients is None:
            return
        clients.pop(websocket, None)
        if not clients:
            self._clients.pop(session_id, None)

    async def broadcast(self, session_id: str, frame: dict[str, Any]) -> None:
        """Send a frame to subscribers whose configured interval is due."""
        stale: list[WebSocket] = []
        sim_time = int(float(frame["sim_time"]))
        for websocket, every_n in list(self._clients.get(session_id, {}).items()):
            if sim_time % every_n:
                continue
            try:
                await websocket.send_json(frame)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session_id, websocket)
