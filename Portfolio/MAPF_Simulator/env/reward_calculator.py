"""Multi-objective reward formulas defined in Section 5."""

from __future__ import annotations

from typing import Mapping


def jains_fairness(values: list[float]) -> float:
    """Compute the fixed Jain fairness formula, with all-zero waits treated as fair."""
    if not values or all(value == 0.0 for value in values):
        return 1.0
    return sum(values) ** 2 / (len(values) * sum(value * value for value in values))


def calculate_av_reward(
    *,
    ego_speed: float,
    target_speed: float,
    acceleration: float,
    co2_emission: float,
    local_signal_reward: float,
    weights: Mapping[str, float],
    harsh_braking_threshold: float,
    include_global_shared: bool = True,
) -> float:
    """Calculate the exact Section 5.1 AV weighted reward."""
    progress = ego_speed / target_speed if target_speed > 0 else 0.0
    harsh_braking = abs(acceleration) if acceleration < harsh_braking_threshold else 0.0
    shared = local_signal_reward if include_global_shared else 0.0
    return (
        weights["av_progress"] * progress
        - weights["av_harsh_braking"] * harsh_braking
        - weights["av_co2"] * max(0.0, co2_emission)
        + weights["av_global_shared"] * shared
    )


def calculate_signal_reward(
    *,
    throughput: float,
    wait_time_increase: float,
    approach_wait_times: list[float],
    emissions: float,
    region_alignment_bonus: float,
    weights: Mapping[str, float],
    include_region_alignment: bool = True,
) -> float:
    """Calculate the exact Section 5.2 local-signal reward."""
    fairness_penalty = 1.0 - jains_fairness(approach_wait_times)
    alignment = region_alignment_bonus if include_region_alignment else 0.0
    return (
        weights["signal_throughput"] * throughput
        - weights["signal_wait_time"] * wait_time_increase
        - weights["signal_fairness"] * fairness_penalty
        - weights["signal_emissions"] * max(0.0, emissions)
        + weights["signal_region_alignment"] * alignment
    )


def calculate_region_reward(
    *,
    total_throughput: float,
    member_wait_times: list[float],
    mean_emissions: float,
    weights: Mapping[str, float],
) -> float:
    """Calculate the exact Section 5.3 regional reward."""
    mean_wait = sum(member_wait_times) / len(member_wait_times) if member_wait_times else 0.0
    fairness_penalty = 1.0 - jains_fairness(member_wait_times)
    return (
        weights["region_throughput"] * total_throughput
        - weights["region_wait_time"] * mean_wait
        - weights["region_fairness"] * fairness_penalty
        - weights["region_emissions"] * max(0.0, mean_emissions)
    )
