"""Gate G and adoption verification for the canonical production policy.

Proves the canonical production stamina/recovery entry point reproduces the
already-measured PROPOSED-PRODUCTION diagnostic exactly on the matched
A / B / E-PROD seeds (DoD steps 20-23).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from inspect import Parameter, signature
from unittest import mock

from ..engine.match import MountMatch
from ..interfaces import batch as batch_module
from ..interfaces.batch import BatchBehaviorMode, BatchSummary, run_escape_first_batch
from ..interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
from ..interfaces.recovery_policy import RecoveryInitiationMode
from .stamina_adoption_candidate import (
    AdoptionGate,
    GateStatus,
    _surface_ab_kwargs,
    _surface_e_prod_kwargs,
    measure_adoption_gates,
)

POLICY_KEYS = frozenset(
    {
        "enable_stamina_settlement_rules",
        "enable_unfunded_responder_cost_waiver",
        "enable_supplemental_hold_settlement",
        "recovery_initiation_mode",
    }
)

SURFACES = ("A", "B", "E-PROD OFF+shadow", "E-PROD ON")


def diagnostic_kwargs(name: str) -> dict:
    if name == "A":
        return _surface_ab_kwargs("A public MATCH")
    if name == "B":
        return _surface_ab_kwargs("B trusts reads")
    if name == "E-PROD OFF+shadow":
        return _surface_e_prod_kwargs(stalling=False, shadow=True)
    if name == "E-PROD ON":
        return _surface_e_prod_kwargs(stalling=True, shadow=False)
    raise KeyError(name)


def canonical_kwargs(name: str) -> dict:
    """Same surface, with every stamina/recovery setting from the policy."""
    base = {
        key: value
        for key, value in diagnostic_kwargs(name).items()
        if key not in POLICY_KEYS
    }
    return {
        **base,
        **PRODUCTION_STAMINA_RECOVERY_POLICY.batch_settings(
            bottom_behavior_mode=base.get(
                "bottom_behavior_mode",
                BatchBehaviorMode.FIXED,
            )
        ),
    }


def effective_settings(kwargs: dict) -> dict:
    """Batch settings with omitted parameters resolved to their defaults.

    Explicit `recovery_initiation_mode=CURRENT` and an omitted (default
    CURRENT) mode are the same configuration.
    """
    defaults = {
        name: parameter.default
        for name, parameter in signature(run_escape_first_batch).parameters.items()
        if parameter.default is not Parameter.empty
    }
    return {**defaults, **kwargs}


def _match_gameplay_signature(match: MountMatch) -> tuple:
    return (
        match.history,
        match.clock_seconds,
        match.axis,
        match.band,
        match.initiator,
        match.position,
        match.top.stamina.current,
        match.top.stamina.band,
        match.bottom.stamina.current,
        match.bottom.stamina.band,
        match.top_behavior_stamina_meter,
        match.bottom_behavior_stamina_meter,
        match.exit_destination,
        match.exit_reason,
        match.setup_state,
        match.submission_state,
        match.submission_tapped,
        match.stalling_tracker,
        match.free_initiative_pending,
        match.free_initiative_beneficiary,
        match.enable_unfunded_responder_cost_waiver,
        match.enable_supplemental_hold_settlement,
        match.enable_stamina_settlement_rules,
    )


def _run_captured(kwargs: dict) -> tuple[BatchSummary, tuple[tuple, ...]]:
    created: list[MountMatch] = []

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        created.append(match)
        return match

    with mock.patch.object(batch_module, "MountMatch", factory):
        summary = run_escape_first_batch(**kwargs)
    return summary, tuple(_match_gameplay_signature(match) for match in created)


@dataclass(frozen=True, slots=True)
class EquivalenceResult:
    surface: str
    settings_equal: bool
    summary_equal: bool
    matches: int
    diverged_matches: int


@lru_cache(maxsize=1)
def canonical_equivalence() -> tuple[EquivalenceResult, ...]:
    results = []
    for name in SURFACES:
        diagnostic = diagnostic_kwargs(name)
        canonical = canonical_kwargs(name)
        diagnostic_summary, diagnostic_matches = _run_captured(diagnostic)
        canonical_summary, canonical_matches = _run_captured(canonical)
        results.append(
            EquivalenceResult(
                surface=name,
                settings_equal=(
                    effective_settings(canonical)
                    == effective_settings(diagnostic)
                ),
                summary_equal=canonical_summary == diagnostic_summary,
                matches=len(canonical_matches),
                diverged_matches=sum(
                    1
                    for left, right in zip(diagnostic_matches, canonical_matches)
                    if left != right
                )
                + abs(len(diagnostic_matches) - len(canonical_matches)),
            )
        )
    return tuple(results)


def measure_gate_g() -> AdoptionGate:
    results = canonical_equivalence()
    policy = PRODUCTION_STAMINA_RECOVERY_POLICY
    policy_ok = (
        policy.unfunded_responder_cost_waiver is True
        and policy.supplemental_hold_settlement is False
        and policy.exhausted_recovery_initiation
        is RecoveryInitiationMode.LOW_WHILE_EXHAUSTED
    )
    ok = policy_ok and all(
        result.settings_equal
        and result.summary_equal
        and result.matches == 100
        and result.diverged_matches == 0
        for result in results
    )
    return AdoptionGate(
        "G",
        "canonical production configuration matches measured candidate",
        GateStatus.PASS if ok else GateStatus.OPEN,
        (
            f"policy Rule1/Rule2/recovery="
            f"{policy.unfunded_responder_cost_waiver}/"
            f"{policy.supplemental_hold_settlement}/"
            f"{policy.exhausted_recovery_initiation.value}; "
            + "; ".join(
                f"{result.surface}: settings equal={result.settings_equal}, "
                f"summary equal={result.summary_equal}, "
                f"diverged={result.diverged_matches}/{result.matches}"
                for result in results
            )
        ),
    )


@lru_cache(maxsize=1)
def adoption_verification_gates() -> tuple[AdoptionGate, ...]:
    """Gates A-H with Gate G evaluated against the canonical entry point."""
    return tuple(
        measure_gate_g() if gate.letter == "G" else gate
        for gate in measure_adoption_gates()
    )


def adoption_state() -> str:
    gates = adoption_verification_gates()
    if all(gate.status is GateStatus.PASS for gate in gates):
        return "ADOPTED"
    return "CANDIDATE REJECTED / OPEN"
