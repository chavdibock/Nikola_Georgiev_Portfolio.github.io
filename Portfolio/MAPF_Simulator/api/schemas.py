"""Pydantic request and response contracts for the simulator service."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ScenarioName = Literal["surge", "rush_hour", "uniform"]
SessionMode = Literal["trained", "baseline"]


class StrictModel(BaseModel):
    """Base API model that rejects misspelled or unsupported fields."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    """Service readiness response."""

    status: Literal["ok"] = "ok"


class CreateSessionRequest(StrictModel):
    """Parameters used to create one isolated simulator session."""

    scenario: ScenarioName
    penetration_rate: Literal[0.05, 0.1, 0.2]
    seed: int
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    mode: SessionMode


class CreateSessionResponse(StrictModel):
    """Identifier returned for a new session."""

    session_id: str


class SessionStatusResponse(StrictModel):
    """Current session metadata."""

    session_id: str
    sim_time: float
    running: bool
    scenario: ScenarioName
    penetration_rate: float


class StopSessionResponse(StrictModel):
    """Session teardown acknowledgement."""

    stopped: bool


class ObservationResponse(StrictModel):
    """Active decision-boundary observations split by policy role."""

    av_agents: dict[str, list[float]]
    signal_agents: dict[str, list[float]]
    region_agents: dict[str, list[float]]


class ActionsRequest(StrictModel):
    """One batched action submission for every currently active role."""

    av_actions: dict[str, list[float]] = Field(default_factory=dict)
    signal_actions: dict[str, int] = Field(default_factory=dict)
    region_actions: dict[str, list[float]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_shapes(self) -> "ActionsRequest":
        """Reject malformed role actions before they reach TraCI."""
        if any(len(action) != 2 for action in self.av_actions.values()):
            raise ValueError("Every AV action must contain exactly two values")
        if any(action not in (0, 1) for action in self.signal_actions.values()):
            raise ValueError("Every signal action must be 0 or 1")
        if any(len(action) != 4 for action in self.region_actions.values()):
            raise ValueError("Every regional action must contain exactly four values")
        return self


class ActionsResponse(StrictModel):
    """Action-batch acceptance acknowledgement."""

    accepted: bool


class StepRequest(StrictModel):
    """Number of one-second simulator ticks to execute."""

    n_steps: int = Field(default=1, ge=1)


class StepResponse(StrictModel):
    """Simulator time and terminal state after stepping."""

    sim_time: float
    done: bool


class MetricsResponse(StrictModel):
    """Cumulative Section 8.1 metrics for a session."""

    avg_travel_time: float
    avg_wait_time: float
    throughput: float
    fairness_index: float
    co2_kg: float
    fuel_l: float
    max_queue_length: int


class VehicleResponse(StrictModel):
    """Raw vehicle state intended for external visualization."""

    vehicle_id: str
    x: float
    y: float
    speed: float
    type: Literal["AV", "HUMAN"]


class SignalStreamState(StrictModel):
    """Traffic-signal state included in a stream frame."""

    intersection_id: str
    current_phase_id: int
    seconds_until_change: float


class StreamRewards(StrictModel):
    """Active rewards split by policy role."""

    av: dict[str, float]
    signal: dict[str, float]
    region: dict[str, float]


class StreamFrame(StrictModel):
    """One read-only WebSocket state frame."""

    sim_time: float
    vehicles: list[VehicleResponse]
    signals: list[SignalStreamState]
    active_agent_rewards: StreamRewards
