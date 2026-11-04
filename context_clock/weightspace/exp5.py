"""Experiment 5: build the network a model's reply describes and report on it."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .edits import apply_reply
from .minatar_eval import NPZ_NAMES


def apply_and_save(run_dir: Path) -> dict:
    """Build the network the reply describes and save it with a report next to the answer."""
    result = apply_reply((run_dir / "answer.md").read_text(encoding="utf-8"))
    nonzero = {name: int(np.count_nonzero(array)) for name, array in result.network.items()}
    report = {
        "found_block": result.found_block,
        "applied": result.applied,
        "errors": list(result.errors),
        "nonzero": nonzero,
        "nonzero_total": sum(nonzero.values()),
        "max_abs": {name: float(np.abs(a).max()) for name, a in result.network.items()},
    }
    np.savez(run_dir / "network.npz", **{NPZ_NAMES[k]: v for k, v in result.network.items()})
    (run_dir / "apply.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report
