from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections import Counter
from enum import Enum
from statistics import median

from ..domain.model import ExitDestination
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
from .stamina_settlement import postchange_surfaces


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
