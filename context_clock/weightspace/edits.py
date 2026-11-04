"""Reader for the `edits` weight language defined in MIT's Experiment 5 prompt.

MIT did not publish their reader, so this one follows the rules stated in the prompt. Replies are
model output, so values are parsed with `ast.literal_eval` and never executed.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

import numpy as np

SHAPES: dict[str, tuple[int, ...]] = {
    "W1": (600, 32),
    "b1": (32,),
    "W2": (32, 32),
    "b2": (32,),
    "W3": (32, 6),
    "b3": (6,),
}
MAX_ABS_VALUE = 1e6
_BLOCK = re.compile(r"^```edits[ \t]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
_STATEMENT = re.compile(r"^(\w+)\s*\[(.*?)\]\s*(=|\*=|\+=|-=)\s*(.+)$", re.DOTALL)


@dataclass(frozen=True)
class EditResult:
    """A network read from one reply, and how the reading went."""

    network: dict[str, np.ndarray]
    found_block: bool
    applied: int
    errors: tuple[str, ...]


def blank_network() -> dict[str, np.ndarray]:
    """Return a new network with every weight at 0, as the prompt specifies."""
    return {name: np.zeros(shape, dtype=np.float32) for name, shape in SHAPES.items()}


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def _join_continued_lines(body: str) -> list[str]:
    """Join lines so that a list left open continues into the following lines."""
    statements: list[str] = []
    pending = ""
    for raw in body.splitlines():
        line = _strip_comment(raw).strip()
        if not line:
            continue
        pending = f"{pending} {line}".strip()
        if pending.count("[") <= pending.count("]"):
            statements.append(pending)
            pending = ""
    if pending:
        statements.append(pending)
    return statements


def last_edits_block(text: str) -> list[str] | None:
    """Return the statements of the reply's last edits block, or None if it has none."""
    blocks = _BLOCK.findall(text)
    return _join_continued_lines(blocks[-1]) if blocks else None


def _parse_axis(token: str) -> int | slice:
    token = token.strip()
    if ":" not in token:
        return int(token)
    parts = [int(p) if p.strip() else None for p in token.split(":")]
    if len(parts) > 3:
        raise ValueError(f"bad range {token!r}")
    return slice(*parts)


def _parse_values(token: str) -> np.ndarray:
    values = np.asarray(ast.literal_eval(token.strip()), dtype=np.float64)
    if not np.all(np.isfinite(values)) or np.any(np.abs(values) > MAX_ABS_VALUE):
        raise ValueError(f"value outside |v| <= {MAX_ABS_VALUE:g}")
    return values


def _apply_statement(
    network: dict[str, np.ndarray], statement: str
) -> dict[str, np.ndarray]:
    """Return a new network with one statement applied, or raise ValueError."""
    match = _STATEMENT.match(statement)
    if match is None:
        raise ValueError("not a statement")
    name, index_text, operator, value_text = match.groups()
    if name not in network:
        raise ValueError(f"unknown tensor {name}")
    index = tuple(_parse_axis(token) for token in index_text.split(","))
    values = _parse_values(value_text)
    tensor = network[name].copy()
    target_shape = tensor[index].shape
    if values.ndim > 0 and values.shape != target_shape:
        raise ValueError(f"{values.shape} values for a {target_shape} range")
    if operator == "=":
        tensor[index] = values
    elif operator == "*=":
        tensor[index] = tensor[index] * values
    elif operator == "+=":
        tensor[index] = tensor[index] + values
    else:
        tensor[index] = tensor[index] - values
    return {**network, name: tensor}


def apply_reply(text: str) -> EditResult:
    """Read a reply's last edits block into a new network, skipping unreadable statements."""
    statements = last_edits_block(text)
    network = blank_network()
    if statements is None:
        return EditResult(network, False, 0, ())
    errors: list[str] = []
    applied = 0
    for statement in statements:
        try:
            network = _apply_statement(network, statement)
            applied += 1
        except (ValueError, SyntaxError, IndexError, TypeError) as exc:
            errors.append(f"{statement[:80]}: {exc}")
    return EditResult(network, True, applied, tuple(errors))
