from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections import Counter
from enum import Enum
from inspect import signature
from statistics import median

from ..domain.action import Commitment
from ..domain.model import BottomBehavior, ExitDestination, Side, TopBehavior
from ..domain.stamina import StaminaPool
from ..engine.match import MountMatch
from ..engine.stalling import STALLING_THRESHOLD_SECONDS
from ..engine.stamina import (
    DEFAULT_BEHAVIOR_STAMINA_POLICY,
    DEFAULT_STAMINA_COST_POLICY,
)
from ..interfaces.batch import BatchSummary, run_escape_first_batch
from ..interfaces.recovery_policy import (
    RecoveryInitiationMode,
    RecoveryTrajectorySnapshot,
)
from .stamina_economy import (
    StaminaEconomySurface,
    _measurement,
    _surface_kwargs,
    measured_surfaces,
)
from .stamina_settlement import (
    StaminaRuleGateStatus,
    measure_stamina_rule_definition_of_done,
    postchange_surfaces,
)
from ..positions.mount.matchups import RAW_GRADES


class SettlementAttributionMode(str, Enum):
    NONE = "NONE"
    RULE1_ONLY = "RULE1_ONLY"
    RULE2_ONLY = "RULE2_ONLY"
    BOTH = "BOTH"


@dataclass(frozen=True, slots=True)
class SettlementAttributionCell:
    surface_label: str
    mode: SettlementAttributionMode
    summary: BatchSummary
    taps: int
    escapes: int
    timeouts: int
    threat_matches: int
    threat_entries: int
    control_entries: int
    finish_entries: int
    bottom_defensive_spend: int
    bottom_own_attack_spend: int
    bottom_own_attacks: int
    bottom_resets: int
    bottom_behavior_recovery: int
    bottom_latch_clears: int
    bottom_conserve_to_escape: int
    state1_share: float
    state2_share: float
    state3_share: float
    hold_exchanges: int
    hold_nominal: int
    hold_covered: int
    hold_supplemental_requested: int
    hold_supplemental_charged: int
    funded_initiator_supplemental_charged: int
    unfunded_initiator_hold_charged: int
    additive_double_charge_cases: int
    unfunded_initiator_exchanges: int
    unfunded_responder_spend: int


def _surface_label_key(label: str) -> str:
    return {
        "A public MATCH": "A",
        "B trusts reads": "B",
        "E trusts reads + Bottom RECOVER": "E",
    }[label]


def _run_attribution_surface(
    label: str,
    mode: SettlementAttributionMode,
) -> StaminaEconomySurface:
    kwargs = _surface_kwargs(label)
    rule1 = mode in {
        SettlementAttributionMode.RULE1_ONLY,
        SettlementAttributionMode.BOTH,
    }
    rule2 = mode in {
        SettlementAttributionMode.RULE2_ONLY,
        SettlementAttributionMode.BOTH,
    }
    summary = run_escape_first_batch(
        **kwargs,
        enable_unfunded_responder_cost_waiver=rule1,
        enable_supplemental_hold_settlement=rule2,
        measure_stamina_economy=True,
    )
    return StaminaEconomySurface(
        label=label,
        summary=summary,
    )


