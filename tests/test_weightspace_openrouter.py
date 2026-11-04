"""Tests for the Astra-through-OpenRouter runner and the Experiment 1 scoring. No network."""
import io
import json
import urllib.error

import pytest

from context_clock.weightspace.codex_run import CodexRunError
from context_clock.weightspace.openrouter_run import (
    allowed_output_tokens,
    run_turn,
    spent,
)
from context_clock.weightspace.replicate import score_exp1


def sse(*chunks):
    lines = [b": OPENROUTER PROCESSING\n"]
    for chunk in chunks:
        lines.append(b"data: " + json.dumps(chunk).encode() + b"\n")
    lines.append(b"data: [DONE]\n")
    return io.BytesIO(b"".join(lines))


def delta(**fields):
    return {"choices": [{"delta": fields, "finish_reason": None}]}


FINISH = {
    "model": "openai/gpt-6-astra",
    "choices": [{"delta": {}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 1.5},
}


class FakeOpen:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(json.loads(request.data))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_turn_saves_answer_reasoning_and_real_cost(tmp_path):
    opener = FakeOpen(sse(delta(reasoning="think "), delta(content="ans"), delta(content="wer"), FINISH))
    run = run_turn("P", tmp_path / "root" / "x", "xhigh", "I\n", "key", tmp_path / "root", opener=opener)
    sent = opener.requests[0]
    assert sent["model"] == "openai/gpt-6-astra"
    assert sent["reasoning"]["effort"] == "xhigh"
    assert sent["messages"] == [{"role": "system", "content": "I"}, {"role": "user", "content": "P"}]
    assert (tmp_path / "root/x/answer.md").read_text() == "answer"
    assert (tmp_path / "root/x/reasoning.txt").read_text() == "think "
    assert run["cost_usd"] == 1.5
    assert run["finish_reason"] == "stop"
    assert run["audit"]["tool_free"] is True
    assert spent(tmp_path / "root") == 1.5


def test_request_never_offers_tools(tmp_path):
    opener = FakeOpen(sse(delta(content="a"), FINISH))
    run_turn("P", tmp_path / "r" / "x", "high", "I", "key", tmp_path / "r", opener=opener)
    assert "tools" not in opener.requests[0]


def test_output_limit_keeps_worst_case_inside_the_cap():
    assert allowed_output_tokens("x" * 15, spent_usd=0.0, cap_usd=10.0) == 64_000
    limited = allowed_output_tokens("x" * 15_000, spent_usd=9.0, cap_usd=10.0)
    assert limited == 18_000  # $1 left, minus $0.10 of input at 1.5 chars per token, at $50/M


def test_turn_refused_when_budget_cannot_cover_it(tmp_path):
    previous = tmp_path / "r" / "old"
    previous.mkdir(parents=True)
    (previous / "run.json").write_text(json.dumps({"cost_usd": 9.99}))
    opener = FakeOpen()
    with pytest.raises(CodexRunError, match="budget"):
        run_turn("P" * 3000, tmp_path / "r" / "x", "high", "I", "key", tmp_path / "r", opener=opener)
    assert opener.requests == []


def test_retries_only_before_the_reply_starts(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    busy = urllib.error.HTTPError("u", 429, "busy", {}, io.BytesIO(b""))
    opener = FakeOpen(busy, sse(delta(content="a"), FINISH))
    run_turn("P", tmp_path / "r" / "x", "high", "I", "key", tmp_path / "r", opener=opener)
    assert len(opener.requests) == 2


def test_error_in_the_stream_fails_without_retry_or_record(tmp_path):
    opener = FakeOpen(sse(delta(content="partial"), {"error": {"message": "provider died"}}))
    with pytest.raises(CodexRunError, match="provider died"):
        run_turn("P", tmp_path / "r" / "x", "high", "I", "key", tmp_path / "r", opener=opener)
    assert len(opener.requests) == 1
    assert not (tmp_path / "r/x/run.json").exists()
    assert (tmp_path / "r/x/partial.md").read_text() == "partial"


def test_client_error_message_is_reported(tmp_path):
    bad = urllib.error.HTTPError("u", 400, "bad", {}, io.BytesIO(b'{"error": "no such effort"}'))
    with pytest.raises(CodexRunError, match="no such effort"):
        run_turn("P", tmp_path / "r" / "x", "high", "I", "key", tmp_path / "r", opener=FakeOpen(bad))


def test_finished_turn_is_never_overwritten(tmp_path):
    (tmp_path / "r/x").mkdir(parents=True)
    (tmp_path / "r/x/run.json").write_text("{}")
    with pytest.raises(CodexRunError, match="already"):
        run_turn("P", tmp_path / "r/x", "high", "I", "key", tmp_path / "r", opener=FakeOpen())


def test_exp1_score_marks_right_and_wrong(tmp_path):
    (tmp_path / "answer.md").write_text("Stuff\n\n**Game:** Frogger, a variant\n\nConfidence: 80%\n")
    assert score_exp1(tmp_path, "freeway") == {
        "game": "freeway", "line": "Frogger, a variant", "named": "freeway",
        "correct": True, "confidence": 80,
    }  # fmt: skip
    assert score_exp1(tmp_path, "pong")["correct"] is False
