from __future__ import annotations

from dataclasses import dataclass

from .model import Side


@dataclass(slots=True)
class Competitor:
    """A grappler participating in a match.

    v0 intentionally stores only identity and side. Stamina, belt, style, attributes,
    injuries and run traits attach here in later versions rather than being scattered
    across position-specific engines.
    """

    side: Side
    name: str
