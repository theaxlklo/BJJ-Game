from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .model import EntityKind, Side, TechniqueEntity


@dataclass(frozen=True, slots=True)
class TechniqueCatalog:
    """Immutable indexed collection of technique/action/response definitions."""

    entities: tuple[TechniqueEntity, ...]
    by_id: Mapping[str, TechniqueEntity]

    @classmethod
    def build(cls, entities: Iterable[TechniqueEntity]) -> "TechniqueCatalog":
        frozen = tuple(entities)
        index = {entity.id: entity for entity in frozen}
        if len(index) != len(frozen):
            raise ValueError("Technique IDs must be unique")
        return cls(frozen, MappingProxyType(index))

    def actions_for(self, side: Side) -> tuple[TechniqueEntity, ...]:
        return tuple(
            entity for entity in self.entities
            if entity.kind is EntityKind.ACTION and entity.side is side
        )

    def responses_for(self, side: Side) -> tuple[TechniqueEntity, ...]:
        return tuple(
            entity for entity in self.entities
            if entity.kind is EntityKind.RESPONSE and entity.side is side
        )

    def get(self, entity_id: str) -> TechniqueEntity:
        try:
            return self.by_id[entity_id]
        except KeyError as exc:
            raise ValueError(f"Unknown technique entity: {entity_id!r}") from exc
