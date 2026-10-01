from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .model import Grade


@dataclass(frozen=True, slots=True)
class MatchupTable:
    """Immutable hand-authored deterministic action/response lookup table."""

    entries: Mapping[tuple[str, str], Grade]

    @classmethod
    def build(cls, entries: Mapping[tuple[str, str], Grade]) -> "MatchupTable":
        return cls(MappingProxyType(dict(entries)))

    def grade(self, action_id: str, response_id: str) -> Grade:
        try:
            return self.entries[(action_id, response_id)]
        except KeyError as exc:
            raise ValueError(
                f"No matchup entry for {action_id!r} vs {response_id!r}"
            ) from exc
