"""Exercise the complete remote simulator stack for exactly 50 ticks."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from api_client.simulator_client import DEFAULT_SIMULATOR_URL, SimulatorClient


def run_smoke_test(base_url: str, steps: int = 50) -> dict[str, object]:
    """Create, batch-control, step, measure, and tear down one remote session."""
    client = SimulatorClient("uniform", 0.05, 42, base_url=base_url, mode="trained")
    observations = client.reset()
    initial_counts = {
        role: len(values) for role, values in client.grouped_observations.items()
    }
    try:
        for _ in range(steps):
            actions: dict[str, int | list[float]] = {}
            signal_ids = set(client.grouped_observations["signal_agents"])
            region_ids = set(client.grouped_observations["region_agents"])
            for agent_id in observations:
                if agent_id in region_ids:
                    actions[agent_id] = [0.5, 0.5, 0.5, 0.5]
                elif agent_id in signal_ids:
                    actions[agent_id] = 0
                else:
                    actions[agent_id] = [0.0, 0.0]
            observations, _, _, _, _ = client.step(actions)
        return {
            "status": "ok",
            "sim_time": client.last_sim_time,
            "initial_active_agents": initial_counts,
            "metrics": client.metrics(),
        }
    finally:
        client.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the external-client smoke test and print its JSON result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_SIMULATOR_URL)
    parser.add_argument("--steps", type=int, default=50)
    args = parser.parse_args(argv)
    print(json.dumps(run_smoke_test(args.url, args.steps), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
