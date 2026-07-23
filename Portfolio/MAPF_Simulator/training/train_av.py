"""M4 isolated AV PPO training smoke entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.networks import AVPolicyValueNetwork
from agents.ppo import PPOTrainer
from agents.rollout_buffer import RolloutBuffer
from env.multi_agent_env import AVOnlyParallelEnv
from env.observation_builder import AV_OBSERVATION_SIZE


def train_av(steps: int, output: Path) -> dict[str, float]:
    """Collect an AV-only rollout, execute PPO, and save a checkpoint."""
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    network = AVPolicyValueNetwork(AV_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"])
    trainer = PPOTrainer(network, config["ppo"])
    buffer = RolloutBuffer()
    environment = AVOnlyParallelEnv("surge")
    observations = environment.reset()
    pending: dict[str, tuple[list[float], list[float], float, float]] = {}
    try:
        for _ in range(steps):
            actions: dict[str, list[float]] = {}
            for agent_id, observation in observations.items():
                action, log_probability, value = trainer.act(observation)
                actions[agent_id] = action
                pending[agent_id] = (observation, action, log_probability, value)
            observations, rewards, _, _, _ = environment.step(actions)
            for agent_id, reward in rewards.items():
                if agent_id in pending:
                    observation, action, log_probability, value = pending[agent_id]
                    buffer.add(agent_id, observation, action, log_probability, reward, value)
            if len(buffer.rewards) >= int(config["ppo"]["minibatch_size"]):
                break
    finally:
        environment.close()
    if not buffer.rewards:
        raise RuntimeError("No AV transitions were collected")
    bootstrap_values = {
        agent_id: trainer.value(observation)
        for agent_id, observation in observations.items()
    }
    metrics = trainer.update(
        buffer.as_batch(
            float(config["ppo"]["gamma"]),
            float(config["ppo"]["gae_lambda"]),
            bootstrap_values,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    import torch

    torch.save(network.state_dict(), output)
    return {**metrics, "transitions": float(len(buffer.rewards))}


def main(argv: Sequence[str] | None = None) -> int:
    """Run a short M4 AV-only PPO update."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "checkpoints" / "m4_av.pt")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    steps = int(args.steps if args.steps is not None else config["training"]["rollout_steps"])
    print(json.dumps(train_av(steps, args.output.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
