"""M5 local-signal-only parallel environment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from baseline.run_baseline import ensure_human_baseline_demand
from env.observation_builder import build_signal_observation
from env.communication import IntentMessage, aggregate_approaches
from env.reward_calculator import calculate_signal_reward
from env.traci_wrapper import DEFAULT_CONFIG, TraciConnection


ROOT = Path(__file__).resolve().parents[1]


class SignalOnlyParallelEnv:
    """Control 16 shared-policy signals against default human-like traffic."""

    def __init__(
        self,
        scenario: str = "surge",
        config_path: Path = DEFAULT_CONFIG,
        *,
        sumo_config_path: Path | None = None,
        enable_region_alignment: bool = False,
        include_av_messages: bool = False,
        use_gui: bool | None = None,
        sumo_extra_args: tuple[str, ...] = (),
    ) -> None:
        """Configure an isolated local-signal experiment with no learned AV controller."""
        self.scenario = scenario
        self.config_path = config_path.resolve()
        self.sumo_config_path = sumo_config_path.resolve() if sumo_config_path else None
        self.config: dict[str, Any] = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.connection: TraciConnection | None = None
        self.enable_region_alignment = enable_region_alignment
        self.include_av_messages = include_av_messages
        self.use_gui = use_gui
        self.sumo_extra_args = sumo_extra_args
        self.signal_ids: list[str] = []
        self._approach_lanes: dict[str, tuple[list[str], list[str], list[str], list[str]]] = {}
        self._throughput: dict[str, int] = {}
        self._emissions: dict[str, float] = {}
        self._last_wait: dict[str, float] = {}
        self._previous_roads: dict[str, str] = {}
        self.region_priorities: dict[str, float] = {}
        self.last_actions: dict[str, int] = {}
        self.regional_throughput: dict[str, int] = {}
        self.regional_emissions: dict[str, float] = {}
        self.regional_emission_samples: dict[str, int] = {}
        self.regional_wait_sum: dict[str, float] = {}
        self.regional_wait_samples: dict[str, int] = {}
        self._incoming_edge_signal: dict[str, str] = {}

    @property
    def agents(self) -> list[str]:
        """Return signals active at the current five-second decision boundary."""
        if self.connection is None or not self.connection.is_connected:
            return []
        interval = int(self.config["signal"]["decision_interval_s"])
        if int(self.connection.simulation_time_s) % interval != 0:
            return []
        green_indices = set(int(value) for value in self.config["signal"]["logical_green_phase_indices"])
        return [
            signal_id
            for signal_id in self.signal_ids
            if int(self.connection.api.trafficlight.getPhase(signal_id)) in green_indices
        ]

    def reset(self) -> dict[str, list[float]]:
        """Start SUMO and return observations for the initial decision boundary."""
        self.close()
        sumo_config = self.sumo_config_path or (
            ROOT / "demand" / f"{self.scenario}.sumocfg"
            if self.include_av_messages
            else ensure_human_baseline_demand(self.scenario, self.config_path)
        )
        self.connection = TraciConnection(
            sumo_config,
            self.config_path,
            use_gui=self.use_gui,
            extra_args=self.sumo_extra_args,
        )
        self.connection.start()
        self.signal_ids = sorted(self.connection.api.trafficlight.getIDList())
        self._approach_lanes = {
            signal_id: self._classify_approach_lanes(signal_id) for signal_id in self.signal_ids
        }
        self._throughput = {signal_id: 0 for signal_id in self.signal_ids}
        self._emissions = {signal_id: 0.0 for signal_id in self.signal_ids}
        self._last_wait = {signal_id: 0.0 for signal_id in self.signal_ids}
        self._previous_roads = {}
        self.region_priorities = {signal_id: 0.5 for signal_id in self.signal_ids}
        self.last_actions = {signal_id: 0 for signal_id in self.signal_ids}
        self.regional_throughput = {signal_id: 0 for signal_id in self.signal_ids}
        self.regional_emissions = {signal_id: 0.0 for signal_id in self.signal_ids}
        self.regional_emission_samples = {signal_id: 0 for signal_id in self.signal_ids}
        self.regional_wait_sum = {signal_id: 0.0 for signal_id in self.signal_ids}
        self.regional_wait_samples = {signal_id: 0 for signal_id in self.signal_ids}
        self._incoming_edge_signal = {
            self.connection.api.lane.getEdgeID(lane_id): signal_id
            for signal_id in self.signal_ids
            for lanes in self._approach_lanes[signal_id]
            for lane_id in lanes
        }
        return self._observations()

    def step(
        self, actions: Mapping[str, int]
    ) -> tuple[
        dict[str, list[float]], dict[str, float], dict[str, bool], dict[str, bool], dict[str, dict[str, Any]]
    ]:
        """Apply local actions, advance one tick, and emit only boundary-active agents."""
        connection = self._require_connection()
        for signal_id, action in actions.items():
            if signal_id in self.agents:
                self._apply_action(signal_id, int(action))
        before = {
            vehicle_id: str(connection.api.vehicle.getRoadID(vehicle_id))
            for vehicle_id in connection.api.vehicle.getIDList()
        }
        connection.step()
        self._accumulate_interval_stats(before)
        active = self.agents
        rewards = {signal_id: self._reward(signal_id) for signal_id in active}
        observations = self._observations()
        done = connection.api.simulation.getMinExpectedNumber() == 0
        return (
            observations,
            {signal_id: rewards[signal_id] for signal_id in observations},
            {signal_id: done for signal_id in observations},
            {signal_id: False for signal_id in observations},
            {signal_id: {} for signal_id in observations},
        )

    def close(self) -> None:
        """Close the active SUMO session."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _classify_approach_lanes(
        self, signal_id: str
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Group controlled incoming lanes into fixed N/S/W/E approach slots."""
        connection = self._require_connection()
        groups: list[list[str]] = [[] for _ in range(4)]
        for lane_id in sorted(set(connection.api.trafficlight.getControlledLanes(signal_id))):
            shape = connection.api.lane.getShape(lane_id)
            if len(shape) < 2:
                continue
            dx = shape[-1][0] - shape[0][0]
            dy = shape[-1][1] - shape[0][1]
            approach = (1 if dy > 0 else 0) if abs(dy) >= abs(dx) else (2 if dx > 0 else 3)
            groups[approach].append(lane_id)
        return tuple(groups)  # type: ignore[return-value]

    def _apply_action(self, signal_id: str, action: int) -> None:
        """Apply extend/switch while respecting configured minimum and maximum green."""
        if action not in (0, 1):
            raise ValueError("Signal action must be 0 (extend) or 1 (switch)")
        connection = self._require_connection()
        self.last_actions[signal_id] = action
        signal_config = self.config["signal"]
        spent = float(connection.api.trafficlight.getSpentDuration(signal_id))
        if action == 0:
            remaining = max(
                0.0,
                float(connection.api.trafficlight.getNextSwitch(signal_id))
                - connection.simulation_time_s,
            )
            allowed = max(0.0, float(signal_config["maximum_green_s"]) - spent)
            connection.api.trafficlight.setPhaseDuration(
                signal_id, min(remaining + float(signal_config["extension_s"]), allowed)
            )
        elif spent >= float(signal_config["minimum_green_s"]):
            current = int(connection.api.trafficlight.getPhase(signal_id))
            phase_count = len(connection.api.trafficlight.getAllProgramLogics(signal_id)[0].phases)
            connection.api.trafficlight.setPhase(signal_id, (current + 1) % phase_count)

    def _accumulate_interval_stats(self, previous_roads: Mapping[str, str]) -> None:
        """Accumulate bounded per-intersection throughput and emissions statistics."""
        connection = self._require_connection()
        for vehicle_id in connection.api.vehicle.getIDList():
            road = str(connection.api.vehicle.getRoadID(vehicle_id))
            old_road = previous_roads.get(vehicle_id, road)
            previous_signal = self._incoming_edge_signal.get(old_road)
            if previous_signal is not None and road != old_road:
                self._throughput[previous_signal] += 1
                self.regional_throughput[previous_signal] += 1
            current_signal = self._incoming_edge_signal.get(road)
            if current_signal is not None:
                emission = (
                    max(0.0, float(connection.api.vehicle.getCO2Emission(vehicle_id)))
                    * float(self.config["simulation"]["step_length_s"])
                    / 1000.0
                )
                self._emissions[current_signal] += emission
                self.regional_emissions[current_signal] += emission
                self.regional_emission_samples[current_signal] += 1
        for signal_id in self.signal_ids:
            _, _, waits, _ = self._approach_values(signal_id)
            self.regional_wait_sum[signal_id] += sum(waits) / 4.0
            self.regional_wait_samples[signal_id] += 1
        self._previous_roads = dict(previous_roads)

    def _approach_values(self, signal_id: str) -> tuple[list[float], list[float], list[float], list[float]]:
        """Return queue, speed, wait, and count arrays for four approaches."""
        connection = self._require_connection()
        queues: list[float] = []
        speeds: list[float] = []
        waits: list[float] = []
        counts: list[float] = []
        for lanes in self._approach_lanes[signal_id]:
            vehicle_ids = [
                vehicle_id for lane in lanes for vehicle_id in connection.api.lane.getLastStepVehicleIDs(lane)
            ]
            vehicle_speeds = [float(connection.api.vehicle.getSpeed(item)) for item in vehicle_ids]
            vehicle_waits = [float(connection.api.vehicle.getWaitingTime(item)) for item in vehicle_ids]
            queues.append(float(sum(speed < self.config["metrics"]["queue_speed_threshold_mps"] for speed in vehicle_speeds)))
            speeds.append(sum(vehicle_speeds) / len(vehicle_speeds) if vehicle_speeds else 0.0)
            waits.append(sum(vehicle_waits) / len(vehicle_waits) if vehicle_waits else 0.0)
            counts.append(float(len(vehicle_ids)))
        return queues, speeds, waits, counts

    def _reward(self, signal_id: str) -> float:
        """Calculate and reset this signal's M5 interval reward terms."""
        _, _, waits, _ = self._approach_values(signal_id)
        total_wait = sum(waits)
        increase = max(0.0, total_wait - self._last_wait[signal_id])
        self._last_wait[signal_id] = total_wait
        reward = calculate_signal_reward(
            throughput=float(self._throughput[signal_id]),
            wait_time_increase=increase,
            approach_wait_times=waits,
            emissions=self._emissions[signal_id],
            region_alignment_bonus=float(
                (self.region_priorities[signal_id] >= 0.5 and self.last_actions[signal_id] == 0)
                or (self.region_priorities[signal_id] < 0.5 and self.last_actions[signal_id] == 1)
            ),
            weights=self.config["reward_weights"],
            include_region_alignment=self.enable_region_alignment,
        )
        self._throughput[signal_id] = 0
        self._emissions[signal_id] = 0.0
        return reward

    def _observations(self) -> dict[str, list[float]]:
        """Build observations only for signals at a valid decision boundary."""
        connection = self._require_connection()
        green_indices = [int(value) for value in self.config["signal"]["logical_green_phase_indices"]]
        observations: dict[str, list[float]] = {}
        for signal_id in self.agents:
            queues, speeds, _, counts = self._approach_values(signal_id)
            av_messages: list[IntentMessage] = []
            human_samples: list[tuple[int, float]] = []
            for approach_id, lanes in enumerate(self._approach_lanes[signal_id]):
                for lane_id in lanes:
                    lane_length = float(connection.api.lane.getLength(lane_id))
                    for vehicle_id in connection.api.lane.getLastStepVehicleIDs(lane_id):
                        speed = float(connection.api.vehicle.getSpeed(vehicle_id))
                        distance = max(
                            0.0,
                            lane_length - float(connection.api.vehicle.getLanePosition(vehicle_id)),
                        )
                        is_av = connection.api.vehicle.getTypeID(vehicle_id) == "AV"
                        if self.include_av_messages and is_av:
                            if distance <= float(
                                self.config["simulation"]["communication_radius_m"]
                            ):
                                av_messages.append(
                                    IntentMessage(vehicle_id, approach_id, distance, speed)
                                )
                        else:
                            human_samples.append((approach_id, speed))
            aggregates = aggregate_approaches(av_messages, human_samples)
            actual_phase = int(connection.api.trafficlight.getPhase(signal_id))
            observations[signal_id] = build_signal_observation(
                logical_phase=green_indices.index(actual_phase),
                seconds_in_phase=float(connection.api.trafficlight.getSpentDuration(signal_id)),
                queue_lengths=queues,
                average_speeds=speeds,
                av_counts=[float(item.av_count) for item in aggregates],
                av_mean_distances=[item.av_mean_distance for item in aggregates],
                av_mean_speeds=[item.av_mean_speed for item in aggregates],
                human_counts=[float(item.human_count) for item in aggregates],
                region_priority=self.region_priorities[signal_id] if self.enable_region_alignment else 0.0,
                intersection_index=self.signal_ids.index(signal_id),
            )
        return observations

    def _require_connection(self) -> TraciConnection:
        """Return the started connection or raise a lifecycle error."""
        if self.connection is None or not self.connection.is_connected:
            raise RuntimeError("Call reset() before using the environment")
        return self.connection
