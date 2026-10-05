"""Canonical production Mount-v0 stamina/recovery policy.

The single entry point a playable frontend uses to request the adopted
production stamina/recovery semantics
(docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md):

    Rule 1 = ON   (UNFUNDED initiator cannot drain responder stamina)
    Rule 2 = OFF  (deferred; legacy hold settlement remains)
    Bottom RECOVER + Exhausted initiation = LOW
    Initiation after Exhausted clears     = baseline commitment (MEDIUM)

Raw MountMatch / batch defaults are unchanged; callers opt in explicitly.
The policy selects only these stamina/recovery settings. It does not enable
v0.4a commitment semantics, v0.3b stalling, Recognition, scoring, or any
initiator commitment choice; those remain separate, composable decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .batch import BatchBehaviorMode
from .recovery_policy import RecoveryInitiationMode


@dataclass(frozen=True, slots=True)
class ProductionStaminaRecoveryPolicy:
    """Adopted production stamina/recovery policy (fixed; no knobs)."""

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
        baseline commitment) is selected.
        """
        return {
            **self.match_settings(),
            "recovery_initiation_mode": (
                self.exhausted_recovery_initiation
                if bottom_behavior_mode is BatchBehaviorMode.RECOVER
                else RecoveryInitiationMode.CURRENT
            ),
        }


PRODUCTION_STAMINA_RECOVERY_POLICY = ProductionStaminaRecoveryPolicy()


def production_stamina_recovery_policy() -> ProductionStaminaRecoveryPolicy:
    return PRODUCTION_STAMINA_RECOVERY_POLICY
