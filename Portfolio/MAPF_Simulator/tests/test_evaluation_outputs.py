"""M9 plot and improvement-table output tests."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from evaluation.plots import METRICS, generate_outputs


class EvaluationOutputTests(unittest.TestCase):
    """Verify all requested metric plots and improvement rows are written."""

    def test_generate_all_plots_and_improvements(self) -> None:
        """Generate seven PNGs and 63 scenario/rate/metric comparisons."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.csv"
            trained = root / "trained.csv"
            metric_values = {metric: 10.0 for metric in METRICS}
            with baseline.open("w", newline="", encoding="utf-8") as stream:
                fields = ["scenario", *METRICS]
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for scenario in ("surge", "rush_hour", "uniform"):
                    writer.writerow({"scenario": scenario, **metric_values})
            with trained.open("w", newline="", encoding="utf-8") as stream:
                fields = ["scenario", "penetration_rate", *METRICS]
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for scenario in ("surge", "rush_hour", "uniform"):
                    for rate in (0.05, 0.10, 0.20):
                        writer.writerow(
                            {"scenario": scenario, "penetration_rate": rate, **metric_values}
                        )
            plot_dir = root / "plots"
            table = root / "improvements.csv"
            generate_outputs(baseline, trained, plot_dir, table)
            self.assertEqual(len(METRICS), len(list(plot_dir.glob("*.png"))))
            with table.open("r", encoding="utf-8", newline="") as stream:
                self.assertEqual(3 * 3 * len(METRICS), len(list(csv.DictReader(stream))))


if __name__ == "__main__":
    unittest.main()
