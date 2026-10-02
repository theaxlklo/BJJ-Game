from __future__ import annotations

from dataclasses import dataclass, field

from .model import Behavior, BottomBehavior, Side, TopBehavior
from .stamina import StaminaPool


@dataclass(slots=True)
class Competitor:
    """A grappler participating in a match.

    Competitor owns player-specific changing state. v0 uses behavior; v0.1 adds
    stamina/commitment here rather than threading them through every engine call.
    """

    side: Side
    name: str
    behavior: Behavior
    stamina: StaminaPool = field(default_factory=StaminaPool)

    def __post_init__(self) -> None:
        self.set_behavior(self.behavior)

    def set_behavior(self, behavior: Behavior) -> None:
        if self.side is Side.TOP and not isinstance(behavior, TopBehavior):
            raise ValueError("Top competitor requires a TopBehavior")
        if self.side is Side.BOTTOM and not isinstance(behavior, BottomBehavior):
            raise ValueError("Bottom competitor requires a BottomBehavior")
        self.behavior = behavior
