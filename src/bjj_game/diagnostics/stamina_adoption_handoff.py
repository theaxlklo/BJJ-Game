"""Stage-1 A9 handoff baseline for the stamina production-policy adoption.

Mechanically applies the A9 selection procedure frozen in
docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md to the
historical LOW+BOTH recovery surface, with CURRENT+Rule1-only as a control.
No analyst discretion: N, X, and M come only from the frozen formulas.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from statistics import median, quantiles

from ..interfaces.batch import (
    BatchSummary,
    HandoffEpisodeStatus,
    ReExhaustionHandoffEpisode,
    run_escape_first_batch,
)
from ..interfaces.recovery_policy import RecoveryInitiationMode
from .stamina_economy import _surface_kwargs
from .stamina_recovery_policy import _candidate_kwargs

A9_HORIZONS_SECONDS = (5, 10, 15, 20)
A9_SELECTION_FRACTION = 0.80
A9_MIN_TOTAL_REEXHAUSTIONS = 10
A9_WILSON_Z = 1.96
A9_MIN_ADMISSIBLE_CLEARS = 43


def wilson_upper_bound(k: int, n: int, z: float = A9_WILSON_Z) -> float:
    """95% Wilson score upper bound, no continuity correction (frozen)."""
    if n <= 0:
        raise ValueError("Wilson bound requires n > 0")
    if not 0 <= k <= n:
        raise ValueError("Wilson bound requires 0 <= k <= n")
    phat = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    center = (phat + z2 / (2 * n)) / denominator
    half = (z / denominator) * math.sqrt(
        phat * (1 - phat) / n + z2 / (4 * n * n)
    )
    return center + half


def display_round_up(value: float) -> float:
    """Display-only: round upward to the next 0.01."""
    return math.ceil(value * 100 - 1e-9) / 100


def minimum_admissible_clears(
    *,
    z: float = A9_WILSON_Z,
    half_width: float = 0.15,
) -> int:
    """Frozen M derivation: z * sqrt(0.25/n) <= half_width."""
    return math.ceil((z / half_width) ** 2 * 0.25)


@dataclass(frozen=True, slots=True)
class HorizonCounts:
    horizon_seconds: int
    reexhausted_within: int
    survived_through: int
    right_censored: int

    @property
    def admissible(self) -> int:
        return self.reexhausted_within + self.survived_through

    @property
    def rate(self) -> float | None:
        if self.admissible == 0:
            return None
        return self.reexhausted_within / self.admissible


def horizon_counts(
    episodes: tuple[ReExhaustionHandoffEpisode, ...],
    horizon_seconds: int,
) -> HorizonCounts:
    statuses = [episode.status_at(horizon_seconds) for episode in episodes]
    return HorizonCounts(
        horizon_seconds=horizon_seconds,
        reexhausted_within=statuses.count(
            HandoffEpisodeStatus.REEXHAUSTED_WITHIN_HORIZON
        ),
        survived_through=statuses.count(
            HandoffEpisodeStatus.SURVIVED_THROUGH_HORIZON
        ),
        right_censored=statuses.count(HandoffEpisodeStatus.RIGHT_CENSORED),
    )


@dataclass(frozen=True, slots=True)
class MatchLevelSensitivity:
    matches_with_admissible_clear: int
    matches_with_rapid_reexhaustion: int

    @property
    def p_match(self) -> float | None:
        if self.matches_with_admissible_clear == 0:
            return None
        return (
            self.matches_with_rapid_reexhaustion
            / self.matches_with_admissible_clear
        )


def match_level_sensitivity(
    episodes: tuple[ReExhaustionHandoffEpisode, ...],
    horizon_seconds: int,
) -> MatchLevelSensitivity:
    admissible_matches: set[int] = set()
    rapid_matches: set[int] = set()
    for episode in episodes:
        status = episode.status_at(horizon_seconds)
        if status is HandoffEpisodeStatus.RIGHT_CENSORED:
            continue
        admissible_matches.add(episode.match_index)
        if status is HandoffEpisodeStatus.REEXHAUSTED_WITHIN_HORIZON:
            rapid_matches.add(episode.match_index)
    return MatchLevelSensitivity(
        matches_with_admissible_clear=len(admissible_matches),
        matches_with_rapid_reexhaustion=len(rapid_matches),
    )


@dataclass(frozen=True, slots=True)
class HandoffSurfaceReport:
    label: str
    matches: int
    clear_events: int
    eventual_reexhaustions: int
    clears_non_exhausted_through_match_end: int
    time_to_reexhaustion_median: float | None
    time_to_reexhaustion_p25: float | None
    time_to_reexhaustion_p75: float | None
    horizons: tuple[HorizonCounts, ...]

    def at(self, horizon_seconds: int) -> HorizonCounts:
        for counts in self.horizons:
            if counts.horizon_seconds == horizon_seconds:
                return counts
        raise KeyError(horizon_seconds)


def surface_report(
    label: str,
    summary: BatchSummary,
) -> HandoffSurfaceReport:
    if summary.reexhaustion_handoffs is None:
        raise RuntimeError("re-exhaustion handoff measurement missing")
    episodes = summary.reexhaustion_handoffs.episodes
    times = sorted(
        episode.seconds_to_reexhaustion
        for episode in episodes
        if episode.seconds_to_reexhaustion is not None
    )
    # Percentiles: statistics.quantiles(n=4, method="inclusive"), defined
    # when at least two re-exhaustions are observed.
    p25 = p75 = None
    if len(times) >= 2:
        p25, _, p75 = quantiles(times, n=4, method="inclusive")
    return HandoffSurfaceReport(
        label=label,
        matches=summary.matches,
        clear_events=len(episodes),
        eventual_reexhaustions=len(times),
        clears_non_exhausted_through_match_end=sum(
            1 for episode in episodes
            if episode.reexhausted_elapsed_seconds is None
        ),
        time_to_reexhaustion_median=median(times) if times else None,
        time_to_reexhaustion_p25=p25,
        time_to_reexhaustion_p75=p75,
        horizons=tuple(
            horizon_counts(episodes, horizon)
            for horizon in A9_HORIZONS_SECONDS
        ),
    )


@dataclass(frozen=True, slots=True)
class A9Selection:
    reexhaustions_by_horizon: tuple[tuple[int, int], ...]
    total_t: int
    selected_n: int | None
    admissible_at_n: int | None
    censored_at_n: int | None
    reexhausted_at_n: int | None
    p_baseline: float | None
    x_upper: float | None
    x_display: float | None
    m_min: int
    stop_reasons: tuple[str, ...]

    @property
    def stopped(self) -> bool:
        return bool(self.stop_reasons)


def select_a9(report: HandoffSurfaceReport) -> A9Selection:
    """Apply the frozen A9 selection procedure and STOP conditions."""
    r_by_h = tuple(
        (counts.horizon_seconds, counts.reexhausted_within)
        for counts in report.horizons
    )
    total_t = report.at(20).reexhausted_within
    m_min = A9_MIN_ADMISSIBLE_CLEARS
    stop: list[str] = []

    if total_t < A9_MIN_TOTAL_REEXHAUSTIONS:
        stop.append(f"T=R(20)={total_t} < {A9_MIN_TOTAL_REEXHAUSTIONS}")

    selected_n = next(
        (
            horizon
            for horizon, observed in r_by_h
            if observed >= A9_SELECTION_FRACTION * total_t
        ),
        None,
    )
    if total_t < A9_MIN_TOTAL_REEXHAUSTIONS:
        # STOP: no N is selected from an inadequate T (including T=0).
        selected_n = None
    elif selected_n is None:
        stop.append("no h in {5,10,15,20}s satisfies R(h) >= 0.80*T")

    admissible = censored = reexhausted = None
    p_baseline = x_upper = x_display = None
    if selected_n is not None:
        at_n = report.at(selected_n)
        admissible = at_n.admissible
        censored = at_n.right_censored
        reexhausted = at_n.reexhausted_within
        if admissible < m_min:
            stop.append(
                f"baseline admissible clears at N={admissible} < {m_min}"
            )
        if admissible > 0:
            p_baseline = reexhausted / admissible
            x_upper = wilson_upper_bound(reexhausted, admissible)
            x_display = display_round_up(x_upper)

    return A9Selection(
        reexhaustions_by_horizon=r_by_h,
        total_t=total_t,
        selected_n=selected_n,
        admissible_at_n=admissible,
        censored_at_n=censored,
        reexhausted_at_n=reexhausted,
        p_baseline=p_baseline,
        x_upper=x_upper,
        x_display=x_display,
        m_min=m_min,
        stop_reasons=tuple(stop),
    )


def low_both_baseline_kwargs() -> dict:
    """Historical LOW+BOTH recovery anchor surface (stalling OFF + shadow)."""
    return {
        **_candidate_kwargs(
            RecoveryInitiationMode.LOW_WHILE_EXHAUSTED,
            stalling=False,
            shadow=True,
        ),
        "measure_reexhaustion_handoffs": True,
    }


def current_rule1_control_kwargs() -> dict:
    """Existing Surface E Rule1-only attribution cell (CURRENT recovery)."""
    return {
        **_surface_kwargs("E trusts reads + Bottom RECOVER"),
        "enable_unfunded_responder_cost_waiver": True,
        "enable_supplemental_hold_settlement": False,
        "measure_stamina_economy": True,
        "measure_reexhaustion_handoffs": True,
    }


@lru_cache(maxsize=1)
def low_both_baseline_summary() -> BatchSummary:
    return run_escape_first_batch(**low_both_baseline_kwargs())


@lru_cache(maxsize=1)
def current_rule1_control_summary() -> BatchSummary:
    return run_escape_first_batch(**current_rule1_control_kwargs())


def a9_baseline() -> tuple[
    HandoffSurfaceReport,
    A9Selection,
    MatchLevelSensitivity | None,
]:
    summary = low_both_baseline_summary()
    report = surface_report("LOW+BOTH historical baseline", summary)
    selection = select_a9(report)
    sensitivity = (
        match_level_sensitivity(
            summary.reexhaustion_handoffs.episodes,
            selection.selected_n,
        )
        if selection.selected_n is not None
        else None
    )
    return report, selection, sensitivity


def a9_control() -> HandoffSurfaceReport:
    return surface_report(
        "CURRENT+Rule1-only control",
        current_rule1_control_summary(),
    )


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else repr(value)


def render_a9_baseline() -> tuple[str, ...]:
    lines: list[str] = []
    report, selection, sensitivity = a9_baseline()
    control = a9_control()
    for surface in (report, control):
        lines.append(
            f"A9 HANDOFF — {surface.label}: matches={surface.matches}; "
            f"clears={surface.clear_events}; "
            f"eventual re-exhaustions={surface.eventual_reexhaustions}; "
            f"non-Exhausted through match end="
            f"{surface.clears_non_exhausted_through_match_end}; "
            f"time-to-re-exhaustion median/p25/p75="
            f"{_fmt(surface.time_to_reexhaustion_median)}/"
            f"{_fmt(surface.time_to_reexhaustion_p25)}/"
            f"{_fmt(surface.time_to_reexhaustion_p75)}"
        )
        for counts in surface.horizons:
            lines.append(
                f"A9 HANDOFF — {surface.label} h={counts.horizon_seconds}s: "
                f"R(h)={counts.reexhausted_within}; "
                f"survived={counts.survived_through}; "
                f"censored={counts.right_censored}; "
                f"admissible={counts.admissible}; "
                f"rate={_fmt(counts.rate)}"
                + (
                    "; reason=no clear events"
                    if surface.clear_events == 0
                    else ""
                )
            )
    lines.append(
        "A9 SELECTION — "
        f"T={selection.total_t}; N={selection.selected_n}; "
        f"admissible@N={selection.admissible_at_n}; "
        f"censored@N={selection.censored_at_n}; "
        f"R(N)={selection.reexhausted_at_n}; "
        f"p_baseline={_fmt(selection.p_baseline)}; "
        f"X={_fmt(selection.x_upper)}; "
        f"X display={_fmt(selection.x_display)}; "
        f"M={selection.m_min}; "
        f"STOP={'; '.join(selection.stop_reasons) or 'none'}"
    )
    if sensitivity is not None:
        lines.append(
            "A9 MATCH-LEVEL SENSITIVITY (advisory) — "
            f"matches with admissible clear="
            f"{sensitivity.matches_with_admissible_clear}; "
            f"matches with rapid re-exhaustion="
            f"{sensitivity.matches_with_rapid_reexhaustion}; "
            f"p_match={_fmt(sensitivity.p_match)}"
        )
    return tuple(lines)