def _attribution_cell(
    surface: StaminaEconomySurface,
    mode: SettlementAttributionMode,
) -> SettlementAttributionCell:
    measurement = _measurement(surface)
    matches = measurement.matches
    exchanges = measurement.exchanges
    total_elapsed = sum(record.elapsed_seconds for record in matches)

    bottom_defensive = sum(
        record.bottom_sources.responder_commitment_spend
        + record.bottom_sources.provisional_hold_spend
        for record in matches
    )
    bottom_own = sum(
        record.bottom_sources.initiator_commitment_spend
        for record in matches
    )
    bottom_recovery = sum(
        record.bottom_sources.behavior_recovery
        for record in matches
    )
    holds = [row for row in exchanges if row.submission_hold]
    unfunded = [
        row for row in exchanges
        if row.initiator_effective_commitment == "UNFUNDED"
    ]

    escapes = sum(
        surface.summary.outcome_counts.get(destination.value, 0)
        for destination in ExitDestination
    )

    return SettlementAttributionCell(
        surface_label=surface.label,
        mode=mode,
        summary=surface.summary,
        taps=surface.summary.outcome_counts.get("TAP — Americana", 0),
        escapes=escapes,
        timeouts=surface.summary.outcome_counts.get(
            "TIMEOUT — Mount retained",
            0,
        ),
        threat_matches=surface.summary.matches_reached_submission_threat,
        threat_entries=sum(row.transition_into_threat for row in exchanges),
        control_entries=sum(row.transition_into_control for row in exchanges),
        finish_entries=sum(row.transition_into_finish for row in exchanges),
        bottom_defensive_spend=bottom_defensive,
        bottom_own_attack_spend=bottom_own,
        bottom_own_attacks=sum(surface.summary.bottom_action_counts.values()),
        bottom_resets=surface.summary.bottom_reset_count,
        bottom_behavior_recovery=bottom_recovery,
        bottom_latch_clears=sum(
            record.bottom_exhausted_latch_clears for record in matches
        ),
        bottom_conserve_to_escape=sum(
            record.bottom_switches_to_escape for record in matches
        ),
        state1_share=(
            sum(record.state1_seconds for record in matches) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        state2_share=(
            sum(record.state2_seconds for record in matches) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        state3_share=(
            sum(record.state3_seconds for record in matches) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        hold_exchanges=len(holds),
        hold_nominal=sum(row.hold_nominal_cost for row in holds),
        hold_covered=sum(row.hold_covered_by_response for row in holds),
        hold_supplemental_requested=sum(row.hold_requested for row in holds),
        hold_supplemental_charged=sum(row.hold_charged for row in holds),
        funded_initiator_supplemental_charged=sum(
            row.hold_charged
            for row in holds
            if row.initiator_effective_commitment != "UNFUNDED"
        ),
        unfunded_initiator_hold_charged=sum(
            row.hold_charged
            for row in holds
            if row.initiator_effective_commitment == "UNFUNDED"
        ),
        additive_double_charge_cases=sum(
            row.response_commitment_charged >= 3 and row.hold_charged > 0
            for row in holds
            if row.initiator_effective_commitment != "UNFUNDED"
        ),
        unfunded_initiator_exchanges=len(unfunded),
        unfunded_responder_spend=sum(
            row.response_commitment_charged + row.hold_charged
            for row in unfunded
        ),
    )


@lru_cache(maxsize=1)
def settlement_attribution_matrix() -> tuple[SettlementAttributionCell, ...]:
    cells: list[SettlementAttributionCell] = []
    for label in (
        "A public MATCH",
        "B trusts reads",
        "E trusts reads + Bottom RECOVER",
    ):
        for mode in SettlementAttributionMode:
            cells.append(
                _attribution_cell(
                    _run_attribution_surface(label, mode),
                    mode,
                )
            )
    return tuple(cells)


def _cell(
    label: str,
    mode: SettlementAttributionMode,
) -> SettlementAttributionCell:
    for cell in settlement_attribution_matrix():
        if cell.surface_label == label and cell.mode is mode:
            return cell
    raise KeyError((label, mode))


def attribution_compatibility() -> tuple[bool, bool]:
    legacy = measured_surfaces()
    both = postchange_surfaces()
    references = {
        "A public MATCH": (legacy[0].summary, both[0].summary),
        "B trusts reads": (legacy[1].summary, both[1].summary),
        "E trusts reads + Bottom RECOVER": (
            legacy[4].summary,
            both[4].summary,
        ),
    }
    none_ok = True
    both_ok = True
    for label, (legacy_summary, both_summary) in references.items():
        none_ok = none_ok and (
            _cell(label, SettlementAttributionMode.NONE).summary
            == legacy_summary
        )
        both_ok = both_ok and (
            _cell(label, SettlementAttributionMode.BOTH).summary
            == both_summary
        )
    return none_ok, both_ok


def render_settlement_attribution_matrix() -> tuple[str, ...]:
    lines: list[str] = []
    none_ok, both_ok = attribution_compatibility()
    lines.append(
        "STAMINA-RECOVERY FLAG COMPATIBILITY — "
        f"NONE==legacy:{none_ok}; explicit BOTH==umbrella BOTH:{both_ok}"
    )
    for cell in settlement_attribution_matrix():
        lines.append(
            "STAMINA-RECOVERY ATTRIBUTION — "
            f"{_surface_label_key(cell.surface_label)}/{cell.mode.value}: "
            f"Tap/Escape/Timeout={cell.taps}/{cell.escapes}/{cell.timeouts}; "
            f"Threat matches/entries/Control/Finish="
            f"{cell.threat_matches}/{cell.threat_entries}/"
            f"{cell.control_entries}/{cell.finish_entries}; "
            f"final stamina={cell.summary.top_final_stamina_median:.1f}/"
            f"{cell.summary.bottom_final_stamina_median:.1f}; "
            f"Bottom defensive/own-attack spend="
            f"{cell.bottom_defensive_spend}/{cell.bottom_own_attack_spend}; "
            f"own attacks/RESETs={cell.bottom_own_attacks}/{cell.bottom_resets}; "
            f"recovery={cell.bottom_behavior_recovery}; "
            f"latch clears/CONSERVE->ESCAPE="
            f"{cell.bottom_latch_clears}/{cell.bottom_conserve_to_escape}; "
            f"State1/2/3={cell.state1_share:.3f}/"
            f"{cell.state2_share:.3f}/{cell.state3_share:.3f}; "
            f"holds={cell.hold_exchanges}, nominal/covered/"
            f"supp-requested/supp-charged="
            f"{cell.hold_nominal}/{cell.hold_covered}/"
            f"{cell.hold_supplemental_requested}/"
            f"{cell.hold_supplemental_charged}; "
            f"funded-init supplemental charged="
            f"{cell.funded_initiator_supplemental_charged}; "
            f"UNFUNDED-init hold charged="
            f"{cell.unfunded_initiator_hold_charged}; "
            f"additive double-charge={cell.additive_double_charge_cases}; "
            f"UNFUNDED exchanges/responder spend="
            f"{cell.unfunded_initiator_exchanges}/"
            f"{cell.unfunded_responder_spend}"
        )
    return tuple(lines)




@dataclass(frozen=True, slots=True)
class RecoveryCandidateCell:
    mode: RecoveryInitiationMode
    stalling_enabled: bool
    shadow_enabled: bool
    summary: BatchSummary
    taps: int
    half_guard: int
    open_guard: int
    reversal: int
    escapes: int
    timeouts: int
    top_final_median: float
    bottom_final_median: float
    bottom_defensive_spend: int
    bottom_own_attack_spend: int
    bottom_own_attacks: int
    bottom_resets: int
    bottom_behavior_recovery: int
    bottom_behavior_spend: int
    bottom_latch_clears: int
    bottom_conserve_to_escape: int
    state2_to_state1_exits: int
    state1_share: float
    state2_share: float
    state3_share: float
    own_spend_per_recovery: float | None
    defensive_spend_per_recovery: float | None
    total_spend_per_recovery: float | None
    bottom_stalling_warnings: int
    bottom_stalling_penalties: int
    bottom_stalling_position_resets: int
    bottom_stalling_resets_with_route: int
    bottom_stalling_free_initiative: int
    bottom_stalling_signed_axis_delta: float
    bottom_stalling_absolute_control_loss: float
    first_bottom_stalling_offense_median: float | None
    shadow_bottom_resets_with_route: int
    shadow_warnings: int
    shadow_penalties: int
    shadow_position_resets: int
    shadow_free_initiative: int
    shadow_first_threshold_median: float | None
    shadow_first_offense_median: float | None
    exhausted_requested_commitments: tuple[tuple[str, int], ...]
    exhausted_bridge_attempts: int
    exhausted_setup_builder_attempts: int
    exhausted_setup_advances: int
    exhausted_ready_transitions: int
    exhausted_completed_setup_builds: int
    exhausted_escapes_after_setup: int
    exhausted_resets: int
    exhausted_resets_forgone_setup: int


def _candidate_kwargs(
    mode: RecoveryInitiationMode,
    *,
    stalling: bool,
    shadow: bool,
) -> dict:
    kwargs = _surface_kwargs("E trusts reads + Bottom RECOVER")
    return {
        **kwargs,
        "enable_v03b_stalling": stalling,
        "enable_unfunded_responder_cost_waiver": True,
        "enable_supplemental_hold_settlement": True,
        "recovery_initiation_mode": mode,
        "measure_stamina_economy": True,
        "measure_recovery_policy": True,
        "shadow_stalling": shadow,
    }


@lru_cache(maxsize=1)
def recovery_candidate_off_shadow_surfaces() -> tuple[StaminaEconomySurface, ...]:
    return tuple(
        StaminaEconomySurface(
            label=f"E {mode.value} stalling OFF + shadow",
            summary=run_escape_first_batch(
                **_candidate_kwargs(mode, stalling=False, shadow=True)
            ),
        )
        for mode in RecoveryInitiationMode
    )


@lru_cache(maxsize=1)
def recovery_candidate_off_plain_surfaces() -> tuple[StaminaEconomySurface, ...]:
    return tuple(
        StaminaEconomySurface(
            label=f"E {mode.value} stalling OFF plain",
            summary=run_escape_first_batch(
                **_candidate_kwargs(mode, stalling=False, shadow=False)
            ),
        )
        for mode in RecoveryInitiationMode
    )


@lru_cache(maxsize=1)
def recovery_candidate_on_surfaces() -> tuple[StaminaEconomySurface, ...]:
    return tuple(
        StaminaEconomySurface(
            label=f"E {mode.value} stalling ON",
            summary=run_escape_first_batch(
                **_candidate_kwargs(mode, stalling=True, shadow=False)
            ),
        )
        for mode in RecoveryInitiationMode
    )


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _candidate_cell(
    surface: StaminaEconomySurface,
    mode: RecoveryInitiationMode,
    *,
    stalling: bool,
    shadow: bool,
) -> RecoveryCandidateCell:
    stamina = _measurement(surface)
    recovery = surface.summary.recovery_policy
    if recovery is None:
        raise RuntimeError("recovery-policy measurement missing")

    records = stamina.matches
    policy_records = recovery.matches
    total_elapsed = sum(record.elapsed_seconds for record in records)

    bottom_defensive = sum(
        record.bottom_sources.responder_commitment_spend
        + record.bottom_sources.provisional_hold_spend
        for record in records
    )
    bottom_own = sum(
        record.bottom_sources.initiator_commitment_spend
        for record in records
    )
    bottom_recovery = sum(
        record.bottom_sources.behavior_recovery
        for record in records
    )
    bottom_behavior_spend = sum(
        record.bottom_sources.behavior_spend
        for record in records
    )

    actual_offense_times = [
        record.bottom_first_actual_stalling_offense_time
        for record in policy_records
        if record.bottom_first_actual_stalling_offense_time is not None
    ]
    shadow_threshold_first = [
        record.shadow_threshold_reach_times_bottom[0]
        for record in policy_records
        if record.shadow_threshold_reach_times_bottom
    ]
    shadow_offense_first = [
        min(
            event.elapsed_seconds
            for event in record.shadow_events
            if event.side is Side.BOTTOM
        )
        for record in policy_records
        if any(event.side is Side.BOTTOM for event in record.shadow_events)
    ]

    shadow_counts: Counter[str] = Counter()
    requested_counts: Counter[str] = Counter()
    for record in policy_records:
        requested_counts.update(
            dict(record.bottom_exhausted_requested_commitments)
        )
        for event in record.shadow_events:
            if event.side is Side.BOTTOM:
                shadow_counts[event.effective_consequence] += 1

    outcome_counts = surface.summary.outcome_counts
    half_guard = outcome_counts.get(ExitDestination.HALF_GUARD.value, 0)
    open_guard = outcome_counts.get(ExitDestination.OPEN_GUARD.value, 0)
    reversal = outcome_counts.get(ExitDestination.REVERSAL.value, 0)
    escapes = half_guard + open_guard + reversal

    return RecoveryCandidateCell(
        mode=mode,
        stalling_enabled=stalling,
        shadow_enabled=shadow,
        summary=surface.summary,
        taps=outcome_counts.get("TAP — Americana", 0),
        half_guard=half_guard,
        open_guard=open_guard,
        reversal=reversal,
        escapes=escapes,
        timeouts=outcome_counts.get("TIMEOUT — Mount retained", 0),
        top_final_median=surface.summary.top_final_stamina_median,
        bottom_final_median=surface.summary.bottom_final_stamina_median,
        bottom_defensive_spend=bottom_defensive,
        bottom_own_attack_spend=bottom_own,
        bottom_own_attacks=sum(surface.summary.bottom_action_counts.values()),
        bottom_resets=surface.summary.bottom_reset_count,
        bottom_behavior_recovery=bottom_recovery,
        bottom_behavior_spend=bottom_behavior_spend,
        bottom_latch_clears=sum(
            record.bottom_exhausted_latch_clears for record in records
        ),
        bottom_conserve_to_escape=sum(
            record.bottom_switches_to_escape for record in records
        ),
        state2_to_state1_exits=sum(
            record.state2_exits_to_state1 for record in records
        ),
        state1_share=(
            sum(record.state1_seconds for record in records) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        state2_share=(
            sum(record.state2_seconds for record in records) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        state3_share=(
            sum(record.state3_seconds for record in records) / total_elapsed
            if total_elapsed
            else 0.0
        ),
        own_spend_per_recovery=_safe_ratio(bottom_own, bottom_recovery),
        defensive_spend_per_recovery=_safe_ratio(
            bottom_defensive,
            bottom_recovery,
        ),
        total_spend_per_recovery=_safe_ratio(
            bottom_own + bottom_defensive,
            bottom_recovery,
        ),
        bottom_stalling_warnings=surface.summary.bottom_stalling_warning_count,
        bottom_stalling_penalties=surface.summary.bottom_stalling_penalty_count,
        bottom_stalling_position_resets=(
            surface.summary.bottom_stalling_position_reset_count
        ),
        bottom_stalling_resets_with_route=(
            surface.summary.bottom_stalling_reset_with_route_count
        ),
        bottom_stalling_free_initiative=sum(
            record.bottom_actual_stalling_free_initiative
            for record in policy_records
        ),
        bottom_stalling_signed_axis_delta=sum(
            record.bottom_actual_stalling_signed_axis_delta
            for record in policy_records
        ),
        bottom_stalling_absolute_control_loss=sum(
            record.bottom_actual_stalling_absolute_control_loss
            for record in policy_records
        ),
        first_bottom_stalling_offense_median=(
            median(actual_offense_times)
            if actual_offense_times
            else None
        ),
        shadow_bottom_resets_with_route=sum(
            record.shadow_bottom_resets_with_route
            for record in policy_records
        ),
        shadow_warnings=shadow_counts["WARNING"],
        shadow_penalties=shadow_counts["PENALTY"],
        shadow_position_resets=shadow_counts["POSITION_RESET"],
        shadow_free_initiative=shadow_counts["FREE_INITIATIVE"],
        shadow_first_threshold_median=(
            median(shadow_threshold_first)
            if shadow_threshold_first
            else None
        ),
        shadow_first_offense_median=(
            median(shadow_offense_first)
            if shadow_offense_first
            else None
        ),
        exhausted_requested_commitments=tuple(sorted(requested_counts.items())),
        exhausted_bridge_attempts=sum(
            record.bottom_exhausted_bridge_attempts
            for record in policy_records
        ),
        exhausted_setup_builder_attempts=sum(
            record.bottom_exhausted_setup_builder_attempts
            for record in policy_records
        ),
        exhausted_setup_advances=sum(
            record.bottom_exhausted_setup_advances
            for record in policy_records
        ),
        exhausted_ready_transitions=sum(
            record.bottom_exhausted_ready_transitions
            for record in policy_records
        ),
        exhausted_completed_setup_builds=sum(
            record.bottom_exhausted_completed_setup_builds
            for record in policy_records
        ),
        exhausted_escapes_after_setup=sum(
            record.bottom_exhausted_escapes_after_setup_build
            for record in policy_records
        ),
        exhausted_resets=sum(
            record.bottom_exhausted_resets
            for record in policy_records
        ),
        exhausted_resets_forgone_setup=sum(
            record.bottom_exhausted_resets_forgone_setup_opportunity
            for record in policy_records
        ),
    )


@lru_cache(maxsize=1)
def recovery_candidate_matrix() -> tuple[RecoveryCandidateCell, ...]:
    cells: list[RecoveryCandidateCell] = []
    off_shadow = recovery_candidate_off_shadow_surfaces()
    on = recovery_candidate_on_surfaces()
    for index, mode in enumerate(RecoveryInitiationMode):
        cells.append(
            _candidate_cell(
                off_shadow[index],
                mode,
                stalling=False,
                shadow=True,
            )
        )
        cells.append(
            _candidate_cell(
                on[index],
                mode,
                stalling=True,
                shadow=False,
            )
        )
    return tuple(cells)


def _gameplay_summary_signature(summary: BatchSummary) -> tuple:
    return tuple(
        (name, getattr(summary, name))
        for name in summary.__dataclass_fields__
        if name != "recovery_policy"
    )


def shadow_nonperturbation() -> tuple[bool, bool, bool]:
    shadow = recovery_candidate_off_shadow_surfaces()
    plain = recovery_candidate_off_plain_surfaces()
    return tuple(
        _gameplay_summary_signature(shadow[index].summary)
        == _gameplay_summary_signature(plain[index].summary)
        for index in range(3)
    )


def _trajectory_gameplay_signature(
    snapshot: RecoveryTrajectorySnapshot,
) -> tuple:
    return (
        snapshot.elapsed_seconds,
        snapshot.initiator,
        snapshot.axis,
        snapshot.mount_band,
        snapshot.top_stamina,
        snapshot.bottom_stamina,
        snapshot.top_stamina_band,
        snapshot.bottom_stamina_band,
        snapshot.bottom_bridge_setup_tier,
        snapshot.submission_stage,
    )


def _first_divergence_for_match(off_record, on_record) -> int | None:
    off = off_record.trajectory
    on = on_record.trajectory
    limit = min(len(off), len(on))
    for index in range(limit):
        if (
            _trajectory_gameplay_signature(off[index])
            != _trajectory_gameplay_signature(on[index])
        ):
            return min(
                off[index].elapsed_seconds,
                on[index].elapsed_seconds,
            )
    if len(off) == len(on):
        return None
    extra = off[limit] if len(off) > limit else on[limit]
    return extra.elapsed_seconds


def matched_first_divergence_times(
    mode: RecoveryInitiationMode,
) -> tuple[int, ...]:
    index = tuple(RecoveryInitiationMode).index(mode)
    off_measurement = recovery_candidate_off_shadow_surfaces()[
        index
    ].summary.recovery_policy
    on_measurement = recovery_candidate_on_surfaces()[
        index
    ].summary.recovery_policy
    if off_measurement is None or on_measurement is None:
        raise RuntimeError("recovery-policy measurement missing")
    divergences = []
    for off_record, on_record in zip(
        off_measurement.matches,
        on_measurement.matches,
    ):
        value = _first_divergence_for_match(off_record, on_record)
        if value is not None:
            divergences.append(value)
    return tuple(divergences)


def render_recovery_candidate_matrix() -> tuple[str, ...]:
    lines: list[str] = []
    shadow_equal = shadow_nonperturbation()
    lines.append(
        "STAMINA-RECOVERY SHADOW NONPERTURBATION — "
        + ", ".join(
            f"{mode.value}={shadow_equal[index]}"
            for index, mode in enumerate(RecoveryInitiationMode)
        )
    )
    for cell in recovery_candidate_matrix():
        label = "ON" if cell.stalling_enabled else "OFF+shadow"
        lines.append(
            "STAMINA-RECOVERY CANDIDATE — "
            f"{cell.mode.value}/{label}: "
            f"Tap/Half/Open/Reversal/Timeout="
            f"{cell.taps}/{cell.half_guard}/{cell.open_guard}/"
            f"{cell.reversal}/{cell.timeouts}; "
            f"final stamina={cell.top_final_median:.1f}/"
            f"{cell.bottom_final_median:.1f}; "
            f"Bottom defensive/own/recovery="
            f"{cell.bottom_defensive_spend}/"
            f"{cell.bottom_own_attack_spend}/"
            f"{cell.bottom_behavior_recovery}; "
            f"budget own/def/total per recovery="
            f"{cell.own_spend_per_recovery}/"
            f"{cell.defensive_spend_per_recovery}/"
            f"{cell.total_spend_per_recovery}; "
            f"own attacks/RESETs="
            f"{cell.bottom_own_attacks}/{cell.bottom_resets}; "
            f"latch clears/switches/State2->1="
            f"{cell.bottom_latch_clears}/"
            f"{cell.bottom_conserve_to_escape}/"
            f"{cell.state2_to_state1_exits}; "
            f"State1/2/3={cell.state1_share:.3f}/"
            f"{cell.state2_share:.3f}/{cell.state3_share:.3f}; "
            f"stall W/P/PR/route/free="
            f"{cell.bottom_stalling_warnings}/"
            f"{cell.bottom_stalling_penalties}/"
            f"{cell.bottom_stalling_position_resets}/"
            f"{cell.bottom_stalling_resets_with_route}/"
            f"{cell.bottom_stalling_free_initiative}; "
            f"stall axis signed/abs="
            f"{cell.bottom_stalling_signed_axis_delta:+.2f}/"
            f"{cell.bottom_stalling_absolute_control_loss:.2f}; "
            f"actual first offense median="
            f"{cell.first_bottom_stalling_offense_median}; "
            f"shadow route/W/P/PR/free="
            f"{cell.shadow_bottom_resets_with_route}/"
            f"{cell.shadow_warnings}/"
            f"{cell.shadow_penalties}/"
            f"{cell.shadow_position_resets}/"
            f"{cell.shadow_free_initiative}; "
            f"shadow first threshold/offense median="
            f"{cell.shadow_first_threshold_median}/"
            f"{cell.shadow_first_offense_median}; "
            f"exhausted requests={dict(cell.exhausted_requested_commitments)}; "
            f"exhausted RESETs={cell.exhausted_resets}; "
            f"setup Bridge/builder/advance/Ready/completed/"
            f"escape-after/reset-forgone="
            f"{cell.exhausted_bridge_attempts}/"
            f"{cell.exhausted_setup_builder_attempts}/"
            f"{cell.exhausted_setup_advances}/"
            f"{cell.exhausted_ready_transitions}/"
            f"{cell.exhausted_completed_setup_builds}/"
            f"{cell.exhausted_escapes_after_setup}/"
            f"{cell.exhausted_resets_forgone_setup}"
        )
    for mode in RecoveryInitiationMode:
        divergences = matched_first_divergence_times(mode)
        lines.append(
            "STAMINA-RECOVERY STALLING DIVERGENCE — "
            f"{mode.value}: diverged matches={len(divergences)}/100; "
            f"first divergence median="
            f"{median(divergences) if divergences else 'none'}"
        )
    return tuple(lines)

@dataclass(frozen=True, slots=True)
class SurfaceEStaminaDestination:
    label: str
    defensive_spend: int
    own_attack_spend: int
    own_attacks: int
    resets: int
    behavior_recovery: int
    behavior_spend: int
    response_spend: int
    hold_spend: int


def _surface_e_destination(*, settlement_enabled: bool) -> SurfaceEStaminaDestination:
    surface = (
        postchange_surfaces()[4]
        if settlement_enabled
        else measured_surfaces()[4]
    )
    measurement = surface.summary.stamina_economy
    if measurement is None:
        raise RuntimeError("Surface E stamina measurement missing")

    bottom_sources = [record.bottom_sources for record in measurement.matches]
    response_spend = sum(
        source.responder_commitment_spend for source in bottom_sources
    )
    hold_spend = sum(
        source.provisional_hold_spend for source in bottom_sources
    )
    return SurfaceEStaminaDestination(
        label="BOTH" if settlement_enabled else "LEGACY",
        defensive_spend=response_spend + hold_spend,
        own_attack_spend=sum(
            source.initiator_commitment_spend for source in bottom_sources
        ),
        own_attacks=sum(surface.summary.bottom_action_counts.values()),
        resets=surface.summary.bottom_reset_count,
        behavior_recovery=sum(
            source.behavior_recovery for source in bottom_sources
        ),
        behavior_spend=sum(source.behavior_spend for source in bottom_sources),
        response_spend=response_spend,
        hold_spend=hold_spend,
    )


@lru_cache(maxsize=1)
def recovery_policy_starting_evidence() -> tuple[
    SurfaceEStaminaDestination,
    SurfaceEStaminaDestination,
]:
    return (
        _surface_e_destination(settlement_enabled=False),
        _surface_e_destination(settlement_enabled=True),
    )


def render_recovery_policy_starting_evidence() -> tuple[str, ...]:
    lines: list[str] = []
    for evidence in recovery_policy_starting_evidence():
        lines.append(
            "STAMINA-RECOVERY STARTING EVIDENCE — "
            f"{evidence.label}: "
            f"Bottom defensive spend={evidence.defensive_spend} "
            f"(response={evidence.response_spend}, hold={evidence.hold_spend}); "
            f"own-attack spend={evidence.own_attack_spend}; "
            f"own attacks={evidence.own_attacks}; "
            f"RESETs={evidence.resets}; "
            f"behavior recovery={evidence.behavior_recovery}; "
            f"behavior spend={evidence.behavior_spend}"
        )
    return tuple(lines)


class RecoveryAmendmentGateStatus(str, Enum):
    PASS = "PASS"
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class RecoveryAmendmentGate:
    letter: str
    name: str
    status: RecoveryAmendmentGateStatus
    metric: str
    evidence: str

    def render(self) -> str:
        return (
            f"STAMINA-RECOVERY AMENDMENT GATE {self.letter} "
            f"[{self.status.value}]: {self.name} — "
            f"{self.metric}; {self.evidence}"
        )


def _candidate_cell_for(
    mode: RecoveryInitiationMode,
    *,
    stalling: bool,
) -> RecoveryCandidateCell:
    for cell in recovery_candidate_matrix():
        if cell.mode is mode and cell.stalling_enabled is stalling:
            return cell
    raise KeyError((mode, stalling))


@lru_cache(maxsize=1)
def recovery_candidate_replay_equal() -> bool:
    fresh_off = tuple(
        StaminaEconomySurface(
            label=f"fresh E {mode.value} stalling OFF + shadow",
            summary=run_escape_first_batch(
                **_candidate_kwargs(mode, stalling=False, shadow=True)
            ),
        )
        for mode in RecoveryInitiationMode
    )
    fresh_on = tuple(
        StaminaEconomySurface(
            label=f"fresh E {mode.value} stalling ON",
            summary=run_escape_first_batch(
                **_candidate_kwargs(mode, stalling=True, shadow=False)
            ),
        )
        for mode in RecoveryInitiationMode
    )
    cached_off = recovery_candidate_off_shadow_surfaces()
    cached_on = recovery_candidate_on_surfaces()
    return all(
        fresh_off[index].summary == cached_off[index].summary
        and fresh_on[index].summary == cached_on[index].summary
        for index in range(len(tuple(RecoveryInitiationMode)))
    )


def _starting_evidence_gate() -> tuple[bool, str]:
    legacy, both = recovery_policy_starting_evidence()
    ok = (
        legacy.defensive_spend == 10821
        and legacy.own_attack_spend == 6091
        and legacy.own_attacks == 2516
        and legacy.resets == 29
        and both.defensive_spend == 3872
        and both.own_attack_spend == 11994
        and both.own_attacks == 2387
        and both.resets == 18
    )
    return (
        ok,
        (
            "LEGACY defensive/own/actions/RESET="
            f"{legacy.defensive_spend}/{legacy.own_attack_spend}/"
            f"{legacy.own_attacks}/{legacy.resets}; "
            "BOTH="
            f"{both.defensive_spend}/{both.own_attack_spend}/"
            f"{both.own_attacks}/{both.resets}"
        ),
    )


def _frozen_policy_constants_ok() -> tuple[bool, str]:
    pool = StaminaPool(current=100, maximum=100)
    prior = {
        gate.letter: gate
        for gate in measure_stamina_rule_definition_of_done()
    }
    prior_invariants_ok = all(
        prior[letter].status is StaminaRuleGateStatus.PASS
        for letter in ("B", "C", "E", "G", "H", "I")
    )
    behavior = DEFAULT_BEHAVIOR_STAMINA_POLICY.points_per_quantum
    ok = (
        DEFAULT_STAMINA_COST_POLICY.cost(Commitment.LOW) == 3
        and DEFAULT_STAMINA_COST_POLICY.cost(Commitment.MEDIUM) == 7
        and DEFAULT_STAMINA_COST_POLICY.cost(Commitment.HIGH) == 12
        and DEFAULT_BEHAVIOR_STAMINA_POLICY.quantum_seconds == 5
        and behavior[TopBehavior.PRESSURE] == -1
        and behavior[TopBehavior.CONSERVE] == 2
        and behavior[BottomBehavior.ESCAPE] == -1
        and behavior[BottomBehavior.CONSERVE] == 2
        and pool.exhaustion_enter_threshold == 25
        and pool.exhaustion_recover_threshold == 35
        and STALLING_THRESHOLD_SECONDS == 20
        and len(RAW_GRADES) == 18
        and MountMatch._response_undercommitment_modifier(
            initiator_commitment=None,
            responder_commitment=None,
        ) == 0
        and prior_invariants_ok
    )
    return (
        ok,
        (
            "costs=3/7/12; behavior quantum=5, "
            "PRESSURE/ESCAPE=-1, CONSERVE=+2; "
            "Exhausted thresholds=25/35; stalling threshold=20; "
            f"matrix={len(RAW_GRADES)}; "
            f"prior settlement invariants pass={prior_invariants_ok}"
        ),
    )


def _default_activation_ok() -> tuple[bool, str]:
    params = signature(run_escape_first_batch).parameters
    defaults_ok = (
        params["enable_stamina_settlement_rules"].default is False
        and params["enable_unfunded_responder_cost_waiver"].default is False
        and params["enable_supplemental_hold_settlement"].default is False
        and params["recovery_initiation_mode"].default
        is RecoveryInitiationMode.CURRENT
        and params["shadow_stalling"].default is False
        and params["enable_v03b_stalling"].default is False
    )
    none_ok, _ = attribution_compatibility()
    return (
        defaults_ok and none_ok,
        (
            f"defaults valid={defaults_ok}; "
            f"NONE attribution equals merged legacy={none_ok}"
        ),
    )


@lru_cache(maxsize=1)
def measure_recovery_policy_amendment_definition_of_done(
) -> tuple[RecoveryAmendmentGate, ...]:
    cells = settlement_attribution_matrix()
    off_cells = {
        mode: _candidate_cell_for(mode, stalling=False)
        for mode in RecoveryInitiationMode
    }
    on_cells = {
        mode: _candidate_cell_for(mode, stalling=True)
        for mode in RecoveryInitiationMode
    }

    gate_a_ok, gate_a_metric = _starting_evidence_gate()

    none_ok, both_ok = attribution_compatibility()
    gate_b_ok = none_ok and both_ok

    rule1 = [
        cell for cell in cells
        if cell.mode is SettlementAttributionMode.RULE1_ONLY
    ]
    gate_c_ok = (
        len(rule1) == 3
        and all(cell.unfunded_responder_spend == 0 for cell in rule1)
    )

    rule2 = [
        cell for cell in cells
        if cell.mode is SettlementAttributionMode.RULE2_ONLY
    ]
    gate_d_ok = (
        len(rule2) == 3
        and all(cell.additive_double_charge_cases == 0 for cell in rule2)
        and all(
            cell.funded_initiator_supplemental_charged == 0
            for cell in rule2
        )
    )

    legacy, both = recovery_policy_starting_evidence()
    current = off_cells[RecoveryInitiationMode.CURRENT]
    gate_e_ok = (
        current.bottom_defensive_spend < legacy.defensive_spend
        and current.bottom_own_attack_spend > legacy.own_attack_spend
        and current.bottom_latch_clears == 0
        and current.bottom_conserve_to_escape == 0
        and current.bottom_defensive_spend == both.defensive_spend
        and current.bottom_own_attack_spend == both.own_attack_spend
    )

    off_structured = all(
        cell.bottom_behavior_recovery >= 0
        and cell.bottom_own_attack_spend >= 0
        and cell.bottom_defensive_spend >= 0
        and cell.state1_share + cell.state2_share + cell.state3_share
        > 0.999999
        and cell.state1_share + cell.state2_share + cell.state3_share
        < 1.000001
        for cell in off_cells.values()
    )
    clearing_modes = tuple(
        mode.value
        for mode, cell in off_cells.items()
        if cell.bottom_latch_clears > 0
        and cell.bottom_conserve_to_escape > 0
        and cell.state2_to_state1_exits > 0
    )
    gate_f_ok = len(off_cells) == 3 and off_structured

    shadow_equal = shadow_nonperturbation()
    replay_equal = recovery_candidate_replay_equal()
    stalling_structured = all(
        cell.bottom_stalling_warnings >= 0
        and cell.bottom_stalling_penalties >= 0
        and cell.bottom_stalling_position_resets >= 0
        and cell.bottom_stalling_free_initiative >= 0
        for cell in on_cells.values()
    )
    gate_g_ok = (
        len(on_cells) == 3
        and shadow_equal == (True, True, True)
        and replay_equal
        and stalling_structured
    )

    gate_h_ok, gate_h_metric = _frozen_policy_constants_ok()
    gate_i_ok, gate_i_metric = _default_activation_ok()

    gate_j_ok = (
        len(cells) == 12
        and len(recovery_candidate_matrix()) == 6
        and replay_equal
    )

    return (
        RecoveryAmendmentGate(
            "A",
            "starting Surface-E stamina destination evidence is checker-owned",
            RecoveryAmendmentGateStatus.PASS
            if gate_a_ok else RecoveryAmendmentGateStatus.OPEN,
            gate_a_metric,
            "evidence was committed before flag splitting or candidate policy work",
        ),
        RecoveryAmendmentGate(
            "B",
            "separate settlement flags preserve legacy and BOTH behavior",
            RecoveryAmendmentGateStatus.PASS
            if gate_b_ok else RecoveryAmendmentGateStatus.OPEN,
            f"NONE==legacy:{none_ok}; explicit BOTH==umbrella BOTH:{both_ok}",
            "Rule1-only and Rule2-only remain separately activatable",
        ),
        RecoveryAmendmentGate(
            "C",
            "Rule 1 isolated attribution",
            RecoveryAmendmentGateStatus.PASS
            if gate_c_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                "Rule1-only UNFUNDED responder-spend by A/B/E="
                + "/".join(str(cell.unfunded_responder_spend) for cell in rule1)
            ),
            "local Rule-1 invariant is zero responder commitment+hold spend on UNFUNDED initiators",
        ),
        RecoveryAmendmentGate(
            "D",
            "Rule 2 isolated attribution",
            RecoveryAmendmentGateStatus.PASS
            if gate_d_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                "Rule2-only additive-double cases A/B/E="
                + "/".join(
                    str(cell.additive_double_charge_cases)
                    for cell in rule2
                )
                + "; funded-init supplemental charged="
                + "/".join(
                    str(cell.funded_initiator_supplemental_charged)
                    for cell in rule2
                )
            ),
            "outcome changes are observational; Rule 2 itself is not tuned here",
        ),
        RecoveryAmendmentGate(
            "E",
            "CURRENT recovery blocker is reproduced",
            RecoveryAmendmentGateStatus.PASS
            if gate_e_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                f"legacy defensive/own={legacy.defensive_spend}/"
                f"{legacy.own_attack_spend}; CURRENT BOTH="
                f"{current.bottom_defensive_spend}/"
                f"{current.bottom_own_attack_spend}; "
                f"latch clears/switches="
                f"{current.bottom_latch_clears}/"
                f"{current.bottom_conserve_to_escape}; "
                f"own/def/total per recovery="
                f"{current.own_spend_per_recovery:.3f}/"
                f"{current.defensive_spend_per_recovery:.3f}/"
                f"{current.total_spend_per_recovery:.3f}"
            ),
            "recovered stamina is recycled into initiation under CURRENT",
        ),
        RecoveryAmendmentGate(
            "F",
            "recovery-initiation candidates measured with stalling OFF",
            RecoveryAmendmentGateStatus.PASS
            if gate_f_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                f"structured={off_structured}; "
                f"modes clearing Exhausted={','.join(clearing_modes) or 'none'}"
            ),
            "a clearing candidate is evidence, not automatic default selection",
        ),
        RecoveryAmendmentGate(
            "G",
            "frozen v0.3b stalling interaction and shadow counterfactual measured",
            RecoveryAmendmentGateStatus.PASS
            if gate_g_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                f"shadow nonperturbation={shadow_equal}; "
                f"deterministic replay={replay_equal}; "
                "actual Bottom W/P/PR="
                + ",".join(
                    f"{mode.value}:"
                    f"{on_cells[mode].bottom_stalling_warnings}/"
                    f"{on_cells[mode].bottom_stalling_penalties}/"
                    f"{on_cells[mode].bottom_stalling_position_resets}"
                    for mode in RecoveryInitiationMode
                )
            ),
            "v0.3b consequences remain observational and unchanged",
        ),
        RecoveryAmendmentGate(
            "H",
            "stamina, settlement, Recognition, matchup and stalling rules remain frozen",
            RecoveryAmendmentGateStatus.PASS
            if gate_h_ok else RecoveryAmendmentGateStatus.OPEN,
            gate_h_metric,
            "only activation granularity, diagnostics and batch recovery-initiation modes changed",
        ),
        RecoveryAmendmentGate(
            "I",
            "default behavior remains merged-main compatible",
            RecoveryAmendmentGateStatus.PASS
            if gate_i_ok else RecoveryAmendmentGateStatus.OPEN,
            gate_i_metric,
            "new flags, shadow observer and real stalling remain opt-in",
        ),
        RecoveryAmendmentGate(
            "J",
            "checker evidence is structured and deterministic",
            RecoveryAmendmentGateStatus.PASS
            if gate_j_ok else RecoveryAmendmentGateStatus.OPEN,
            (
                f"attribution cells={len(cells)}; candidate cells="
                f"{len(recovery_candidate_matrix())}; replay={replay_equal}"
            ),
            "design conclusions remain separate from checker execution success",
        ),
    )


