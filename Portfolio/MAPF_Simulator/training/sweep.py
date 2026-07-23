"""M8 curriculum training sweep for 5%, 10%, and 20% AV penetration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.train import train


PENETRATION_RATES = (0.05, 0.10, 0.20)


def run_sweep(iterations: int, steps: int) -> list[dict[str, Any]]:
    """Regenerate isolated demand and train one curriculum policy set per rate."""
    all_logs: list[dict[str, Any]] = []
    for rate in PENETRATION_RATES:
        group = f"p{int(rate * 100):02d}"
        output_dir = ROOT / "demand" / group
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "demand" / "generate_demand.py"),
                "--penetration-rate", str(rate),
                "--output-dir", str(output_dir),
            ],
            cwd=ROOT,
            check=True,
        )
        all_logs.extend(
            train(
                iterations,
                steps,
                rate,
                ROOT / "outputs" / "checkpoints",
                artifact_group=group,
            )
        )
    log_path = ROOT / "outputs" / "metrics_csv" / "m8_training_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(all_logs, indent=2), encoding="utf-8")
    return all_logs


def main(argv: Sequence[str] | None = None) -> int:
    """Run the penetration sweep CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--steps", type=int)
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    iterations = int(
        args.iterations if args.iterations is not None else config["training"]["iterations"]
    )
    steps = int(args.steps if args.steps is not None else config["training"]["rollout_steps"])
    logs = run_sweep(iterations, steps)
    print(f"Completed {len(logs)} curriculum iterations across three penetration rates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
