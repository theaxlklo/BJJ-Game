from __future__ import annotations

from dataclasses import dataclass, field

from ..positions.mount.catalog import (
    BOTTOM_ELBOW_KNEE_ESCAPE,
    ENTITY_BY_ID,
    ENTITIES,
    TOP_ACTIONS,
    BOTTOM_ACTIONS,
    TOP_RESPONSES,
    BOTTOM_RESPONSES,
    actions_for,
    responses_for,
)
from ..positions.mount.matchups import RAW_GRADES, raw_grade
from ..positions.mount.compat import axis_can_have_band, resolve_action
from ..domain.model import Band, BottomBehavior, ExitDestination, Grade, Side, TopBehavior
from ..positions.mount.names import RESOLVER, normalize_name


@dataclass(frozen=True, slots=True)
class ReachabilityHit:
    action_id: str
    top_behavior: TopBehavior
    destination: ExitDestination
    band: Band
    axis: float
    response_id: str
    final_grade: Grade


@dataclass(slots=True)
class CheckReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    reachable_exits: dict[ExitDestination, list[str]] = field(default_factory=dict)
    escape_reachability: dict[
        tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
    ] = field(default_factory=dict)
    never_best_responses: list[str] = field(default_factory=list)
    perfect_response_lock: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def _sample_axes() -> list[float]:
    return [round(i / 100, 2) for i in range(10, 401)]


def _final_grade_without_behavior(action_id: str, response_id: str, side: Side, band: Band) -> Grade:
    result = resolve_action(
        axis={Band.LOOSE: 0.50, Band.STABLE: 1.50, Band.STRONG: 2.50, Band.LOCKED: 3.50}[band],
        band=band,
        initiator=side,
        action_id=action_id,
        response_id=response_id,
        top_behavior=TopBehavior.PRESSURE,
        bottom_behavior=BottomBehavior.ESCAPE,
    )
    return result.final_grade


def _collect_escape_reachability() -> dict[
    tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
]:
    reachability: dict[
        tuple[str, TopBehavior, ExitDestination], list[ReachabilityHit]
    ] = {}
    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        destinations = set(action.exit_map.values()) | set(action.band_exit_overrides.values())
        for top_behavior in TopBehavior:
            for destination in destinations:
                reachability[(action.id, top_behavior, destination)] = []
            for band in Band:
                for axis in _sample_axes():
                    if not axis_can_have_band(axis, band):
                        continue
                    for response in TOP_RESPONSES:
                        result = resolve_action(
                            axis=axis,
                            band=band,
                            initiator=Side.BOTTOM,
                            action_id=action.id,
                            response_id=response.id,
                            top_behavior=top_behavior,
                            bottom_behavior=BottomBehavior.ESCAPE,
                        )
                        if result.exit_destination is None:
                            continue
                        reachability[(action.id, top_behavior, result.exit_destination)].append(
                            ReachabilityHit(
                                action_id=action.id,
                                top_behavior=top_behavior,
                                destination=result.exit_destination,
                                band=band,
                                axis=axis,
                                response_id=response.id,
                                final_grade=result.final_grade,
                            )
                        )
    return reachability


def _axis_range(hits: list[ReachabilityHit]) -> tuple[float, float] | None:
    if not hits:
        return None
    axes = [hit.axis for hit in hits]
    return min(axes), max(axes)


