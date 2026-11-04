"""Run one tool-free GPT-6 Astra turn through the Codex CLI, as MIT's `run.json` files record it.

Uses the owner's OpenAI subscription login. Each turn runs from a new empty folder with MIT's
no-tools config, and its event stream is audited afterwards the way MIT describes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

MODEL = "gpt-6-astra"
ALLOWED_ITEMS = frozenset({"reasoning", "agent_message", "error"})
TURN_TIMEOUT_SECONDS = 3_600
DEFAULT_AUTH = Path.home() / ".codex" / "auth.json"


class CodexRunError(RuntimeError):
    """A turn could not be run or would overwrite an earlier run."""


@dataclass(frozen=True)
class Audit:
    """What the event stream of one turn contains."""

    tool_free: bool
    completed: bool
    item_types: dict[str, int]
    tool_items: dict[str, int]
    usage: dict[str, int]


@dataclass(frozen=True)
class TurnRecord:
    """The saved record of one turn."""

    model: str
    effort: str
    wall_s: float
    return_code: int
    command: tuple[str, ...]
    audit: Audit


def build_command(
    codex: tuple[str, ...], effort: str, instructions: Path, answer: Path
) -> list[str]:
    """Return the command line MIT recorded in `run.json`."""
    return [
        *codex, "exec", "--strict-config", "--skip-git-repo-check", "--json",
        "-m", MODEL,
        "-c", f'model_reasoning_effort="{effort}"',
        "-c", "model_context_window=872000",
        "-c", "model_auto_compact_token_limit=1000000",
        "-c", f'model_instructions_file="{instructions}"',
        "-o", str(answer),
        "-c", 'model_reasoning_summary="detailed"',
        "-",
    ]  # fmt: skip


def audit_events(stream: str) -> Audit:
    """Classify a turn's events. Any item other than messages or reasoning counts as a tool."""
    items: Counter[str] = Counter()
    usage: dict[str, int] = {}
    completed = False
    for line in stream.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") == "item.completed":
            items[event.get("item", {}).get("type", "unknown")] += 1
        elif event.get("type") == "turn.completed":
            completed = True
            usage = dict(event.get("usage") or {})
    tools = {name: count for name, count in items.items() if name not in ALLOWED_ITEMS}
    return Audit(not tools, completed, dict(items), tools, usage)


def prepare_codex_home(home: Path, config: Path, auth: Path = DEFAULT_AUTH) -> Path:
    """Make a Codex home holding MIT's config and a link to the owner's login."""
    if not auth.exists():
        raise CodexRunError(f"no login at {auth}: run `codex login` first")
    home.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config, home / "config.toml")
    link = home / "auth.json"
    if not link.is_symlink():
        link.symlink_to(auth)
    return home


def run_turn(
    prompt: str,
    run_dir: Path,
    codex: tuple[str, ...],
    effort: str,
    instructions: Path,
    codex_home: Path,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> TurnRecord:
    """Run one turn, save its files in `run_dir` and return the record."""
    if (run_dir / "run.json").exists():
        raise CodexRunError(f"run already recorded in {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    answer = run_dir.resolve() / "answer.md"
    command = build_command(codex, effort, instructions.resolve(), answer)
    environment = {**os.environ, "CODEX_HOME": str(codex_home)}
    with tempfile.TemporaryDirectory(prefix="wsp-turn-") as workdir:
        started = time.monotonic()
        result = runner(
            command, input=prompt, cwd=workdir, env=environment,
            capture_output=True, text=True, timeout=TURN_TIMEOUT_SECONDS,
        )  # fmt: skip
        wall = time.monotonic() - started
    (run_dir / "events.jsonl").write_text(result.stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise CodexRunError(
            f"codex exited {result.returncode}: {result.stderr.strip()[-500:]} "
            f"{result.stdout.strip()[-500:]}"
        )
    record = TurnRecord(MODEL, effort, round(wall, 1), result.returncode, tuple(command),
                        audit_events(result.stdout))  # fmt: skip
    (run_dir / "run.json").write_text(json.dumps(asdict(record), indent=1), encoding="utf-8")
    return record
