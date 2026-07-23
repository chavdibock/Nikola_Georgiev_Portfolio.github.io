"""Generate deterministic SUMO demand for the three required M1 scenarios."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"
DEFAULT_NETWORK = ROOT / "network" / "grid_4x4.net.xml"
SCENARIOS = ("surge", "rush_hour", "uniform")


@dataclass(frozen=True)
class BoundaryEdge:
    """A directed boundary edge and its compass-side classification."""

    edge_id: str
    side: str
    coordinate: float


def load_json_yaml(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML configuration without extra dependencies."""
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration root must be an object: {path}")
    return value


def interpolate_curve(points: Sequence[Sequence[float]], time_s: float) -> float:
    """Linearly interpolate a configured piecewise demand multiplier curve."""
    if time_s <= points[0][0]:
        return float(points[0][1])
    for left, right in zip(points, points[1:]):
        if time_s <= right[0]:
            span = float(right[0] - left[0])
            fraction = 0.0 if span == 0 else (time_s - left[0]) / span
            return float(left[1] + fraction * (right[1] - left[1]))
    return float(points[-1][1])


def _load_sumolib() -> Any:
    """Import sumolib with a clear virtual-environment installation error."""
    try:
        import sumolib  # type: ignore[import-not-found]
    except ImportError as error:
        try:
            import sumo  # type: ignore[import-not-found]

            tools_path = str(Path(sumo.SUMO_HOME) / "tools")
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            import sumolib  # type: ignore[import-not-found,no-redef]
        except ImportError as nested_error:
            raise RuntimeError(
                "sumolib is unavailable; install requirements.txt in the active .venv"
            ) from nested_error
    return sumolib


def find_boundary_edges(network_path: Path) -> tuple[list[BoundaryEdge], list[BoundaryEdge]]:
    """Return the 16 inbound and 16 outbound fringe edges, ordered by side."""
    net = _load_sumolib().net.readNet(str(network_path))
    nodes = net.getNodes()
    xs = [node.getCoord()[0] for node in nodes]
    ys = [node.getCoord()[1] for node in nodes]
    bounds = (min(xs), max(xs), min(ys), max(ys))

    def is_fringe(node: Any) -> bool:
        x, y = node.getCoord()
        return any(
            math.isclose(value, bound)
            for value, bound in ((x, bounds[0]), (x, bounds[1]), (y, bounds[2]), (y, bounds[3]))
        )

    def classify(node: Any) -> tuple[str, float]:
        x, y = node.getCoord()
        if math.isclose(x, bounds[0]):
            return "west", y
        if math.isclose(x, bounds[1]):
            return "east", y
        if math.isclose(y, bounds[0 + 2]):
            return "south", x
        if math.isclose(y, bounds[1 + 2]):
            return "north", x
        raise ValueError(f"Node {node.getID()} is not on the network boundary")

    inbound: list[BoundaryEdge] = []
    outbound: list[BoundaryEdge] = []
    for edge in net.getEdges(withInternal=False):
        from_node, to_node = edge.getFromNode(), edge.getToNode()
        if is_fringe(from_node) and not is_fringe(to_node):
            side, coordinate = classify(from_node)
            inbound.append(BoundaryEdge(edge.getID(), side, coordinate))
        if not is_fringe(from_node) and is_fringe(to_node):
            side, coordinate = classify(to_node)
            outbound.append(BoundaryEdge(edge.getID(), side, coordinate))
    ordering = {"west": 0, "east": 1, "south": 2, "north": 3}
    key = lambda edge: (ordering[edge.side], edge.coordinate, edge.edge_id)
    return sorted(inbound, key=key), sorted(outbound, key=key)


def choose_destination(
    source: BoundaryEdge,
    destinations: Sequence[BoundaryEdge],
    rng: random.Random,
) -> BoundaryEdge:
    """Choose a boundary exit on a different side to avoid trivial U-turn trips."""
    candidates = [edge for edge in destinations if edge.side != source.side]
    return rng.choice(candidates)


def _stochastic_count(expected: float, rng: random.Random) -> int:
    """Convert an expected interval count to an unbiased integer count."""
    whole = math.floor(expected)
    return whole + int(rng.random() < expected - whole)


