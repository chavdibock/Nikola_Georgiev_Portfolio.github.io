"""M6 hierarchical signal/coordinator PPO smoke training."""

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

from agents.networks import RegionalPolicyValueNetwork, SignalPolicyValueNetwork
from agents.ppo import PPOTrainer, SignalPPOTrainer
from agents.rollout_buffer import RolloutBuffer
from env.hierarchical_signal_env import HierarchicalSignalParallelEnv
from env.observation_builder import REGION_OBSERVATION_SIZE, SIGNAL_OBSERVATION_SIZE


def train_hierarchy(steps: int, output_dir: Path) -> dict[str, float]:
    """Jointly update shared local and regional policies in the M6 environment."""
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    signal_network = SignalPolicyValueNetwork(SIGNAL_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"])
    region_network = RegionalPolicyValueNetwork(REGION_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"])
    signal_trainer = SignalPPOTrainer(signal_network, config["ppo"])
    region_trainer = PPOTrainer(region_network, config["ppo"])  # same clipped math for Beta actions
    environment = HierarchicalSignalParallelEnv("surge")
    observations = environment.reset()
    signal_pending: dict[str, tuple[list[float], int, float, float]] = {}
    region_pending: dict[str, tuple[list[float], list[float], float, float]] = {}
    signal_buffer = RolloutBuffer()
    region_buffer = RolloutBuffer()
    try:
        for _ in range(steps):
            actions: dict[str, int | list[float]] = {}
            for agent_id, observation in observations.items():
                if agent_id.startswith("region_"):
                    action, log_probability, value = region_trainer.act(observation)
                    actions[agent_id] = action
                    region_pending[agent_id] = (observation, action, log_probability, value)
                else:
                    action, log_probability, value = signal_trainer.act(observation)
                    actions[agent_id] = action
                    signal_pending[agent_id] = (observation, action, log_probability, value)
            observations, rewards, terminations, _, _ = environment.step(actions)
            for agent_id, reward in rewards.items():
                if agent_id.startswith("region_") and agent_id in region_pending:
                    observation, action, log_probability, value = region_pending.pop(agent_id)
                    region_buffer.add(
                        agent_id, observation, action, log_probability, reward, value,
                        terminations.get(agent_id, False),
                    )
                elif agent_id in signal_pending:
                    observation, action, log_probability, value = signal_pending.pop(agent_id)
                    signal_buffer.add(
                        agent_id, observation, action, log_probability, reward, value,
                        terminations.get(agent_id, False),
                    )
    finally:
        environment.close()
    if not signal_buffer.rewards or not region_buffer.rewards:
        raise RuntimeError("Both signal and regional transitions are required")
    gamma = float(config["ppo"]["gamma"])
    gae_lambda = float(config["ppo"]["gae_lambda"])
    signal_bootstrap = {
        agent_id: signal_trainer.value(observation)
        for agent_id, observation in observations.items()
        if not agent_id.startswith("region_")
    }
    region_bootstrap = {
        agent_id: region_trainer.value(observation)
        for agent_id, observation in observations.items()
        if agent_id.startswith("region_")
    }
    signal_result = signal_trainer.update(
        signal_buffer.as_batch(
            gamma,
            gae_lambda,
            signal_bootstrap,
            discrete_actions=True,
        )
    )
    region_result = region_trainer.update(
        region_buffer.as_batch(gamma, gae_lambda, region_bootstrap)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(signal_network.state_dict(), output_dir / "m6_signals.pt")
    torch.save(region_network.state_dict(), output_dir / "m6_regions.pt")
    return {
        "signal_loss": signal_result["loss"],
        "region_loss": region_result["loss"],
        "signal_transitions": float(len(signal_buffer.rewards)),
        "region_transitions": float(len(region_buffer.rewards)),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run M6 hierarchical smoke training."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "checkpoints")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    steps = int(args.steps if args.steps is not None else config["training"]["rollout_steps"])
    print(json.dumps(train_hierarchy(steps, args.output_dir.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
