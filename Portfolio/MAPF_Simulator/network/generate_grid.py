"""Generate the configurable 4x4 SUMO road network for M1."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_OUTPUT = ROOT / "network" / "grid_4x4.net.xml"


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML configuration without extra dependencies."""
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return value


def find_sumo_binary(name: str) -> Path:
    """Find a SUMO executable in the active Python environment or SUMO_HOME."""
    suffix = ".exe" if os.name == "nt" else ""
    candidates = [Path(sys.executable).parent / f"{name}{suffix}"]
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        candidates.insert(0, Path(sumo_home) / "bin" / f"{name}{suffix}")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find {name!r}. Install requirements into the active virtual "
        "environment and run this script with that environment's Python."
    )


def build_command(config: dict[str, Any], output: Path) -> list[str]:
    """Build the netgenerate command for the configured network."""
    network = config["network"]
    grid_size = int(network["grid_size"])
    tls_ids = ",".join(
        f"{chr(ord('A') + column)}{row}"
        for column in range(grid_size)
        for row in range(grid_size)
    )
    return [
        str(find_sumo_binary("netgenerate")),
        "--grid",
        "--grid.number", str(grid_size),
        "--grid.length", str(network["block_length_m"]),
        "--grid.attach-length", str(network["boundary_edge_length_m"]),
        "--default.lanenumber", str(network["lanes_per_direction"]),
        "--default.speed", str(network["speed_limit_mps"]),
        "--turn-lanes", str(network["left_turn_pockets"]),
        "--turn-lanes.length", str(network["left_turn_pocket_length_m"]),
        "--tls.set", tls_ids,
        "--tls.default-type", "static",
        "--tls.layout", "opposites",
        "--tls.green.time", str(network["signal_green_s"]),
        "--tls.left-green.time", str(network["signal_left_green_s"]),
        "--tls.yellow.time", str(network["signal_yellow_s"]),
        "--tls.allred.time", str(network["signal_all_red_s"]),
        "--no-turnarounds",
        "--output-file", str(output),
    ]


def generate_grid(config_path: Path, output: Path) -> Path:
    """Generate the SUMO network and return the created artifact path."""
    config = load_json_yaml(config_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        build_command(config, output), check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "netgenerate failed:\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not output.is_file():
        raise RuntimeError(f"netgenerate did not create {output}")
    return output


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the network generator CLI."""
    args = parse_args(argv)
    artifact = generate_grid(args.config.resolve(), args.output.resolve())
    print(f"Generated SUMO network: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
