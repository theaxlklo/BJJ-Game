"""Stage-2 Rule1-only + LOW production-candidate measurement.

Implements the PROPOSED-PRODUCTION diagnostic configuration and the frozen
Gate A-H / A1-A10 evaluation from
docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md, using the A9
values frozen in docs/STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md.

This is a diagnostic configuration only. It changes no default and is not
the canonical production entry point (DoD steps 20-21 follow only if Gates
A-F pass and the user authorizes promotion).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
from statistics import median

from ..engine.stalling import STALLING_THRESHOLD_SECONDS
from ..interfaces.batch import (
    BatchSummary,
    ReExhaustionHandoffEpisode,
    run_escape_first_batch,
)
from ..interfaces.recovery_policy import RecoveryInitiationMode
from .stamina_adoption_handoff import (
    A9_MIN_ADMISSIBLE_CLEARS,
    HorizonCounts,
    MatchLevelSensitivity,
    horizon_counts,
    match_level_sensitivity,
    surface_report,
    HandoffSurfaceReport,
)
from .stamina_economy import StaminaEconomySurface, _measurement, _surface_kwargs
from .stamina_recovery_policy import (
    RecoveryCandidateCell,
    SettlementAttributionCell,
    SettlementAttributionMode,
    _attribution_cell,
    _candidate_cell,
    _candidate_kwargs,
    _cell,
    _default_activation_ok,
    _first_divergence_for_match,
    _gameplay_summary_signature,
    attribution_compatibility,
)

# Frozen in STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md.
A9_FROZEN_N_SECONDS = 10
A9_FROZEN_X = 0.975034786099515
A9_FROZEN_P_BASELINE = 59 / 63
A9_BASELINE_P_MATCH = 58 / 61

ORIGINAL_BASE_SEED = 42
EXT_100_BASE_SEED = 142

E_LABEL = "E trusts reads + Bottom RECOVER"

PROPOSED_PRODUCTION_SETTLEMENT = {
    "enable_stamina_settlement_rules": False,
    "enable_unfunded_responder_cost_waiver": True,
    "enable_supplemental_hold_settlement": False,
}

# Recovery LOW applies only where Bottom uses RECOVER (Surface E-PROD); the
# batch rejects non-CURRENT recovery modes elsewhere, and the DoD states LOW
# is irrelevant on Surfaces A and B.
PROPOSED_PRODUCTION_DIAGNOSTIC = {
    **PROPOSED_PRODUCTION_SETTLEMENT,
    "recovery_initiation_mode": RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
}


def _surface_ab_kwargs(label: str) -> dict:
    return {
        **_surface_kwargs(label),
        **PROPOSED_PRODUCTION_SETTLEMENT,
        "measure_stamina_economy": True,
    }


def _surface_e_prod_kwargs(
    *,
    stalling: bool,
    shadow: bool,
    base_seed: int = ORIGINAL_BASE_SEED,
) -> dict:
    return {
        **_candidate_kwargs(
            RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
            stalling=stalling,
            shadow=shadow,
        ),
        **PROPOSED_PRODUCTION_DIAGNOSTIC,
        "base_seed": base_seed,
        "measure_reexhaustion_handoffs": True,
    }


@lru_cache(maxsize=None)
def candidate_surface(name: str) -> BatchSummary:
    if name == "A":
        return run_escape_first_batch(**_surface_ab_kwargs("A public MATCH"))
    if name == "B":
        return run_escape_first_batch(**_surface_ab_kwargs("B trusts reads"))
    if name == "E-PROD OFF+shadow":
        return run_escape_first_batch(
            **_surface_e_prod_kwargs(stalling=False, shadow=True)
        )
    if name == "E-PROD OFF plain":
        return run_escape_first_batch(
            **_surface_e_prod_kwargs(stalling=False, shadow=False)
        )
    if name == "E-PROD ON":
        return run_escape_first_batch(
            **_surface_e_prod_kwargs(stalling=True, shadow=False)
        )
    if name == "E-PROD OFF+shadow EXT-100":
        return run_escape_first_batch(
            **_surface_e_prod_kwargs(
                stalling=False,
                shadow=True,
                base_seed=EXT_100_BASE_SEED,
            )
        )
    raise KeyError(name)


def settlement_cell(name: str) -> SettlementAttributionCell:
    label = {
        "A": "A public MATCH",
        "B": "B trusts reads",
        "E-PROD OFF+shadow": E_LABEL,
        "E-PROD ON": E_LABEL,
    }[name]
    return _attribution_cell(
        StaminaEconomySurface(label=label, summary=candidate_surface(name)),
        SettlementAttributionMode.RULE1_ONLY,
    )


def recovery_cell(name: str) -> RecoveryCandidateCell:
    stalling = name == "E-PROD ON"
    return _candidate_cell(
        StaminaEconomySurface(label=name, summary=candidate_surface(name)),
        RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        stalling=stalling,
        shadow=name == "E-PROD OFF+shadow",
    )


# ---------------------------------------------------------------------------
# A9 candidate verdict (frozen rule)
# ---------------------------------------------------------------------------


class A9Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNSCOREABLE = "UNSCOREABLE"


@dataclass(frozen=True, slots=True)
class A9CandidateResult:
    original_at_n: HorizonCounts
    ext_triggered: bool
    ext_at_n: HorizonCounts | None
    pooled_at_n: HorizonCounts
    p_candidate: float | None
    verdict: A9Verdict
    sensitivity: MatchLevelSensitivity

    @property
    def p_episode_minus_baseline(self) -> float | None:
        if self.p_candidate is None:
            return None
        return self.p_candidate - A9_FROZEN_P_BASELINE


def a9_verdict(admissible: int, reexhausted: int) -> tuple[float | None, A9Verdict]:
    """Frozen A9 rule: admissible >= 43 and unrounded p <= X (inclusive)."""
    if admissible < A9_MIN_ADMISSIBLE_CLEARS:
        p = reexhausted / admissible if admissible else None
        return p, A9Verdict.UNSCOREABLE
    p = reexhausted / admissible
    return p, A9Verdict.PASS if p <= A9_FROZEN_X else A9Verdict.FAIL


def ext_100_triggered(original_admissible_at_n: int) -> bool:
    """Sample-adequacy trigger only: original admissible clears at N < 43."""
    return original_admissible_at_n < A9_MIN_ADMISSIBLE_CLEARS


def _sum_counts(left: HorizonCounts, right: HorizonCounts) -> HorizonCounts:
    return HorizonCounts(
        horizon_seconds=left.horizon_seconds,
        reexhausted_within=left.reexhausted_within + right.reexhausted_within,
        survived_through=left.survived_through + right.survived_through,
        right_censored=left.right_censored + right.right_censored,
    )


def _offset_episodes(
    episodes: tuple[ReExhaustionHandoffEpisode, ...],
    offset: int,
) -> tuple[ReExhaustionHandoffEpisode, ...]:
    return tuple(
        replace(episode, match_index=episode.match_index + offset)
        for episode in episodes
    )


@lru_cache(maxsize=1)
def a9_candidate() -> A9CandidateResult:
    original = candidate_surface("E-PROD OFF+shadow").reexhaustion_handoffs
    if original is None:
        raise RuntimeError("re-exhaustion handoff measurement missing")
    original_at_n = horizon_counts(original.episodes, A9_FROZEN_N_SECONDS)
    triggered = ext_100_triggered(original_at_n.admissible)

    episodes = original.episodes
    ext_at_n = None
    pooled_at_n = original_at_n
    if triggered:
        ext = candidate_surface("E-PROD OFF+shadow EXT-100").reexhaustion_handoffs
        if ext is None:
            raise RuntimeError("EXT-100 handoff measurement missing")
        ext_at_n = horizon_counts(ext.episodes, A9_FROZEN_N_SECONDS)
        pooled_at_n = _sum_counts(original_at_n, ext_at_n)
        episodes = episodes + _offset_episodes(ext.episodes, 100)

    p, verdict = a9_verdict(
        pooled_at_n.admissible,
        pooled_at_n.reexhausted_within,
    )
    return A9CandidateResult(
        original_at_n=original_at_n,
        ext_triggered=triggered,
        ext_at_n=ext_at_n,
        pooled_at_n=pooled_at_n,
        p_candidate=p,
        verdict=verdict,
        sensitivity=match_level_sensitivity(episodes, A9_FROZEN_N_SECONDS),
    )


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def ordering_flip(
    *,
    p_episode_candidate: float,
    p_match_candidate: float,
) -> bool:
    """Frozen strict-sign rule; equality at either level is not a flip."""
    episode = _sign(p_episode_candidate - A9_FROZEN_P_BASELINE)
    match = _sign(p_match_candidate - A9_BASELINE_P_MATCH)
    return episode != 0 and match != 0 and episode != match


def clustering_explanation_required(result: A9CandidateResult) -> bool:
    baseline_gap = abs(A9_FROZEN_P_BASELINE - A9_BASELINE_P_MATCH)
    p_match = result.sensitivity.p_match
    if result.p_candidate is None or p_match is None:
        return baseline_gap > 0.05
    return (
        baseline_gap > 0.05
        or abs(result.p_candidate - p_match) > 0.05
        or ordering_flip(
            p_episode_candidate=result.p_candidate,
            p_match_candidate=p_match,
        )
    )


# ---------------------------------------------------------------------------
# A1-A10 scoring rubric (fixed before the candidate run)
# ---------------------------------------------------------------------------


class Prediction(str, Enum):
    CONFIRMED = "CONFIRMED"
    PARTIAL = "PARTIAL"
    NOT_CONFIRMED = "NOT CONFIRMED"


def score_a1(threat_matches: int, threat_entries: int, taps: int) -> Prediction:
    exact = (threat_matches, threat_entries, taps) == (78, 1950, 0)
    return Prediction.CONFIRMED if exact else Prediction.NOT_CONFIRMED


def _score_floor_range(value: int, *, floor: int, low: int, high: int) -> Prediction:
    if low <= value <= high:
        return Prediction.CONFIRMED
    if value >= floor:
        return Prediction.PARTIAL
    return Prediction.NOT_CONFIRMED


def score_a2(latch_clears: int) -> Prediction:
    return _score_floor_range(latch_clears, floor=34, low=40, high=120)


def score_a3(setup_builders: int) -> Prediction:
    return _score_floor_range(setup_builders, floor=557, low=800, high=1400)


def _score_range(value: float, *, low: float, high: float) -> Prediction:
    return (
        Prediction.CONFIRMED if low <= value <= high else Prediction.NOT_CONFIRMED
    )


def score_a4(bottom_final_median: float) -> Prediction:
    return _score_range(bottom_final_median, low=20, high=35)


def score_a5(timeouts: int) -> Prediction:
    return _score_range(timeouts, low=30, high=75)


def score_a6(exposure: int, warnings: int, penalties: int, resets: int) -> Prediction:
    exposure_ok = exposure <= 15
    offense_free = (warnings, penalties, resets) == (0, 0, 0)
    if exposure_ok and offense_free:
        return Prediction.CONFIRMED
    if exposure_ok or offense_free:
        return Prediction.PARTIAL
    return Prediction.NOT_CONFIRMED


def score_a7(*, real_offense_fired: bool, diverged_matches: int) -> Prediction:
    if diverged_matches == 0:
        return Prediction.CONFIRMED
    # Divergence after a real offense is legitimate new evidence.
    return Prediction.PARTIAL if real_offense_fired else Prediction.NOT_CONFIRMED


def score_a8(half: int, open_: int, reversal: int, matches: int) -> Prediction:
    half_largest = half > open_ and half > reversal
    reversal_ok = reversal < 0.15 * matches
    if half_largest and reversal_ok:
        return Prediction.CONFIRMED
    if half_largest or reversal_ok:
        return Prediction.PARTIAL
    return Prediction.NOT_CONFIRMED


def score_a9(verdict: A9Verdict) -> Prediction:
    return (
        Prediction.CONFIRMED
        if verdict is A9Verdict.PASS
        else Prediction.NOT_CONFIRMED
    )


def score_a10(taps: int, matches: int) -> Prediction:
    return (
        Prediction.CONFIRMED
        if 0 < taps < 0.5 * matches
        else Prediction.NOT_CONFIRMED
    )


# ---------------------------------------------------------------------------
# Gates A-H
# ---------------------------------------------------------------------------


class GateStatus(str, Enum):
    PASS = "PASS"
    OPEN = "OPEN"
    NOT_EVALUATED = "NOT EVALUATED"


@dataclass(frozen=True, slots=True)
class AdoptionGate:
    letter: str
    title: str
    status: GateStatus
    metric: str

    def render(self) -> str:
        return (
            f"STAMINA-ADOPTION GATE {self.letter} [{self.status.value}]: "
            f"{self.title} — {self.metric}"
        )


def _status(ok: bool) -> GateStatus:
    return GateStatus.PASS if ok else GateStatus.OPEN


def matched_divergences() -> tuple[int, ...]:
    off = candidate_surface("E-PROD OFF+shadow").recovery_policy
    on = candidate_surface("E-PROD ON").recovery_policy
    if off is None or on is None:
        raise RuntimeError("recovery-policy measurement missing")
    return tuple(
        value
        for off_record, on_record in zip(off.matches, on.matches)
        if (value := _first_divergence_for_match(off_record, on_record))
        is not None
    )


def shadow_nonperturbation() -> bool:
    return _gameplay_summary_signature(
        candidate_surface("E-PROD OFF+shadow")
    ) == _gameplay_summary_signature(candidate_surface("E-PROD OFF plain"))


@lru_cache(maxsize=1)
def measure_adoption_gates() -> tuple[AdoptionGate, ...]:
    settlement = {
        name: settlement_cell(name)
        for name in ("A", "B", "E-PROD OFF+shadow", "E-PROD ON")
    }
    off = recovery_cell("E-PROD OFF+shadow")
    on = recovery_cell("E-PROD ON")
    a9 = a9_candidate()

    # Gate A — Rule 1 exact on every true-UNFUNDED initiator exchange.
    violations = {
        name: cell.unfunded_responder_spend
        for name, cell in settlement.items()
    }
    rule1_a = candidate_surface("A") == _cell(
        "A public MATCH", SettlementAttributionMode.RULE1_ONLY
    ).summary
    rule1_b = candidate_surface("B") == _cell(
        "B trusts reads", SettlementAttributionMode.RULE1_ONLY
    ).summary
    gate_a = AdoptionGate(
        "A",
        "Rule 1 remains exact",
        _status(all(value == 0 for value in violations.values())),
        (
            "UNFUNDED exchanges/responder spend "
            + ", ".join(
                f"{name}={settlement[name].unfunded_initiator_exchanges}/"
                f"{value}"
                for name, value in violations.items()
            )
            + f"; A/B identical to isolated Rule1-only cells={rule1_a}/{rule1_b}"
        ),
    )

    # Gate B — Rule 2 absent; Surface A retains 78/1,950.
    covered = {name: cell.hold_covered for name, cell in settlement.items()}
    a_cell = settlement["A"]
    rule2_off = (
        PROPOSED_PRODUCTION_DIAGNOSTIC["enable_supplemental_hold_settlement"]
        is False
        and PROPOSED_PRODUCTION_DIAGNOSTIC["enable_stamina_settlement_rules"]
        is False
        and all(value == 0 for value in covered.values())
    )
    gate_b = AdoptionGate(
        "B",
        "Rule 2 is absent from production candidate",
        _status(
            rule2_off
            and a_cell.threat_matches == 78
            and a_cell.threat_entries == 1950
        ),
        (
            f"effective Rule 2 OFF={rule2_off}; hold covered by response "
            + ", ".join(f"{name}={value}" for name, value in covered.items())
            + f"; A Threat matches/entries="
            f"{a_cell.threat_matches}/{a_cell.threat_entries}"
        ),
    )

    # Gate C — minimal recovery transitions + frozen A9.
    minimal = (
        off.bottom_latch_clears > 0
        and off.bottom_conserve_to_escape > 0
        and off.state2_to_state1_exits > 0
    )
    gate_c = AdoptionGate(
        "C",
        "LOW recovery fixes the deadlock under Rule1-only settlement",
        _status(minimal and a9.verdict is A9Verdict.PASS),
        (
            f"latch clears={off.bottom_latch_clears}; "
            f"CONSERVE->ESCAPE={off.bottom_conserve_to_escape}; "
            f"State2->State1={off.state2_to_state1_exits}; "
            f"A9 N={A9_FROZEN_N_SECONDS}s admissible={a9.pooled_at_n.admissible} "
            f"R(N)={a9.pooled_at_n.reexhausted_within} "
            f"p={a9.p_candidate!r} X={A9_FROZEN_X!r} "
            f"EXT-100 triggered={a9.ext_triggered} -> {a9.verdict.value}"
        ),
    )

    # Gate D — LOW preserves real tactical activity while Exhausted.
    gate_d = AdoptionGate(
        "D",
        "LOW preserves real tactical activity",
        _status(
            off.exhausted_setup_builder_attempts > 0
            and off.exhausted_bridge_attempts > 0
            and off.exhausted_completed_setup_builds > 0
        ),
        (
            f"setup builders={off.exhausted_setup_builder_attempts}; "
            f"Bridge={off.exhausted_bridge_attempts}; "
            f"completed builds={off.exhausted_completed_setup_builds}; "
            "prior CURRENT/RESET/LOW+BOTH builders=1326/0/1114"
        ),
    )

    # Gate E — competent-defender Tap gate.
    b_taps = settlement["B"].taps
    b_matches = candidate_surface("B").matches
    gate_e = AdoptionGate(
        "E",
        "competent-defender submission gate remains valid",
        _status(0 < b_taps < 0.5 * b_matches),
        (
            f"Surface B Tap={b_taps}/{b_matches}; "
            "legacy/Rule1-only/BOTH=6/9/7"
        ),
    )

    # Gate F — frozen v0.3b observational and unchanged.
    divergences = matched_divergences()
    shadow_ok = shadow_nonperturbation()
    v03b_frozen = STALLING_THRESHOLD_SECONDS == 20
    counters_populated = all(
        value is not None
        for value in (
            off.shadow_bottom_resets_with_route,
            off.shadow_warnings,
            off.shadow_penalties,
            off.shadow_position_resets,
            off.shadow_free_initiative,
            on.bottom_stalling_warnings,
            on.bottom_stalling_penalties,
            on.bottom_stalling_position_resets,
            on.bottom_stalling_free_initiative,
            on.bottom_stalling_signed_axis_delta,
        )
    )
    gate_f = AdoptionGate(
        "F",
        "frozen v0.3b remains observational and unchanged",
        _status(shadow_ok and v03b_frozen and counters_populated),
        (
            f"shadow nonperturbation={shadow_ok}; "
            f"stalling threshold={STALLING_THRESHOLD_SECONDS}s; "
            f"counters populated={counters_populated}; "
            f"real W/P/PR/free={on.bottom_stalling_warnings}/"
            f"{on.bottom_stalling_penalties}/"
            f"{on.bottom_stalling_position_resets}/"
            f"{on.bottom_stalling_free_initiative}; "
            f"matched divergence={len(divergences)}/100"
        ),
    )

    # Gate G — only after canonical promotion.
    gate_g = AdoptionGate(
        "G",
        "canonical production configuration matches measured candidate",
        GateStatus.NOT_EVALUATED,
        "canonical entry point not added; evaluated only after Gates A-F "
        "PASS and promotion is authorized",
    )

    # Gate H — historical replay and defaults remain available.
    defaults_ok, defaults_metric = _default_activation_ok()
    none_ok, both_ok = attribution_compatibility()
    modes_callable = {mode for mode in RecoveryInitiationMode} == {
        RecoveryInitiationMode.CURRENT,
        RecoveryInitiationMode.RESET_WHILE_EXHAUSTED,
        RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
    }
    gate_h = AdoptionGate(
        "H",
        "historical replay and defaults remain available",
        _status(defaults_ok and none_ok and both_ok and modes_callable),
        (
            f"{defaults_metric}; BOTH equals PR8 BOTH={both_ok}; "
            f"CURRENT/RESET/LOW callable={modes_callable}"
        ),
    )

    return (gate_a, gate_b, gate_c, gate_d, gate_e, gate_f, gate_g, gate_h)


@lru_cache(maxsize=1)
def score_predictions() -> tuple[tuple[str, Prediction, str], ...]:
    a = settlement_cell("A")
    b = settlement_cell("B")
    off = recovery_cell("E-PROD OFF+shadow")
    on = recovery_cell("E-PROD ON")
    a9 = a9_candidate()
    divergences = matched_divergences()
    real_offense = (
        on.bottom_stalling_warnings
        + on.bottom_stalling_penalties
        + on.bottom_stalling_position_resets
    ) > 0
    matches = candidate_surface("E-PROD OFF+shadow").matches
    b_matches = candidate_surface("B").matches
    return (
        (
            "A1",
            score_a1(a.threat_matches, a.threat_entries, a.taps),
            f"Threat matches/entries/Tap={a.threat_matches}/"
            f"{a.threat_entries}/{a.taps}; expected exact 78/1950/0",
        ),
        (
            "A2",
            score_a2(off.bottom_latch_clears),
            f"latch clears={off.bottom_latch_clears}; floor>=34; "
            "expected 40-120; LOW+BOTH=67",
        ),
        (
            "A3",
            score_a3(off.exhausted_setup_builder_attempts),
            f"setup builders={off.exhausted_setup_builder_attempts}; "
            "floor>=557; expected 800-1400; LOW+BOTH=1114",
        ),
        (
            "A4",
            score_a4(off.bottom_final_median),
            f"Bottom final median={off.bottom_final_median}; "
            "expected 20-35; LOW+BOTH=26",
        ),
        (
            "A5",
            score_a5(off.timeouts),
            f"timeouts={off.timeouts}; expected 30-75; "
            "LOW+BOTH=44, CURRENT+BOTH=75",
        ),
        (
            "A6",
            score_a6(
                off.shadow_bottom_resets_with_route,
                on.bottom_stalling_warnings,
                on.bottom_stalling_penalties,
                on.bottom_stalling_position_resets,
            ),
            f"RESET-with-route exposure={off.shadow_bottom_resets_with_route} "
            f"(<=15); real W/P/PR={on.bottom_stalling_warnings}/"
            f"{on.bottom_stalling_penalties}/"
            f"{on.bottom_stalling_position_resets} (0/0/0)",
        ),
        (
            "A7",
            score_a7(
                real_offense_fired=real_offense,
                diverged_matches=len(divergences),
            ),
            f"real offense fired={real_offense}; "
            f"OFF/ON gameplay identical={not divergences}; "
            f"diverged matches={len(divergences)}/100",
        ),
        (
            "A8",
            score_a8(off.half_guard, off.open_guard, off.reversal, matches),
            f"Half/Open/Reversal={off.half_guard}/{off.open_guard}/"
            f"{off.reversal}; Half largest and Reversal<15%; "
            "LOW+BOTH=31/15/5",
        ),
        (
            "A9",
            score_a9(a9.verdict),
            f"N={A9_FROZEN_N_SECONDS}s admissible={a9.pooled_at_n.admissible} "
            f"R(N)={a9.pooled_at_n.reexhausted_within} "
            f"p_candidate={a9.p_candidate!r} X={A9_FROZEN_X!r} "
            f"p_baseline={A9_FROZEN_P_BASELINE!r} "
            f"EXT-100={a9.ext_triggered} -> {a9.verdict.value}",
        ),
        (
            "A10",
            score_a10(b.taps, b_matches),
            f"trust-read Tap={b.taps}/{b_matches}; expected 0%<Tap<50%",
        ),
    )


def handoff_report() -> HandoffSurfaceReport:
    return surface_report(
        "E-PROD Rule1-only + LOW (original 100)",
        candidate_surface("E-PROD OFF+shadow"),
    )


def first_clear_times() -> tuple[int, ...]:
    episodes = candidate_surface("E-PROD OFF+shadow").reexhaustion_handoffs.episodes
    first: dict[int, int] = {}
    for episode in episodes:
        first.setdefault(episode.match_index, episode.clear_elapsed_seconds)
    return tuple(sorted(first.values()))


def clear_stamina_distribution() -> dict[int, int]:
    records = _measurement(
        StaminaEconomySurface(
            label="E-PROD OFF+shadow",
            summary=candidate_surface("E-PROD OFF+shadow"),
        )
    ).matches
    counts: dict[int, int] = {}
    for record in records:
        for value in record.bottom_latch_clear_stamina:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def first_clear_median() -> float | None:
    times = first_clear_times()
    return median(times) if times else None
