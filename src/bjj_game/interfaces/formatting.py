from __future__ import annotations

from ..positions.mount.catalog import ENTITY_BY_ID
from ..domain.model import DriftResult, ResolutionResult


def format_clock(seconds: int) -> str:
    minutes, secs = divmod(max(0, seconds), 60)
    return f"{minutes}:{secs:02d}"


def format_drift(result: DriftResult, top_behavior: str, bottom_behavior: str) -> str:
    lines = [
        "DRIFT SUMMARY",
        f"Clock: {format_clock(result.start_clock)} → {format_clock(result.end_clock)}",
        f"Actual Duration: {result.start_clock - result.end_clock} simulated seconds",
        f"Top: {top_behavior}",
        f"Bottom: {bottom_behavior}",
        f"Start Axis: {result.start_axis:+.2f}",
        f"Total Drift: {result.total_drift:+.2f}",
        f"End Axis: {result.end_axis:+.2f}",
        f"Visible Band: {result.end_band.value}",
    ]
    for change in result.band_changes:
        when = f" at {format_clock(change.clock_seconds)}" if change.clock_seconds is not None else ""
        lines.append(f"Band Change: {change.before.value} → {change.after.value}{when}")
    return "\n".join(lines)


def format_resolution(result: ResolutionResult, clock_seconds: int, top_behavior: str, bottom_behavior: str) -> str:
    action = ENTITY_BY_ID[result.action_id]
    response = ENTITY_BY_ID[result.response_id]
    behavior_text = "None" if result.behavior_modifier == 0 else f"{result.behavior_modifier:+d} grade"
    position_text = "None" if result.positional_modifier == 0 else f"{result.positional_modifier:+d} grade"
    exit_text = result.exit_destination.value if result.exit_destination else "None"
    lines = [
        "DECISION",
        f"Clock: {format_clock(clock_seconds)}",
        f"Axis before: {result.axis_before:+.2f}",
        f"Visible band before: {result.band_before.value}",
        f"Top behavior: {top_behavior}",
        f"Bottom behavior: {bottom_behavior}",
        f"Initiator: {result.initiator.value.title()}",
        f"Initiated action: {action.canonical_name} [{action.id}]",
        f"Response: {response.canonical_name} [{response.id}]",
        f"Raw grade: {result.raw_grade.display} ({int(result.raw_grade):+d})",
        f"Behavior modifier: {behavior_text}",
        f"Grade after behavior: {result.behavior_grade.display}",
        f"Positional modifier: {position_text}",
        f"Final grade: {result.final_grade.display} ({int(result.final_grade):+d})",
        f"Grade numeric value: {result.grade_value:+d}",
        f"Axis delta: {result.axis_delta:+.2f}",
        f"Proposed axis: {result.proposed_axis:+.2f}",
        f"Failure clamp used?: {'Yes' if result.failure_clamp_used else 'No'}",
        f"Bridge clamp used?: {'Yes' if result.bridge_clamp_used else 'No'}",
        f"Escape threshold reached?: {'Yes' if result.escape_threshold_reached else 'No'}",
        f"Exit-capable action?: {'Yes' if result.exit_capable_action else 'No'}",
        f"Axis after: {result.axis_after:+.2f}",
        f"Visible band after: {result.band_after.value}",
        f"Exit destination: {exit_text}",
    ]
    for change in result.band_changes:
        lines.append(f"Band Change: {change.before.value} → {change.after.value}")
    if result.bridge_clamp_used:
        lines.append("Bridge Special Rule: successful disruption may reach Loose, but Bridge cannot break Mount in v0.")
    return "\n".join(lines)
