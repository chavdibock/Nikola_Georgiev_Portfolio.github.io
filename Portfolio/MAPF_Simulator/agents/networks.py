"""Small CPU-friendly policy/value networks."""

from __future__ import annotations

from typing import Sequence

import torch
from torch import nn


class AVPolicyValueNetwork(nn.Module):
    """Shared Gaussian AV actor and scalar critic with two 64-unit layers."""

    def __init__(self, observation_size: int, hidden_sizes: Sequence[int] = (64, 64)) -> None:
        """Construct shared features and separate policy/value heads."""
        super().__init__()
        layers: list[nn.Module] = []
        size = observation_size
        for hidden_size in hidden_sizes:
            layers.extend((nn.Linear(size, hidden_size), nn.ReLU()))
            size = hidden_size
        self.features = nn.Sequential(*layers)
        self.action_mean = nn.Linear(size, 2)
        self.action_log_std = nn.Parameter(torch.zeros(2))
        self.value_head = nn.Linear(size, 1)

    def forward(self, observations: torch.Tensor) -> tuple[torch.distributions.Normal, torch.Tensor]:
        """Return the diagonal Gaussian policy distribution and values."""
        features = self.features(observations)
        mean = self.action_mean(features)
        standard_deviation = self.action_log_std.exp().expand_as(mean)
        return torch.distributions.Normal(mean, standard_deviation), self.value_head(features).squeeze(-1)


class SignalPolicyValueNetwork(nn.Module):
    """Shared categorical local-signal actor and scalar critic."""

    def __init__(self, observation_size: int, hidden_sizes: Sequence[int] = (64, 64)) -> None:
        """Construct the specified two-layer local-signal network."""
        super().__init__()
        layers: list[nn.Module] = []
        size = observation_size
        for hidden_size in hidden_sizes:
            layers.extend((nn.Linear(size, hidden_size), nn.ReLU()))
            size = hidden_size
        self.features = nn.Sequential(*layers)
        self.action_logits = nn.Linear(size, 2)
        self.value_head = nn.Linear(size, 1)

    def forward(
        self, observations: torch.Tensor
    ) -> tuple[torch.distributions.Categorical, torch.Tensor]:
        """Return extend/switch distribution and values."""
        features = self.features(observations)
        return (
            torch.distributions.Categorical(logits=self.action_logits(features)),
            self.value_head(features).squeeze(-1),
        )


class RegionalPolicyValueNetwork(nn.Module):
    """Shared Beta-distribution regional actor and scalar critic."""

    def __init__(self, observation_size: int, hidden_sizes: Sequence[int] = (64, 64)) -> None:
        """Construct the specified two-layer four-priority policy."""
        super().__init__()
        layers: list[nn.Module] = []
        size = observation_size
        for hidden_size in hidden_sizes:
            layers.extend((nn.Linear(size, hidden_size), nn.ReLU()))
            size = hidden_size
        self.features = nn.Sequential(*layers)
        self.alpha_head = nn.Linear(size, 4)
        self.beta_head = nn.Linear(size, 4)
        self.value_head = nn.Linear(size, 1)

    def forward(self, observations: torch.Tensor) -> tuple[torch.distributions.Beta, torch.Tensor]:
        """Return bounded Beta priority distributions and values."""
        features = self.features(observations)
        alpha = torch.nn.functional.softplus(self.alpha_head(features)) + 1.0
        beta = torch.nn.functional.softplus(self.beta_head(features)) + 1.0
        return torch.distributions.Beta(alpha, beta), self.value_head(features).squeeze(-1)
