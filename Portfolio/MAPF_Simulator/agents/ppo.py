"""From-scratch clipped PPO update for the shared AV policy."""

from __future__ import annotations

import torch

from agents.networks import AVPolicyValueNetwork, SignalPolicyValueNetwork
from agents.rollout_buffer import RolloutBatch


class PPOTrainer:
    """CPU-friendly clipped-objective PPO trainer."""

    def __init__(self, network: AVPolicyValueNetwork, config: dict[str, float | int]) -> None:
        """Initialize optimizer and tunable PPO coefficients."""
        self.network = network
        self.config = config
        self.optimizer = torch.optim.Adam(network.parameters(), lr=float(config["learning_rate"]))

    def act(self, observation: list[float]) -> tuple[list[float], float, float]:
        """Sample one action and return action, joint log probability, and value."""
        with torch.no_grad():
            distribution, value = self.network(torch.tensor([observation], dtype=torch.float32))
            action = distribution.sample()
            log_probability = distribution.log_prob(action).sum(-1)
        return action[0].tolist(), float(log_probability.item()), float(value.item())

    def value(self, observation: list[float]) -> float:
        """Evaluate the critic for rollout-boundary GAE bootstrapping."""
        with torch.no_grad():
            _, value = self.network(torch.tensor([observation], dtype=torch.float32))
        return float(value.item())

    def update(self, batch: RolloutBatch) -> dict[str, float]:
        """Run configured epochs of the PPO clipped surrogate update."""
        sample_count = int(batch.observations.shape[0])
        minibatch_size = min(int(self.config["minibatch_size"]), sample_count)
        losses: list[float] = []
        for _ in range(int(self.config["update_epochs"])):
            for indices in torch.randperm(sample_count).split(minibatch_size):
                distribution, values = self.network(batch.observations[indices])
                log_probabilities = distribution.log_prob(batch.actions[indices]).sum(-1)
                ratio = (log_probabilities - batch.old_log_probabilities[indices]).exp()
                clipped = ratio.clamp(
                    1.0 - float(self.config["clip_epsilon"]),
                    1.0 + float(self.config["clip_epsilon"]),
                )
                policy_loss = -torch.min(
                    ratio * batch.advantages[indices],
                    clipped * batch.advantages[indices],
                ).mean()
                value_loss = (batch.returns[indices] - values).pow(2).mean()
                entropy = distribution.entropy().sum(-1).mean()
                loss = (
                    policy_loss
                    + float(self.config["value_coefficient"]) * value_loss
                    - float(self.config["entropy_coefficient"]) * entropy
                )
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.network.parameters(), float(self.config["max_gradient_norm"])
                )
                self.optimizer.step()
                losses.append(float(loss.detach().item()))
        return {"loss": sum(losses) / len(losses)}


class SignalPPOTrainer:
    """Clipped PPO trainer for the shared categorical signal policy."""

    def __init__(self, network: SignalPolicyValueNetwork, config: dict[str, float | int]) -> None:
        """Initialize the categorical policy optimizer."""
        self.network = network
        self.config = config
        self.optimizer = torch.optim.Adam(network.parameters(), lr=float(config["learning_rate"]))

    def act(self, observation: list[float]) -> tuple[int, float, float]:
        """Sample extend/switch and return action, log probability, and value."""
        with torch.no_grad():
            distribution, value = self.network(torch.tensor([observation], dtype=torch.float32))
            action = distribution.sample()
        return int(action.item()), float(distribution.log_prob(action).item()), float(value.item())

    def value(self, observation: list[float]) -> float:
        """Evaluate the signal critic for rollout-boundary GAE bootstrapping."""
        with torch.no_grad():
            _, value = self.network(torch.tensor([observation], dtype=torch.float32))
        return float(value.item())

    def update(self, batch: RolloutBatch) -> dict[str, float]:
        """Apply configured epochs of minibatched categorical clipped PPO."""
        sample_count = int(batch.observations.shape[0])
        minibatch_size = min(int(self.config["minibatch_size"]), sample_count)
        losses: list[float] = []
        for _ in range(int(self.config["update_epochs"])):
            for indices in torch.randperm(sample_count).split(minibatch_size):
                distribution, values = self.network(batch.observations[indices])
                logs = distribution.log_prob(batch.actions[indices])
                ratio = (logs - batch.old_log_probabilities[indices]).exp()
                clipped = ratio.clamp(
                    1.0 - float(self.config["clip_epsilon"]),
                    1.0 + float(self.config["clip_epsilon"]),
                )
                policy_loss = -torch.min(
                    ratio * batch.advantages[indices],
                    clipped * batch.advantages[indices],
                ).mean()
                value_loss = (batch.returns[indices] - values).pow(2).mean()
                entropy = distribution.entropy().mean()
                loss = policy_loss + float(self.config["value_coefficient"]) * value_loss - float(
                    self.config["entropy_coefficient"]
                ) * entropy
                self.optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.network.parameters(), float(self.config["max_gradient_norm"])
                )
                self.optimizer.step()
                losses.append(float(loss.detach().item()))
        return {"loss": sum(losses) / len(losses)}
