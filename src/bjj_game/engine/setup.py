from __future__ import annotations

from dataclasses import dataclass

from ..domain.model import ResolutionResult
from ..positions.mount.catalog import (
    BOTTOM_BRIDGE,
    BOTTOM_RESPONSE_FOREARM_FRAME,
    BOTTOM_RESPONSE_TURN_IN_RECOVERY,
    BOTTOM_TRAP_AND_ROLL_ESCAPE,
    TOP_AMERICANA_ARM_ISOLATION,
    TOP_HIGH_MOUNT_CLIMB,
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
)


@dataclass(frozen=True, slots=True)
class SetupRule:
    builder_action_id: str
    target_action_id: str
    ready_response_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MountSetupPolicy:
    rules: tuple[SetupRule, ...]

    @classmethod
    def default(cls) -> "MountSetupPolicy":
        return cls(
            rules=(
                SetupRule(
                    builder_action_id=BOTTOM_BRIDGE,
                    target_action_id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
                    ready_response_ids=(TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,),
                ),
                SetupRule(
                    builder_action_id=TOP_HIGH_MOUNT_CLIMB,
                    target_action_id=TOP_AMERICANA_ARM_ISOLATION,
                    ready_response_ids=(
                        BOTTOM_RESPONSE_FOREARM_FRAME,
                        BOTTOM_RESPONSE_TURN_IN_RECOVERY,
                    ),
                ),
            )
        )

    @property
    def target_action_ids(self) -> tuple[str, ...]:
        return tuple(rule.target_action_id for rule in self.rules)

    def rule_for_builder(self, action_id: str) -> SetupRule | None:
        return next(
            (rule for rule in self.rules if rule.builder_action_id == action_id),
            None,
        )

    def rule_for_target(self, action_id: str) -> SetupRule | None:
        return next(
            (rule for rule in self.rules if rule.target_action_id == action_id),
            None,
        )

    def target_for_builder(self, action_id: str) -> str | None:
        rule = self.rule_for_builder(action_id)
        return rule.target_action_id if rule is not None else None

    def ready_response_ids(self, action_id: str) -> tuple[str, ...] | None:
        rule = self.rule_for_target(action_id)
        return rule.ready_response_ids if rule is not None else None

    def setup_advances_from(self, result: ResolutionResult) -> bool:
        """A designated builder creates setup pressure even when answered.

        v0.2a originally advanced only on Success+, which let a perfect
        responder deny Ready forever by repeating the builder's best counter.
        For the minimal setup chains, the builder itself represents forcing a
        reaction: Bridge makes Top commit base/posture, and High Mount Climb
        makes Bottom commit defensive structure. The local exchange grade still
        controls axis movement; setup pressure is a separate state signal.

        Correct-response disruption/decay is intentionally a later v0.2 rule.
        """
        return self.rule_for_builder(result.action_id) is not None


DEFAULT_MOUNT_SETUP_POLICY = MountSetupPolicy.default()
