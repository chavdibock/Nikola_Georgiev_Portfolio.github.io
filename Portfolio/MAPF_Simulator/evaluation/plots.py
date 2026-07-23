"""Create Section 8.2 grouped plots and improvement table."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MATPLOTLIB_CONFIG = ROOT / "outputs" / ".matplotlib"
MATPLOTLIB_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CONFIG))

import matplotlib.pyplot as plt
import numpy as np


METRICS = (
    "avg_travel_time",
    "avg_wait_time",
    "throughput",
    "fairness_index",
    "co2_kg",
    "fuel_l",
    "max_queue_length",
)
LOWER_IS_BETTER = {"avg_travel_time", "avg_wait_time", "co2_kg", "fuel_l", "max_queue_length"}


def _read(path: Path) -> list[dict[str, str]]:
    """Read one metric CSV."""
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def generate_outputs(baseline_csv: Path, trained_csv: Path, plot_dir: Path, table_csv: Path) -> None:
    """Generate one grouped bar chart per metric and improvement percentages."""
    baseline_rows = _read(baseline_csv)
    trained_rows = _read(trained_csv)
    baseline = {row["scenario"]: row for row in baseline_rows}
    scenarios = ("surge", "rush_hour", "uniform")
    rates = (0.05, 0.10, 0.20)
    plot_dir.mkdir(parents=True, exist_ok=True)
    improvement_rows: list[dict[str, Any]] = []
    for metric in METRICS:
        x = np.arange(len(scenarios))
        width = 0.2
        figure, axis = plt.subplots(figsize=(9, 5))
        axis.bar(x - 1.5 * width, [float(baseline[item][metric]) for item in scenarios], width, label="baseline")
        for offset, rate in enumerate(rates, start=0):
            values = []
            for scenario in scenarios:
                row = next(
                    item for item in trained_rows
                    if item["scenario"] == scenario and float(item["penetration_rate"]) == rate
                )
                trained = float(row[metric])
                base = float(baseline[scenario][metric])
                values.append(trained)
                if base != 0:
                    improvement = (base - trained) / base * 100.0 if metric in LOWER_IS_BETTER else (
                        trained - base
                    ) / base * 100.0
                else:
                    improvement = 0.0
                improvement_rows.append(
                    {
                        "scenario": scenario,
                        "penetration_rate": rate,
                        "metric": metric,
                        "improvement_percent": improvement,
                    }
                )
            axis.bar(x + (offset - 0.5) * width, values, width, label=f"trained {rate:.0%}")
        axis.set_xticks(x, scenarios)
        axis.set_ylabel(metric.replace("_", " "))
        axis.legend()
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        figure.savefig(plot_dir / f"{metric}.png", dpi=150)
        plt.close(figure)
    table_csv.parent.mkdir(parents=True, exist_ok=True)
    with table_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(improvement_rows[0]))
        writer.writeheader()
        writer.writerows(improvement_rows)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate plots from default or supplied metric files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "outputs" / "metrics_csv" / "baseline.csv")
    parser.add_argument("--trained", type=Path, default=ROOT / "outputs" / "metrics_csv" / "trained.csv")
    args = parser.parse_args(argv)
    generate_outputs(
        args.baseline.resolve(),
        args.trained.resolve(),
        ROOT / "outputs" / "plots",
        ROOT / "outputs" / "metrics_csv" / "improvements.csv",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
