"""Create, isolate, step, inspect, and tear down SUMO API sessions."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from baseline.fixed_time_controller import FixedTimeController
from demand.generate_demand import write_route_file, write_sumo_config
from env.joint_env import JointParallelEnv
from env.traci_wrapper import DEFAULT_CONFIG, TraciConnection
from evaluation.metrics import MetricsCollector


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "network" / "grid_4x4.net.xml"


def _load_object(path: Path) -> dict[str, Any]:
    """Load one JSON-compatible YAML object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def _merge_known(target: dict[str, Any], overrides: Mapping[str, Any], prefix: str = "") -> None:
    """Recursively apply overrides while rejecting unknown configuration keys."""
    for key, value in overrides.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in target:
            raise ValueError(f"Unknown config override: {path}")
        if isinstance(target[key], dict):
            if not isinstance(value, Mapping):
                raise ValueError(f"Config override {path} must be an object")
            _merge_known(target[key], value, path)
        else:
            target[key] = value


class SimulationSession:
    """One isolated SUMO lifecycle with cumulative metrics and pending actions."""

    def __init__(
        self,
        *,
        scenario: str,
        penetration_rate: float,
        seed: int,
        mode: str,
        config_overrides: Mapping[str, Any],
    ) -> None:
        """Generate private artifacts and start one baseline or joint environment."""
        self.session_id = uuid.uuid4().hex
        self.scenario = scenario
        self.penetration_rate = penetration_rate
        self.seed = seed
        self.mode = mode
        self.created_at = time.monotonic()
        self.last_activity_time = self.created_at
        self.done = False
        self._lock = threading.RLock()
        self.config = _load_object(DEFAULT_CONFIG)
        _merge_known(self.config, config_overrides)
        self.config["demand"]["seed"] = seed
        self.config["demand"]["penetration_rate"] = penetration_rate
        # The service contract requires independently addressable SUMO subprocesses.
        # libsumo is intentionally retained for the older in-process environments,
        # while API sessions use labeled TraCI connections for safe concurrency.
        self.config["simulation"]["traci_backend"] = "traci"
        self._temporary = tempfile.TemporaryDirectory(prefix=f"mapf-{self.session_id[:8]}-")
        temporary = Path(self._temporary.name)
        self.config_path = temporary / "config.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

        scenario_config = _load_object(ROOT / "config" / f"scenario_{scenario}.yaml")
        route_path = temporary / f"{scenario}.rou.xml"
        sumo_config_path = temporary / f"{scenario}.sumocfg"
        write_route_file(
            route_path,
            NETWORK,
            self.config,
            scenario_config,
            penetration_rate if mode == "trained" else 0.0,
            seed,
        )
        write_sumo_config(sumo_config_path, NETWORK, route_path)

        self.joint_environment: JointParallelEnv | None = None
        self.connection: TraciConnection
        self.controller: FixedTimeController | None = None
        if mode == "trained":
            self.joint_environment = JointParallelEnv(
                scenario,
                config_path=self.config_path,
                sumo_config_path=sumo_config_path,
            )
            self.latest_observations = self.joint_environment.reset()
            self.connection = self.joint_environment.connection
        else:
            self.connection = TraciConnection(sumo_config_path, self.config_path)
            self.connection.start()
            self.controller = FixedTimeController(
                self.connection.api,
                str(self.config["baseline"]["program_id"]),
                int(self.config["baseline"]["initial_phase_index"]),
            )
            self.controller.initialize()
            self.latest_observations: dict[str, list[float]] = {}
        self.latest_rewards: dict[str, float] = {}
        self.pending_actions: dict[str, int | list[float]] = {}
        self.collector = MetricsCollector(
            self.connection.api,
            float(self.config["simulation"]["step_length_s"]),
            float(self.config["metrics"]["fuel_density_g_per_l"]),
            float(self.config["metrics"]["queue_speed_threshold_mps"]),
        )

    @property
    def sim_time(self) -> float:
        """Return current simulation time."""
        return self.connection.simulation_time_s

    def touch(self) -> None:
        """Record external activity for idle-session cleanup."""
        self.last_activity_time = time.monotonic()

    def observations(self) -> dict[str, dict[str, list[float]]]:
        """Return current boundary-active observations grouped by role."""
        self.touch()
        signal_ids = (
            set(self.joint_environment.hierarchy.local.signal_ids)
            if self.joint_environment is not None else set()
        )
        return {
            "av_agents": {
                key: value for key, value in self.latest_observations.items()
                if key not in signal_ids and not key.startswith("region_")
            },
            "signal_agents": {
                key: value for key, value in self.latest_observations.items()
                if key in signal_ids
            },
            "region_agents": {
                key: value for key, value in self.latest_observations.items()
                if key.startswith("region_")
            },
        }

    def submit_actions(
        self,
        av_actions: Mapping[str, list[float]],
        signal_actions: Mapping[str, int],
        region_actions: Mapping[str, list[float]],
    ) -> None:
        """Replace the persisted action batch with one validated combined mapping."""
        with self._lock:
            self.pending_actions = {**av_actions, **signal_actions, **region_actions}
            self.touch()

    def step(self) -> dict[str, float | bool]:
        """Advance exactly one simulator tick and update observations and metrics."""
        with self._lock:
            if self.done:
                return {"sim_time": self.sim_time, "done": True}
            if self.joint_environment is not None:
                (
                    self.latest_observations,
                    self.latest_rewards,
                    _,
                    _,
                    _,
                ) = self.joint_environment.step(self.pending_actions)
            else:
                if self.controller is not None:
                    self.controller.step()
                self.connection.step()
                self.latest_observations = {}
                self.latest_rewards = {}
            self.collector.observe_step()
            self.done = self.connection.api.simulation.getMinExpectedNumber() == 0
            self.touch()
            return {"sim_time": self.sim_time, "done": self.done}

    def metrics(self) -> dict[str, float | int]:
        """Return cumulative Section 8.1 metrics without ending the session."""
        self.touch()
        values = self.collector.finalize(self.sim_time).to_dict()
        return {
            key: values[key]
            for key in (
                "avg_travel_time", "avg_wait_time", "throughput", "fairness_index",
                "co2_kg", "fuel_l", "max_queue_length",
            )
        }

    def vehicles(self) -> list[dict[str, str | float]]:
        """Return raw active vehicle positions and speeds for visualization."""
        self.touch()
        result: list[dict[str, str | float]] = []
        for vehicle_id, state in self.connection.get_vehicle_states().items():
            result.append(
                {
                    "vehicle_id": vehicle_id,
                    "x": state.position[0],
                    "y": state.position[1],
                    "speed": state.speed_mps,
                    "type": "AV" if state.vehicle_type == "AV" else "HUMAN",
                }
            )
        return result

    def stream_frame(self) -> dict[str, Any]:
        """Build one WebSocket frame with fixed-role rewards and live state."""
        signal_ids = (
            set(self.joint_environment.hierarchy.local.signal_ids)
            if self.joint_environment is not None else set(self.connection.get_signal_states())
        )
        rewards = {
            "av": {
                key: value for key, value in self.latest_rewards.items()
                if key not in signal_ids and not key.startswith("region_")
            },
            "signal": {key: value for key, value in self.latest_rewards.items() if key in signal_ids},
            "region": {
                key: value for key, value in self.latest_rewards.items() if key.startswith("region_")
            },
        }
        now = self.sim_time
        return {
            "sim_time": now,
            "vehicles": self.vehicles(),
            "signals": [
                {
                    "intersection_id": key,
                    "current_phase_id": state.phase_index,
                    "seconds_until_change": max(0.0, state.next_switch_s - now),
                }
                for key, state in self.connection.get_signal_states().items()
            ],
            "active_agent_rewards": rewards,
        }

    def close(self) -> None:
        """Stop SUMO and remove this session's temporary artifacts."""
        with self._lock:
            if self.joint_environment is not None:
                self.joint_environment.close()
            else:
                self.connection.close()
            self.done = True
            self._temporary.cleanup()


