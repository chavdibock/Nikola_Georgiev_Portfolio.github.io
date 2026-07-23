"""Run a trained policy through the API and visualize it in the browser viewer."""

from __future__ import annotations

import argparse
import json
import sys
import time
import webbrowser
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from api_client.simulator_client import SimulatorClient
from evaluation.evaluate import _load_networks


def main(argv: Sequence[str] | None = None) -> int:
    """Create an API session, open its viewer, and drive it with trained policies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", choices=("surge", "rush_hour", "uniform"), default="surge")
    parser.add_argument("--penetration-rate", type=float, choices=(0.05, 0.10, 0.20), default=0.20)
    parser.add_argument("--steps", type=int, default=1800)
    parser.add_argument("--delay-ms", type=int, default=120)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    networks = _load_networks(args.penetration_rate, config)
    environment = SimulatorClient(
        args.scenario,
        args.penetration_rate,
        int(config["demand"]["seed"]),
        base_url=args.simulator_url,
        mode="trained",
    )
    observations = environment.reset()
    viewer_url = f"{args.simulator_url}/viewer?session={environment.session_id}"
    print(f"Policy replay viewer: {viewer_url}")
    if not args.no_browser:
        webbrowser.open(viewer_url)
    try:
        for _ in range(args.steps):
            actions: dict[str, int | list[float]] = {}
            signal_ids = environment.signal_agent_ids
            with torch.no_grad():
                for agent_id, observation in observations.items():
                    tensor = torch.tensor([observation], dtype=torch.float32)
                    if agent_id.startswith("region_"):
                        distribution, _ = networks[2](tensor)
                        actions[agent_id] = (
                            distribution.concentration1
                            / (distribution.concentration1 + distribution.concentration0)
                        )[0].tolist()
                    elif agent_id in signal_ids:
                        distribution, _ = networks[1](tensor)
                        actions[agent_id] = int(distribution.probs.argmax(-1).item())
                    else:
                        distribution, _ = networks[0](tensor)
                        actions[agent_id] = distribution.mean[0].tolist()
            observations, _, _, _, _ = environment.step(actions)
            if environment.last_done:
                break
            time.sleep(max(0, args.delay_ms) / 1000.0)
    except KeyboardInterrupt:
        pass
    finally:
        print(json.dumps(environment.metrics(), sort_keys=True))
        environment.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
