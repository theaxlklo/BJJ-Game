"""Setup-policy observer-only characterization
(docs/SETUP_POLICY_CHARACTERIZATION.md).

No candidate policy is implemented. The observer wraps
EscapeFirstInitiatorPolicy.choose and MountMatch.attempt, delegating each real
call exactly once. For every real decision it also asks, read-only, what the
same lexicographic policy would choose if the setup tier did not exist (setup
advance probability forced to 0 for that query only). Not thread-safe: run
standalone, never concurrently with gameplay.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch

from ..domain.action import Commitment
from ..domain.model import Band, BottomBehavior, Side, TopBehavior
from ..engine.match import MountMatch
from ..interfaces.batch import (
    BatchBehaviorMode,
    BatchResponderMode,
    EscapeFirstInitiatorPolicy,
    run_escape_first_batch,
)
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from .d3b_promotion import canonical_kwargs
from .d3b_promotion_reference import canonical_surface_kwargs

EPS = 1e-12


def historical_protect_probe_kwargs() -> dict:
    """The v0.3a informed PRESSURE/PROTECT probe behind the --check debt line."""
    return dict(
        matches=100, base_seed=42, top_behavior=TopBehavior.PRESSURE,
        bottom_behavior=BottomBehavior.PROTECT, commitment=Commitment.MEDIUM,
        initial_clock=300, starting_axis=1.50, interval_seconds=5,
        top_stamina=100, bottom_stamina=100,
        bottom_behavior_mode=BatchBehaviorMode.FIXED,
        bottom_responder_mode=BatchResponderMode.INFORMED,
        enable_v02_setup=True, enable_v03_submissions=True,
    )


def surfaces() -> dict[str, dict]:
    return {
        "v0.3a PROTECT probe (historical debt)": historical_protect_probe_kwargs(),
        "A-PROD": canonical_surface_kwargs("A"),
        "B-PROD": canonical_surface_kwargs("B"),
        "E-PROD 42": canonical_kwargs(42, "OFF"),
        "E-PROD 142": canonical_kwargs(142, "OFF"),
    }


def _tiers(match) -> dict[str, int]:
    return {target: int(match.setup_state.tier(target))
            for target in match.setup_policy.target_action_ids}


def informed_ready_isolation_success(match) -> bool:
    """Would Ready Americana Arm Isolation succeed now against an informed
    (minimum-grade) Bottom, at the policy's own preview fidelity?

    Same engine call, Ready response set, stalemate override, exhaustion
    modifier and band condition as EscapeFirstInitiatorPolicy's
    _submission_entry_probability; only the responder model differs
    (minimum grade instead of random-blind weighting). Read-only.
    """
    if (not match.enable_v03_submissions
            or match.band not in {Band.STRONG, Band.LOCKED}):
        return False
    target = TOP_AMERICANA_ARM_ISOLATION
    ready_ids = match.setup_policy.ready_response_ids(target)
    modifier = match.exhaustion_policy.exchange_grade_modifier(
        initiator_band=match.top.stamina.band,
        responder_band=match.bottom.stamina.band,
    )
    grades = [
        match.engine.resolve_action(
            axis=match.axis, band=match.band, initiator=Side.TOP,
            action_id=target, response_id=response_id,
            top_behavior=match.top.behavior, bottom_behavior=match.bottom.behavior,
            external_grade_modifier=modifier,
            post_positional_grade_override=match.setup_policy.ready_final_grade_override(
                target, response_id),
        ).final_grade
        for response_id in ready_ids
    ]
    return min(grades).successful


def observe_batch(**kwargs):
    """Return the unmodified BatchSummary plus per-match ordered records."""
    original_choose = EscapeFirstInitiatorPolicy.choose
    original_setup = EscapeFirstInitiatorPolicy._setup_advance_probability
    original_attempt = MountMatch.attempt
    matches: list = []
    timelines: list[list[dict]] = []

    def current(match) -> list[dict]:
        if not matches or matches[-1] is not match:
            matches.append(match)
            timelines.append([])
        return timelines[-1]

    def observed_choose(policy, match):
        decision = original_choose(policy, match)
        with patch.object(EscapeFirstInitiatorPolicy, "_setup_advance_probability",
                          lambda *a, **k: 0.0):
            alternative = original_choose(policy, match)
        current(match).append(dict(
            kind="decision",
            t=match.elapsed_simulated_time,
            side=match.initiator.value,
            axis=match.axis,
            band=match.band.value,
            stamina=match.competitor(match.initiator).stamina.current,
            tiers=_tiers(match),
            informed_ready_isolation_success=(
                informed_ready_isolation_success(match)
                if match.initiator is Side.TOP else None
            ),
            action_id=decision.action_id,
            reason=decision.reason,
            escape_probability=decision.escape_probability,
            submission_probability=decision.submission_progress_probability,
            realized_axis=decision.expected_realized_axis,
            raw_axis=decision.expected_raw_axis,
            alt_action_id=alternative.action_id,
            alt_reason=alternative.reason,
            alt_realized_axis=alternative.expected_realized_axis,
            alt_raw_axis=alternative.expected_raw_axis,
        ))
        return decision

    def observed_attempt(match, *args, **kw):
        before = dict(axis=match.axis, tiers=_tiers(match),
                      stage=(match.submission_state.stage.value
                             if match.submission_state.active else None),
                      stamina=match.competitor(match.initiator).stamina.current,
                      side=match.initiator.value)
        result = original_attempt(match, *args, **kw)
        current(match).append(dict(
            kind="attempt",
            t=match.elapsed_simulated_time,
            action_id=kw["action_id"],
            side=before["side"],
            axis_before=before["axis"],
            axis_after=match.axis,
            tiers_before=before["tiers"],
            tiers_after=_tiers(match),
            stage_before=before["stage"],
            stage_after=(match.submission_state.stage.value
                         if match.submission_state.active else None),
            tapped=match.submission_tapped,
            exit=match.exit_destination.value if match.exit_destination else None,
            initiator_charged=result.stamina.charged,
            final_grade=result.resolution.final_grade.display,
            successful=result.resolution.final_grade.successful,
        ))
        return result

    with ExitStack() as stack:
        stack.enter_context(patch.object(EscapeFirstInitiatorPolicy, "choose", observed_choose))
        stack.enter_context(patch.object(MountMatch, "attempt", observed_attempt))
        summary = run_escape_first_batch(**kwargs)
    if (EscapeFirstInitiatorPolicy.choose is not original_choose
            or EscapeFirstInitiatorPolicy._setup_advance_probability is not original_setup):
        raise RuntimeError("policy wrappers not restored")
    return summary, timelines


def _following_attempt(events: list[dict], index: int):
    following = events[index + 1] if index + 1 < len(events) else None
    event = events[index]
    if (following is not None and following["kind"] == "attempt"
            and following["action_id"] == event["action_id"]
            and following["side"] == event["side"]):
        return following
    return None


def _is_counterfactual(events: list[dict], index: int) -> bool:
    """An action decision that is never executed. The D3-B handoff collector
    calls choose() for a LOCKOUT_HOLD counterfactual (interfaces/batch.py) and
    the window then holds; characterize() checks the count against D3-B holds."""
    event = events[index]
    return event["action_id"] is not None and _following_attempt(events, index) is None


def _pair(events: list[dict]):
    """Yield (decision, attempt or None) for every real policy decision."""
    for index, event in enumerate(events):
        if event["kind"] != "decision" or _is_counterfactual(events, index):
            continue
        yield event, _following_attempt(events, index)


def characterize(summary, timelines) -> dict:
    setup_targets = {}
    decisions = Counter()
    setup = Counter()
    builders = Counter()
    for events in timelines:
        for decision, attempt in _pair(events):
            side = decision["side"]
            decisions[f"{side}:{decision['reason']}"] += 1
            if decision["reason"] != "setup":
                continue
            key = side
            builders[f"{side}:{decision['action_id']}"] += 1
            setup[f"{key}:decisions"] += 1
            setup[f"{key}:alt_{decision['alt_reason']}"] += 1
            if side == Side.TOP.value:
                # Candidate gate S1: Ready target valued against an informed defender.
                blocked = not decision["informed_ready_isolation_success"]
                setup[f"{key}:S1_informed_gate_would_block"] += blocked
                if blocked:
                    setup[f"{key}:S1_block_alt_{decision['alt_reason']}"] += 1
            if decision["realized_axis"] < -EPS:
                setup[f"{key}:expected_realized_axis<0"] += 1
            if decision["alt_reason"] == "position" and (
                decision["alt_realized_axis"] > decision["realized_axis"] + EPS
            ):
                setup[f"{key}:forgoes_better_position"] += 1
                setup[f"{key}:forgone_expected_axis_x1000"] += round(
                    1000 * (decision["alt_realized_axis"] - decision["realized_axis"])
                )
            if attempt is not None:
                setup[f"{key}:attempts"] += 1
                setup[f"{key}:stamina_spent"] += attempt["initiator_charged"]
                delta = attempt["axis_after"] - attempt["axis_before"]
                # Attacker-signed axis: positive is good for the initiator.
                signed = delta if side == Side.TOP.value else -delta
                setup[f"{key}:realized_axis_x1000"] += round(1000 * signed)
                advanced = any(
                    attempt["tiers_after"][t] > attempt["tiers_before"][t]
                    for t in attempt["tiers_before"]
                )
                setup[f"{key}:advanced"] += advanced
                became_ready = any(
                    attempt["tiers_after"][t] == 2 and attempt["tiers_before"][t] < 2
                    for t in attempt["tiers_before"]
                )
                setup[f"{key}:reached_ready"] += became_ready

    ready_uses = Counter()
    calibration = Counter()
    for events in timelines:
        for decision, attempt in _pair(events):
            if attempt is None:
                continue
            target = attempt["action_id"]
            if target not in attempt["tiers_before"] or attempt["tiers_before"][target] != 2:
                continue
            # The policy's own success estimate for the Ready target, under its
            # random-blind responder model, versus the realized result.
            predicted = (decision["submission_probability"]
                         if target == TOP_AMERICANA_ARM_ISOLATION
                         else decision["escape_probability"])
            key = f"{attempt['side']}:{target}"
            calibration[f"{key}:policy_uses"] += 1
            calibration[f"{key}:predicted_successes_x1000"] += round(1000 * predicted)
            if target == TOP_AMERICANA_ARM_ISOLATION:
                calibration[f"{key}:informed_model_predicted_successes"] += bool(
                    decision["informed_ready_isolation_success"])
            calibration[f"{key}:actual_successes"] += (
                (attempt["stage_before"] is None and attempt["stage_after"] is not None)
                if target == TOP_AMERICANA_ARM_ISOLATION
                else attempt["exit"] is not None
            )
    for events in timelines:
        for event in events:
            if event["kind"] != "attempt":
                continue
            target = event["action_id"]
            if target not in event["tiers_before"] or event["tiers_before"][target] != 2:
                continue
            side = event["side"]
            ready_uses[f"{side}:{target}:uses"] += 1
            ready_uses[f"{side}:{target}:successful"] += event["successful"]
            ready_uses[f"{side}:{target}:exit"] += event["exit"] is not None
            if target == TOP_AMERICANA_ARM_ISOLATION:
                ready_uses[f"{side}:{target}:threat_entry"] += (
                    event["stage_before"] is None and event["stage_after"] is not None
                )
            setup_targets[target] = True

    unused_ready_at_end = Counter()
    for events in timelines:
        attempts = [e for e in events if e["kind"] == "attempt"]
        if attempts:
            for target, tier in attempts[-1]["tiers_after"].items():
                unused_ready_at_end[f"{target}:tier{tier}"] += 1

    counterfactual_calls = sum(
        _is_counterfactual(events, index)
        for events in timelines
        for index, event in enumerate(events)
        if event["kind"] == "decision"
    )
    handoff = getattr(summary, "post_clear_handoff", None)
    holds = (
        sum(event.get("k") == "hold" for match in handoff.matches for event in match.events)
        if handoff is not None else 0
    )
    if counterfactual_calls != holds:
        raise RuntimeError("unexecuted decisions do not match D3-B lockout holds")
    outcomes = Counter(summary.outcome_counts)
    return dict(
        matches=summary.matches,
        outcomes=dict(outcomes),
        threat_matches=summary.matches_reached_submission_threat,
        top_completed_setup_builds=summary.top_completed_setup_build_count,
        bottom_completed_setup_builds=summary.bottom_completed_setup_build_count,
        decisions_by_side_and_reason=dict(decisions),
        excluded_d3b_counterfactual_choose_calls=counterfactual_calls,
        setup_decisions=dict(setup),
        setup_builders=dict(builders),
        ready_target_uses=dict(ready_uses),
        ready_target_calibration=dict(calibration),
        setup_tiers_at_last_attempt=dict(unused_ready_at_end),
    )


def measure() -> dict:
    return {name: characterize(*observe_batch(**kwargs))
            for name, kwargs in surfaces().items()}


if __name__ == "__main__":
    target = Path("docs/evidence/setup_policy_characterization.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(measure(), indent=1, sort_keys=True) + "\n")
    print(target)
