"""Re-derive every published result from the saved replies. Makes no model calls and writes nothing.

Usage, from the repo root:
    python -m context_clock.weightspace.verify_runs             # replays every game, some minutes
    python -m context_clock.weightspace.verify_runs --no-play   # seconds: skips replaying the games
    python -m context_clock.weightspace.verify_runs --mit DIR   # also compares prompts with MIT's logs
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .edits import apply_reply
from .minatar_eval import load_npz, score_network
from .which_game import extract_answer, map_game

ENGINES = ("astra", "opus")
EXP1_GAMES = ("breakout", "pong", "pacman", "freeway")
EXP5_GAMES = ("breakout", "seaquest", "asterix")
MIT_PROMPTS = {
    "exp1": ("exp1_which_game", "prompt.txt"),
    "exp5": ("exp5_write_from_scratch", "message.txt"),
}


@dataclass(frozen=True)
class Check:
    """One check on one saved run."""

    run: str
    passed: bool
    detail: str


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_exp5(run_dir: Path, game: str, play: bool = True) -> Check:
    """Rebuild the network from the reply, then replay it and compare with the recorded score."""
    saved = load_npz(str(run_dir / "network.npz"))
    rebuilt = apply_reply((run_dir / "answer.md").read_text(encoding="utf-8")).network
    if not all(np.array_equal(saved[name], rebuilt[name]) for name in saved):
        return Check(str(run_dir), False, "network differs from the one the reply builds")
    recorded = _read_json(run_dir / "score.json")
    if not play:
        return Check(str(run_dir), True, f"network rebuilt, recorded mean {recorded['mean']:.3f}")
    score = score_network(game, saved, recorded["episodes"])
    if (score.mean, score.se) != (recorded["mean"], recorded["se"]):
        return Check(str(run_dir), False, f"score {score.mean:.3f}, recorded {recorded['mean']:.3f}")
    return Check(str(run_dir), True, f"network rebuilt, replayed mean {score.mean:.3f} +/- {score.se:.2f}")


def check_exp1(run_dir: Path, game: str) -> Check:
    """Mark the saved answer again and compare with the recorded mark."""
    line, confidence = extract_answer((run_dir / "answer.md").read_text(encoding="utf-8"))
    named = map_game(line) if line else None
    recorded = _read_json(run_dir / "score.json")
    mark = (named, named == game, confidence)
    passed = mark == (recorded["named"], recorded["correct"], recorded["confidence"])
    return Check(str(run_dir), passed, f"named {named}, correct {named == game}, confidence {confidence}%")


def check_tool_free(run_dir: Path) -> Check:
    """Read the tool audit saved when the turn ran."""
    passed = bool(_read_json(run_dir / "run.json")["audit"]["tool_free"])
    return Check(str(run_dir), passed, "no tools offered or called" if passed else "tools were available")


def check_prompt(run_dir: Path, experiment: str, game: str, mit: Path) -> Check:
    """Compare the prompt sent with the one in MIT's published logs, byte for byte."""
    folder, name = MIT_PROMPTS[experiment]
    same = (run_dir / "prompt.txt").read_bytes() == (mit / folder / "runs" / game / name).read_bytes()
    return Check(str(run_dir), same, "prompt identical to MIT's" if same else "prompt differs from MIT's")


def verify_all(root: Path, play: bool = True, mit: Path | None = None) -> list[Check]:
    """Run every check on every saved model turn under `root`."""
    checks: list[Check] = []
    plan = [("exp1", game) for game in EXP1_GAMES] + [("exp5", game) for game in EXP5_GAMES]
    for engine in ENGINES:
        for experiment, game in plan:
            run_dir = root / engine / experiment / game
            result = check_exp1(run_dir, game) if experiment == "exp1" else check_exp5(run_dir, game, play)
            checks += [result, check_tool_free(run_dir)]
            if mit is not None:
                checks.append(check_prompt(run_dir, experiment, game, mit))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=Path("weightspace_runs"))
    parser.add_argument("--no-play", action="store_true")
    parser.add_argument("--mit", type=Path)
    args = parser.parse_args()
    checks = verify_all(args.runs, not args.no_play, args.mit)
    for check in checks:
        print(f"{'PASS' if check.passed else 'FAIL'}  {check.run}  {check.detail}", flush=True)
    failed = sum(not check.passed for check in checks)
    print(f"{len(checks) - failed} of {len(checks)} checks passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
