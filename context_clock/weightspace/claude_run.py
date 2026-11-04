"""Run one tool-free Opus turn through `claude -p`, the counterpart of `codex_run` for Astra.

Uses the owner's Claude subscription, so any API key in the environment is dropped. Tools, settings,
hooks, MCP servers and session history are all off, and the turn runs from a new empty folder.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from .codex_run import Audit, CodexRunError, TurnRecord

MODEL = "claude-opus-5-5"
TURN_TIMEOUT_SECONDS = 3_600
MAX_OUTPUT_TOKENS = "128000"
_DROPPED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE")


def build_command(claude: tuple[str, ...], effort: str, instructions: str) -> list[str]:
    """Return the command line. The prompt goes on stdin."""
    return [
        *claude, "-p",
        "--model", MODEL,
        "--effort", effort,
        "--tools", "",
        "--setting-sources", "",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--system-prompt", instructions.strip(),
        "--output-format", "stream-json",
        "--verbose",
    ]  # fmt: skip


def _final_event(stream: str) -> dict:
    """Return the stream's `result` event, or an empty dict."""
    for line in reversed(stream.splitlines()):
        if line.strip():
            event = json.loads(line)
            if event.get("type") == "result":
                return event
    return {}


def audit_stream(stream: str) -> Audit:
    """Classify a turn's events. A tool offered or called makes the turn not tool-free."""
    blocks: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    for line in stream.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") == "system" and event.get("subtype") == "init":
            tools.update(f"offered:{name}" for name in event.get("tools", []))
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                blocks[block.get("type", "unknown")] += 1
                if block.get("type") == "tool_use":
                    tools[f"called:{block.get('name')}"] += 1
    final = _final_event(stream)
    completed = bool(final) and not final.get("is_error", True)
    return Audit(not tools, completed, dict(blocks), dict(tools), dict(final.get("usage") or {}))


def run_turn(
    prompt: str,
    run_dir: Path,
    claude: tuple[str, ...],
    effort: str,
    instructions: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> TurnRecord:
    """Run one turn, save its files in `run_dir` and return the record."""
    if (run_dir / "run.json").exists():
        raise CodexRunError(f"run already recorded in {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    command = build_command(claude, effort, instructions)
    environment = {k: v for k, v in os.environ.items() if k not in _DROPPED_ENV}
    environment["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = MAX_OUTPUT_TOKENS
    with tempfile.TemporaryDirectory(prefix="wsp-turn-") as workdir:
        started = time.monotonic()
        result = runner(
            command, input=prompt, cwd=workdir, env=environment,
            capture_output=True, text=True, timeout=TURN_TIMEOUT_SECONDS,
        )  # fmt: skip
        wall = time.monotonic() - started
    (run_dir / "events.jsonl").write_text(result.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
    final = _final_event(result.stdout)
    audit = audit_stream(result.stdout)
    if result.returncode != 0 or not audit.completed:
        detail = final.get("result") or result.stderr.strip()[-500:] or result.stdout.strip()[-500:]
        raise CodexRunError(f"claude exited {result.returncode}: {detail}")
    (run_dir / "answer.md").write_text(final.get("result") or "", encoding="utf-8")
    record = TurnRecord(MODEL, effort, round(wall, 1), result.returncode, tuple(command), audit)
    (run_dir / "run.json").write_text(json.dumps(asdict(record), indent=1), encoding="utf-8")
    return record
