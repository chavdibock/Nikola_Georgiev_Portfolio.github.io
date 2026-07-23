"""Section 8.1 network metrics accumulated from TraCI state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _traci_constants() -> Any:
    """Load TraCI constants only when an in-process collector is instantiated."""
    import sys
    from pathlib import Path

    import sumo  # type: ignore[import-not-found]

    tools = str(Path(sumo.SUMO_HOME) / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import traci.constants as constants  # type: ignore[import-not-found]

    return constants


def jains_fairness(values: list[float]) -> float:
    """Compute Jain's fairness index, treating an all-zero vector as perfectly fair."""
    if not values or all(value == 0 for value in values):
        return 1.0
    numerator = sum(values) ** 2
    denominator = len(values) * sum(value * value for value in values)
    return numerator / denominator if denominator else 1.0


@dataclass(frozen=True)
class EvaluationMetrics:
    """Final metric values required by Section 8.1."""

    avg_travel_time: float
    avg_wait_time: float
    throughput: float
    fairness_index: float
    co2_kg: float
    fuel_l: float
    max_queue_length: int
    completed_vehicles: int
    simulated_seconds: float

    def to_dict(self) -> dict[str, float | int]:
        """Return a serialization-ready representation."""
        return asdict(self)


class MetricsCollector:
    """Incrementally collect bounded aggregates while a SUMO session advances."""

    def __init__(
        self,
        traci_api: Any,
        step_length_s: float,
        fuel_density_g_per_l: float,
        queue_speed_threshold_mps: float,
    ) -> None:
        """Initialize cumulative scalars and per-active-vehicle lifecycle bookkeeping."""
        self._traci = traci_api
        self._step_length_s = step_length_s
        self._fuel_density_g_per_l = fuel_density_g_per_l
        self._queue_speed_threshold_mps = queue_speed_threshold_mps
        self._tc = _traci_constants()
        self._departures: dict[str, float] = {}
        self._last_wait: dict[str, float] = {}
        self._travel_times: list[float] = []
        self._completed_waits: list[float] = []
        self._lane_wait_totals: dict[str, float] = {}
        self._co2_mg = 0.0
        self._fuel_mg = 0.0
        self._max_queue = 0

    def observe_step(self) -> None:
        """Consume state after one simulation step without storing trajectory histories."""
        now = float(self._traci.simulation.getTime())
        for vehicle_id in self._traci.simulation.getDepartedIDList():
            self._departures[vehicle_id] = now
            self._traci.vehicle.subscribe(
                vehicle_id,
                (
                    self._tc.VAR_SPEED,
                    self._tc.VAR_ACCUMULATED_WAITING_TIME,
                    self._tc.VAR_CO2EMISSION,
                    self._tc.VAR_FUELCONSUMPTION,
                    self._tc.VAR_LANE_ID,
                ),
            )
        lane_queues: dict[str, int] = {}
        for vehicle_id, result in self._traci.vehicle.getAllSubscriptionResults().items():
            wait = float(result.get(self._tc.VAR_ACCUMULATED_WAITING_TIME, 0.0))
            self._last_wait[vehicle_id] = wait
            self._co2_mg += max(
                0.0, float(result.get(self._tc.VAR_CO2EMISSION, 0.0))
            ) * self._step_length_s
            self._fuel_mg += max(
                0.0, float(result.get(self._tc.VAR_FUELCONSUMPTION, 0.0))
            ) * self._step_length_s
            lane_id = str(result.get(self._tc.VAR_LANE_ID, ""))
            if lane_id and not lane_id.startswith(":"):
                stopped = float(result.get(self._tc.VAR_SPEED, 0.0)) < self._queue_speed_threshold_mps
                self._lane_wait_totals[lane_id] = self._lane_wait_totals.get(lane_id, 0.0) + (
                    self._step_length_s if stopped else 0.0
                )
                if stopped:
                    lane_queues[lane_id] = lane_queues.get(lane_id, 0) + 1
        self._max_queue = max(self._max_queue, max(lane_queues.values(), default=0))
        for vehicle_id in self._traci.simulation.getArrivedIDList():
            departure = self._departures.pop(vehicle_id, now)
            self._travel_times.append(max(0.0, now - departure))
            self._completed_waits.append(self._last_wait.pop(vehicle_id, 0.0))

    def finalize(self, simulated_seconds: float) -> EvaluationMetrics:
        """Compute final normalized values from the accumulated aggregates."""
        completed = len(self._travel_times)
        hours = simulated_seconds / 3600.0
        return EvaluationMetrics(
            avg_travel_time=sum(self._travel_times) / completed if completed else 0.0,
            avg_wait_time=sum(self._completed_waits) / completed if completed else 0.0,
            throughput=completed / hours if hours > 0 else 0.0,
            fairness_index=jains_fairness(list(self._lane_wait_totals.values())),
            co2_kg=self._co2_mg / 1_000_000.0,
            fuel_l=self._fuel_mg / (self._fuel_density_g_per_l * 1000.0),
            max_queue_length=self._max_queue,
            completed_vehicles=completed,
            simulated_seconds=simulated_seconds,
        )
