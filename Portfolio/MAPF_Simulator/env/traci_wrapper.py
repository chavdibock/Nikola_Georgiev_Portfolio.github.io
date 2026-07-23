"""Low-level lifecycle wrapper for one SUMO TraCI connection."""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


@dataclass(frozen=True)
class VehicleState:
    """Raw state exposed by SUMO for one active vehicle."""

    vehicle_id: str
    position: tuple[float, float]
    speed_mps: float
    vehicle_type: str
    road_id: str
    lane_id: str


@dataclass(frozen=True)
class SignalState:
    """Raw state exposed by SUMO for one traffic light."""

    signal_id: str
    phase_index: int
    next_switch_s: float


def _load_config(path: Path) -> dict[str, Any]:
    """Load the repository's JSON-compatible YAML configuration."""
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return value


def _load_sumo_module(preferred_backend: str) -> tuple[ModuleType, str]:
    """Load libsumo when available and otherwise return the TraCI module."""
    try:
        import sumo  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("Install requirements.txt in the active .venv") from error
    tools = str(Path(sumo.SUMO_HOME) / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    if preferred_backend == "libsumo":
        try:
            import libsumo  # type: ignore[import-not-found]

            return libsumo, "libsumo"
        except ImportError:
            pass
    import traci  # type: ignore[import-not-found]

    return traci, "traci"


def _sumo_binary(use_gui: bool) -> Path:
    """Resolve SUMO from the active virtual environment or SUMO_HOME."""
    name = "sumo-gui" if use_gui else "sumo"
    suffix = ".exe" if os.name == "nt" else ""
    candidates = [Path(sys.executable).parent / f"{name}{suffix}"]
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        candidates.insert(0, Path(sumo_home) / "bin" / f"{name}{suffix}")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not locate {name} in the active Python environment")


class TraciConnection:
    """Own a single SUMO lifecycle and expose typed state accessors."""

    def __init__(
        self,
        sumo_config: Path,
        config_path: Path = DEFAULT_CONFIG,
        *,
        use_gui: bool | None = None,
        extra_args: Sequence[str] = (),
    ) -> None:
        """Configure a connection without starting SUMO until :meth:`start`."""
        self.sumo_config = sumo_config.resolve()
        self.config = _load_config(config_path.resolve())
        simulation = self.config["simulation"]
        self.use_gui = bool(simulation["use_gui"] if use_gui is None else use_gui)
        self.extra_args = tuple(extra_args)
        self._module, self.backend = _load_sumo_module(str(simulation["traci_backend"]))
        self._connection: Any | None = None
        self._label = f"mapf-{uuid.uuid4().hex}"

    @property
    def is_connected(self) -> bool:
        """Return whether this wrapper currently owns a live connection."""
        return self._connection is not None

    @property
    def simulation_time_s(self) -> float:
        """Return current SUMO simulation time in seconds."""
        connection = self._require_connection()
        return float(connection.simulation.getTime())

    @property
    def api(self) -> Any:
        """Expose the session-scoped TraCI API for higher-level environment components."""
        return self._require_connection()

    def start(self) -> None:
        """Start SUMO and establish the connection."""
        if self.is_connected:
            raise RuntimeError("SUMO connection is already started")
        if not self.sumo_config.is_file():
            raise FileNotFoundError(self.sumo_config)
        simulation = self.config["simulation"]
        command = [
            str(_sumo_binary(self.use_gui)),
            "-c", str(self.sumo_config),
            "--step-length", str(simulation["step_length_s"]),
            "--no-step-log", "true",
            "--quit-on-end", str(bool(simulation["quit_on_end"])).lower(),
            *self.extra_args,
        ]
        if self.backend == "traci":
            self._module.start(command, label=self._label)
            self._connection = self._module.getConnection(self._label)
        else:
            self._module.start(command)
            self._connection = self._module

    def step(self, n_steps: int = 1) -> float:
        """Advance SUMO by a positive number of ticks and return simulation time."""
        if n_steps < 1:
            raise ValueError("n_steps must be at least 1")
        connection = self._require_connection()
        for _ in range(n_steps):
            connection.simulationStep()
        return self.simulation_time_s

    def get_vehicle_states(self) -> Mapping[str, VehicleState]:
        """Read current active vehicles without retaining an unbounded global vector."""
        connection = self._require_connection()
        states: dict[str, VehicleState] = {}
        for vehicle_id in connection.vehicle.getIDList():
            states[vehicle_id] = VehicleState(
                vehicle_id=vehicle_id,
                position=tuple(connection.vehicle.getPosition(vehicle_id)),
                speed_mps=float(connection.vehicle.getSpeed(vehicle_id)),
                vehicle_type=str(connection.vehicle.getTypeID(vehicle_id)),
                road_id=str(connection.vehicle.getRoadID(vehicle_id)),
                lane_id=str(connection.vehicle.getLaneID(vehicle_id)),
            )
        return states

    def get_signal_states(self) -> Mapping[str, SignalState]:
        """Read current state for each network traffic light."""
        connection = self._require_connection()
        return {
            signal_id: SignalState(
                signal_id=signal_id,
                phase_index=int(connection.trafficlight.getPhase(signal_id)),
                next_switch_s=float(connection.trafficlight.getNextSwitch(signal_id)),
            )
            for signal_id in connection.trafficlight.getIDList()
        }

    def close(self) -> None:
        """Close TraCI and terminate the owned SUMO process cleanly."""
        if not self.is_connected:
            return
        connection = self._connection
        self._connection = None
        try:
            connection.close()
        finally:
            if self.backend == "traci":
                try:
                    self._module.switch(self._label)
                    self._module.close(False)
                except Exception:
                    pass

    def __enter__(self) -> "TraciConnection":
        """Start SUMO when entering a context manager."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Always close SUMO when leaving a context manager."""
        self.close()

    def _require_connection(self) -> Any:
        """Return the active connection or raise a lifecycle error."""
        if self._connection is None:
            raise RuntimeError("SUMO connection is not started")
        return self._connection
