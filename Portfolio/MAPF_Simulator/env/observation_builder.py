"""Fixed-size observation construction for decentralized agents."""

from __future__ import annotations

from typing import Any
from typing import Mapping

from env.communication import SignalStateMessage


AV_OBSERVATION_SIZE = 9
SIGNAL_OBSERVATION_SIZE = 46
REGION_OBSERVATION_SIZE = 10


def build_av_observation(
    traci_api: Any,
    vehicle_id: str,
    *,
    leader_sensor_range_m: float,
    communication_radius_m: float,
    max_signal_cycle_s: float,
    signal_phase_counts: Mapping[str, int] | None = None,
) -> list[float]:
    """Build the fixed nine-value Section 3.1 observation for one AV."""
    speed = float(traci_api.vehicle.getSpeed(vehicle_id))
    acceleration = float(traci_api.vehicle.getAcceleration(vehicle_id))
    leader = traci_api.vehicle.getLeader(vehicle_id, leader_sensor_range_m)
    leader_distance = float(leader[1]) if leader else -1.0
    leader_speed = float(traci_api.vehicle.getSpeed(leader[0])) if leader else 0.0
    lane_index = int(traci_api.vehicle.getLaneIndex(vehicle_id))
    lane_count = int(traci_api.edge.getLaneNumber(traci_api.vehicle.getRoadID(vehicle_id)))
    normalized_lane = lane_index / max(1, lane_count - 1)
    next_lights = traci_api.vehicle.getNextTLS(vehicle_id)
    if next_lights:
        signal_id, _, distance, _ = next_lights[0]
        stopline_distance = float(distance)
        if stopline_distance <= communication_radius_m:
            current_phase = int(traci_api.trafficlight.getPhase(signal_id))
            phase_count = (
                int(signal_phase_counts[signal_id])
                if signal_phase_counts is not None and signal_id in signal_phase_counts
                else max(1, len(traci_api.trafficlight.getAllProgramLogics(signal_id)[0].phases))
            )
            message = SignalStateMessage(
                intersection_id=sorted(traci_api.trafficlight.getIDList()).index(signal_id),
                current_phase_id=current_phase,
                seconds_until_phase_change=max(
                    0.0,
                    float(traci_api.trafficlight.getNextSwitch(signal_id))
                    - float(traci_api.simulation.getTime()),
                ),
                next_phase_id=(current_phase + 1) % phase_count,
            )
            phase_denominator = max(1, phase_count - 1)
            signal_values = [
                message.current_phase_id / phase_denominator,
                min(message.seconds_until_phase_change, max_signal_cycle_s),
                message.next_phase_id / phase_denominator,
            ]
        else:
            signal_values = [0.0, 0.0, 0.0]
    else:
        stopline_distance = leader_sensor_range_m
        signal_values = [0.0, 0.0, 0.0]
    observation = [
        speed,
        acceleration,
        leader_distance,
        leader_speed,
        stopline_distance,
        normalized_lane,
        *signal_values,
    ]
    if len(observation) != AV_OBSERVATION_SIZE:
        raise AssertionError("AV observation dimension changed")
    return observation


def build_signal_observation(
    *,
    logical_phase: int,
    seconds_in_phase: float,
    queue_lengths: list[float],
    average_speeds: list[float],
    av_counts: list[float],
    av_mean_distances: list[float],
    av_mean_speeds: list[float],
    human_counts: list[float],
    region_priority: float,
    intersection_index: int,
) -> list[float]:
    """Build the fixed 46-value Section 3.2 local-signal observation."""
    four_value_fields = (
        queue_lengths,
        average_speeds,
        av_counts,
        av_mean_distances,
        av_mean_speeds,
        human_counts,
    )
    if any(len(field) != 4 for field in four_value_fields):
        raise ValueError("Every approach field must contain exactly four values")
    if not 0 <= logical_phase < 4 or not 0 <= intersection_index < 16:
        raise ValueError("Invalid phase or intersection index")
    phase_one_hot = [float(index == logical_phase) for index in range(4)]
    identity = [float(index == intersection_index) for index in range(16)]
    observation = [
        *phase_one_hot,
        seconds_in_phase,
        *queue_lengths,
        *average_speeds,
        *av_counts,
        *av_mean_distances,
        *av_mean_speeds,
        *human_counts,
        region_priority,
        *identity,
    ]
    if len(observation) != SIGNAL_OBSERVATION_SIZE:
        raise AssertionError("Signal observation dimension changed")
    return observation


def build_region_observation(
    *,
    mean_queue: float,
    max_queue: float,
    mean_wait: float,
    total_throughput: float,
    mean_emissions: float,
    queue_stddev: float,
    region_index: int,
) -> list[float]:
    """Build the fixed ten-value Section 3.3 regional observation."""
    if not 0 <= region_index < 4:
        raise ValueError("region_index must be in [0, 3]")
    identity = [float(index == region_index) for index in range(4)]
    observation = [
        mean_queue,
        max_queue,
        mean_wait,
        total_throughput,
        mean_emissions,
        queue_stddev,
        *identity,
    ]
    if len(observation) != REGION_OBSERVATION_SIZE:
        raise AssertionError("Region observation dimension changed")
    return observation
