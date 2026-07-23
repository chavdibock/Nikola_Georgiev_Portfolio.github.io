"""Bounded AV-signal and signal-region message aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


APPROACH_COUNT = 4


@dataclass(frozen=True)
class IntentMessage:
    """One AV intent payload before fixed-size aggregation."""

    vehicle_id: str
    approach_id: int
    distance_to_stopline: float
    current_speed: float


@dataclass(frozen=True)
class ApproachFeatures:
    """Fixed-size aggregate for one intersection approach."""

    av_count: int = 0
    av_mean_distance: float = 0.0
    av_mean_speed: float = 0.0
    human_count: int = 0
    human_mean_speed: float = 0.0


@dataclass(frozen=True)
class SignalStatsMessage:
    """Fixed-size local-to-region interval message."""

    intersection_id: int
    queue_length_per_approach: tuple[float, float, float, float]
    avg_wait_time_last_interval: float
    throughput_last_interval: int
    avg_emissions_last_interval: float


@dataclass(frozen=True)
class SignalStateMessage:
    """Fixed signal-to-AV Channel A payload."""

    intersection_id: int
    current_phase_id: int
    seconds_until_phase_change: float
    next_phase_id: int


def aggregate_approaches(
    av_messages: Iterable[IntentMessage],
    human_samples: Iterable[tuple[int, float]],
) -> tuple[ApproachFeatures, ApproachFeatures, ApproachFeatures, ApproachFeatures]:
    """Aggregate arbitrary vehicle populations into exactly four approach records."""
    av_buckets: list[list[IntentMessage]] = [[] for _ in range(APPROACH_COUNT)]
    human_buckets: list[list[float]] = [[] for _ in range(APPROACH_COUNT)]
    for message in av_messages:
        if not 0 <= message.approach_id < APPROACH_COUNT:
            raise ValueError("approach_id must be in [0, 3]")
        av_buckets[message.approach_id].append(message)
    for approach_id, speed in human_samples:
        if not 0 <= approach_id < APPROACH_COUNT:
            raise ValueError("approach_id must be in [0, 3]")
        human_buckets[approach_id].append(speed)
    aggregates = []
    for approach_id in range(APPROACH_COUNT):
        avs = av_buckets[approach_id]
        humans = human_buckets[approach_id]
        aggregates.append(
            ApproachFeatures(
                av_count=len(avs),
                av_mean_distance=sum(item.distance_to_stopline for item in avs) / len(avs) if avs else 0.0,
                av_mean_speed=sum(item.current_speed for item in avs) / len(avs) if avs else 0.0,
                human_count=len(humans),
                human_mean_speed=sum(humans) / len(humans) if humans else 0.0,
            )
        )
    return tuple(aggregates)  # type: ignore[return-value]
