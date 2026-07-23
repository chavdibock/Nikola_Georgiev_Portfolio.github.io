"""M7 full joint AV, local-signal, and regional parallel environment."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from env.hierarchical_signal_env import HierarchicalSignalParallelEnv
from env.observation_builder import build_av_observation
from env.reward_calculator import calculate_av_reward
from env.traci_wrapper import DEFAULT_CONFIG


class JointParallelEnv:
    """Run all three shared-policy roles in one multi-rate SUMO session."""

    def __init__(
        self,
        scenario: str = "surge",
        *,
        config_path: Path = DEFAULT_CONFIG,
        sumo_config_path: Path | None = None,
        use_gui: bool | None = None,
        sumo_extra_args: tuple[str, ...] = (),
    ) -> None:
        """Configure the joint environment with both communication channels active."""
        self.hierarchy = HierarchicalSignalParallelEnv(
            scenario,
            config_path=config_path,
            sumo_config_path=sumo_config_path,
            include_av_messages=True,
            use_gui=use_gui,
            sumo_extra_args=sumo_extra_args,
        )
        self.current_signal_rewards: dict[str, float] = {}
        self.signal_phase_counts: dict[str, int] = {}

    @property
    def connection(self) -> Any:
        """Expose the single connection owned by all roles."""
        return self.hierarchy.connection

    def reset(self) -> dict[str, list[float]]:
        """Start a joint episode and return agents active at time zero."""
        observations = self.hierarchy.reset()
        self.current_signal_rewards = {
            signal_id: 0.0 for signal_id in self.hierarchy.local.signal_ids
        }
        self.signal_phase_counts = {
            signal_id: len(
                self.connection.api.trafficlight.getAllProgramLogics(signal_id)[0].phases
            )
            for signal_id in self.hierarchy.local.signal_ids
        }
        observations.update(self._av_observations())
        return observations

    def step(
        self, actions: Mapping[str, int | Sequence[float]]
    ) -> tuple[
        dict[str, list[float]], dict[str, float], dict[str, bool], dict[str, bool], dict[str, dict[str, Any]]
    ]:
        """Apply all active-role actions, advance one tick, and compute full rewards."""
        connection = self.connection
        if connection is None:
            raise RuntimeError("Call reset() first")
        av_ids = set(self._av_ids())
        for vehicle_id in av_ids:
            if vehicle_id in actions:
                self._apply_av_action(vehicle_id, actions[vehicle_id])
        hierarchy_actions = {key: value for key, value in actions.items() if key not in av_ids}
        observations, rewards, terminations, truncations, infos = self.hierarchy.step(hierarchy_actions)
        self.current_signal_rewards = {
            signal_id: float(rewards.get(signal_id, 0.0))
            for signal_id in self.hierarchy.local.signal_ids
        }
        av_observations = self._av_observations()
        av_rewards = {vehicle_id: self._av_reward(vehicle_id) for vehicle_id in av_observations}
        observations.update(av_observations)
        rewards.update(av_rewards)
        done = connection.api.simulation.getMinExpectedNumber() == 0
        terminations.update({vehicle_id: done for vehicle_id in av_observations})
        truncations.update({vehicle_id: False for vehicle_id in av_observations})
        infos.update({vehicle_id: {} for vehicle_id in av_observations})
        return observations, rewards, terminations, truncations, infos

    def close(self) -> None:
        """Close the shared SUMO session."""
        self.hierarchy.close()

    def _av_ids(self) -> list[str]:
        """Return only currently active AV vehicles."""
        connection = self.connection
        if connection is None:
            return []
        return [
            vehicle_id
            for vehicle_id in connection.api.vehicle.getIDList()
            if connection.api.vehicle.getTypeID(vehicle_id) == "AV"
        ]

    def _apply_av_action(self, vehicle_id: str, action: int | Sequence[float]) -> None:
        """Clip acceleration and lane intent to the Section 3.1 bounds."""
        if isinstance(action, int):
            raise ValueError("AV action must contain acceleration and lane intent")
        values = list(action)
        if len(values) != 2:
            raise ValueError("AV action must have length two")
        connection = self.connection
        config = self.hierarchy.local.config
        av_config = config["av"]
        acceleration = max(
            float(av_config["min_acceleration_mps2"]),
            min(float(av_config["max_acceleration_mps2"]), float(values[0])),
        )
        connection.api.vehicle.setAcceleration(
            vehicle_id, acceleration, float(config["simulation"]["step_length_s"])
        )
        intent = max(-1.0, min(1.0, float(values[1])))
        threshold = float(av_config["lane_change_threshold"])
        offset = -1 if intent < -threshold else (1 if intent > threshold else 0)
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
            float(config["demand"]["vehicle_length_m"])
            + float(config["demand"]["vehicle_min_gap_m"]),
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

    def _av_observations(self) -> dict[str, list[float]]:
        """Build fixed-size observations for all and only active AVs."""
        connection = self.connection
        if connection is None:
            return {}
        config = self.hierarchy.local.config
        baseline = config["baseline"]
        max_cycle = 4.0 * (
            float(baseline["green_s"]) + float(baseline["yellow_s"]) + float(baseline["all_red_s"])
        )
        return {
            vehicle_id: build_av_observation(
                connection.api,
                vehicle_id,
                leader_sensor_range_m=float(config["av"]["leader_sensor_range_m"]),
                communication_radius_m=float(config["simulation"]["communication_radius_m"]),
                max_signal_cycle_s=max_cycle,
                signal_phase_counts=self.signal_phase_counts,
            )
            for vehicle_id in self._av_ids()
        }

    def _av_reward(self, vehicle_id: str) -> float:
        """Compute the full AV reward including its nearest signal's cached reward."""
        connection = self.connection
        config = self.hierarchy.local.config
        next_lights = connection.api.vehicle.getNextTLS(vehicle_id)
        signal_reward = (
            self.current_signal_rewards.get(next_lights[0][0], 0.0)
            if next_lights and float(next_lights[0][2]) <= float(
                config["simulation"]["communication_radius_m"]
            )
            else 0.0
        )
        return calculate_av_reward(
            ego_speed=float(connection.api.vehicle.getSpeed(vehicle_id)),
            target_speed=float(config["av"]["target_speed_mps"]),
            acceleration=float(connection.api.vehicle.getAcceleration(vehicle_id)),
            co2_emission=(
                max(0.0, float(connection.api.vehicle.getCO2Emission(vehicle_id)))
                * float(config["simulation"]["step_length_s"])
                / 1000.0
            ),
            local_signal_reward=signal_reward,
            weights=config["reward_weights"],
            harsh_braking_threshold=float(config["av"]["harsh_braking_threshold_mps2"]),
            include_global_shared=True,
        )
