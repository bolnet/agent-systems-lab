"""Tests for the Opus runner and the Experiment 5 pipeline. No network, no real CLI."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from context_clock.weightspace.claude_run import audit_stream, build_command, run_turn
from context_clock.weightspace.codex_run import CodexRunError
from context_clock.weightspace.exp5 import apply_and_save


def stream(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


INIT = {"type": "system", "subtype": "init", "tools": [], "mcp_servers": [], "model": "claude-opus-5-5"}
REPLY = {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}
DONE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "answer text",
    "usage": {"input_tokens": 5, "output_tokens": 2},
    "total_cost_usd": 0.1,
}


def test_command_switches_off_tools_settings_and_memory():
    command = build_command(("claude",), "xhigh", "Answer the user's request.\n")
    assert command[command.index("--model") + 1] == "claude-opus-5-5"
    assert command[command.index("--effort") + 1] == "xhigh"
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--setting-sources") + 1] == ""
    assert command[command.index("--system-prompt") + 1] == "Answer the user's request."
    assert "--strict-mcp-config" in command
    assert "--no-session-persistence" in command


def test_audit_accepts_a_turn_with_no_tools():
    audit = audit_stream(stream(INIT, REPLY, DONE))
    assert audit.tool_free is True
    assert audit.completed is True
    assert audit.usage["output_tokens"] == 2


def test_audit_flags_a_tool_on_offer():
    audit = audit_stream(stream({**INIT, "tools": ["Bash"]}, REPLY, DONE))
    assert audit.tool_free is False
    assert audit.tool_items == {"offered:Bash": 1}


def test_audit_flags_a_tool_call():
    call = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}}
    audit = audit_stream(stream(INIT, call, DONE))
    assert audit.tool_free is False
    assert audit.tool_items == {"called:Read": 1}


def test_audit_flags_a_failed_turn():
    assert audit_stream(stream(INIT, {**DONE, "is_error": True})).completed is False


def fake_runner(stdout, returncode=0):
    def run(command, **kwargs):
        run.kwargs = kwargs
        run.workdir_contents = list(Path(kwargs["cwd"]).iterdir())
        return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")

    return run


def test_run_turn_saves_answer_in_an_empty_folder_and_drops_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-pass")
    runner = fake_runner(stream(INIT, REPLY, DONE))
    record = run_turn("PROMPT", tmp_path / "run", ("claude",), "xhigh", "I", runner=runner)
    assert record.audit.tool_free is True
    assert runner.kwargs["input"] == "PROMPT"
    assert runner.workdir_contents == []
    assert "ANTHROPIC_API_KEY" not in runner.kwargs["env"]
    assert (tmp_path / "run" / "answer.md").read_text() == "answer text"
    for name in ("prompt.txt", "events.jsonl", "run.json"):
        assert (tmp_path / "run" / name).exists()


def test_run_turn_refuses_to_overwrite(tmp_path):
    (tmp_path / "run").mkdir()
    (tmp_path / "run" / "run.json").write_text("{}")
    with pytest.raises(CodexRunError, match="already"):
        run_turn("P", tmp_path / "run", ("claude",), "xhigh", "I", runner=fake_runner(""))


def test_run_turn_reports_a_failed_turn(tmp_path):
    runner = fake_runner(stream(INIT, {**DONE, "is_error": True, "result": "limit reached"}), 1)
    with pytest.raises(CodexRunError, match="limit reached"):
        run_turn("P", tmp_path / "run", ("claude",), "xhigh", "I", runner=runner)


def test_apply_and_save_writes_network_and_report(tmp_path):
    (tmp_path / "answer.md").write_text("```edits\nb3[0] = 2.5\nnonsense\n```\n")
    report = apply_and_save(tmp_path)
    assert report["found_block"] is True
    assert report["applied"] == 1
    assert len(report["errors"]) == 1
    assert report["nonzero_total"] == 1
    with np.load(tmp_path / "network.npz") as saved:
        assert saved["actor/logits/bias"][0] == 2.5
    assert json.loads((tmp_path / "apply.json").read_text())["applied"] == 1
