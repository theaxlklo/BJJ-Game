from __future__ import annotations

from dataclasses import dataclass

from .action import Commitment


@dataclass(frozen=True, slots=True)
class CommitmentRecognitionRead:
    """A defender's separate noisy reads of intent and funded capability."""

    true_requested: Commitment
    perceived_requested: Commitment
    true_effective: Commitment | None
    perceived_effective: Commitment | None
    intent_roll: int
    capability_roll: int

    @property
    def intent_exact(self) -> bool:
        return self.perceived_requested is self.true_requested

    @property
    def capability_exact(self) -> bool:
        return self.perceived_effective is self.true_effective


@dataclass(frozen=True, slots=True)
class CommitmentRecognitionPolicy:
    """Frozen v0.4b adjacent-only d6 Recognition policy."""

    requested_levels: tuple[Commitment, ...] = (
        Commitment.LOW,
        Commitment.MEDIUM,
        Commitment.HIGH,
    )
    effective_levels: tuple[Commitment | None, ...] = (
        None,
        Commitment.LOW,
        Commitment.MEDIUM,
        Commitment.HIGH,
    )

    @staticmethod
    def _validate_roll(roll: int) -> None:
        if roll < 1 or roll > 6:
            raise ValueError("recognition roll must be in 1..6")

    @classmethod
    def _shift(
        cls,
        value,
        *,
        levels: tuple,
        roll: int,
    ):
        cls._validate_roll(roll)
        index = levels.index(value)
        if roll == 1:
            index = max(0, index - 1)
        elif roll == 6:
            index = min(len(levels) - 1, index + 1)
        return levels[index]

    def read(
        self,
        *,
        requested: Commitment,
        effective: Commitment | None,
        intent_roll: int,
        capability_roll: int,
    ) -> CommitmentRecognitionRead:
        return CommitmentRecognitionRead(
            true_requested=requested,
            perceived_requested=self._shift(
                requested,
                levels=self.requested_levels,
                roll=intent_roll,
            ),
            true_effective=effective,
            perceived_effective=self._shift(
                effective,
                levels=self.effective_levels,
                roll=capability_roll,
            ),
            intent_roll=intent_roll,
            capability_roll=capability_roll,
        )


DEFAULT_COMMITMENT_RECOGNITION_POLICY = CommitmentRecognitionPolicy()