def run_checks() -> CheckReport:
    report = CheckReport()

    if len(ENTITIES) != 12:
        report.errors.append(f"Expected 12 canonical entities, found {len(ENTITIES)}")
    if len(TOP_ACTIONS) != 3 or len(BOTTOM_ACTIONS) != 3:
        report.errors.append("Expected exactly three actions per side")
    if len(TOP_RESPONSES) != 3 or len(BOTTOM_RESPONSES) != 3:
        report.errors.append("Expected exactly three responses per side")
    if len(RAW_GRADES) != 18:
        report.errors.append(f"Expected 18 raw lookup entries, found {len(RAW_GRADES)}")

    expected = {
        (action.id, response.id)
        for side in (Side.TOP, Side.BOTTOM)
        for action in actions_for(side)
        for response in responses_for(side.opponent)
    }
    actual = set(RAW_GRADES)
    for missing in sorted(expected - actual):
        report.errors.append(f"Missing lookup entry: {missing[0]} vs {missing[1]}")
    for extra in sorted(actual - expected):
        report.errors.append(f"Unexpected lookup entry: {extra[0]} vs {extra[1]}")

    ids = [entity.id for entity in ENTITIES]
    if len(ids) != len(set(ids)):
        report.errors.append("Stable IDs are not unique")

    if RESOLVER.collision_map():
        report.errors.append(f"Normalized aliases collide: {RESOLVER.collision_map()}")

    for forbidden in ("S-Mount", "Elbow-Knee Connection", "High Mount", "Hip Frame", "Body Frame"):
        try:
            RESOLVER.resolve(forbidden)
        except ValueError:
            pass
        else:
            report.errors.append(f"Reserved/misleading name unexpectedly resolves: {forbidden!r}")

    try:
        upa = RESOLVER.resolve("upa")
        if upa.canonical_name != "Trap-and-Roll Escape":
            report.errors.append("'upa' does not resolve to Trap-and-Roll Escape")
    except ValueError as exc:
        report.errors.append(str(exc))

    for entity in ENTITIES:
        if "+" in entity.canonical_name or "&" in entity.canonical_name:
            report.errors.append(f"Canonical name contains + or &: {entity.canonical_name}")

    if normalize_name("follow+knee") != "follow and knee":
        report.errors.append("'+' is not replaced as a character during normalization")
    if normalize_name("follow&knee") != "follow and knee":
        report.errors.append("'&' is not replaced as a character during normalization")
    for value in (
        "Repummel",
        "Hip Follow + Knee Re-Pummel",
        "Hip Follow & Knee Repummel",
        "hip_follow_and_knee_repummel",
        "HIP-FOLLOW-AND-KNEE-RE-PUMMEL",
    ):
        try:
            if RESOLVER.resolve(value).canonical_name != "Hip Follow and Knee Re-Pummel":
                report.errors.append(f"Hip Follow alias resolves incorrectly: {value!r}")
        except ValueError as exc:
            report.errors.append(str(exc))

    bridge = next(e for e in ENTITIES if e.canonical_name == "Bridge")
    elbow = ENTITY_BY_ID[BOTTOM_ELBOW_KNEE_ESCAPE]
    trap = next(e for e in ENTITIES if e.canonical_name == "Trap-and-Roll Escape")
    americana = next(e for e in ENTITIES if e.canonical_name == "Americana Arm Isolation")
    if bridge.escape_capable:
        report.errors.append("Bridge must not be escape-capable")
    if not elbow.escape_capable or not trap.escape_capable:
        report.errors.append("Elbow-Knee and Trap-and-Roll must be escape-capable")
    if americana.exit_map:
        report.errors.append("Americana Arm Isolation must not have a submission finish in v0")

    for responder_side in (Side.TOP, Side.BOTTOM):
        responses = responses_for(responder_side)
        initiator_side = responder_side.opponent
        actions = actions_for(initiator_side)
        for response in responses:
            grades = [raw_grade(action.id, response.id) for action in actions]
            if all(grade <= Grade.FAILURE for grade in grades):
                report.errors.append(f"Response beats every initiated action: {response.canonical_name}")
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            grades = [raw_grade(action.id, response.id) for response in responses_for(side.opponent)]
            if all(not grade.successful for grade in grades):
                report.errors.append(f"Initiated action never succeeds raw: {action.canonical_name}")
            if all(grade.successful for grade in grades):
                report.errors.append(f"Initiated action always succeeds raw: {action.canonical_name}")

    report.escape_reachability = _collect_escape_reachability()
    aggregate: dict[ExitDestination, list[str]] = {dest: [] for dest in ExitDestination}
    for (action_id, top_behavior, destination), hits in report.escape_reachability.items():
        action = ENTITY_BY_ID[action_id]
        if not hits:
            report.errors.append(
                f"Unreachable Exit Map branch under Top {top_behavior.value}: "
                f"{action.canonical_name} -> {destination.value}"
            )
            continue
        for hit in hits:
            response = ENTITY_BY_ID[hit.response_id]
            aggregate[destination].append(
                f"{action.canonical_name}; Top {top_behavior.value}; {hit.band.value} "
                f"axis={hit.axis:+.2f} vs {response.canonical_name} -> {hit.final_grade.display}"
            )
    report.reachable_exits = aggregate

    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        for destination in sorted(set(action.exit_map.values()) | set(action.band_exit_overrides.values()), key=lambda d: d.value):
            p_hits = report.escape_reachability[(action.id, TopBehavior.PRESSURE, destination)]
            h_hits = report.escape_reachability[(action.id, TopBehavior.HOLD, destination)]
            p_range = _axis_range(p_hits)
            h_range = _axis_range(h_hits)
            if p_range and h_range and p_range != h_range:
                report.info.append(
                    f"TOP-BEHAVIOR REACHABILITY EFFECT: {action.canonical_name} -> {destination.value}; "
                    f"PRESSURE {p_range[0]:+.2f}..{p_range[1]:+.2f}; "
                    f"HOLD {h_range[0]:+.2f}..{h_range[1]:+.2f}"
                )

    response_is_best: dict[str, bool] = {
        response.id: False for response in (*TOP_RESPONSES, *BOTTOM_RESPONSES)
    }
    all_actions_have_failure_counter = True
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            pairs = [(response, raw_grade(action.id, response.id)) for response in responses_for(side.opponent)]
            best_grade = min(grade for _, grade in pairs)
            if best_grade > Grade.FAILURE:
                all_actions_have_failure_counter = False
            for response, grade in pairs:
                if grade == best_grade:
                    response_is_best[response.id] = True
    report.perfect_response_lock = all_actions_have_failure_counter
    if report.perfect_response_lock:
        report.info.append(
            "PERFECT-RESPONSE LOCK: PRESENT — every initiated action has an unrestricted response that holds it to Failure or worse; known v0 scaffolding limitation"
        )
    for response_id, is_best in response_is_best.items():
        if not is_best:
            response = ENTITY_BY_ID[response_id]
            report.never_best_responses.append(response.canonical_name)
            report.info.append(f"NEVER-BEST (hedge response): {response.canonical_name}")

    cap_hits = 0
    modifier_applications = 0
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            for response in responses_for(side.opponent):
                raw = raw_grade(action.id, response.id)
                for band in Band:
                    shift = -1 if (
                        (side is Side.BOTTOM and band in {Band.STRONG, Band.LOCKED})
                        or (side is Side.TOP and band is Band.LOOSE)
                    ) else 0
                    if shift:
                        modifier_applications += 1
                        if raw is Grade.STRONG_FAILURE:
                            cap_hits += 1
    if cap_hits:
        report.info.append(
            f"POSITIONAL MODIFIER CAP-HITS: {cap_hits}/{modifier_applications} applicable raw-grade cases clamp at Strong Failure"
        )

    return report


