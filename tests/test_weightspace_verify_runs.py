"""Tests for the checker that re-derives every published result. No network, no model calls."""
import json
from pathlib import Path

import numpy as np
import pytest

from context_clock.weightspace.exp5 import apply_and_save
from context_clock.weightspace.verify_runs import (
    check_exp1,
    check_exp5,
    check_tool_free,
    verify_all,
)

ANSWER = "Design.\n\n```edits\nb3[0] = 5\n```\n"
PUBLISHED = Path("weightspace_runs")


def exp5_run(tmp_path, episodes=3):
    pytest.importorskip("minatar")
    from context_clock.weightspace.replicate import score_exp5

    (tmp_path / "answer.md").write_text(ANSWER)
    score_exp5(tmp_path, "breakout", episodes)
    return tmp_path


def test_exp5_passes_when_answer_network_and_score_agree(tmp_path):
    assert check_exp5(exp5_run(tmp_path), "breakout").passed


def test_exp5_fails_when_the_answer_no_longer_builds_the_saved_network(tmp_path):
    run = exp5_run(tmp_path)
    (run / "answer.md").write_text(ANSWER.replace("5", "6"))
    check = check_exp5(run, "breakout")
    assert not check.passed
    assert "network" in check.detail


def test_exp5_fails_when_the_recorded_score_was_changed(tmp_path):
    run = exp5_run(tmp_path)
    score = json.loads((run / "score.json").read_text())
    (run / "score.json").write_text(json.dumps({**score, "mean": score["mean"] + 1}))
    check = check_exp5(run, "breakout")
    assert not check.passed
    assert "score" in check.detail


def test_exp5_without_play_checks_only_the_network(tmp_path):
    (tmp_path / "answer.md").write_text(ANSWER)
    apply_and_save(tmp_path)
    (tmp_path / "score.json").write_text(json.dumps({"mean": 1.0, "se": 0.0, "episodes": 3}))
    assert check_exp5(tmp_path, "breakout", play=False).passed


def test_exp1_passes_and_fails_on_the_recorded_mark(tmp_path):
    (tmp_path / "answer.md").write_text("Game: Pong\nConfidence: 80%\n")
    (tmp_path / "score.json").write_text(json.dumps({"named": "pong", "correct": True, "confidence": 80}))
    assert check_exp1(tmp_path, "pong").passed
    (tmp_path / "score.json").write_text(json.dumps({"named": "pacman", "correct": True, "confidence": 80}))
    assert not check_exp1(tmp_path, "pong").passed


def test_tool_free_reads_the_run_record(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"audit": {"tool_free": False}}))
    assert not check_tool_free(tmp_path).passed


def test_published_runs_match_their_records_without_playing():
    checks = verify_all(PUBLISHED, play=False)
    assert len(checks) == 28  # 14 model turns, each with a result check and a tool audit
    assert [c for c in checks if not c.passed] == []


def test_published_networks_have_every_expected_array():
    with np.load(PUBLISHED / "opus/exp5/breakout/network.npz") as saved:
        assert saved["actor/dense1/kernel"].shape == (600, 32)
