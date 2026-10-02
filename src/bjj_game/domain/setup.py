from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class SetupTier(IntEnum):
    NONE = 0
    PARTIAL = 1
    READY = 2

    @property
    def display(self) -> str:
        return {
            SetupTier.NONE: "None",
            SetupTier.PARTIAL: "Partial",
            SetupTier.READY: "Ready",
        }[self]


@dataclass(frozen=True, slots=True)
class SetupChange:
    target_action_id: str
    before: SetupTier
    after: SetupTier


@dataclass(slots=True)
class SetupTrack:
    target_action_id: str
    tier: SetupTier = SetupTier.NONE

    @property
    def ready(self) -> bool:
        return self.tier is SetupTier.READY

    def advance(self) -> SetupChange:
        before = self.tier
        self.tier = SetupTier(min(int(SetupTier.READY), int(self.tier) + 1))
        return SetupChange(
            target_action_id=self.target_action_id,
            before=before,
            after=self.tier,
        )

    def consume(self) -> SetupChange:
        before = self.tier
        self.tier = SetupTier.NONE
        return SetupChange(
            target_action_id=self.target_action_id,
            before=before,
            after=self.tier,
        )


@dataclass(slots=True)
class SetupState:
    tracks: dict[str, SetupTrack] = field(default_factory=dict)

    @classmethod
    def for_targets(cls, target_action_ids: tuple[str, ...]) -> "SetupState":
        return cls(
            tracks={
                action_id: SetupTrack(target_action_id=action_id)
                for action_id in target_action_ids
            }
        )

    def tier(self, target_action_id: str) -> SetupTier:
        track = self.tracks.get(target_action_id)
        return track.tier if track is not None else SetupTier.NONE

    def is_ready(self, target_action_id: str) -> bool:
        return self.tier(target_action_id) is SetupTier.READY

    def advance(self, target_action_id: str) -> SetupChange:
        try:
            track = self.tracks[target_action_id]
        except KeyError as exc:
            raise ValueError(f"Unknown setup target: {target_action_id!r}") from exc
        return track.advance()

    def consume(self, target_action_id: str) -> SetupChange:
        try:
            track = self.tracks[target_action_id]
        except KeyError as exc:
            raise ValueError(f"Unknown setup target: {target_action_id!r}") from exc
        return track.consume()