def generate_departures(
    scenario: dict[str, Any],
    inbound: Sequence[BoundaryEdge],
    interval_s: int,
    rng: random.Random,
) -> Iterable[tuple[float, BoundaryEdge]]:
    """Yield sorted departure times and entry edges for a scenario."""
    duration = int(scenario["duration_s"])
    curve = scenario["multiplier_curve"]
    base_rate = float(scenario["base_vehicles_per_hour_per_entry"])
    surge_edge: BoundaryEdge | None = None
    if scenario["scenario"] == "surge":
        side_edges = [edge for edge in inbound if edge.side == scenario["surge_side"]]
        surge_edge = side_edges[int(scenario["surge_entry_index"])]

    departures: list[tuple[float, BoundaryEdge]] = []
    for begin in range(0, duration, interval_s):
        end = min(begin + interval_s, duration)
        midpoint = (begin + end) / 2.0
        multiplier = interpolate_curve(curve, midpoint)
        for edge in inbound:
            applied_multiplier = multiplier if surge_edge is None or edge == surge_edge else 1.0
            expected = base_rate * applied_multiplier * (end - begin) / 3600.0
            count = _stochastic_count(expected, rng)
            for index in range(count):
                departure = begin + (index + 0.5) * (end - begin) / max(count, 1)
                departures.append((departure, edge))
    return sorted(departures, key=lambda item: (item[0], item[1].edge_id))


def write_route_file(
    output: Path,
    network_path: Path,
    defaults: dict[str, Any],
    scenario: dict[str, Any],
    penetration_rate: float,
    seed: int,
) -> int:
    """Write a routed SUMO demand file and return its vehicle count."""
    sumolib = _load_sumolib()
    net = sumolib.net.readNet(str(network_path))
    inbound, outbound = find_boundary_edges(network_path)
    if len(inbound) != 16 or len(outbound) != 16:
        raise ValueError(
            f"Expected 16 inbound/outbound boundary edges, got {len(inbound)}/{len(outbound)}"
        )
    rng = random.Random(seed)
    root = ET.Element("routes")
    demand_config = defaults["demand"]
    common_type = {
        "length": str(demand_config["vehicle_length_m"]),
        "minGap": str(demand_config["vehicle_min_gap_m"]),
        "maxSpeed": str(defaults["network"]["speed_limit_mps"]),
    }
    ET.SubElement(
        root, "vType", id="HUMAN", carFollowModel=demand_config["human_car_follow_model"],
        **common_type,
    )
    ET.SubElement(root, "vType", id="AV", carFollowModel="Krauss", **common_type)

    interval = int(demand_config["generation_interval_s"])
    departures = generate_departures(scenario, inbound, interval, rng)
    count = 0
    for count, (departure, source) in enumerate(departures, start=1):
        destination = choose_destination(source, outbound, rng)
        path, _ = net.getShortestPath(net.getEdge(source.edge_id), net.getEdge(destination.edge_id))
        if not path:
            raise RuntimeError(f"No route from {source.edge_id} to {destination.edge_id}")
        vehicle_type = "AV" if rng.random() < penetration_rate else "HUMAN"
        vehicle = ET.SubElement(
            root,
            "vehicle",
            id=f"{scenario['scenario']}_{count - 1:06d}",
            type=vehicle_type,
            depart=f"{departure:.2f}",
            departLane="best",
            departSpeed="max",
        )
        ET.SubElement(vehicle, "route", edges=" ".join(edge.getID() for edge in path))

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return count


def write_sumo_config(output: Path, network_path: Path, route_path: Path) -> None:
    """Write a portable SUMO configuration next to a generated route file."""
    root = ET.Element("configuration")
    inputs = ET.SubElement(root, "input")
    relative_network = Path(os.path.relpath(network_path, output.parent)).as_posix()
    ET.SubElement(inputs, "net-file", value=relative_network)
    ET.SubElement(inputs, "route-files", value=route_path.name)
    time = ET.SubElement(root, "time")
    ET.SubElement(time, "begin", value="0")
    ET.SubElement(time, "step-length", value="1")
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    parser.add_argument("--penetration-rate", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "demand")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the demand generator CLI."""
    args = parse_args(argv)
    defaults = load_json_yaml(args.config.resolve())
    penetration = (
        float(args.penetration_rate)
        if args.penetration_rate is not None
        else float(defaults["demand"]["penetration_rate"])
    )
    if penetration not in {0.05, 0.10, 0.20}:
        raise ValueError("penetration-rate must be one of 0.05, 0.10, or 0.20")
    seed = int(args.seed if args.seed is not None else defaults["demand"]["seed"])
    names = SCENARIOS if args.scenario == "all" else (args.scenario,)
    for offset, name in enumerate(names):
        scenario = load_json_yaml(ROOT / "config" / f"scenario_{name}.yaml")
        route_path = args.output_dir.resolve() / f"{name}.rou.xml"
        count = write_route_file(
            route_path, args.network.resolve(), defaults, scenario, penetration, seed + offset
        )
        config_path = args.output_dir.resolve() / f"{name}.sumocfg"
        write_sumo_config(config_path, args.network.resolve(), route_path)
        print(f"Generated {route_path} ({count} vehicles, AV rate={penetration:.0%})")
        print(f"Generated {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
