"""Tests for M1 network and demand artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MilestoneOneGenerationTests(unittest.TestCase):
    """Verify generated network topology and scenario demand contracts."""

    def test_generated_network_and_demand_are_valid(self) -> None:
        """Generate all M1 artifacts and validate them with SUMO itself."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            network = temporary / "grid_4x4.net.xml"
            demand_dir = temporary / "demand"
            subprocess.run(
                [sys.executable, str(ROOT / "network" / "generate_grid.py"), "--output", str(network)],
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "demand" / "generate_demand.py"),
                    "--network", str(network),
                    "--output-dir", str(demand_dir),
                ],
                cwd=ROOT,
                check=True,
            )

            network_root = ET.parse(network).getroot()
            junctions = [
                node for node in network_root.findall("junction")
                if node.attrib.get("type") == "traffic_light"
            ]
            self.assertEqual(16, len(junctions))
            programs = network_root.findall("tlLogic")
            self.assertEqual(16, len(programs))
            for program in programs:
                green_phases = [
                    phase for phase in program.findall("phase")
                    if "y" not in phase.attrib["state"].lower()
                    and "g" in phase.attrib["state"].lower()
                ]
                self.assertEqual(4, len(green_phases), program.attrib["id"])

            defaults = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
            for name in ("surge", "rush_hour", "uniform"):
                route_file = demand_dir / f"{name}.rou.xml"
                vehicles = ET.parse(route_file).getroot().findall("vehicle")
                self.assertGreater(len(vehicles), 0)
                departures = [float(vehicle.attrib["depart"]) for vehicle in vehicles]
                self.assertEqual(departures, sorted(departures))
                self.assertTrue({vehicle.attrib["type"] for vehicle in vehicles} <= {"AV", "HUMAN"})
                sumo = Path(sys.executable).parent / ("sumo.exe" if sys.platform == "win32" else "sumo")
                completed = subprocess.run(
                    [
                        str(sumo), "--net-file", str(network), "--route-files", str(route_file),
                        "--begin", "0", "--end", "1", "--route-steps", "0",
                        "--no-step-log", "true",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(4, defaults["network"]["signal_phase_count"])


if __name__ == "__main__":
    unittest.main()