class SessionManager:
    """Thread-safe in-memory registry for independently owned sessions."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG) -> None:
        """Load configured resource limits and initialize an empty registry."""
        config = _load_object(config_path)
        self.idle_timeout_s = float(config["api"]["session_idle_timeout_s"])
        self.max_concurrent_sessions = int(config["api"]["max_concurrent_sessions"])
        self.sessions: dict[str, SimulationSession] = {}
        self._lock = threading.RLock()

    def create(self, **parameters: Any) -> SimulationSession:
        """Create and register a session or raise when capacity is exhausted."""
        self.cleanup_idle()
        with self._lock:
            if len(self.sessions) >= self.max_concurrent_sessions:
                raise RuntimeError("Maximum concurrent session limit reached")
            session = SimulationSession(**parameters)
            self.sessions[session.session_id] = session
            return session

    def get(self, session_id: str) -> SimulationSession:
        """Return a live session by identifier."""
        with self._lock:
            try:
                session = self.sessions[session_id]
            except KeyError as error:
                raise KeyError(f"Unknown session: {session_id}") from error
        session.touch()
        return session

    def stop(self, session_id: str) -> None:
        """Unregister and close one session."""
        with self._lock:
            try:
                session = self.sessions.pop(session_id)
            except KeyError as error:
                raise KeyError(f"Unknown session: {session_id}") from error
        session.close()

    def cleanup_idle(self) -> list[str]:
        """Close sessions whose last external activity exceeds the configured timeout."""
        now = time.monotonic()
        with self._lock:
            expired = [
                session_id for session_id, session in self.sessions.items()
                if now - session.last_activity_time > self.idle_timeout_s
            ]
        for session_id in expired:
            try:
                self.stop(session_id)
            except KeyError:
                pass
        return expired

    def close_all(self) -> None:
        """Close every registered session during service shutdown."""
        with self._lock:
            identifiers = list(self.sessions)
        for session_id in identifiers:
            try:
                self.stop(session_id)
            except KeyError:
                pass
