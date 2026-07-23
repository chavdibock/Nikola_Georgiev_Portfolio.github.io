"""M10 REST, WebSocket, session-isolation, and viewer contract tests."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app


class SimulatorApiContractTests(unittest.TestCase):
    """Exercise the externally visible simulator-service contract."""

    def test_rest_lifecycle_and_viewer(self) -> None:
        """Create, inspect, batch-control, step, measure, and delete a session."""
        with TestClient(app) as client:
            self.assertEqual({"status": "ok"}, client.get("/health").json())
            schema = client.get("/config/schema")
            self.assertEqual(200, schema.status_code)
            self.assertIn("simulation", schema.json()["properties"])
            viewer = client.get("/viewer")
            self.assertEqual(200, viewer.status_code)
            self.assertIn("Joint AV", viewer.text)

            created = client.post(
                "/sessions",
                json={
                    "scenario": "uniform",
                    "penetration_rate": 0.05,
                    "seed": 123,
                    "config_overrides": {},
                    "mode": "trained",
                },
            )
            self.assertEqual(201, created.status_code, created.text)
            session_id = created.json()["session_id"]

            status = client.get(f"/sessions/{session_id}").json()
            self.assertEqual("uniform", status["scenario"])
            self.assertTrue(status["running"])
            observations = client.get(f"/sessions/{session_id}/observations").json()
            self.assertEqual(16, len(observations["signal_agents"]))
            self.assertEqual(4, len(observations["region_agents"]))
            self.assertTrue(all(len(value) == 46 for value in observations["signal_agents"].values()))
            self.assertTrue(all(len(value) == 10 for value in observations["region_agents"].values()))

            actions = {
                "av_actions": {},
                "signal_actions": {key: 0 for key in observations["signal_agents"]},
                "region_actions": {key: [0.5] * 4 for key in observations["region_agents"]},
            }
            accepted = client.post(f"/sessions/{session_id}/actions", json=actions)
            self.assertEqual({"accepted": True}, accepted.json())
            stepped = client.post(f"/sessions/{session_id}/step", json={"n_steps": 50})
            self.assertEqual(50.0, stepped.json()["sim_time"])
            self.assertIsInstance(client.get(f"/sessions/{session_id}/vehicles").json(), list)
            metrics = client.get(f"/sessions/{session_id}/metrics").json()
            self.assertEqual(
                {
                    "avg_travel_time", "avg_wait_time", "throughput", "fairness_index",
                    "co2_kg", "fuel_l", "max_queue_length",
                },
                set(metrics),
            )
            stopped = client.delete(f"/sessions/{session_id}")
            self.assertEqual({"stopped": True}, stopped.json())
            self.assertEqual(404, client.get(f"/sessions/{session_id}").status_code)

    def test_two_websocket_subscribers_receive_the_same_step(self) -> None:
        """Broadcast one state frame to two simultaneous read-only viewers."""
        with TestClient(app) as client:
            created = client.post(
                "/sessions",
                json={
                    "scenario": "surge",
                    "penetration_rate": 0.1,
                    "seed": 7,
                    "config_overrides": {},
                    "mode": "baseline",
                },
            )
            session_id = created.json()["session_id"]
            with (
                client.websocket_connect(f"/sessions/{session_id}/stream") as first,
                client.websocket_connect(f"/sessions/{session_id}/stream") as second,
            ):
                self.assertEqual(0.0, first.receive_json()["sim_time"])
                self.assertEqual(0.0, second.receive_json()["sim_time"])
                response = client.post(f"/sessions/{session_id}/step", json={"n_steps": 1})
                self.assertEqual(200, response.status_code)
                self.assertEqual(1.0, first.receive_json()["sim_time"])
                self.assertEqual(1.0, second.receive_json()["sim_time"])
            client.delete(f"/sessions/{session_id}")

    def test_two_sessions_step_independently(self) -> None:
        """Interleave two TraCI subprocesses without sharing simulation state."""
        with TestClient(app) as client:
            identifiers = []
            for seed in (17, 29):
                response = client.post(
                    "/sessions",
                    json={
                        "scenario": "uniform",
                        "penetration_rate": 0.05,
                        "seed": seed,
                        "config_overrides": {},
                        "mode": "baseline",
                    },
                )
                self.assertEqual(201, response.status_code, response.text)
                identifiers.append(response.json()["session_id"])
            try:
                first, second = identifiers
                self.assertEqual(
                    1.0,
                    client.post(f"/sessions/{first}/step", json={"n_steps": 1}).json()["sim_time"],
                )
                self.assertEqual(0.0, client.get(f"/sessions/{second}").json()["sim_time"])
                self.assertEqual(
                    2.0,
                    client.post(f"/sessions/{second}/step", json={"n_steps": 2}).json()["sim_time"],
                )
                self.assertEqual(1.0, client.get(f"/sessions/{first}").json()["sim_time"])
            finally:
                for session_id in identifiers:
                    client.delete(f"/sessions/{session_id}")

    def test_invalid_batches_and_overrides_are_rejected(self) -> None:
        """Reject malformed external input before creating or mutating SUMO state."""
        with TestClient(app) as client:
            bad_override = client.post(
                "/sessions",
                json={
                    "scenario": "uniform",
                    "penetration_rate": 0.2,
                    "seed": 1,
                    "config_overrides": {"unknown": 1},
                    "mode": "baseline",
                },
            )
            self.assertEqual(422, bad_override.status_code)
            malformed = client.post(
                "/sessions/not-real/actions",
                json={"av_actions": {"av": [1.0]}, "signal_actions": {}, "region_actions": {}},
            )
            self.assertEqual(422, malformed.status_code)


if __name__ == "__main__":
    unittest.main()
