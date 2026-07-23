"""Lightweight on-policy transition storage for PPO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch


@dataclass
class RolloutBatch:
    """Tensor batch consumed by a PPO update."""

    observations: torch.Tensor
    actions: torch.Tensor
    old_log_probabilities: torch.Tensor
    returns: torch.Tensor
    advantages: torch.Tensor


class RolloutBuffer:
    """Store flattened shared-policy AV transitions for one rollout."""

    def __init__(self) -> None:
        """Create empty transition lists."""
        self.observations: list[list[float]] = []
        self.agent_ids: list[str] = []
        self.actions: list[list[float] | int] = []
        self.log_probabilities: list[float] = []
        self.rewards: list[float] = []
        self.values: list[float] = []
        self.dones: list[bool] = []

    def add(
        self,
        agent_id: str,
        observation: list[float],
        action: list[float] | int,
        log_probability: float,
        reward: float,
        value: float,
        done: bool = False,
    ) -> None:
        """Append one transition."""
        self.agent_ids.append(agent_id)
        self.observations.append(observation)
        self.actions.append(action)
        self.log_probabilities.append(log_probability)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)

    def as_batch(
        self,
        gamma: float,
        gae_lambda: float,
        bootstrap_values: Mapping[str, float] | None = None,
        *,
        discrete_actions: bool = False,
    ) -> RolloutBatch:
        """Compute per-agent generalized advantages and returns for a pooled role batch."""
        advantages = [0.0] * len(self.rewards)
        next_values = dict(bootstrap_values or {})
        next_advantages: dict[str, float] = {}
        for index in range(len(self.rewards) - 1, -1, -1):
            agent_id = self.agent_ids[index]
            continuation = 0.0 if self.dones[index] else 1.0
            delta = (
                self.rewards[index]
                + gamma * continuation * next_values.get(agent_id, 0.0)
                - self.values[index]
            )
            advantage = delta + (
                gamma
                * gae_lambda
                * continuation
                * next_advantages.get(agent_id, 0.0)
            )
            advantages[index] = advantage
            next_values[agent_id] = self.values[index]
            next_advantages[agent_id] = advantage
        value_tensor = torch.tensor(self.values, dtype=torch.float32)
        advantage_tensor = torch.tensor(advantages, dtype=torch.float32)
        return_tensor = advantage_tensor + value_tensor
        normalized_advantages = (advantage_tensor - advantage_tensor.mean()) / (
            advantage_tensor.std(unbiased=False) + 1e-8
        )
        return RolloutBatch(
            observations=torch.tensor(self.observations, dtype=torch.float32),
            actions=torch.tensor(
                self.actions,
                dtype=torch.int64 if discrete_actions else torch.float32,
            ),
            old_log_probabilities=torch.tensor(self.log_probabilities, dtype=torch.float32),
            returns=return_tensor,
            advantages=normalized_advantages,
        )
