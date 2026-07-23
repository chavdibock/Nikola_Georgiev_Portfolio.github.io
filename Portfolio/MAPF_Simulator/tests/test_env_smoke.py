"""M2 end-to-end TraCI lifecycle smoke test."""

from __future__ import annotations

import unittest
from pathlib import Path

from env.traci_wrapper import TraciConnection
from env.signal_env import SignalOnlyParallelEnv
from env.hierarchical_signal_env import HierarchicalSignalParallelEnv
from env.joint_env import JointParallelEnv


ROOT = Path(__file__).resolve().parents[1]


class TraciSmokeTests(unittest.TestCase):
    """Verify connect, step, state reads, and clean disconnect."""

    def test_connection_lifecycle_and_state_reads(self) -> None:
        """Run enough surge ticks to observe signals and active vehicles."""
        connection = TraciConnection(ROOT / "demand" / "surge.sumocfg")
        self.assertFalse(connection.is_connected)
        try:
            connection.start()
            self.assertTrue(connection.is_connected)
            self.assertEqual("traci", connection.backend)
            self.assertEqual(16, len(connection.get_signal_states()))
            self.assertEqual(50.0, connection.step(50))
            vehicles = connection.get_vehicle_states()
            self.assertGreater(len(vehicles), 0)
            self.assertTrue(all(state.speed_mps >= 0 for state in vehicles.values()))
        finally:
            connection.close()
        self.assertFalse(connection.is_connected)

    def test_signal_only_decision_boundaries(self) -> None:
        """Run M5 extend actions while emitting fixed-size observations every five seconds."""
        environment = SignalOnlyParallelEnv("uniform")
        observations = environment.reset()
        boundary_counts: list[int] = []
        try:
            for _ in range(20):
                observations, rewards, _, _, _ = environment.step(
                    {signal_id: 0 for signal_id in observations}
                )
                if observations:
                    boundary_counts.append(len(observations))
                    self.assertEqual(set(observations), set(rewards))
                    self.assertTrue(all(len(value) == 46 for value in observations.values()))
        finally:
            environment.close()
        self.assertTrue(boundary_counts)

    def test_hierarchical_region_boundary(self) -> None:
        """Emit four fixed-size regional agents on the 60-second clock."""
        environment = HierarchicalSignalParallelEnv("uniform")
        observations = environment.reset()
        self.assertEqual(4, sum(agent.startswith("region_") for agent in observations))
        try:
            for _ in range(60):
                actions = {
                    agent: ([0.5] * 4 if agent.startswith("region_") else 0)
                    for agent in observations
                }
                observations, rewards, _, _, _ = environment.step(actions)
            region_observations = {
                agent: value for agent, value in observations.items() if agent.startswith("region_")
            }
            self.assertEqual(4, len(region_observations))
            self.assertTrue(all(len(value) == 10 for value in region_observations.values()))
            self.assertTrue(set(region_observations) <= set(rewards))
        finally:
            environment.close()

    def test_joint_three_role_environment(self) -> None:
        """Run M7 with AV, signal, and regional agents in one SUMO session."""
        environment = JointParallelEnv("surge")
        observations = environment.reset()
        roles_seen = {"signal": False, "region": False, "av": False}
        try:
            for _ in range(90):
                actions = {}
                for agent_id in observations:
                    if agent_id.startswith("region_"):
                        actions[agent_id] = [0.5] * 4
                        roles_seen["region"] = True
                    elif agent_id in environment.hierarchy.local.signal_ids:
                        actions[agent_id] = 0
                        roles_seen["signal"] = True
                    else:
                        actions[agent_id] = [0.0, 0.0]
                        roles_seen["av"] = True
                observations, _, _, _, _ = environment.step(actions)
        finally:
            environment.close()
        self.assertTrue(all(roles_seen.values()), roles_seen)


if __name__ == "__main__":
    unittest.main()
