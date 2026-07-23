"""M7 in-process simultaneous three-role PPO training entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from agents.networks import AVPolicyValueNetwork, RegionalPolicyValueNetwork, SignalPolicyValueNetwork
from agents.ppo import PPOTrainer, SignalPPOTrainer
from agents.rollout_buffer import RolloutBuffer
from api_client.simulator_client import DEFAULT_SIMULATOR_URL, SimulatorClient
from env.observation_builder import AV_OBSERVATION_SIZE, REGION_OBSERVATION_SIZE, SIGNAL_OBSERVATION_SIZE


def run_joint_iteration(
    scenario: str,
    steps: int,
    config: dict[str, Any],
    networks: tuple[AVPolicyValueNetwork, SignalPolicyValueNetwork, RegionalPolicyValueNetwork],
    trainers: tuple[PPOTrainer, SignalPPOTrainer, PPOTrainer] | None = None,
    *,
    penetration_rate: float = 0.05,
    seed: int = 42,
    simulator_url: str = DEFAULT_SIMULATOR_URL,
) -> dict[str, float]:
    """Collect and update all policies through the external simulator API."""
    av_network, signal_network, region_network = networks
    av_trainer, signal_trainer, region_trainer = trainers or (
        PPOTrainer(av_network, config["ppo"]),
        SignalPPOTrainer(signal_network, config["ppo"]),
        PPOTrainer(region_network, config["ppo"]),
    )
    av_buffer, signal_buffer, region_buffer = RolloutBuffer(), RolloutBuffer(), RolloutBuffer()
    pending_av: dict[str, tuple[list[float], list[float], float, float]] = {}
    pending_signal: dict[str, tuple[list[float], int, float, float]] = {}
    pending_region: dict[str, tuple[list[float], list[float], float, float]] = {}
    environment = SimulatorClient(
        scenario,
        penetration_rate,
        seed,
        base_url=simulator_url,
        mode="trained",
    )
    observations = environment.reset()
    try:
        for _ in range(steps):
            actions: dict[str, int | list[float]] = {}
            signal_ids = environment.signal_agent_ids
            for agent_id, observation in observations.items():
                if agent_id.startswith("region_"):
                    action, log_probability, value = region_trainer.act(observation)
                    actions[agent_id] = action
                    pending_region[agent_id] = (observation, action, log_probability, value)
                elif agent_id in signal_ids:
                    action, log_probability, value = signal_trainer.act(observation)
                    actions[agent_id] = action
                    pending_signal[agent_id] = (observation, action, log_probability, value)
                else:
                    action, log_probability, value = av_trainer.act(observation)
                    actions[agent_id] = action
                    pending_av[agent_id] = (observation, action, log_probability, value)
            observations, rewards, terminations, _, _ = environment.step(actions)
            for agent_id, reward in rewards.items():
                if agent_id in pending_region:
                    observation, action, log_probability, value = pending_region.pop(agent_id)
                    region_buffer.add(
                        agent_id, observation, action, log_probability, reward, value,
                        terminations.get(agent_id, False),
                    )
                elif agent_id in pending_signal:
                    observation, action, log_probability, value = pending_signal.pop(agent_id)
                    signal_buffer.add(
                        agent_id, observation, action, log_probability, reward, value,
                        terminations.get(agent_id, False),
                    )
                elif agent_id in pending_av:
                    observation, action, log_probability, value = pending_av.pop(agent_id)
                    av_buffer.add(
                        agent_id, observation, action, log_probability, reward, value,
                        terminations.get(agent_id, False),
                    )
    finally:
        environment.close()
    if not av_buffer.rewards or not signal_buffer.rewards or not region_buffer.rewards:
        raise RuntimeError("Joint rollout must contain transitions for all three roles")
    gamma = float(config["ppo"]["gamma"])
    gae_lambda = float(config["ppo"]["gae_lambda"])
    signal_ids = environment.signal_agent_ids
    av_bootstrap = {
        agent_id: av_trainer.value(observation)
        for agent_id, observation in observations.items()
        if agent_id not in signal_ids and not agent_id.startswith("region_")
    }
    signal_bootstrap = {
        agent_id: signal_trainer.value(observation)
        for agent_id, observation in observations.items()
        if agent_id in signal_ids
    }
    region_bootstrap = {
        agent_id: region_trainer.value(observation)
        for agent_id, observation in observations.items()
        if agent_id.startswith("region_")
    }
    av_result = av_trainer.update(
        av_buffer.as_batch(gamma, gae_lambda, av_bootstrap)
    )
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
    return {
        "av_loss": av_result["loss"],
        "signal_loss": signal_result["loss"],
        "region_loss": region_result["loss"],
        "av_transitions": float(len(av_buffer.rewards)),
        "signal_transitions": float(len(signal_buffer.rewards)),
        "region_transitions": float(len(region_buffer.rewards)),
    }


def train(
    iterations: int,
    steps: int,
    penetration_rate: float,
    output_dir: Path,
    artifact_group: str | None = None,
    simulator_url: str | None = None,
) -> list[dict[str, Any]]:
    """Run curriculum training against the configured simulator service."""
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    torch.manual_seed(int(config["demand"]["seed"]))
    networks = (
        AVPolicyValueNetwork(AV_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
        SignalPolicyValueNetwork(SIGNAL_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
        RegionalPolicyValueNetwork(REGION_OBSERVATION_SIZE, config["ppo"]["hidden_sizes"]),
    )
    trainers = (
        PPOTrainer(networks[0], config["ppo"]),
        SignalPPOTrainer(networks[1], config["ppo"]),
        PPOTrainer(networks[2], config["ppo"]),
    )
    scenarios = list(config["training"]["curriculum_scenarios"])
    service_url = simulator_url or os.environ.get("SIMULATOR_API_URL", DEFAULT_SIMULATOR_URL)
    logs: list[dict[str, Any]] = []
    for iteration in range(iterations):
        scenario = scenarios[iteration % len(scenarios)]
        metrics = run_joint_iteration(
            scenario,
            steps,
            config,
            networks,
            trainers,
            penetration_rate=penetration_rate,
            seed=int(config["demand"]["seed"]) + iteration,
            simulator_url=service_url,
        )
        log = {
            "iteration": iteration,
            "scenario": scenario,
            "penetration_rate": penetration_rate,
            "training_mode": "curriculum",
            **metrics,
        }
        logs.append(log)
        print(json.dumps(log, sort_keys=True))
        if (iteration + 1) % int(config["ppo"]["checkpoint_interval_iterations"]) == 0:
            output_dir.mkdir(parents=True, exist_ok=True)
            for name, network in zip(("av", "signals", "regions"), networks):
                torch.save(
                    network.state_dict(),
                    output_dir / (
                        f"m7_{name}_p{int(penetration_rate * 100):02d}_"
                        f"iter{iteration + 1:04d}.pt"
                    ),
                )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, network in zip(("av", "signals", "regions"), networks):
        torch.save(network.state_dict(), output_dir / f"m7_{name}_p{int(penetration_rate * 100):02d}.pt")
    return logs


def main(argv: Sequence[str] | None = None) -> int:
    """Run joint training using the confirmed curriculum mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--penetration-rate", type=float)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "checkpoints")
    parser.add_argument("--artifact-group")
    parser.add_argument("--simulator-url")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    train(
        int(args.iterations if args.iterations is not None else config["training"]["iterations"]),
        int(args.steps if args.steps is not None else config["training"]["rollout_steps"]),
        float(
            args.penetration_rate
            if args.penetration_rate is not None
            else config["demand"]["penetration_rate"]
        ),
        args.output_dir.resolve(),
        args.artifact_group,
        args.simulator_url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
