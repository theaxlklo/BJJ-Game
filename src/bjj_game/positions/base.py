from __future__ import annotations

from abc import ABC, abstractmethod


class Position(ABC):
    """Base class for positional state owned by a match."""

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError
