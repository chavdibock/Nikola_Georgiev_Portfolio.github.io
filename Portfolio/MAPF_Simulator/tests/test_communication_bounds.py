"""Scalability tests for fixed-size communication aggregation."""

from __future__ import annotations

import unittest

from env.communication import IntentMessage, aggregate_approaches
from env.hierarchical_signal_env import REGION_MEMBERS


class CommunicationBoundsTests(unittest.TestCase):
    """Ensure message outputs never grow with vehicle population."""

    def test_approach_aggregate_size_is_population_independent(self) -> None:
        """Return four records for zero, ten, or ten thousand messages."""
        for population in (0, 10, 10_000):
            messages = [
                IntentMessage(str(index), index % 4, float(index), 10.0)
                for index in range(population)
            ]
            aggregates = aggregate_approaches(messages, [])
            self.assertEqual(4, len(aggregates))
            self.assertEqual(population, sum(item.av_count for item in aggregates))

    def test_regions_are_bounded_disjoint_groups(self) -> None:
        """Assign all 16 intersections exactly once across four groups of four."""
        self.assertEqual(4, len(REGION_MEMBERS))
        self.assertTrue(all(len(members) == 4 for members in REGION_MEMBERS.values()))
        flattened = [member for members in REGION_MEMBERS.values() for member in members]
        self.assertEqual(16, len(set(flattened)))


if __name__ == "__main__":
    unittest.main()
