"""Tests for the reader of the `edits` language in MIT's Experiment 5 prompt."""
import os
from pathlib import Path

import numpy as np
import pytest

from context_clock.weightspace.edits import apply_reply, blank_network, last_edits_block

MIT_LOGS = os.environ.get("WSP_MIT_LOGS")
GAMES = ("breakout", "seaquest", "asterix")
NPZ_NAMES = {
    "W1": "actor/dense1/kernel",
    "b1": "actor/dense1/bias",
    "W2": "actor/dense2/kernel",
    "b2": "actor/dense2/bias",
    "W3": "actor/logits/kernel",
    "b3": "actor/logits/bias",
}


def reply(*lines):
    return "Design notes.\n\n```edits\n" + "\n".join(lines) + "\n```\n"


def test_blank_network_is_all_zero_with_published_parameter_count():
    net = blank_network()
    assert sum(t.size for t in net.values()) == 20486
    assert all(not t.any() for t in net.values())


def test_only_the_last_block_is_read():
    text = "```edits\nb1[0] = 1\n```\nmore\n```edits\nb1[1] = 2\n```\n"
    assert last_edits_block(text) == ["b1[1] = 2"]


def test_prompt_examples_read_as_documented():
    result = apply_reply(reply(
        "W1[12, 0] = 2.5                     # one entry",
        "W1[0:6, 3] = [1, 0, -1, 0, 2, 0]",
        "b1[0:4] = -1",
        "W1[3:600:60, 0] = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]",
        "W2[0:2, 0:3] = [[1, -1, 0.5], [0, 2, 0]]",
        "W3[:, 2] = 3",
        "W3[:, 2] *= 2",
    ))
    assert result.errors == ()
    assert result.applied == 7
    assert result.network["W1"][12, 0] == 2.5
    assert result.network["W1"][0:6, 3].tolist() == [1, 0, -1, 0, 2, 0]
    assert result.network["b1"][0:4].tolist() == [-1, -1, -1, -1]
    assert result.network["W1"][543, 0] == 1
    assert result.network["W2"][0, 2] == 0.5
    assert result.network["W3"][0, 2] == 6


def test_list_may_continue_over_lines_and_allow_space_after_bracket():
    result = apply_reply(reply(
        "W2[0:2, 0:2] = [ [1, 2],   # first row",
        "                 [3, 4] ]",
    ))
    assert result.errors == ()
    assert result.network["W2"][1, 1] == 4


def test_later_statement_overwrites_earlier():
    assert apply_reply(reply("b1[0] = 1", "b1[0] = 2")).network["b1"][0] == 2


def test_bad_statement_is_skipped_and_reported_while_others_apply():
    result = apply_reply(reply(
        "nonsense here",
        "Q1[0] = 1",
        "b1[0:3] = [1, 2]",
        "b1[0] = 9999999",
        "b1[5] = 7",
    ))
    assert len(result.errors) == 4
    assert result.applied == 1
    assert result.network["b1"][5] == 7
    assert result.network["b1"][0] == 0


def test_code_in_values_is_never_executed():
    result = apply_reply(reply("b1[0] = __import__('os').getpid()"))
    assert len(result.errors) == 1
    assert result.network["b1"][0] == 0


def test_reply_without_block_is_reported():
    result = apply_reply("I decline to write weights.")
    assert result.found_block is False
    assert not any(t.any() for t in result.network.values())


def test_applying_does_not_mutate_a_shared_starting_network():
    apply_reply(reply("b1[0] = 1"))
    assert apply_reply(reply("b1[1] = 1")).network["b1"][0] == 0


@pytest.mark.skipif(not MIT_LOGS, reason="set WSP_MIT_LOGS to the extracted MIT logs")
@pytest.mark.parametrize("game", GAMES)
def test_published_reply_rebuilds_published_network_exactly(game):
    root = Path(MIT_LOGS) / "exp5_write_from_scratch"
    text = (root / "runs" / game / "reply" / "answer.md").read_text(encoding="utf-8")
    result = apply_reply(text)
    published = np.load(root / "networks" / game / "hand.npz")
    assert result.errors == ()
    for short, long_name in NPZ_NAMES.items():
        np.testing.assert_array_equal(result.network[short], published[long_name])