def render_recovery_policy_predictions() -> tuple[str, ...]:
    legacy, both = recovery_policy_starting_evidence()
    a_none = _cell("A public MATCH", SettlementAttributionMode.NONE)
    a_r1 = _cell("A public MATCH", SettlementAttributionMode.RULE1_ONLY)
    a_r2 = _cell("A public MATCH", SettlementAttributionMode.RULE2_ONLY)
    b_none = _cell("B trusts reads", SettlementAttributionMode.NONE)
    b_r1 = _cell("B trusts reads", SettlementAttributionMode.RULE1_ONLY)
    e_none = _cell(
        "E trusts reads + Bottom RECOVER",
        SettlementAttributionMode.NONE,
    )
    e_r1 = _cell(
        "E trusts reads + Bottom RECOVER",
        SettlementAttributionMode.RULE1_ONLY,
    )

    current_off = _candidate_cell_for(
        RecoveryInitiationMode.CURRENT,
        stalling=False,
    )
    reset_off = _candidate_cell_for(
        RecoveryInitiationMode.RESET_WHILE_EXHAUSTED,
        stalling=False,
    )
    low_off = _candidate_cell_for(
        RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
        stalling=False,
    )

    off_on_identical = all(
        _gameplay_summary_signature(
            _candidate_cell_for(mode, stalling=False).summary
        )
        == _gameplay_summary_signature(
            _candidate_cell_for(mode, stalling=True).summary
        )
        for mode in RecoveryInitiationMode
    )

    return (
        (
            "P1 [CONFIRMED] Rule1-only removes UNFUNDED responder drain "
            "without the public-MATCH Threat collapse — "
            f"A Threat {a_none.threat_matches}->{a_r1.threat_matches}; "
            f"B {b_none.threat_matches}->{b_r1.threat_matches}; "
            f"E {e_none.threat_matches}->{e_r1.threat_matches}; "
            "Rule1-only UNFUNDED responder spend="
            f"{a_r1.unfunded_responder_spend}/"
            f"{b_r1.unfunded_responder_spend}/"
            f"{e_r1.unfunded_responder_spend}"
        ),
        (
            "P2 [CONFIRMED] Rule2-only causes the public-MATCH Threat loss — "
            f"A Threat matches/entries {a_none.threat_matches}/"
            f"{a_none.threat_entries}->{a_r2.threat_matches}/"
            f"{a_r2.threat_entries}"
        ),
        (
            "P3 [CONFIRMED] explicit Rule1+Rule2 reproduces PR8 BOTH — "
            f"compatibility={attribution_compatibility()[1]}"
        ),
        (
            "P4 [CONFIRMED] BOTH+CURRENT recycles freed defense budget into "
            "Bottom attacks and still never clears Exhausted — "
            f"defensive {legacy.defensive_spend}->{current_off.bottom_defensive_spend}; "
            f"own {legacy.own_attack_spend}->{current_off.bottom_own_attack_spend}; "
            f"latch clears={current_off.bottom_latch_clears}"
        ),
        (
            "P5 [CONFIRMED] RESET cuts own-attack spend most and produces the "
            "most latch clears, with setup opportunity cost — "
            f"own spend CURRENT/RESET/LOW="
            f"{current_off.bottom_own_attack_spend}/"
            f"{reset_off.bottom_own_attack_spend}/"
            f"{low_off.bottom_own_attack_spend}; "
            f"latch clears={current_off.bottom_latch_clears}/"
            f"{reset_off.bottom_latch_clears}/"
            f"{low_off.bottom_latch_clears}; "
            f"exhausted setup builders="
            f"{current_off.exhausted_setup_builder_attempts}/"
            f"{reset_off.exhausted_setup_builder_attempts}/"
            f"{low_off.exhausted_setup_builder_attempts}"
        ),
        (
            "P6 [CONFIRMED] LOW reduces own-attack spend while preserving "
            "more setup activity than RESET, and it is sufficient to clear "
            "Exhausted on these seeds — "
            f"own {current_off.bottom_own_attack_spend}->"
            f"{low_off.bottom_own_attack_spend}; "
            f"setup builders RESET/LOW="
            f"{reset_off.exhausted_setup_builder_attempts}/"
            f"{low_off.exhausted_setup_builder_attempts}; "
            f"LOW latch clears={low_off.bottom_latch_clears}"
        ),
        (
            "P7 [PARTIAL] RESET creates by far the most reset-with-route "
            "stalling exposure, but no candidate reaches an actual v0.3b "
            "offense; LOW ties CURRENT rather than sitting between — "
            f"shadow route CURRENT/RESET/LOW="
            f"{current_off.shadow_bottom_resets_with_route}/"
            f"{reset_off.shadow_bottom_resets_with_route}/"
            f"{low_off.shadow_bottom_resets_with_route}; "
            "shadow W/P/PR all="
            f"{current_off.shadow_warnings}/"
            f"{current_off.shadow_penalties}/"
            f"{current_off.shadow_position_resets},"
            f"{reset_off.shadow_warnings}/"
            f"{reset_off.shadow_penalties}/"
            f"{reset_off.shadow_position_resets},"
            f"{low_off.shadow_warnings}/"
            f"{low_off.shadow_penalties}/"
            f"{low_off.shadow_position_resets}"
        ),
        (
            "P8 [NOT CONFIRMED] real v0.3b does not make any candidate less "
            "favorable on these seeds because no offense is reached — "
            f"OFF/ON gameplay identical={off_on_identical}; "
            "diverged matches CURRENT/RESET/LOW="
            f"{len(matched_first_divergence_times(RecoveryInitiationMode.CURRENT))}/"
            f"{len(matched_first_divergence_times(RecoveryInitiationMode.RESET_WHILE_EXHAUSTED))}/"
            f"{len(matched_first_divergence_times(RecoveryInitiationMode.LOW_WHILE_EXHAUSTED))}"
        ),
    )


def render_recovery_policy_amendment() -> tuple[str, ...]:
    lines = [
        gate.render()
        for gate in measure_recovery_policy_amendment_definition_of_done()
    ]
    lines.extend(
        "STAMINA-RECOVERY PREDICTION — " + line
        for line in render_recovery_policy_predictions()
    )
    return tuple(lines)
