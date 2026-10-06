"""Late recovery / match-pacing observer-only characterization
(docs/LATE_RECOVERY_CHARACTERIZATION.md).

No candidate mechanics are implemented. Scoped wrappers delegate each
MountMatch advance/attempt/reset_window call exactly once and record detached
stamina snapshots. Not thread-safe: run standalone, never concurrently with
gameplay.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch

from ..domain.model import Side
from ..domain.stamina import StaminaBand
from ..engine.match import MountMatch
from ..interfaces.batch import run_escape_first_batch
from .d3b_promotion import canonical_kwargs

ESCAPES = ("Half Guard", "Open Guard", "Reversal")
CLEAR_BINS = (
    ("never Exhausted", None),
    ("Exhausted, never cleared", None),
    ("cleared <= 150 s", 150),
    ("cleared 151-200 s", 200),
    ("cleared 201-250 s", 250),
    ("cleared 251-300 s", 300),
)


def production_runs() -> dict[str, dict]:
    """Canonical E-PROD, both seeds, stalling OFF + shadow and ON."""
    return {
        f"E-PROD {seed} {stalling}": canonical_kwargs(seed, stalling)
        for seed in (42, 142)
        for stalling in ("OFF", "ON")
    }


def _exhausted(pool) -> bool:
    return pool.band is StaminaBand.EXHAUSTED


def observe_batch(**kwargs):
    """Return the unmodified BatchSummary plus per-match ordered event lists."""
    originals = {name: getattr(MountMatch, name)
                 for name in ("advance", "attempt", "reset_window")}
    matches: list = []
    timelines: list[list[dict]] = []

    def wrap(name):
        def delegated(match, *args, **kw):
            if not matches or matches[-1] is not match:
                matches.append(match)
                timelines.append([])
            before = dict(
                t0=match.elapsed_simulated_time,
                initiator=match.initiator.value,
                bottom_before=match.bottom.stamina.current,
                top_before=match.top.stamina.current,
                bottom_exhausted_before=_exhausted(match.bottom.stamina),
                top_exhausted_before=_exhausted(match.top.stamina),
            )
            result = originals[name](match, *args, **kw)
            event = dict(
                kind=name,
                **before,
                t=match.elapsed_simulated_time,
                bottom_after=match.bottom.stamina.current,
                top_after=match.top.stamina.current,
                bottom_exhausted_after=_exhausted(match.bottom.stamina),
                top_exhausted_after=_exhausted(match.top.stamina),
            )
            if name == "advance":
                event.update(
                    bottom_behavior=result.bottom_stamina.behavior.value,
                    bottom_behavior_gain=result.bottom_stamina.recovered,
                    bottom_behavior_drain=result.bottom_stamina.spent,
                )
            elif name == "attempt":
                effective = result.attempt.effective_commitment
                event.update(
                    action_id=kw["action_id"],
                    requested=kw["commitment"].value,
                    effective=effective.value if effective else "UNFUNDED",
                    initiator_charged=result.stamina.charged,
                    response_charged=(
                        result.response_stamina.charged
                        if result.response_stamina is not None else 0
                    ),
                    hold_charged=(
                        result.submission_hold_stamina.charged
                        if result.submission_hold_stamina is not None else 0
                    ),
                )
            timelines[-1].append(event)
            return result
        return delegated

    with ExitStack() as stack:
        for name in originals:
            stack.enter_context(patch.object(MountMatch, name, wrap(name)))
        summary = run_escape_first_batch(**{**kwargs, "measure_stamina_economy": True})
    return summary, timelines


def _bottom_delta(event: dict) -> int:
    """Bottom stamina change attributed to explicit sources."""
    if event["kind"] == "advance":
        return event["bottom_behavior_gain"] - event["bottom_behavior_drain"]
    if event["kind"] == "attempt":
        if event["initiator"] == Side.BOTTOM.value:
            return -event["initiator_charged"]
        return -(event["response_charged"] + event["hold_charged"])
    return 0


def match_record(index: int, outcome: str, end: int, events: list[dict]) -> dict:
    entry = next((e["t"] for e in events
                  if not e["bottom_exhausted_before"] and e["bottom_exhausted_after"]), None)
    clear = next((e["t"] for e in events
                  if e["bottom_exhausted_before"] and not e["bottom_exhausted_after"]), None)
    top_entry = next((e["t"] for e in events
                      if not e["top_exhausted_before"] and e["top_exhausted_after"]), None)
    unexplained = sum(
        e["bottom_after"] - e["bottom_before"] - _bottom_delta(e) for e in events
    )
    exhausted_seconds = sum(
        e["t"] - e["t0"] for e in events
        if e["kind"] == "advance" and e["bottom_exhausted_before"]
    )

    entry_stamina = next((e["bottom_after"] for e in events
                          if not e["bottom_exhausted_before"] and e["bottom_exhausted_after"]), None)
    opening = Counter()
    for e in events:
        if entry is not None and e["t"] > entry:
            break
        if e["kind"] == "advance":
            opening["seconds"] += e["t"] - e["t0"]
            opening["behavior_drain"] += e["bottom_behavior_drain"]
            opening["behavior_gain"] += e["bottom_behavior_gain"]
        elif e["kind"] == "attempt" and e["initiator"] == Side.BOTTOM.value:
            opening[f"bottom_attempts_{e['requested']}"] += 1
            opening["bottom_initiation_spend"] += e["initiator_charged"]
        elif e["kind"] == "attempt":
            opening[f"top_attempts_{e['effective']}"] += 1
            opening["response_spend"] += e["response_charged"]
            opening["hold_spend"] += e["hold_charged"]
            opening["top_initiation_spend"] += e["initiator_charged"]

    episode = Counter()
    if entry is not None:
        stop = clear if clear is not None else end
        for e in events:
            if e["t0"] < entry or e["t"] > stop or not e["bottom_exhausted_before"]:
                continue
            if e["kind"] == "advance":
                episode["seconds"] += e["t"] - e["t0"]
                episode["conserve_gain"] += e["bottom_behavior_gain"]
                episode["behavior_drain"] += e["bottom_behavior_drain"]
            elif e["kind"] == "attempt" and e["initiator"] == Side.BOTTOM.value:
                episode["bottom_attempts"] += 1
                episode[f"bottom_attempts_{e['requested']}"] += 1
                episode["bottom_initiation_spend"] += e["initiator_charged"]
            elif e["kind"] == "attempt":
                episode["top_attempts"] += 1
                episode["top_attempts_funded"] += e["effective"] != "UNFUNDED"
                episode["response_spend"] += e["response_charged"]
                episode["hold_spend"] += e["hold_charged"]
            elif e["kind"] == "reset_window" and e["initiator"] == Side.BOTTOM.value:
                episode["bottom_resets"] += 1

    after_clear = Counter()
    if clear is not None:
        for e in events:
            if e["t0"] < clear or e["initiator"] != Side.BOTTOM.value:
                continue
            if e["kind"] == "attempt":
                state = "Exhausted" if e["bottom_exhausted_before"] else "non-Exhausted"
                after_clear[f"attempts_{state}_{e['requested']}"] += 1
            elif e["kind"] == "reset_window":
                after_clear["resets"] += 1

    terminal = None
    if outcome in ESCAPES:
        last = next(e for e in reversed(events) if e["kind"] == "attempt")
        if entry is None or last["t"] <= entry:
            phase = "before first Exhausted entry"
        elif clear is None or last["t0"] < clear:
            phase = "during first Exhausted episode"
        else:
            phase = "after first clear"
        terminal = dict(
            phase=phase,
            requested=last["requested"],
            bottom_exhausted=last["bottom_exhausted_before"],
        )

    return dict(
        match_index=index,
        outcome=outcome,
        end=end,
        bottom_first_exhausted=entry,
        bottom_stamina_at_first_exhausted=entry_stamina,
        bottom_first_clear=clear,
        top_first_exhausted=top_entry,
        bottom_exhausted_seconds=exhausted_seconds,
        unexplained_bottom_delta=unexplained,
        opening_to_first_exhausted=dict(opening),
        first_episode=dict(episode),
        after_first_clear=dict(after_clear),
        escape=terminal,
    )


def _quantiles(values: list[int]) -> dict:
    if not values:
        return dict(n=0)
    ordered = sorted(values)

    def rank(p: float) -> int:
        return ordered[min(len(ordered) - 1, max(0, round(p * (len(ordered) - 1))))]

    return dict(n=len(ordered), min=ordered[0], p10=rank(0.10), median=rank(0.50),
                p90=rank(0.90), max=ordered[-1])


def _bin(record: dict) -> str:
    if record["bottom_first_exhausted"] is None:
        return CLEAR_BINS[0][0]
    if record["bottom_first_clear"] is None:
        return CLEAR_BINS[1][0]
    for label, limit in CLEAR_BINS[2:]:
        if record["bottom_first_clear"] <= limit:
            return label
    raise AssertionError("clear after match end")


def _outcome_class(outcome: str) -> str:
    if outcome in ESCAPES:
        return "escape"
    if outcome.startswith("TAP"):
        return "tap"
    if outcome.startswith("TIMEOUT"):
        return "timeout"
    return outcome


def characterize(summary, timelines) -> dict:
    match_records = summary.stamina_economy.matches
    if len(match_records) != len(timelines):
        raise RuntimeError("match/timeline alignment failed")
    records = [
        match_record(index, rec.outcome, rec.elapsed_seconds, events)
        for index, (rec, events) in enumerate(zip(match_records, timelines))
    ]
    entered = [r for r in records if r["bottom_first_exhausted"] is not None]
    cleared = [r for r in records if r["bottom_first_clear"] is not None]

    opening_totals = Counter()
    for r in entered:
        opening_totals.update(r["opening_to_first_exhausted"])
    episode_totals = Counter()
    for r in entered:
        episode_totals.update(r["first_episode"])
    after_totals = Counter()
    for r in cleared:
        after_totals.update(r["after_first_clear"])

    by_bin = {label: Counter() for label, _ in CLEAR_BINS}
    for r in records:
        by_bin[_bin(r)][_outcome_class(r["outcome"])] += 1

    return dict(
        matches=len(records),
        unexplained_bottom_delta=sum(r["unexplained_bottom_delta"] for r in records),
        outcomes=dict(Counter(r["outcome"] for r in records)),
        bottom_first_exhausted=_quantiles([r["bottom_first_exhausted"] for r in entered]),
        top_first_exhausted=_quantiles(
            [r["top_first_exhausted"] for r in records if r["top_first_exhausted"] is not None]
        ),
        bottom_first_clear=_quantiles([r["bottom_first_clear"] for r in cleared]),
        first_episode_duration_cleared=_quantiles(
            [r["bottom_first_clear"] - r["bottom_first_exhausted"] for r in cleared]
        ),
        bottom_exhausted_share_of_match_time=round(
            sum(r["bottom_exhausted_seconds"] for r in records)
            / sum(r["end"] for r in records), 4
        ),
        remaining_after_first_clear=_quantiles([r["end"] - r["bottom_first_clear"] for r in cleared]),
        bottom_stamina_at_first_exhausted=_quantiles(
            [r["bottom_stamina_at_first_exhausted"] for r in entered]
        ),
        opening_totals_entered_matches=dict(opening_totals),
        first_episode_totals=dict(episode_totals),
        after_first_clear_totals=dict(after_totals),
        outcome_by_first_clear=({label: dict(counts) for label, counts in by_bin.items()}),
        escapes_by_phase=dict(Counter(
            r["escape"]["phase"] for r in records if r["escape"] is not None
        )),
        escapes_by_commitment_and_state=dict(Counter(
            f'{r["escape"]["requested"]}/{"Exhausted" if r["escape"]["bottom_exhausted"] else "non-Exhausted"}'
            for r in records if r["escape"] is not None
        )),
        per_match=records,
    )


def measure() -> dict:
    return {name: characterize(*observe_batch(**kwargs))
            for name, kwargs in production_runs().items()}


if __name__ == "__main__":
    target = Path("docs/evidence/late_recovery_characterization.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(measure(), indent=1, sort_keys=True) + "\n")
    print(target)
