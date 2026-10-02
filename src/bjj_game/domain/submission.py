from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SubmissionStage(str, Enum):
    THREAT = "Threat"
    CONTROL = "Control"
    FINISH = "Finish"


@dataclass(frozen=True, slots=True)
class SubmissionChange:
    before: SubmissionStage | None
    after: SubmissionStage | None
    tapped: bool = False


@dataclass(slots=True)
class SubmissionState:
    stage: SubmissionStage | None = None

    @property
    def active(self) -> bool:
        return self.stage is not None

    def start(self) -> SubmissionChange:
        before = self.stage
        self.stage = SubmissionStage.THREAT
        return SubmissionChange(before=before, after=self.stage)

    def defend(self) -> SubmissionChange:
        before = self.stage
        if before is None:
            raise RuntimeError("Cannot defend an inactive submission track")
        if before is SubmissionStage.THREAT:
            self.stage = None
        elif before is SubmissionStage.CONTROL:
            self.stage = SubmissionStage.THREAT
        else:
            self.stage = SubmissionStage.CONTROL
        return SubmissionChange(before=before, after=self.stage)

    def advance(self) -> SubmissionChange:
        before = self.stage
        if before is None:
            raise RuntimeError("Cannot advance an inactive submission track")
        if before is SubmissionStage.THREAT:
            self.stage = SubmissionStage.CONTROL
            return SubmissionChange(before=before, after=self.stage)
        if before is SubmissionStage.CONTROL:
            self.stage = SubmissionStage.FINISH
            return SubmissionChange(before=before, after=self.stage)
        return SubmissionChange(before=before, after=before, tapped=True)
