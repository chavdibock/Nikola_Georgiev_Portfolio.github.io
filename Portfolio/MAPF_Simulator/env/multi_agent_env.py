"""Milestone-staged PettingZoo-style parallel SUMO environment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from env.observation_builder import build_av_observation
from env.reward_calculator import calculate_av_reward
from env.traci_wrapper import DEFAULT_CONFIG, TraciConnection


ROOT = Path(__file__).resolve().parents[1]


class AVOnlyParallelEnv:
    """M4 parallel environment containing only learned AV agents."""

    def __init__(self, scenario: str = "surge", config_path: Path = DEFAULT_CONFIG) -> None:
        """Configure an AV-only episode against fixed-time traffic lights."""
        self.scenario = scenario
        self.config_path = config_path.resolve()
        with self.config_path.open("r", encoding="utf-8") as stream:
            self.config: dict[str, Any] = json.load(stream)
        self.connection: TraciConnection | None = None

    @property
    def agents(self) -> list[str]:
        """Return currently active AV identifiers only."""
        if self.connection is None or not self.connection.is_connected:
            return []
        return [
            vehicle_id
            for vehicle_id in self.connection.api.vehicle.getIDList()
            if self.connection.api.vehicle.getTypeID(vehicle_id) == "AV"
        ]

    def reset(self) -> dict[str, list[float]]:
        """Start a fresh SUMO session and return active AV observations."""
        self.close()
        self.connection = TraciConnection(ROOT / "demand" / f"{self.scenario}.sumocfg", self.config_path)
        self.connection.start()
        return self._observations()

    def step(
        self, actions: Mapping[str, list[float] | tuple[float, float]]
    ) -> tuple[
        dict[str, list[float]], dict[str, float], dict[str, bool], dict[str, bool], dict[str, dict[str, Any]]
    ]:
        """Apply bounded AV actions, advance one second, and return parallel dictionaries."""
        connection = self._require_connection()
        av_config = self.config["av"]
        prior_agents = set(self.agents)
        for vehicle_id, action in actions.items():
            if vehicle_id not in prior_agents:
                continue
            acceleration = max(
                float(av_config["min_acceleration_mps2"]),
                min(float(av_config["max_acceleration_mps2"]), float(action[0])),
            )
            connection.api.vehicle.setAcceleration(
                vehicle_id, acceleration, float(self.config["simulation"]["step_length_s"])
            )
            lane_intent = max(-1.0, min(1.0, float(action[1])))
            offset = -1 if lane_intent < -float(av_config["lane_change_threshold"]) else (
                1 if lane_intent > float(av_config["lane_change_threshold"]) else 0
            )
            lane_index = int(connection.api.vehicle.getLaneIndex(vehicle_id))
            road_id = connection.api.vehicle.getRoadID(vehicle_id)
            lane_count = int(connection.api.edge.getLaneNumber(road_id))
            target_lane_id = f"{road_id}_{lane_index + offset}"
            best_lanes = connection.api.vehicle.getBestLanes(vehicle_id)
            target_continues = any(
                lane_data[0] == target_lane_id and bool(lane_data[4])
                for lane_data in best_lanes
            )
            current_lane_id = connection.api.vehicle.getLaneID(vehicle_id)
            best_offset = next(
                (int(lane_data[3]) for lane_data in best_lanes if lane_data[0] == current_lane_id),
                0,
            )
            remaining_lane = (
                float(connection.api.lane.getLength(current_lane_id))
                - float(connection.api.vehicle.getLanePosition(vehicle_id))
            )
            maneuver_clearance = max(
                float(self.config["demand"]["vehicle_length_m"])
                + float(self.config["demand"]["vehicle_min_gap_m"]),
                float(connection.api.vehicle.getSpeed(vehicle_id))
                * float(av_config["lane_change_duration_s"]),
            )
            if (
                offset
                and 0 <= lane_index + offset < lane_count
                and connection.api.vehicle.couldChangeLane(vehicle_id, offset)
                and target_continues
                and best_offset * offset > 0
                and remaining_lane > maneuver_clearance
            ):
                try:
                    connection.api.vehicle.changeLaneRelative(
                        vehicle_id, offset, float(av_config["lane_change_duration_s"])
                    )
                except Exception:
                    pass
        connection.step()
        current_agents = set(self.agents)
        rewards = {
            vehicle_id: calculate_av_reward(
                ego_speed=float(connection.api.vehicle.getSpeed(vehicle_id)),
                target_speed=float(av_config["target_speed_mps"]),
                acceleration=float(connection.api.vehicle.getAcceleration(vehicle_id)),
                co2_emission=(
                    max(0.0, float(connection.api.vehicle.getCO2Emission(vehicle_id)))
                    * float(self.config["simulation"]["step_length_s"])
                    / 1000.0
                ),
                local_signal_reward=0.0,
                weights=self.config["reward_weights"],
                harsh_braking_threshold=float(av_config["harsh_braking_threshold_mps2"]),
                include_global_shared=False,
            )
            for vehicle_id in current_agents
        }
        done = connection.api.simulation.getMinExpectedNumber() == 0
        terminations = {vehicle_id: done for vehicle_id in current_agents}
        truncations = {vehicle_id: False for vehicle_id in current_agents}
        infos = {vehicle_id: {} for vehicle_id in current_agents}
        return self._observations(), rewards, terminations, truncations, infos

    def close(self) -> None:
        """Close the active SUMO episode, if any."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _observations(self) -> dict[str, list[float]]:
        """Build observations only for currently active AVs."""
        connection = self._require_connection()
        av_config = self.config["av"]
        baseline = self.config["baseline"]
        max_cycle = 4.0 * (
            float(baseline["green_s"]) + float(baseline["yellow_s"]) + float(baseline["all_red_s"])
        )
        return {
            vehicle_id: build_av_observation(
                connection.api,
                vehicle_id,
                leader_sensor_range_m=float(av_config["leader_sensor_range_m"]),
                communication_radius_m=float(
                    self.config["simulation"]["communication_radius_m"]
                ),
                max_signal_cycle_s=max_cycle,
            )
            for vehicle_id in self.agents
        }

    def _require_connection(self) -> TraciConnection:
        """Return the started connection or raise a lifecycle error."""
        if self.connection is None or not self.connection.is_connected:
            raise RuntimeError("Call reset() before using the environment")
        return self.connection
