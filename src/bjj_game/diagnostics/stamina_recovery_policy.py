from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from collections import Counter
from enum import Enum

from ..domain.model import ExitDestination
from ..interfaces.batch import BatchSummary, run_escape_first_batch
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
            f"UNFUNDED exchanges/responder spend="
            f"{cell.unfunded_initiator_exchanges}/"
            f"{cell.unfunded_responder_spend}"
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
