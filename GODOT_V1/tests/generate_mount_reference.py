#!/usr/bin/env python3
"""Independent Python Mount-v0 fixture generator; run with PYTHONPATH=src."""
import json
from pathlib import Path

from bjj_game.domain.model import Band, Grade, TopBehavior, BottomBehavior
from bjj_game.engine.mount_engine import MOUNT_ENGINE
from bjj_game.positions.mount.catalog import MOUNT_CATALOG
from bjj_game.positions.mount.matchups import MOUNT_MATCHUPS

BAND = {Band.LOOSE: 0, Band.STABLE: 1, Band.STRONG: 2, Band.LOCKED: 3}
AXIS = [
    (0.10, Band.LOOSE), (0.50, Band.LOOSE), (0.80, Band.LOOSE),
    (1.0, Band.STABLE), (1.19, Band.STABLE),
    (1.5, Band.STABLE), (1.9, Band.STABLE), (1.9, Band.STRONG),
    (2.1, Band.STABLE), (2.1, Band.STRONG), (2.5, Band.STRONG),
    (2.9, Band.STRONG), (2.9, Band.LOCKED),
    (3.5, Band.LOCKED), (4.0, Band.LOCKED),
]
BEHAVIORS = [
    (TopBehavior.PRESSURE, BottomBehavior.ESCAPE),
    (TopBehavior.PRESSURE, BottomBehavior.PROTECT),
    (TopBehavior.HOLD, BottomBehavior.ESCAPE),
    (TopBehavior.HOLD, BottomBehavior.PROTECT),
    (TopBehavior.CONSERVE, BottomBehavior.CONSERVE),
]
FIELDS = (
    "raw_grade", "behavior_grade", "final_grade", "behavior_modifier",
    "positional_modifier", "external_grade_modifier", "grade_value",
    "axis_before", "axis_delta", "proposed_axis", "axis_after",
    "band_before", "band_after", "failure_clamp_used", "floor_clamp_used",
    "escape_threshold_reached", "exit_capable_action", "exit_destination",
)


def changes(data):
    return [
        {"before": BAND[c.before], "after": BAND[c.after],
         **({"clock_seconds": c.clock_seconds} if c.clock_seconds is not None else {})}
        for c in data
    ]


def result_fields(result):
    out = {}
    for field in FIELDS:
        value = getattr(result, field)
        if field in ("band_before", "band_after"):
            value = BAND[value]
        elif field == "exit_destination":
            value = "" if value is None else value.value
        elif isinstance(value, Grade):
            value = int(value)
        out[field] = value
    out["band_changes"] = changes(result.band_changes)
    return out


def main():
    assert len(MOUNT_CATALOG.entities) == 12
    assert len(MOUNT_MATCHUPS.entries) == 18
    cases, drifts = [], []
    for axis, band in AXIS:
        assert MOUNT_ENGINE.rules.axis_can_have_band(axis, band)
    for action_id, response_id in sorted(MOUNT_MATCHUPS.entries):
        side = MOUNT_CATALOG.get(action_id).side
        for axis, band in AXIS:
            for top, bottom in BEHAVIORS:
                for modifier in (-1, 0, 1):
                    r = MOUNT_ENGINE.resolve_action(
                        axis=axis, band=band, initiator=side,
                        action_id=action_id, response_id=response_id,
                        top_behavior=top, bottom_behavior=bottom,
                        external_grade_modifier=modifier)
                    cases.append({
                        "axis": axis, "band": BAND[band], "initiator": side.value,
                        "action_id": action_id, "response_id": response_id,
                        "top_behavior": top.value, "bottom_behavior": bottom.value,
                        "external_grade_modifier": modifier, "override": 99,
                        "expected": result_fields(r),
                    })
        for grade in Grade:
            r = MOUNT_ENGINE.resolve_action(
                axis=1.5, band=Band.STABLE, initiator=side,
                action_id=action_id, response_id=response_id,
                post_positional_grade_override=grade)
            cases.append({
                "axis": 1.5, "band": BAND[Band.STABLE], "initiator": side.value,
                "action_id": action_id, "response_id": response_id,
                "top_behavior": "PRESSURE", "bottom_behavior": "ESCAPE",
                "external_grade_modifier": 0, "override": int(grade),
                "expected": result_fields(r),
            })
    for axis, band in AXIS:
        for top, bottom in BEHAVIORS:
            for clock, duration in ((0, 5), (1, 5), (4, 7), (15, 10)):
                r = MOUNT_ENGINE.simulate_drift(
                    axis=axis, band=band, clock_seconds=clock,
                    duration_seconds=duration,
                    top_behavior=top, bottom_behavior=bottom)
                drifts.append({
                    "axis": axis, "band": BAND[band],
                    "clock_seconds": clock, "duration_seconds": duration,
                    "top_behavior": top.value, "bottom_behavior": bottom.value,
                    "expected": {
                        "start_axis": r.start_axis, "end_axis": r.end_axis,
                        "total_drift": r.total_drift,
                        "start_clock": r.start_clock, "end_clock": r.end_clock,
                        "start_band": BAND[r.start_band], "end_band": BAND[r.end_band],
                        "band_changes": changes(r.band_changes),
                    },
                })
    output = Path(__file__).parent / "generated" / "mount_reference.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({
        "schema": 1, "actions": cases, "drifts": drifts,
    }, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Python reference generated: {len(cases)} actions, {len(drifts)} drifts")


if __name__ == "__main__":
    main()
