"""Evaluate trained joint policies and fixed-time baselines on the full 3x3 grid."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from agents.networks import AVPolicyValueNetwork, RegionalPolicyValueNetwork, SignalPolicyValueNetwork
from api_client.simulator_client import DEFAULT_SIMULATOR_URL, SimulatorClient
from env.observation_builder import AV_OBSERVATION_SIZE, REGION_OBSERVATION_SIZE, SIGNAL_OBSERVATION_SIZE
from evaluation.metrics import EvaluationMetrics


SCENARIOS = ("surge", "rush_hour", "uniform")
RATES = (0.05, 0.10, 0.20)


def _load_networks(rate: float, config: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Load one penetration rate's three shared policy checkpoints."""
    networks = (
        AVPolicyValueNetwork(AV_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
        SignalPolicyValueNetwork(SIGNAL_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
        RegionalPolicyValueNetwork(REGION_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
    )
    suffix = f"p{int(rate * 100):02d}"
    for name, network in zip(("av", "signals", "regions"), networks):
        checkpoint = ROOT / "outputs" / "checkpoints" / f"m7_{name}_{suffix}.pt"
        network.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        network.eval()
    return networks


def evaluate_trained(
    scenario: str,
    rate: float,
    *,
    max_simulation_s: float | None = None,
    simulator_url: str | None = None,
) -> EvaluationMetrics:
    """Run one deterministic trained-policy cell through the simulator API."""
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    scenario_config = json.loads(
        (ROOT / "config" / f"scenario_{scenario}.yaml").read_text(encoding="utf-8")
    )
    networks = _load_networks(rate, config)
    environment = SimulatorClient(
        scenario,
        rate,
        int(config["demand"]["seed"]) + SCENARIOS.index(scenario),
        base_url=simulator_url or os.environ.get("SIMULATOR_API_URL", DEFAULT_SIMULATOR_URL),
        mode="trained",
    )
    observations = environment.reset()
    demand_end = float(scenario_config["duration_s"])
    hard_end = max_simulation_s or demand_end + float(config["simulation"]["drain_timeout_s"])
    try:
        while environment.last_sim_time < hard_end:
            actions: dict[str, int | list[float]] = {}
            signal_ids = environment.signal_agent_ids
            with torch.no_grad():
                for agent_id, observation in observations.items():
                    tensor = torch.tensor([observation], dtype=torch.float32)
                    if agent_id.startswith("region_"):
                        distribution, _ = networks[2](tensor)
                        actions[agent_id] = (distribution.concentration1 / (
                            distribution.concentration1 + distribution.concentration0
                        ))[0].tolist()
                    elif agent_id in signal_ids:
                        distribution, _ = networks[1](tensor)
                        actions[agent_id] = int(distribution.probs.argmax(-1).item())
                    else:
                        distribution, _ = networks[0](tensor)
                        actions[agent_id] = distribution.mean[0].tolist()
            observations, _, _, _, _ = environment.step(actions)
            if (
                max_simulation_s is None
                and environment.last_sim_time >= demand_end
                and environment.last_done
            ):
                break
        values = environment.metrics()
        completed = int(round(float(values["throughput"]) * environment.last_sim_time / 3600.0))
        return EvaluationMetrics(
            avg_travel_time=float(values["avg_travel_time"]),
            avg_wait_time=float(values["avg_wait_time"]),
            throughput=float(values["throughput"]),
            fairness_index=float(values["fairness_index"]),
            co2_kg=float(values["co2_kg"]),
            fuel_l=float(values["fuel_l"]),
            max_queue_length=int(values["max_queue_length"]),
            completed_vehicles=completed,
            simulated_seconds=environment.last_sim_time,
        )
    finally:
        environment.close()


def write_rows(rows: list[dict[str, Any]], output: Path) -> None:
    """Write evaluation cells to CSV."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def merge_rate_files(output: Path) -> None:
    """Merge independently evaluated rate CSVs into the canonical trained CSV."""
    rows: list[dict[str, Any]] = []
    for tag in ("005", "010", "020"):
        path = ROOT / "outputs" / "metrics_csv" / f"trained_{tag}.csv"
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows.extend(csv.DictReader(stream))
    write_rows(rows, output)


def main(argv: Sequence[str] | None = None) -> int:
    """Run all trained evaluation cells or a bounded smoke subset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-simulation-s", type=float)
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    parser.add_argument("--rate", type=float)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "metrics_csv" / "trained.csv")
    parser.add_argument("--merge-rate-files", action="store_true")
    parser.add_argument("--simulator-url")
    args = parser.parse_args(argv)
    if args.merge_rate_files:
        merge_rate_files(args.output.resolve())
        return 0
    scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
    rates = RATES if args.rate is None else (args.rate,)
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for rate in rates:
            metrics = evaluate_trained(
                scenario,
                rate,
                max_simulation_s=args.max_simulation_s,
                simulator_url=args.simulator_url,
            )
            row = {
                "scenario": scenario,
                "mode": "trained",
                "penetration_rate": rate,
                **metrics.to_dict(),
            }
            rows.append(row)
            print(json.dumps(row, sort_keys=True))
    write_rows(rows, args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
