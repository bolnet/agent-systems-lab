"""Tests for the MinAtar observation map and scorer used in Experiment 5."""
import numpy as np
import pytest

from context_clock.weightspace.edits import blank_network
from context_clock.weightspace.minatar_eval import CHANNEL_MAP, forward, to_observation

pytest.importorskip("minatar")

from minatar import Environment

from context_clock.weightspace.minatar_eval import score_network


def test_observation_index_matches_prompt_formula():
    env = Environment("breakout", sticky_action_prob=0.1)
    env.seed(1)
    env.reset()
    obs = to_observation("breakout", env.state(), env.env.channels)
    assert obs.shape == (600,)
    paddle_index = (9 * 10 + env.env.pos) * 6 + 0
    ball_index = (env.env.ball_y * 10 + env.env.ball_x) * 6 + 3
    assert obs[paddle_index] == 1
    assert obs[ball_index] == 1
    assert obs[1::6].sum() == 0
    assert obs[5::6].sum() == 0


def test_cell_is_one_when_any_source_channel_is_one():
    names = sorted({name for group in CHANNEL_MAP["seaquest"] for name in group})
    channels = {name: i for i, name in enumerate(names)}
    state = np.zeros((10, 10, len(channels)), dtype=bool)
    state[4, 5, channels["enemy_fish"]] = True
    obs = to_observation("seaquest", state, channels)
    cell = (4 * 10 + 5) * 6
    assert obs[cell + 1] == 1
    assert obs[cell + 2] == 1
    assert obs[cell + 0] == 0


def test_every_mapped_channel_exists_in_the_real_game():
    for game, groups in CHANNEL_MAP.items():
        env = Environment(game, sticky_action_prob=0.1)
        assert len(groups) == 6
        assert {name for group in groups for name in group} == set(env.env.channels)


def test_forward_computes_the_published_formula():
    net = blank_network()
    net["b3"][4] = 5.0
    net["W1"][0, 0] = 100.0
    net["W2"][0, 0] = 100.0
    net["W3"][0, 2] = 3.0
    obs = np.zeros((2, 600), dtype=np.float32)
    obs[0, 0] = 1
    logits = forward(net, obs)
    assert logits.shape == (2, 6)
    assert logits[0, 2] == pytest.approx(3.0)
    assert logits[1, 2] == pytest.approx(0.0)
    assert logits[1, 4] == pytest.approx(5.0)


def test_zero_network_gets_a_finite_score_and_is_reproducible():
    first = score_network("breakout", blank_network(), episodes=8, seed=3)
    second = score_network("breakout", blank_network(), episodes=8, seed=3)
    assert first == second
    assert first.episodes == 8
    assert first.mean >= 0
    assert first.se >= 0
