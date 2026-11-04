"""Score Experiment 1 answers: map a reply's `Game:` line to a game by keywords, as MIT describes."""
from __future__ import annotations

import re

# Frogger counts as Freeway, per MIT's README. MIT did not publish the full keyword list.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "breakout": ("breakout", "arkanoid", "brick"),
    "pong": ("pong",),
    "pacman": ("pac-man", "pacman", "pac man"),
    "freeway": ("freeway", "frogger", "road-crossing", "road crossing"),
}
# Replies write either `Game: X` or a `## Game` heading with X on a later line.
_GAME_LINE = re.compile(
    r"^(?:[\s*#_]*game[\s*_]*:|#+\s*game\s*$)[\s*_]*(.+?)[\s*_]*$", re.IGNORECASE | re.MULTILINE
)
_CONFIDENCE = re.compile(r"confidence[\s*_:]*~?(\d{1,3})", re.IGNORECASE)


def map_game(line: str) -> str | None:
    """Return the game named first in the line, or None if it names none of the four."""
    lowered = line.lower()
    hits = [
        (position, game)
        for game, words in KEYWORDS.items()
        for word in words
        if (position := lowered.find(word)) >= 0
    ]
    return min(hits)[1] if hits else None


def extract_answer(text: str) -> tuple[str | None, int | None]:
    """Return the reply's last `Game:` line and its confidence, as far as present."""
    games = _GAME_LINE.findall(text)
    confidence = _CONFIDENCE.findall(text)
    return (
        games[-1] if games else None,
        int(confidence[-1]) if confidence else None,
    )
