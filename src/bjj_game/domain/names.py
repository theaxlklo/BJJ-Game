from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from .catalog import TechniqueCatalog
from .model import EntityKind, Side, TechniqueEntity

_SPACE_RE = re.compile(r"\s+")


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).lower()
    text = text.replace("+", " and ").replace("&", " and ")
    text = text.replace("_", " ").replace("-", " ")
    return _SPACE_RE.sub(" ", text).strip()


def _names_for(entity: TechniqueEntity) -> tuple[str, ...]:
    values = (entity.id, entity.canonical_name, entity.short_name, entity.legacy_name, *entity.aliases)
    return tuple(dict.fromkeys(values))


class NameResolver:
    def __init__(self, catalog: TechniqueCatalog) -> None:
        self.catalog = catalog
        buckets: dict[str, set[str]] = defaultdict(set)
        for entity in catalog.entities:
            for name in _names_for(entity):
                buckets[normalize_name(name)].add(entity.id)
        self._buckets = dict(buckets)

    def collision_map(self) -> dict[str, set[str]]:
        return {name: ids for name, ids in self._buckets.items() if len(ids) > 1}

    def resolve(self, value: str, *, kind: EntityKind | None = None, side: Side | None = None) -> TechniqueEntity:
        normalized = normalize_name(value)
        candidates = [self.catalog.get(entity_id) for entity_id in self._buckets.get(normalized, set())]
        if kind is not None:
            candidates = [entity for entity in candidates if entity.kind is kind]
        if side is not None:
            candidates = [entity for entity in candidates if entity.side is side]
        if not candidates:
            raise ValueError(f"Unknown Mount v0 name: {value!r}")
        if len(candidates) != 1:
            ids = ", ".join(sorted(entity.id for entity in candidates))
            raise ValueError(f"Ambiguous Mount v0 name {value!r}: {ids}")
        return candidates[0]
