from __future__ import annotations

from dataclasses import dataclass

from ..domain.catalog import TechniqueCatalog
from ..domain.matchup import MatchupTable
from ..domain.model import Band, BandChange, BottomBehavior, DriftResult, ResolutionResult, Side, TopBehavior
from ..positions.mount.catalog import MOUNT_CATALOG
from ..positions.mount.matchups import MOUNT_MATCHUPS
from ..positions.mount.rules import MOUNT_RULES, MountRuleSet


@dataclass(frozen=True, slots=True)
class MountResolutionEngine:
    """Deterministic service that resolves Mount drift and action/response exchanges.

    All policy/data dependencies are constructor-injected. ``default()`` wires the
    production Mount-v0 catalog, matchup table and rule set.
    """

    rules: MountRuleSet
    catalog: TechniqueCatalog
    matchups: MatchupTable

    @classmethod
    def default(cls) -> "MountResolutionEngine":
        return cls(rules=MOUNT_RULES, catalog=MOUNT_CATALOG, matchups=MOUNT_MATCHUPS)

    def simulate_drift(
        self,
        *,
        axis: float,
        band: Band,
        clock_seconds: int,
        duration_seconds: int,
        top_behavior: TopBehavior,
        bottom_behavior: BottomBehavior,
    ) -> DriftResult:
        if clock_seconds < 0:
            raise ValueError("clock_seconds must be non-negative")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        actual = min(clock_seconds, duration_seconds)
        start_axis = axis
        start_band = band
        changes: list[BandChange] = []
        rate = self.rules.drift_rate(top_behavior, bottom_behavior)
        for elapsed in range(1, actual + 1):
            axis = self.rules.clamp_axis(axis + rate)
            next_band, tick_changes = self.rules.update_band(axis, band)
            clock_at_change = clock_seconds - elapsed
            for change in tick_changes:
                changes.append(BandChange(change.before, change.after, clock_at_change))
            band = next_band
        return DriftResult(
            start_axis=start_axis,
            end_axis=axis,
            total_drift=round(axis - start_axis, 10),
            start_clock=clock_seconds,
            end_clock=clock_seconds - actual,
            start_band=start_band,
            end_band=band,
            band_changes=tuple(changes),
        )

    def resolve_action(
        self,
        *,
        axis: float,
        band: Band,
        initiator: Side,
        action_id: str,
        response_id: str,
        top_behavior: TopBehavior = TopBehavior.PRESSURE,
        bottom_behavior: BottomBehavior = BottomBehavior.ESCAPE,
        external_grade_modifier: int = 0,
    ) -> ResolutionResult:
        action = self.catalog.get(action_id)
        response = self.catalog.get(response_id)
        if action.side is not initiator:
            raise ValueError(f"{action_id} belongs to {action.side.value}, not {initiator.value}")
        if response.side is not initiator.opponent:
            raise ValueError(f"{response_id} is not a {initiator.opponent.value} response")

        raw = self.matchups.grade(action_id, response_id)
        opposing_behavior = bottom_behavior if initiator is Side.TOP else top_behavior
        bmod = self.rules.behavior_modifier(action=action, opposing_behavior=opposing_behavior)
        behavior_grade = raw.shift(bmod)
        pmod = self.rules.positional_modifier(initiator=initiator, band=band)
        positional_grade = behavior_grade.shift(pmod)
        final = positional_grade.shift(external_grade_modifier)
        value = int(final)
        delta = float(value if initiator is Side.TOP else -value)
        proposed = round(axis + delta, 10)

        special_clamp = False
        failure_clamp = False
        escape_threshold = False
        exit_destination = None

        if action.clamp_at_mount_floor and proposed <= self.rules.min_axis:
            special_clamp = True
            axis_after = self.rules.min_axis
        elif final.failed and proposed <= self.rules.min_axis:
            failure_clamp = True
            axis_after = self.rules.min_axis
        else:
            escape_threshold = (
                action.escape_capable and final.successful and proposed <= self.rules.min_axis
            )
            if escape_threshold:
                exit_destination = self.rules.exit_destination(
                    action=action, final_grade=final, band_before=band
                )
                if exit_destination is None:
                    raise RuntimeError(
                        f"Escape-capable action {action.id} has no Exit Map for final grade {final.display}"
                    )
                axis_after = proposed
            else:
                axis_after = self.rules.clamp_axis(proposed)

        if exit_destination is None:
            band_after, changes = self.rules.update_band(axis_after, band)
        else:
            band_after, changes = band, ()

        return ResolutionResult(
            initiator=initiator,
            action_id=action_id,
            response_id=response_id,
            raw_grade=raw,
            behavior_grade=behavior_grade,
            final_grade=final,
            behavior_modifier=bmod,
            positional_modifier=pmod,
            external_grade_modifier=external_grade_modifier,
            grade_value=value,
            axis_before=axis,
            axis_delta=delta,
            proposed_axis=proposed,
            axis_after=axis_after,
            band_before=band,
            band_after=band_after,
            band_changes=changes,
            failure_clamp_used=failure_clamp,
            floor_clamp_used=special_clamp,
            escape_threshold_reached=escape_threshold,
            exit_capable_action=action.escape_capable,
            exit_destination=exit_destination,
        )


MOUNT_ENGINE = MountResolutionEngine.default()
