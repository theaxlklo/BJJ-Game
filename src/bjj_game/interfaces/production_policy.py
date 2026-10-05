"""Canonical production Mount-v0 stamina/recovery policy.

The single entry point a playable frontend uses to request the adopted
production stamina/recovery semantics
(docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md):

    Rule 1 = ON   (UNFUNDED initiator cannot drain responder stamina)
    Rule 2 = OFF  (deferred; legacy hold settlement remains)
    Bottom RECOVER + Exhausted initiation = LOW
    Initiation after Exhausted clears     = baseline commitment (MEDIUM)
    Bottom RECOVER post-clear handoff     = D3-B (one Exhausted LOW token per
        armed Exhausted episode, then initiation lockout until the latch
        clears; docs/BURST_RECOVERY_LOCKOUT_D3B_RESULT.md)

Raw MountMatch / batch defaults are unchanged; callers opt in explicitly.
The policy selects only these stamina/recovery settings. It does not enable
v0.4a commitment semantics, v0.3b stalling, Recognition, scoring, or any
initiator commitment choice; those remain separate, composable decisions.

D3-B is a batch decision-window controller, not a MountMatch setting, so
match_settings() is unchanged; it is selected only under Bottom RECOVER, and
batch validation rejects RECOVER configurations outside the measured E-PROD
shape (no silent fallback).

GATE_G_STAMINA_RECOVERY_POLICY is the Gate-G adopted policy (no post-clear
handoff), frozen under its own name
(docs/BURST_RECOVERY_LOCKOUT_D3B_PROMOTION_PREREGISTRATION.md). Its output
depends only on its own immutable state, so historical controls keep
reproducing whatever the canonical policy selects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .batch import BatchBehaviorMode
from .handoff_policy import PostClearHandoffMode
from .recovery_policy import RecoveryInitiationMode


@dataclass(frozen=True, slots=True)
class ProductionStaminaRecoveryPolicy:
    """Production stamina/recovery policy (fixed instances; no runtime knobs).

    post_clear_handoff_mode is the Bottom RECOVER post-clear handoff. NONE is
    the Gate-G adopted policy.
    """

    post_clear_handoff_mode: PostClearHandoffMode = PostClearHandoffMode.NONE

    @property
    def unfunded_responder_cost_waiver(self) -> bool:
        return True

    @property
    def supplemental_hold_settlement(self) -> bool:
        return False

    @property
    def exhausted_recovery_initiation(self) -> RecoveryInitiationMode:
        return RecoveryInitiationMode.LOW_WHILE_EXHAUSTED

    def match_settings(self) -> dict:
        """Settlement settings for MountMatch (requires v0.4a semantics)."""
        return {
            "enable_stamina_settlement_rules": False,
            "enable_unfunded_responder_cost_waiver": (
                self.unfunded_responder_cost_waiver
            ),
            "enable_supplemental_hold_settlement": (
                self.supplemental_hold_settlement
            ),
        }

    def batch_settings(self, *, bottom_behavior_mode: BatchBehaviorMode) -> dict:
        """Settlement plus recovery-initiation settings for batch play.

        LOW recovery initiation is defined only for Bottom RECOVER. Without
        RECOVER no recovery-initiation policy is active, so CURRENT (the
        baseline commitment) is selected. A post-clear handoff mode, when the
        policy has one, is likewise selected only under RECOVER; batch
        validation rejects it outside the configuration it was measured on.
        """
        settings = {
            **self.match_settings(),
            "recovery_initiation_mode": (
                self.exhausted_recovery_initiation
                if bottom_behavior_mode is BatchBehaviorMode.RECOVER
                else RecoveryInitiationMode.CURRENT
            ),
        }
        if (
            bottom_behavior_mode is BatchBehaviorMode.RECOVER
            and self.post_clear_handoff_mode is not PostClearHandoffMode.NONE
        ):
            settings["post_clear_handoff_mode"] = self.post_clear_handoff_mode
        return settings


GATE_G_STAMINA_RECOVERY_POLICY = ProductionStaminaRecoveryPolicy(
    post_clear_handoff_mode=PostClearHandoffMode.NONE
)

PRODUCTION_STAMINA_RECOVERY_POLICY = ProductionStaminaRecoveryPolicy(
    post_clear_handoff_mode=PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT
)


def production_stamina_recovery_policy() -> ProductionStaminaRecoveryPolicy:
    return PRODUCTION_STAMINA_RECOVERY_POLICY