def _render_reachability_ranges(report: CheckReport) -> list[str]:
    lines: list[str] = []
    for action in BOTTOM_ACTIONS:
        if not action.escape_capable:
            continue
        destinations = sorted(set(action.exit_map.values()) | set(action.band_exit_overrides.values()), key=lambda d: d.value)
        for top_behavior in TopBehavior:
            lines.append(f"
{action.canonical_name} — Top {top_behavior.value}")
            for destination in destinations:
                hits = report.escape_reachability.get((action.id, top_behavior, destination), [])
                lines.append(f"  {destination.value}: {'REACHABLE' if hits else 'UNREACHABLE'}")
                overall = _axis_range(hits)
                if overall is not None:
                    lines.append(f"    Overall axis range: {overall[0]:+.2f}..{overall[1]:+.2f}")
                for band in Band:
                    band_hits = [hit for hit in hits if hit.band is band]
                    band_range = _axis_range(band_hits)
                    if band_range is None:
                        continue
                    responses = sorted({ENTITY_BY_ID[hit.response_id].canonical_name for hit in band_hits})
                    grades = sorted({hit.final_grade.display for hit in band_hits})
                    lines.append(
                        f"    {band.value:<6} {band_range[0]:+.2f}..{band_range[1]:+.2f} | "
                        f"response(s): {', '.join(responses)} | final grade(s): {', '.join(grades)}"
                    )
    return lines


def render_enumeration() -> str:
    lines: list[str] = []
    lines.append("MOUNT v0 — EXHAUSTIVE CHECKER")
    lines.append("=" * 34)

    for side in (Side.TOP, Side.BOTTOM):
        lines.append("")
        lines.append(f"{side.value.upper()} INITIATED — RAW 3x3 MATRIX")
        for action in actions_for(side):
            lines.append(f"
{action.canonical_name} [{action.id}]")
            for response in responses_for(side.opponent):
                grade = raw_grade(action.id, response.id)
                lines.append(f"  vs {response.canonical_name:<32} -> {grade.display}")

    lines.append("
VISIBLE-BAND POSITIONAL MODIFIERS (behavior-neutral)")
    lines.append("-" * 52)
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            for response in responses_for(side.opponent):
                finals = ", ".join(
                    f"{band.value}={_final_grade_without_behavior(action.id, response.id, side, band).display}"
                    for band in Band
                )
                lines.append(f"{action.short_name} vs {response.short_name}: {finals}")

    lines.append("
BEST-COUNTER ANALYSIS")
    lines.append("-" * 21)
    for side in (Side.TOP, Side.BOTTOM):
        for action in actions_for(side):
            pairs = [(response, raw_grade(action.id, response.id)) for response in responses_for(side.opponent)]
            best_grade = min(grade for _, grade in pairs)
            best = [response for response, grade in pairs if grade == best_grade]
            best_names = ", ".join(response.canonical_name for response in best)
            band_finals = []
            for band in Band:
                finals = [_final_grade_without_behavior(action.id, response.id, side, band) for response in best]
                band_finals.append(f"{band.value}={min(finals).display}")
            succeeds = any(
                _final_grade_without_behavior(action.id, response.id, side, band).successful
                for response in best
                for band in Band
            )
            lines.append(
                f"{action.canonical_name}: best response={best_names}; raw={best_grade.display}; "
                f"{' | '.join(band_finals)}; succeeds vs unrestricted best response={'YES' if succeeds else 'NO'}"
            )

    report = run_checks()
    lines.append("
ESCAPE BRANCH REACHABILITY — FULL TUNING WATCH")
    lines.append("-" * 51)
    lines.extend(_render_reachability_ranges(report))

    lines.append("
STRUCTURAL DIAGNOSTICS")
    lines.append("-" * 22)
    if report.perfect_response_lock:
        lines.append("PERFECT-RESPONSE LOCK: PRESENT")
        lines.append("Classification: KNOWN V0 SCAFFOLDING LIMITATION")
        lines.append("Expected future resolution: v0.2 setup/Ready/initiative legality restricts available responses.")
    else:
        lines.append("PERFECT-RESPONSE LOCK: ABSENT")
    for name in report.never_best_responses:
        lines.append(f"INFO: NEVER-BEST (hedge response): {name}")

    lines.append("
CHECK RESULT")
    lines.append("-" * 12)
    for message in report.info:
        if not message.startswith("PERFECT-RESPONSE") and not message.startswith("NEVER-BEST"):
            lines.append(f"INFO: {message}")
    for warning in report.warnings:
        lines.append(f"WARN: {warning}")
    for error in report.errors:
        lines.append(f"ERROR: {error}")
    lines.append(f"STATUS: {'PASS' if report.ok else 'FAIL'}")
    return "
".join(lines)
