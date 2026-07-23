"""Reward formula tests introduced with M4."""

from __future__ import annotations

import unittest

from agents.rollout_buffer import RolloutBuffer
from env.reward_calculator import calculate_av_reward, calculate_region_reward, calculate_signal_reward


class RewardCalculatorTests(unittest.TestCase):
    """Verify exact AV weighted-term behavior."""

    def test_m4_reward_excludes_global_shared_term(self) -> None:
        """Ignore local signal reward during isolated AV training."""
        weights = {
            "av_progress": 1.0,
            "av_harsh_braking": 0.5,
            "av_co2": 0.05,
            "av_global_shared": 0.3,
        }
        reward = calculate_av_reward(
            ego_speed=10.0,
            target_speed=10.0,
            acceleration=-4.0,
            co2_emission=2.0,
            local_signal_reward=100.0,
            weights=weights,
            harsh_braking_threshold=-3.0,
            include_global_shared=False,
        )
        self.assertAlmostEqual(-1.1, reward)

    def test_negative_emission_sentinel_is_ignored(self) -> None:
        """Do not turn TraCI's unavailable-value sentinel into a reward bonus."""
        weights = {
            "av_progress": 1.0,
            "av_harsh_braking": 0.5,
            "av_co2": 0.05,
            "av_global_shared": 0.3,
        }
        reward = calculate_av_reward(
            ego_speed=10.0,
            target_speed=10.0,
            acceleration=0.0,
            co2_emission=-1_073_741_824.0,
            local_signal_reward=0.0,
            weights=weights,
            harsh_braking_threshold=-3.0,
        )
        self.assertEqual(1.0, reward)

    def test_gae_is_computed_separately_per_agent(self) -> None:
        """Keep interleaved shared-policy trajectories independent during GAE."""
        buffer = RolloutBuffer()
        buffer.add("av_a", [0.0], [0.0, 0.0], 0.0, 1.0, 0.0)
        buffer.add("av_b", [0.0], [0.0, 0.0], 0.0, 10.0, 0.0, done=True)
        buffer.add("av_a", [0.0], [0.0, 0.0], 0.0, 2.0, 0.0, done=True)
        batch = buffer.as_batch(gamma=1.0, gae_lambda=1.0)
        self.assertEqual([3.0, 10.0, 2.0], batch.returns.tolist())

    def test_m5_signal_reward_excludes_region_alignment(self) -> None:
        """Apply throughput, wait, fairness, and emissions but no regional bonus."""
        weights = {
            "signal_throughput": 1.0,
            "signal_wait_time": 1.0,
            "signal_fairness": 0.5,
            "signal_emissions": 0.2,
            "signal_region_alignment": 0.1,
        }
        reward = calculate_signal_reward(
            throughput=4.0,
            wait_time_increase=2.0,
            approach_wait_times=[1.0, 1.0, 1.0, 1.0],
            emissions=5.0,
            region_alignment_bonus=100.0,
            weights=weights,
            include_region_alignment=False,
        )
        self.assertAlmostEqual(1.0, reward)

    def test_region_reward_uses_member_fairness(self) -> None:
        """Penalize unequal member waits with the fixed Jain formula."""
        weights = {
            "region_throughput": 1.0,
            "region_wait_time": 1.0,
            "region_fairness": 0.5,
            "region_emissions": 0.2,
        }
        equal = calculate_region_reward(
            total_throughput=10.0,
            member_wait_times=[2.0] * 4,
            mean_emissions=1.0,
            weights=weights,
        )
        unequal = calculate_region_reward(
            total_throughput=10.0,
            member_wait_times=[0.0, 0.0, 0.0, 8.0],
            mean_emissions=1.0,
            weights=weights,
        )
        self.assertGreater(equal, unequal)


if __name__ == "__main__":
    unittest.main()
