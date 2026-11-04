"""Run one tool-free GPT-6 Astra turn through OpenRouter, for owners whose plan refuses it in Codex.

Same model, prompt and instructions as MIT's Codex runs; what differs is the path to the model.
Stdlib only. The reply is streamed so a long think cannot hit an idle timeout, and the output limit
is set per turn so the worst case stays inside the budget. Nothing is retried once a reply starts,
because a retry at that point could be billed twice.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .codex_run import Audit, CodexRunError
from .openrouter_settings import (
    BUDGET_USD,
    CHARS_PER_TOKEN,
    INPUT_USD_PER_TOKEN,
    MAX_OUTPUT_TOKENS,
    MIN_OUTPUT_TOKENS,
    MODEL,
    OUTPUT_USD_PER_TOKEN,
    STREAM_TIMEOUT_SECONDS,
    URL,
)

_CONNECT_ATTEMPTS = 3
_BACKOFF_SECONDS = 20


def spent(root: Path) -> float:
    """Return the billed dollars recorded by every finished turn under `root`."""
    return sum(
        json.loads(path.read_text()).get("cost_usd") or 0.0 for path in root.rglob("run.json")
    )


def allowed_output_tokens(prompt: str, spent_usd: float, cap_usd: float) -> int:
    """Return the output limit that keeps this turn's worst case inside the cap."""
    input_cost = len(prompt) / CHARS_PER_TOKEN * INPUT_USD_PER_TOKEN
    left = cap_usd - spent_usd - input_cost
    return min(MAX_OUTPUT_TOKENS, max(0, round(left / OUTPUT_USD_PER_TOKEN)))


def _open_stream(payload: bytes, key: str, opener: Callable) -> Any:
    """Open the request, retrying only rate limits and server errors."""
    request = urllib.request.Request(
        URL,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    for attempt in range(_CONNECT_ATTEMPTS):
        try:
            return opener(request, timeout=STREAM_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as error:
            transient = error.code == 429 or error.code >= 500
            if not transient or attempt == _CONNECT_ATTEMPTS - 1:
                detail = error.read().decode("utf-8", "replace")[:500]
                raise CodexRunError(f"OpenRouter HTTP {error.code}: {detail}") from error
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
    raise CodexRunError("OpenRouter could not be reached")


def _read_stream(stream: Any) -> tuple[str, str, dict, str | None]:
    """Collect content and reasoning. Returns them with the final chunk and any stream error."""
    content: list[str] = []
    reasoning: list[str] = []
    final: dict = {}
    for raw in stream:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        chunk = json.loads(line[len("data: "):])
        if "error" in chunk:
            return "".join(content), "".join(reasoning), final, str(chunk["error"])
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            content.append(delta.get("content") or "")
            reasoning.append(delta.get("reasoning") or "")
            if choice.get("finish_reason"):
                final = {**final, "finish_reason": choice["finish_reason"]}
        if chunk.get("usage"):
            final = {**final, "usage": chunk["usage"], "model": chunk.get("model")}
    return "".join(content), "".join(reasoning), final, None


def run_turn(
    prompt: str,
    run_dir: Path,
    effort: str,
    instructions: str,
    key: str,
    budget_root: Path,
    cap_usd: float = BUDGET_USD,
    opener: Callable = urllib.request.urlopen,
) -> dict:
    """Run one turn, save its files in `run_dir` and return the saved record."""
    if (run_dir / "run.json").exists():
        raise CodexRunError(f"run already recorded in {run_dir}")
    limit = allowed_output_tokens(prompt, spent(budget_root), cap_usd)
    if limit < MIN_OUTPUT_TOKENS:
        raise CodexRunError(
            f"budget: ${spent(budget_root):.2f} of ${cap_usd:.2f} spent, too little left for this turn"
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": instructions.strip()},
                {"role": "user", "content": prompt},
            ],
            "reasoning": {"effort": effort},
            "max_tokens": limit,
            "usage": {"include": True},
            "stream": True,
        }
    ).encode("utf-8")
    started = time.monotonic()
    with _open_stream(payload, key, opener) as stream:
        content, reasoning, final, error = _read_stream(stream)
    wall = round(time.monotonic() - started, 1)
    (run_dir / "reasoning.txt").write_text(reasoning, encoding="utf-8")
    if error:
        (run_dir / "partial.md").write_text(content, encoding="utf-8")
        raise CodexRunError(f"stream failed after {wall}s: {error}")
    (run_dir / "answer.md").write_text(content, encoding="utf-8")
    usage = final.get("usage") or {}
    record = {
        "model": MODEL,
        "route": "openrouter",
        "served_by": final.get("model"),
        "effort": effort,
        "max_tokens": limit,
        "wall_s": wall,
        "finish_reason": final.get("finish_reason"),
        "cost_usd": usage.get("cost"),
        "audit": asdict(Audit(True, final.get("finish_reason") == "stop", {}, {}, usage)),
    }
    (run_dir / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record
