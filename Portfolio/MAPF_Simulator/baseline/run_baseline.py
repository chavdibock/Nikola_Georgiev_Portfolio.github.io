"""Run the Section 7 fixed-time baseline and write Section 8.1 metrics."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline.fixed_time_controller import FixedTimeController
from demand.generate_demand import write_route_file, write_sumo_config
from env.traci_wrapper import DEFAULT_CONFIG, TraciConnection
from evaluation.metrics import EvaluationMetrics, MetricsCollector


SCENARIOS = ("surge", "rush_hour", "uniform")


def load_config(path: Path) -> dict[str, Any]:
    """Load JSON-compatible YAML configuration."""
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def ensure_human_baseline_demand(
    scenario: str,
    config_path: Path = DEFAULT_CONFIG,
) -> Path:
    """Generate the deterministic 100%-human route required by the M3 baseline."""
    defaults = load_config(config_path)
    scenario_config = load_config(ROOT / "config" / f"scenario_{scenario}.yaml")
    route_path = ROOT / "demand" / f"baseline_{scenario}.rou.xml"
    sumo_config_path = ROOT / "demand" / f"baseline_{scenario}.sumocfg"
    network_path = ROOT / "network" / "grid_4x4.net.xml"
    expected_seed = int(defaults["demand"]["seed"]) + SCENARIOS.index(scenario)

    regenerate = not route_path.is_file() or not sumo_config_path.is_file()
    if not regenerate:
        root = ET.parse(route_path).getroot()
        regenerate = any(
            vehicle.attrib.get("type") != "HUMAN" for vehicle in root.findall("vehicle")
        )
    if regenerate:
        write_route_file(
            route_path,
            network_path,
            defaults,
            scenario_config,
            penetration_rate=0.0,
            seed=expected_seed,
        )
        write_sumo_config(sumo_config_path, network_path, route_path)
    return sumo_config_path


def run_baseline(
    scenario: str,
    config_path: Path = DEFAULT_CONFIG,
    *,
    max_simulation_s: float | None = None,
) -> EvaluationMetrics:
    """Run one complete fixed-time scenario and return its metrics."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    config = load_config(config_path)
    scenario_config = load_config(ROOT / "config" / f"scenario_{scenario}.yaml")
    demand_end = float(scenario_config["duration_s"])
    hard_end = max_simulation_s or demand_end + float(config["simulation"]["drain_timeout_s"])
    sumo_config_path = ensure_human_baseline_demand(scenario, config_path)
    with TraciConnection(sumo_config_path, config_path) as connection:
        controller = FixedTimeController(
            connection.api,
            str(config["baseline"]["program_id"]),
            int(config["baseline"]["initial_phase_index"]),
        )
        controller.initialize()
        collector = MetricsCollector(
            connection.api,
            float(config["simulation"]["step_length_s"]),
            float(config["metrics"]["fuel_density_g_per_l"]),
            float(config["metrics"]["queue_speed_threshold_mps"]),
        )
        while connection.simulation_time_s < hard_end:
            controller.step()
            connection.step()
            collector.observe_step()
            if (
                max_simulation_s is None
                and connection.simulation_time_s >= demand_end
                and connection.api.simulation.getMinExpectedNumber() == 0
            ):
                break
        return collector.finalize(connection.simulation_time_s)


def write_metrics(rows: list[dict[str, Any]], output: Path) -> None:
    """Write baseline metrics as a reproducible CSV artifact."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse baseline command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    parser.add_argument("--max-simulation-s", type=float)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs" / "metrics_csv" / "baseline.csv"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run requested baseline scenarios and save their metrics."""
    args = parse_args(argv)
    names = SCENARIOS if args.scenario == "all" else (args.scenario,)
    rows: list[dict[str, Any]] = []
    for name in names:
        metrics = run_baseline(name, max_simulation_s=args.max_simulation_s)
        row = {"scenario": name, "mode": "baseline", **metrics.to_dict()}
        rows.append(row)
        print(json.dumps(row, sort_keys=True))
    write_metrics(rows, args.output.resolve())
    print(f"Wrote baseline metrics: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
