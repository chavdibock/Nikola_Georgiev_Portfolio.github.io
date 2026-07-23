"""Fixed-size observation tests introduced with M4."""

from __future__ import annotations

import unittest

from env.multi_agent_env import AVOnlyParallelEnv
from env.observation_builder import (
    AV_OBSERVATION_SIZE,
    REGION_OBSERVATION_SIZE,
    SIGNAL_OBSERVATION_SIZE,
    build_region_observation,
    build_signal_observation,
)


class ObservationShapeTests(unittest.TestCase):
    """Assert AV observation size is independent of active vehicle count."""

    def test_av_observations_are_fixed_size(self) -> None:
        """Observe multiple traffic populations without changing per-AV dimension."""
        environment = AVOnlyParallelEnv("surge")
        observations = environment.reset()
        seen_sizes: set[int] = set()
        seen_agents: set[int] = set()
        try:
            for _ in range(180):
                observations, _, _, _, _ = environment.step(
                    {agent_id: [0.0, 0.0] for agent_id in observations}
                )
                seen_agents.add(len(observations))
                seen_sizes.update(len(value) for value in observations.values())
        finally:
            environment.close()
        self.assertEqual({AV_OBSERVATION_SIZE}, seen_sizes)
        self.assertGreater(max(seen_agents), 0)

    def test_signal_observation_is_fixed_size(self) -> None:
        """Build a signal observation with only bounded four-approach aggregates."""
        observation = build_signal_observation(
            logical_phase=0,
            seconds_in_phase=5.0,
            queue_lengths=[0.0] * 4,
            average_speeds=[0.0] * 4,
            av_counts=[0.0] * 4,
            av_mean_distances=[0.0] * 4,
            av_mean_speeds=[0.0] * 4,
            human_counts=[0.0] * 4,
            region_priority=0.0,
            intersection_index=0,
        )
        self.assertEqual(SIGNAL_OBSERVATION_SIZE, len(observation))

    def test_region_observation_is_fixed_size(self) -> None:
        """Keep one coordinator observation independent of city size."""
        observation = build_region_observation(
            mean_queue=1.0,
            max_queue=2.0,
            mean_wait=3.0,
            total_throughput=4.0,
            mean_emissions=5.0,
            queue_stddev=0.5,
            region_index=2,
        )
        self.assertEqual(REGION_OBSERVATION_SIZE, len(observation))


if __name__ == "__main__":
    unittest.main()
