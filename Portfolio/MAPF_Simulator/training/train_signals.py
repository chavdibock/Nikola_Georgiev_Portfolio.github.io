"""M5 isolated local-signal PPO training smoke entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from agents.networks import SignalPolicyValueNetwork
from agents.ppo import SignalPPOTrainer
from agents.rollout_buffer import RolloutBuffer
from env.observation_builder import SIGNAL_OBSERVATION_SIZE
from env.signal_env import SignalOnlyParallelEnv


def train_signals(steps: int, output: Path) -> dict[str, float]:
    """Collect local-signal transitions, run one PPO update, and checkpoint it."""
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    network = SignalPolicyValueNetwork(SIGNAL_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"])
    trainer = SignalPPOTrainer(network, config["ppo"])
    environment = SignalOnlyParallelEnv("surge")
    observations = environment.reset()
    buffer = RolloutBuffer()
    pending: dict[str, tuple[list[float], int, float, float]] = {}
    try:
        for _ in range(steps):
            actions: dict[str, int] = {}
            for agent_id, observation in observations.items():
                action, log_probability, value = trainer.act(observation)
                actions[agent_id] = action
                pending[agent_id] = (observation, action, log_probability, value)
            observations, rewards, terminations, _, _ = environment.step(actions)
            for agent_id, reward in rewards.items():
                if agent_id in pending:
                    observation, action, log_probability, value = pending[agent_id]
                    buffer.add(
                        agent_id,
                        observation,
                        action,
                        log_probability,
                        reward,
                        value,
                        terminations.get(agent_id, False),
                    )
                    pending.pop(agent_id, None)
            if len(buffer.rewards) >= int(config["ppo"]["minibatch_size"]):
                break
    finally:
        environment.close()
    if not buffer.rewards:
        raise RuntimeError("No signal transitions were collected")
    bootstrap_values = {
        agent_id: trainer.value(observation)
        for agent_id, observation in observations.items()
    }
    result = trainer.update(
        buffer.as_batch(
            float(config["ppo"]["gamma"]),
            float(config["ppo"]["gae_lambda"]),
            bootstrap_values,
            discrete_actions=True,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(network.state_dict(), output)
    return {**result, "transitions": float(len(buffer.rewards))}


def main(argv: Sequence[str] | None = None) -> int:
    """Run a short M5 signal-only PPO update."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "checkpoints" / "m5_signals.pt")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    steps = int(args.steps if args.steps is not None else config["training"]["rollout_steps"])
    print(json.dumps(train_signals(steps, args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
