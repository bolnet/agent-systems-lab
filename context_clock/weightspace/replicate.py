"""Run MIT's Experiments 1 and 5 on Opus or Astra with MIT's prompts, then score them.

Usage, from the repo root:
    python -m context_clock.weightspace.replicate --exp 5 --engine astra --game breakout \
        --mit DIR --out weightspace_runs
A finished turn is never asked again, so rerunning only repeats the scoring.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import claude_run, openrouter_run
from .exp5 import apply_and_save
from .minatar_eval import NPZ_NAMES, score_network
from .which_game import extract_answer, map_game

EXPERIMENTS = {
    1: ("exp1_which_game", "prompt.txt", "high", ("breakout", "pong", "pacman", "freeway")),
    5: ("exp5_write_from_scratch", "message.txt", "xhigh", ("breakout", "seaquest", "asterix")),
}


def _openrouter_key() -> str:
    """Read the key from the environment or the gitignored .env. Never logged."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    env = Path(".env")
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not found (env var or .env)")
    return key


def ask(engine: str, prompt: str, run_dir: Path, effort: str, instructions: str, root: Path) -> None:
    """Ask the chosen model once. Astra's budget covers everything under `root/astra`."""
    if engine == "opus":
        claude_run.run_turn(prompt, run_dir, ("claude",), effort, instructions)
    else:
        openrouter_run.run_turn(prompt, run_dir, effort, instructions, _openrouter_key(), root / "astra")


def score_exp1(run_dir: Path, game: str) -> dict:
    """Mark one Experiment 1 answer and save the mark."""
    line, confidence = extract_answer((run_dir / "answer.md").read_text(encoding="utf-8"))
    named = map_game(line) if line else None
    score = {
        "game": game, "line": line, "named": named,
        "correct": named == game, "confidence": confidence,
    }  # fmt: skip
    (run_dir / "score.json").write_text(json.dumps(score, indent=1), encoding="utf-8")
    return score


def score_exp5(run_dir: Path, game: str, episodes: int) -> dict:
    """Build the network from the reply, play it and save the score."""
    apply_and_save(run_dir)
    with np.load(run_dir / "network.npz") as saved:
        network = {short: saved[long_name] for short, long_name in NPZ_NAMES.items()}
    score = {"game": game, **asdict(score_network(game, network, episodes))}
    (run_dir / "score.json").write_text(json.dumps(score, indent=1), encoding="utf-8")
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp", required=True, type=int, choices=sorted(EXPERIMENTS))
    parser.add_argument("--engine", required=True, choices=("opus", "astra"))
    parser.add_argument("--game", required=True)
    parser.add_argument("--mit", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--episodes", type=int, default=1_000)
    args = parser.parse_args()
    folder, prompt_name, effort, games = EXPERIMENTS[args.exp]
    if args.game not in games:
        raise SystemExit(f"Experiment {args.exp} has no game {args.game}: {games}")
    source = args.mit / folder / "runs" / args.game
    run_dir = args.out / args.engine / f"exp{args.exp}" / args.game
    if not (run_dir / "run.json").exists():
        ask(
            args.engine,
            (source / prompt_name).read_text(encoding="utf-8"),
            run_dir,
            effort,
            (source / "instructions.md").read_text(encoding="utf-8"),
            args.out,
        )
    score = (
        score_exp1(run_dir, args.game)
        if args.exp == 1
        else score_exp5(run_dir, args.game, args.episodes)
    )
    print(json.dumps(score))


if __name__ == "__main__":
    main()
