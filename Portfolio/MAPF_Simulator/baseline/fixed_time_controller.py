"""Static fixed-time traffic signal controller from Section 7."""

from __future__ import annotations

from typing import Any


class FixedTimeController:
    """Select and initialize the generated static program at every signal."""

    def __init__(self, traci_api: Any, program_id: str = "0", initial_phase: int = 0) -> None:
        """Store the session-scoped TraCI API and fixed program selection."""
        self._traci = traci_api
        self.program_id = program_id
        self.initial_phase = initial_phase

    def initialize(self) -> None:
        """Reset all traffic lights to the same fixed cycle program and phase."""
        for signal_id in self._traci.trafficlight.getIDList():
            self._traci.trafficlight.setProgram(signal_id, self.program_id)
            self._traci.trafficlight.setPhase(signal_id, self.initial_phase)

    def step(self) -> None:
        """Retain the static SUMO program; no traffic-responsive action is applied."""
        return None

