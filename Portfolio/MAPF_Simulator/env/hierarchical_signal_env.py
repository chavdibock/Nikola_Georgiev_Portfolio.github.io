"""M6 two-tier local-signal and regional-coordinator environment."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from env.communication import SignalStatsMessage
from env.observation_builder import build_region_observation
from env.reward_calculator import calculate_region_reward
from env.signal_env import SignalOnlyParallelEnv
from env.traci_wrapper import DEFAULT_CONFIG


REGION_MEMBERS: dict[str, tuple[str, str, str, str]] = {
    "region_0": ("A2", "A3", "B2", "B3"),
    "region_1": ("C2", "C3", "D2", "D3"),
    "region_2": ("A0", "A1", "B0", "B1"),
    "region_3": ("C0", "C1", "D0", "D1"),
}


class HierarchicalSignalParallelEnv:
    """Add four fixed-size regional coordinators to M5 local signals."""

    def __init__(
        self,
        scenario: str = "surge",
        *,
        config_path: Path = DEFAULT_CONFIG,
        sumo_config_path: Path | None = None,
        include_av_messages: bool = False,
        use_gui: bool | None = None,
        sumo_extra_args: tuple[str, ...] = (),
    ) -> None:
        """Configure the hierarchical signal-only environment."""
        self.local = SignalOnlyParallelEnv(
            scenario,
            config_path,
            sumo_config_path=sumo_config_path,
            enable_region_alignment=True,
            include_av_messages=include_av_messages,
            use_gui=use_gui,
            sumo_extra_args=sumo_extra_args,
        )

    @property
    def connection(self) -> Any:
        """Expose the owned connection for smoke-test inspection."""
        return self.local.connection

    def reset(self) -> dict[str, list[float]]:
        """Start the local environment and include the initial regional boundary."""
        local_observations = self.local.reset()
        return {**local_observations, **self._region_observations()}

    def step(
        self, actions: Mapping[str, int | Sequence[float]]
    ) -> tuple[
        dict[str, list[float]], dict[str, float], dict[str, bool], dict[str, bool], dict[str, dict[str, Any]]
    ]:
        """Apply region priorities and local actions on their independent clocks."""
        if self.local.connection is None:
            raise RuntimeError("Call reset() first")
        if int(self.local.connection.simulation_time_s) % int(
            self.local.config["simulation"]["regional_decision_interval_s"]
        ) == 0:
            for region_id, members in REGION_MEMBERS.items():
                if region_id in actions:
                    priorities = list(actions[region_id])  # type: ignore[arg-type]
                    if len(priorities) != 4:
                        raise ValueError("Regional action must have four priorities")
                    for member, priority in zip(members, priorities):
                        self.local.region_priorities[member] = max(0.0, min(1.0, float(priority)))
        local_actions = {
            agent_id: int(action)
            for agent_id, action in actions.items()
            if agent_id in self.local.signal_ids
        }
        observations, rewards, terminations, truncations, infos = self.local.step(local_actions)
        if int(self.local.connection.simulation_time_s) % int(
            self.local.config["simulation"]["regional_decision_interval_s"]
        ) == 0:
            region_observations = self._region_observations()
            region_rewards = self._region_rewards()
            observations.update(region_observations)
            rewards.update(region_rewards)
            done = self.local.connection.api.simulation.getMinExpectedNumber() == 0
            terminations.update({region_id: done for region_id in region_observations})
            truncations.update({region_id: False for region_id in region_observations})
            infos.update({region_id: {} for region_id in region_observations})
        return observations, rewards, terminations, truncations, infos

    def close(self) -> None:
        """Close the underlying local SUMO environment."""
        self.local.close()

    def _member_values(self, members: Sequence[str]) -> tuple[list[float], list[float]]:
        """Return per-member total queues and interval-average waits via Channel B."""
        messages = self._signal_stats(members)
        return (
            [sum(message.queue_length_per_approach) for message in messages],
            [message.avg_wait_time_last_interval for message in messages],
        )

    def _signal_stats(self, members: Sequence[str]) -> list[SignalStatsMessage]:
        """Build the four fixed-size local-to-region Channel B messages."""
        messages: list[SignalStatsMessage] = []
        for signal_id in members:
            approach_queues, _, _, _ = self.local._approach_values(signal_id)
            wait_samples = self.local.regional_wait_samples[signal_id]
            emission_samples = self.local.regional_emission_samples[signal_id]
            messages.append(
                SignalStatsMessage(
                    intersection_id=self.local.signal_ids.index(signal_id),
                    queue_length_per_approach=tuple(approach_queues),  # type: ignore[arg-type]
                    avg_wait_time_last_interval=(
                        self.local.regional_wait_sum[signal_id] / wait_samples
                        if wait_samples else 0.0
                    ),
                    throughput_last_interval=self.local.regional_throughput[signal_id],
                    avg_emissions_last_interval=(
                        self.local.regional_emissions[signal_id] / emission_samples
                        if emission_samples else 0.0
                    ),
                )
            )
        return messages

    def _region_observations(self) -> dict[str, list[float]]:
        """Aggregate four bounded member messages into each regional observation."""
        observations: dict[str, list[float]] = {}
        for index, (region_id, members) in enumerate(REGION_MEMBERS.items()):
            messages = self._signal_stats(members)
            queues = [sum(message.queue_length_per_approach) for message in messages]
            waits = [message.avg_wait_time_last_interval for message in messages]
            mean_queue = sum(queues) / 4.0
            variance = sum((queue - mean_queue) ** 2 for queue in queues) / 4.0
            emissions = [message.avg_emissions_last_interval for message in messages]
            observations[region_id] = build_region_observation(
                mean_queue=mean_queue,
                max_queue=max(queues),
                mean_wait=sum(waits) / 4.0,
                total_throughput=float(
                    sum(message.throughput_last_interval for message in messages)
                ),
                mean_emissions=sum(emissions) / 4.0,
                queue_stddev=math.sqrt(variance),
                region_index=index,
            )
        return observations

    def _region_rewards(self) -> dict[str, float]:
        """Compute Section 5.3 rewards and reset 60-second regional accumulators."""
        rewards: dict[str, float] = {}
        for region_id, members in REGION_MEMBERS.items():
            messages = self._signal_stats(members)
            waits = [message.avg_wait_time_last_interval for message in messages]
            throughput = sum(message.throughput_last_interval for message in messages)
            emissions = [message.avg_emissions_last_interval for message in messages]
            rewards[region_id] = calculate_region_reward(
                total_throughput=float(throughput),
                member_wait_times=waits,
                mean_emissions=sum(emissions) / 4.0,
                weights=self.local.config["reward_weights"],
            )
            for member in members:
                self.local.regional_throughput[member] = 0
                self.local.regional_emissions[member] = 0.0
                self.local.regional_emission_samples[member] = 0
                self.local.regional_wait_sum[member] = 0.0
                self.local.regional_wait_samples[member] = 0
        return rewards
