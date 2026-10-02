from __future__ import annotations

import random
from dataclasses import dataclass

from ..domain.model import Side, TechniqueEntity
from ..positions.mount.catalog import (
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
    TOP_RESPONSE_WIDE_MOUNT_BASE,
    ENTITY_BY_ID,
)


@dataclass(frozen=True, slots=True)
class BlindResponseChoice:
    ordinal: int
    responder: Side
    response_id: str
    draw: int
    total_weight: int

    @property
    def response(self) -> TechniqueEntity:
        return ENTITY_BY_ID[self.response_id]


class RandomBlindResponder:
    """Deterministic solo responder for blind hot-seat playtests.

    The fixed mixes come from the raw simultaneous-game analysis used to seed
    v0.1e playtests. Zero-weight responses are deliberately absent.
    """

    POLICY: dict[Side, tuple[tuple[str, int], ...]] = {
        Side.BOTTOM: (
            (BOTTOM_RESPONSE_FOREARM_FRAME, 4),
            (BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE, 3),
        ),
        Side.TOP: (
            (TOP_RESPONSE_WIDE_MOUNT_BASE, 2),
            (TOP_RESPONSE_HIP_FOLLOW_REPUMMEL, 1),
        ),
    }

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        self._ordinal = 0

    @classmethod
    def mix_description(cls, side: Side) -> str:
        parts = []
        for response_id, weight in cls.POLICY[side]:
            response = ENTITY_BY_ID[response_id]
            parts.append(f"{response.short_name}={weight}")
        return ", ".join(parts)

    def choose(self, responder: Side) -> BlindResponseChoice:
        weighted = self.POLICY[responder]
        total = sum(weight for _, weight in weighted)
        draw = self._rng.randrange(total)

        cursor = 0
        selected_id = weighted[-1][0]
        for response_id, weight in weighted:
            cursor += weight
            if draw < cursor:
                selected_id = response_id
                break

        self._ordinal += 1
        return BlindResponseChoice(
            ordinal=self._ordinal,
            responder=responder,
            response_id=selected_id,
            draw=draw,
            total_weight=total,
        )
