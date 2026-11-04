"""Tests for the Codex runner and the Experiment 1 answer scorer. No network, no real Codex."""
import json
import subprocess
from pathlib import Path

import pytest

from context_clock.weightspace.codex_run import (
    CodexRunError,
    audit_events,
    build_command,
    prepare_codex_home,
    run_turn,
)
from context_clock.weightspace.which_game import extract_answer, map_game


def event_lines(*items, usage=None):
    rows = [{"type": "thread.started", "thread_id": "t1"}, {"type": "turn.started"}]
    rows += [{"type": "item.completed", "item": item} for item in items]
    rows.append({"type": "turn.completed", "usage": usage or {"input_tokens": 5, "output_tokens": 2}})
    return "\n".join(json.dumps(row) for row in rows) + "\n"


def test_command_carries_the_flags_mit_recorded():
    command = build_command(("codex",), "high", Path("/x/instructions.md"), Path("/x/answer.md"))
    assert command[:5] == ["codex", "exec", "--strict-config", "--skip-git-repo-check", "--json"]
    assert command[command.index("-m") + 1] == "gpt-6-astra"
    assert 'model_reasoning_effort="high"' in command
    assert "model_context_window=872000" in command
    assert "model_auto_compact_token_limit=1000000" in command
    assert 'model_reasoning_summary="detailed"' in command
    assert command[-1] == "-"


def test_audit_accepts_only_messages_reasoning_and_notices():
    clean = audit_events(event_lines({"type": "reasoning"}, {"type": "agent_message", "text": "hi"}))
    assert clean.tool_free is True
    assert clean.completed is True
    assert clean.usage["output_tokens"] == 2


def test_audit_flags_a_tool_call():
    dirty = audit_events(event_lines({"type": "command_execution"}, {"type": "agent_message"}))
    assert dirty.tool_free is False
    assert dirty.tool_items == {"command_execution": 1}


def test_audit_flags_an_unfinished_turn():
    assert audit_events('{"type": "turn.started"}\n').completed is False


def test_home_links_login_and_never_copies_it(tmp_path):
    auth = tmp_path / "auth.json"
    auth.write_text("{}")
    config = tmp_path / "config.toml"
    config.write_text('model = "x"\n')
    home = prepare_codex_home(tmp_path / "home", config, auth)
    assert (home / "config.toml").read_text() == 'model = "x"\n'
    assert (home / "auth.json").is_symlink()


def test_home_requires_a_login(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("")
    with pytest.raises(CodexRunError, match="codex login"):
        prepare_codex_home(tmp_path / "home", config, tmp_path / "missing.json")


def fake_runner(stdout, returncode=0, answer="Game: Pong"):
    def run(command, **kwargs):
        run.kwargs = kwargs
        run.workdir_contents = list(Path(kwargs["cwd"]).iterdir())
        Path(command[command.index("-o") + 1]).write_text(answer)
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")

    return run


def test_run_turn_saves_everything_in_an_empty_working_folder(tmp_path):
    runner = fake_runner(event_lines({"type": "agent_message"}))
    instructions = tmp_path / "i.md"
    instructions.write_text("Answer the user's request.\n")
    record = run_turn(
        "PROMPT", tmp_path / "run", ("codex",), "high", instructions, tmp_path / "home", runner=runner
    )
    assert record.audit.tool_free is True
    assert runner.kwargs["input"] == "PROMPT"
    assert runner.kwargs["env"]["CODEX_HOME"] == str(tmp_path / "home")
    assert Path(runner.kwargs["cwd"]) != tmp_path / "run"
    assert runner.workdir_contents == []
    for name in ("prompt.txt", "answer.md", "events.jsonl", "run.json"):
        assert (tmp_path / "run" / name).exists()
    assert json.loads((tmp_path / "run" / "run.json").read_text())["audit"]["tool_free"] is True


def test_run_turn_refuses_to_overwrite_an_existing_run(tmp_path):
    instructions = tmp_path / "i.md"
    instructions.write_text("x")
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "run.json").write_text("{}")
    with pytest.raises(CodexRunError, match="already"):
        run_turn("P", tmp_path / "run", ("codex",), "high", instructions, tmp_path / "h",
                 runner=fake_runner(""))


def test_run_turn_reports_failure_with_stderr(tmp_path):
    instructions = tmp_path / "i.md"
    instructions.write_text("x")

    def failing(command, **kwargs):
        return subprocess.CompletedProcess(command, 3, stdout="", stderr="model not available")

    with pytest.raises(CodexRunError, match="model not available"):
        run_turn("P", tmp_path / "run", ("codex",), "high", instructions, tmp_path / "h", runner=failing)


@pytest.mark.parametrize(
    "line,game",
    [
        ("Breakout, a small grid-based brick-breaking variant", "breakout"),
        ("Pong, most likely a single-player wall-Pong variant", "pong"),
        ("Pac-Man, or a simplified grid-based Pac-Man clone", "pacman"),
        ("Frogger, a simplified grid-based traffic-crossing variant", "freeway"),
        ("Freeway", "freeway"),
        ("Tetris", None),
    ],
)
def test_game_keywords_match_the_published_answers(line, game):
    assert map_game(line) == game


def test_extract_answer_reads_game_and_confidence():
    text = "Observations...\n\n**Game:** Pong, a variant\n\nDescription: x\n\nConfidence: 96%\n"
    assert extract_answer(text) == ("Pong, a variant", 96)


@pytest.mark.parametrize(
    "text",
    [
        "## Game\n\n**Breakout — a brick-breaker.**\n\n## Description\nx\n\n## Confidence\n\n**98%**\n",
        "## Game:\n**Breakout — a brick-breaker.**\n\n## Confidence:\n98%\n",
        "**Game:** Breakout — a brick-breaker.\n\nConfidence: 98%\n",
    ],
)
def test_extract_answer_reads_heading_and_inline_forms(text):
    assert extract_answer(text) == ("Breakout — a brick-breaker.", 98)


def test_extract_answer_ignores_the_word_game_in_prose():
    text = "## Observations\nA game with paddles.\nThis game is fun\n"
    assert extract_answer(text) == (None, None)


def test_extract_answer_handles_a_reply_with_no_game_line():
    assert extract_answer("I cannot tell.") == (None, None)
