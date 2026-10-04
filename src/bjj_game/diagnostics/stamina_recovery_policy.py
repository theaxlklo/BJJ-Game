from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .stamina_economy import measured_surfaces
from .stamina_settlement import postchange_surfaces


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
