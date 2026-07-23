"""M3 fixed-time baseline and metrics tests."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from baseline.run_baseline import ensure_human_baseline_demand, run_baseline
from evaluation.metrics import jains_fairness


class BaselineMetricsTests(unittest.TestCase):
    """Verify formulas and a short fixed-time SUMO run."""

    def test_jains_fairness(self) -> None:
        """Return one for equal allocation and less than one when unequal."""
        self.assertEqual(1.0, jains_fairness([0.0, 0.0, 0.0, 0.0]))
        self.assertEqual(1.0, jains_fairness([2.0, 2.0, 2.0, 2.0]))
        self.assertLess(jains_fairness([1.0, 1.0, 1.0, 10.0]), 1.0)

    def test_short_uniform_baseline(self) -> None:
        """Run a short static-control session and produce finite metrics."""
        sumo_config = ensure_human_baseline_demand("uniform")
        route_file = sumo_config.with_name("baseline_uniform.rou.xml")
        vehicle_types = {
            vehicle.attrib["type"]
            for vehicle in ET.parse(route_file).getroot().findall("vehicle")
        }
        self.assertEqual({"HUMAN"}, vehicle_types)
        metrics = run_baseline("uniform", max_simulation_s=300.0)
        self.assertEqual(300.0, metrics.simulated_seconds)
        self.assertGreater(metrics.completed_vehicles, 0)
        self.assertGreater(metrics.throughput, 0.0)
        self.assertGreaterEqual(metrics.fairness_index, 0.0)
        self.assertLessEqual(metrics.fairness_index, 1.0)
        self.assertGreater(metrics.co2_kg, 0.0)
        self.assertGreater(metrics.fuel_l, 0.0)


if __name__ == "__main__":
    unittest.main()
