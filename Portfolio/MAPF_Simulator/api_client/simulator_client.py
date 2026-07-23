"""Synchronous batched REST/WebSocket client for the simulator service."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

import httpx
from websockets.sync.client import ClientConnection, connect


DEFAULT_SIMULATOR_URL = "http://simulator-service:8000"


class SimulatorClient:
    """Expose the remote simulator behind the previous parallel-environment interface."""

    def __init__(
        self,
        scenario: str,
        penetration_rate: float,
        seed: int,
        *,
        base_url: str | None = None,
        mode: str = "trained",
        config_overrides: Mapping[str, Any] | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        """Configure a client without creating a remote session until :meth:`reset`."""
        self.scenario = scenario
        self.penetration_rate = penetration_rate
        self.seed = seed
        self.mode = mode
        self.config_overrides = dict(config_overrides or {})
        self.base_url = (base_url or os.environ.get("SIMULATOR_API_URL", DEFAULT_SIMULATOR_URL)).rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout_s)
        self._stream: ClientConnection | None = None
        self.session_id: str | None = None
        self.last_sim_time = 0.0
        self.last_done = False
        self._known_signal_agent_ids: set[str] = set()
        self.grouped_observations: dict[str, dict[str, list[float]]] = {
            "av_agents": {}, "signal_agents": {}, "region_agents": {},
        }

    @property
    def signal_agent_ids(self) -> set[str]:
        """Return the fixed signal identifier set observed during this session."""
        return set(self._known_signal_agent_ids)

    def reset(self) -> dict[str, list[float]]:
        """Create a remote session, connect its stream, and return initial observations."""
        self.close()
        self.last_sim_time = 0.0
        self.last_done = False
        self._known_signal_agent_ids.clear()
        response = self._http.post(
            "/sessions",
            json={
                "scenario": self.scenario,
                "penetration_rate": self.penetration_rate,
                "seed": self.seed,
                "config_overrides": self.config_overrides,
                "mode": self.mode,
            },
        )
        response.raise_for_status()
        self.session_id = str(response.json()["session_id"])
        try:
            self._stream = connect(self._websocket_url(), open_timeout=30, close_timeout=5)
            self._stream.recv(timeout=30)  # initial time-zero frame
            return self.get_observations()
        except Exception:
            self.close()
            raise

    def get_observations(self) -> dict[str, list[float]]:
        """Fetch and flatten the current role-grouped active observations."""
        session_id = self._require_session()
        response = self._http.get(f"/sessions/{session_id}/observations")
        response.raise_for_status()
        self.grouped_observations = response.json()
        self._known_signal_agent_ids.update(self.grouped_observations["signal_agents"])
        return {
            key: value
            for group in self.grouped_observations.values()
            for key, value in group.items()
        }

    def step(
        self,
        actions: Mapping[str, int | Sequence[float]],
    ) -> tuple[
        dict[str, list[float]], dict[str, float], dict[str, bool],
        dict[str, bool], dict[str, dict[str, Any]],
    ]:
        """Submit one batched action request, advance one tick, and receive its stream frame."""
        session_id = self._require_session()
        signal_ids = set(self.grouped_observations["signal_agents"])
        region_ids = set(self.grouped_observations["region_agents"])
        payload = {
            "av_actions": {
                key: list(value)  # type: ignore[arg-type]
                for key, value in actions.items()
                if key not in signal_ids and key not in region_ids
            },
            "signal_actions": {
                key: int(value) for key, value in actions.items() if key in signal_ids
            },
            "region_actions": {
                key: list(value)  # type: ignore[arg-type]
                for key, value in actions.items() if key in region_ids
            },
        }
        accepted = self._http.post(f"/sessions/{session_id}/actions", json=payload)
        accepted.raise_for_status()
        stepped = self._http.post(f"/sessions/{session_id}/step", json={"n_steps": 1})
        stepped.raise_for_status()
        result = stepped.json()
        self.last_sim_time = float(result["sim_time"])
        self.last_done = bool(result["done"])
        if self._stream is None:
            raise RuntimeError("WebSocket stream is not connected")
        frame = self._stream.recv(timeout=30)
        if isinstance(frame, bytes):
            frame = frame.decode("utf-8")
        reward_groups = json.loads(frame)["active_agent_rewards"]
        rewards = {key: float(value) for group in reward_groups.values() for key, value in group.items()}
        observations = self.get_observations()
        done = self.last_done
        agent_ids = set(observations) | set(rewards)
        return (
            observations,
            rewards,
            {key: done for key in agent_ids},
            {key: False for key in agent_ids},
            {key: {} for key in agent_ids},
        )

    def metrics(self) -> dict[str, float | int]:
        """Return cumulative remote session metrics."""
        response = self._http.get(f"/sessions/{self._require_session()}/metrics")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the stream and tear down the remote session, if any."""
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        if self.session_id is not None:
            try:
                self._http.delete(f"/sessions/{self.session_id}")
            except httpx.HTTPError:
                pass
            self.session_id = None

    def __enter__(self) -> "SimulatorClient":
        """Create the session when entering a context manager."""
        self.reset()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Always tear down the remote session when leaving a context manager."""
        self.close()

    def _require_session(self) -> str:
        """Return the current session identifier or raise a lifecycle error."""
        if self.session_id is None:
            raise RuntimeError("Call reset() before using the simulator client")
        return self.session_id

    def _websocket_url(self) -> str:
        """Convert the configured HTTP service URL into the session stream URL."""
        session_id = self._require_session()
        parsed = urlsplit(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunsplit((scheme, parsed.netloc, f"/sessions/{session_id}/stream", "every_n=1", ""))
