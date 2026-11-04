"""Score a 600-32-32-6 network on MinAtar with the protocol stated in MIT's Experiment 5.

Protocol: mean score over 1,000 episodes, actions sampled from the softmax of the logits, sticky
actions 0.1, episodes cut at 10,000 steps. The channel map comes from the prompt's "THE INPUT".
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

STICKY_ACTION_PROB = 0.1
MAX_STEPS = 10_000
DEFAULT_EPISODES = 1_000
BATCH_SLOTS = 64
OBSERVATION_SIZE = 600

# game -> source channels for player, danger, reward, projectile, trail, gauge.
CHANNEL_MAP: dict[str, tuple[tuple[str, ...], ...]] = {
    "breakout": (("paddle",), (), ("brick",), ("ball",), ("trail",), ()),
    "seaquest": (
        ("sub_front", "sub_back"),
        ("enemy_fish", "enemy_sub", "enemy_bullet"),
        ("enemy_fish", "enemy_sub", "diver"),
        ("friendly_bullet",),
        ("trail", "sub_back"),
        ("oxygen_guage", "diver_guage"),
    ),
    "asterix": (("player",), ("enemy",), ("gold",), (), ("trail",), ()),
}
NPZ_NAMES = {
    "W1": "actor/dense1/kernel",
    "b1": "actor/dense1/bias",
    "W2": "actor/dense2/kernel",
    "b2": "actor/dense2/bias",
    "W3": "actor/logits/kernel",
    "b3": "actor/logits/bias",
}


@dataclass(frozen=True)
class Score:
    """Result of scoring one network, in the same fields as MIT's `minatar_eval.json`."""

    mean: float
    se: float
    episodes: int
    max: float
    mean_length: float


def to_observation(
    game: str, state: np.ndarray, channels: dict[str, int]
) -> np.ndarray:
    """Build the 600-number input: index = (row * 10 + column) * 6 + channel."""
    grid = np.zeros((10, 10, 6), dtype=np.float32)
    for target, sources in enumerate(CHANNEL_MAP[game]):
        if sources:
            indices = [channels[name] for name in sources]
            grid[:, :, target] = state[:, :, indices].any(axis=2)
    return grid.reshape(OBSERVATION_SIZE)


def forward(network: dict[str, np.ndarray], observations: np.ndarray) -> np.ndarray:
    """Compute the logits for a batch of observations."""
    h1 = np.tanh(observations @ network["W1"] + network["b1"])
    h2 = np.tanh(h1 @ network["W2"] + network["b2"])
    return h2 @ network["W3"] + network["b3"]


def _sample_actions(logits: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    centered = logits.astype(np.float64) - logits.max(axis=1, keepdims=True)
    probabilities = np.exp(centered)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    draws = rng.random((len(logits), 1))
    return (probabilities.cumsum(axis=1) < draws).sum(axis=1).clip(max=5)


def _new_episode(game: str, seed: int) -> object:
    from minatar import Environment

    env = Environment(game, sticky_action_prob=STICKY_ACTION_PROB)
    env.seed(seed)
    env.reset()
    return env


def score_network(
    game: str,
    network: dict[str, np.ndarray],
    episodes: int = DEFAULT_EPISODES,
    seed: int = 0,
) -> Score:
    """Play `episodes` games in batches and return the protocol's score."""
    rng = np.random.default_rng(seed)
    next_episode = 0
    slots: list[list] = []
    totals: list[float] = []
    lengths: list[int] = []
    while len(totals) < episodes:
        while len(slots) < BATCH_SLOTS and next_episode < episodes:
            slots.append([_new_episode(game, seed + next_episode), 0.0, 0])
            next_episode += 1
        observations = np.stack(
            [to_observation(game, s[0].state(), s[0].env.channels) for s in slots]
        )
        actions = _sample_actions(forward(network, observations), rng)
        remaining = []
        for slot, action in zip(slots, actions):
            reward, terminal = slot[0].act(int(action))
            slot[1] += float(reward)
            slot[2] += 1
            if terminal or slot[2] >= MAX_STEPS:
                totals.append(slot[1])
                lengths.append(slot[2])
            else:
                remaining.append(slot)
        slots = remaining
    scores = np.asarray(totals)
    return Score(
        mean=float(scores.mean()),
        se=float(scores.std(ddof=1) / np.sqrt(len(scores))) if len(scores) > 1 else 0.0,
        episodes=len(scores),
        max=float(scores.max()),
        mean_length=float(np.mean(lengths)),
    )


def load_npz(path: str) -> dict[str, np.ndarray]:
    """Load a network stored with MIT's array names."""
    with np.load(path) as data:
        return {short: data[long_name] for short, long_name in NPZ_NAMES.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, choices=sorted(CHANNEL_MAP))
    parser.add_argument("--npz", required=True)
    parser.add_argument("--episodes", type=int, default=DEFAULT_EPISODES)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    result = score_network(args.game, load_npz(args.npz), args.episodes, args.seed)
    print(json.dumps({"game": args.game, **asdict(result)}))


if __name__ == "__main__":
    main()
