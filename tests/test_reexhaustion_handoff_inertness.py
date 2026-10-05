"""Stage-1A A9 observer hardening: sampling completeness and inertness.

These tests never inspect A9 episode contents on the frozen historical
surfaces. The 100-seed replay compares gameplay only, with the observer's own
output dropped before comparison. Episode-level checks use synthetic fixtures
only (non-canonical seeds and starting stamina).
"""

from dataclasses import replace
import unittest
from unittest import mock

from bjj_game.diagnostics.stamina_recovery_policy import (
    _candidate_kwargs,
    _first_divergence_for_match,
    _gameplay_summary_signature,
    matched_first_divergence_times,
    recovery_candidate_matrix,
)
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, TopBehavior
from bjj_game.domain.stamina import StaminaBand, StaminaPool
from bjj_game.engine.match import MountMatch
from bjj_game.engine.stamina import (
    DEFAULT_BEHAVIOR_STAMINA_POLICY,
    BehaviorStaminaMeter,
)
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces.batch import (
    BatchBehaviorMode,
    BatchResponderMode,
    BatchResponseCommitmentMode,
    ReExhaustionHandoffObserver,
    run_escape_first_batch,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode


def _record_matches():
    """Patch batch's MountMatch factory to keep each real match instance.

    The factory returns the genuine MountMatch; it only remembers it.
    """
    created: list[MountMatch] = []

    def factory(*args, **kwargs):
        match = MountMatch(*args, **kwargs)
        created.append(match)
        return match

    return created, mock.patch.object(batch_module, "MountMatch", factory)


def _match_gameplay_signature(match: MountMatch) -> tuple:
    """Every gameplay-authoritative per-match field the engine exposes."""
    return (
        match.history,
        match.clock_seconds,
        match.axis,
        match.band,
        match.initiator,
        match.position,
        match.top.stamina.current,
        match.top.stamina.band,
        match.bottom.stamina.current,
        match.bottom.stamina.band,
        match.top.behavior,
        match.bottom.behavior,
        match.top_behavior_stamina_meter,
        match.bottom_behavior_stamina_meter,
        match.exit_destination,
        match.exit_reason,
        match.setup_state,
        match.submission_state,
        match.submission_tapped,
        match.stalling_tracker,
        match.free_initiative_pending,
        match.free_initiative_beneficiary,
    )


def _run_gameplay_only(kwargs: dict, *, observer: bool):
    """Run a batch and return gameplay evidence with A9 output discarded.

    Returns (summary without A9 output, per-match signatures, observer ran).
    The A9 episodes are never returned, counted, or rendered.
    """
    created, patch = _record_matches()
    with patch:
        summary = run_escape_first_batch(
            **kwargs,
            measure_reexhaustion_handoffs=observer,
        )
    observer_ran = summary.reexhaustion_handoffs is not None
    summary = replace(summary, reexhaustion_handoffs=None)
    return (
        summary,
        tuple(_match_gameplay_signature(match) for match in created),
        observer_ran,
    )


class StaminaLatchMutationDirectionTests(unittest.TestCase):
    """Case-A proof obligations at the StaminaPool mutation boundary."""

    @staticmethod
    def _reachable_pools():
        """Every reachable (current, latched) state for a 100-point pool."""
        for current in range(0, 101):
            if current <= 25:
                yield StaminaPool(current=current)
                continue
            unlatched = StaminaPool(current=100)
            unlatched.spend_up_to(100 - current)
            yield unlatched
            if current < 35:
                latched = StaminaPool(current=25)
                latched.recover_up_to(current - 25)
                yield latched

    @staticmethod
    def _clone(pool: StaminaPool) -> StaminaPool:
        clone = StaminaPool(current=pool.current)
        if (clone.band is StaminaBand.EXHAUSTED) != (
            pool.band is StaminaBand.EXHAUSTED
        ):
            clone = StaminaPool(current=25)
            clone.recover_up_to(pool.current - 25)
        return clone

    def test_reachable_states_cover_both_hysteresis_branches(self):
        states = {
            (pool.current, pool.band is StaminaBand.EXHAUSTED)
            for pool in self._reachable_pools()
        }
        for current in range(26, 35):
            self.assertIn((current, True), states)
            self.assertIn((current, False), states)
        for exhausted_current in range(0, 26):
            self.assertIn((exhausted_current, True), states)
            self.assertNotIn((exhausted_current, False), states)
        for clear_current in range(35, 101):
            self.assertIn((clear_current, False), states)
            self.assertNotIn((clear_current, True), states)

    def test_spend_can_never_clear_exhausted(self):
        for template in self._reachable_pools():
            for amount in range(0, 101):
                pool = self._clone(template)
                before = pool.band is StaminaBand.EXHAUSTED
                pool.spend_up_to(amount)
                after = pool.band is StaminaBand.EXHAUSTED
                self.assertFalse(
                    before and not after,
                    (template.current, amount),
                )

    def test_recover_can_never_enter_exhausted(self):
        for template in self._reachable_pools():
            for amount in range(0, 101):
                pool = self._clone(template)
                before = pool.band is StaminaBand.EXHAUSTED
                pool.recover_up_to(amount)
                after = pool.band is StaminaBand.EXHAUSTED
                self.assertFalse(
                    not before and after,
                    (template.current, amount),
                )

    def test_behavior_economy_applies_at_most_one_mutation_per_advance(self):
        calls: list[str] = []
        original_spend = StaminaPool.spend_up_to
        original_recover = StaminaPool.recover_up_to

        def spend(self, requested):
            calls.append("spend")
            return original_spend(self, requested)

        def recover(self, requested):
            calls.append("recover")
            return original_recover(self, requested)

        behaviors = (*TopBehavior, *BottomBehavior)
        with mock.patch.object(StaminaPool, "spend_up_to", spend), \
                mock.patch.object(StaminaPool, "recover_up_to", recover):
            for behavior in behaviors:
                for remainder in range(-4, 5):
                    for duration in range(0, 61):
                        calls.clear()
                        DEFAULT_BEHAVIOR_STAMINA_POLICY.apply(
                            pool=StaminaPool(current=30),
                            behavior=behavior,
                            duration_seconds=duration,
                            meter=BehaviorStaminaMeter(
                                remainder_units=remainder
                            ),
                        )
                        self.assertLessEqual(
                            len(calls),
                            1,
                            (behavior, remainder, duration),
                        )


def _audit_timeline(events) -> tuple[list[str], list[list[tuple]]]:
    """Check fixed-sample completeness against mutation-level transitions.

    Events are tuples:
      ("start", exhausted)
      ("sample", elapsed, exhausted)
      ("transition", elapsed, exhausted_after)  # Bottom latch changes only
      ("finish",)

    Returns (violations, per-match reference episodes) where reference
    episodes are rebuilt from mutation-level transitions only.
    """
    violations: list[str] = []
    matches: list[list[tuple]] = []
    active = False
    transitions_since_sample = 0
    episodes: list[list] = []
    for event in events:
        kind = event[0]
        if kind == "start":
            active = True
            transitions_since_sample = 0
            episodes = []
        elif kind == "transition":
            if not active:
                continue
            _, elapsed, exhausted_after = event
            transitions_since_sample += 1
            if transitions_since_sample > 1:
                violations.append(
                    f"multiple Bottom latch transitions before sample "
                    f"at {elapsed}s"
                )
            if not exhausted_after:
                episodes.append([elapsed, None])
            elif episodes and episodes[-1][1] is None:
                episodes[-1][1] = elapsed
        elif kind == "sample":
            transitions_since_sample = 0
        elif kind == "finish":
            matches.append([tuple(episode) for episode in episodes])
            active = False
    return violations, matches


def _traced_batch(kwargs: dict):
    """Run with the observer and a mutation-level Bottom latch trace."""
    events: list[tuple] = []
    created: list[MountMatch] = []

    def factory(*args, **factory_kwargs):
        match = MountMatch(*args, **factory_kwargs)
        created.append(match)
        return match

    original_refresh = StaminaPool._refresh_exhaustion_latch
    original_start = ReExhaustionHandoffObserver.start_match
    original_observe = ReExhaustionHandoffObserver.observe
    original_finish = ReExhaustionHandoffObserver.finish_match

    def refresh(self):
        before = self._exhausted_latched
        original_refresh(self)
        after = self._exhausted_latched
        if before != after and created and self is created[-1].bottom.stamina:
            events.append(
                ("transition", created[-1].elapsed_simulated_time, after)
            )

    def start(self, *, match_index, elapsed_seconds, bottom_exhausted):
        events.append(("start", bottom_exhausted))
        return original_start(
            self,
            match_index=match_index,
            elapsed_seconds=elapsed_seconds,
            bottom_exhausted=bottom_exhausted,
        )

    def observe(self, *, elapsed_seconds, bottom_exhausted):
        events.append(("sample", elapsed_seconds, bottom_exhausted))
        return original_observe(
            self,
            elapsed_seconds=elapsed_seconds,
            bottom_exhausted=bottom_exhausted,
        )

    def finish(self, *, elapsed_seconds, bottom_exhausted):
        result = original_finish(
            self,
            elapsed_seconds=elapsed_seconds,
            bottom_exhausted=bottom_exhausted,
        )
        events.append(("finish",))
        return result

    with mock.patch.object(batch_module, "MountMatch", factory), \
            mock.patch.object(
                StaminaPool, "_refresh_exhaustion_latch", refresh
            ), \
            mock.patch.object(
                ReExhaustionHandoffObserver, "start_match", start
            ), \
            mock.patch.object(ReExhaustionHandoffObserver, "observe", observe), \
            mock.patch.object(
                ReExhaustionHandoffObserver, "finish_match", finish
            ):
        summary = run_escape_first_batch(
            **kwargs,
            measure_reexhaustion_handoffs=True,
        )
    return summary, events


# Synthetic completeness fixtures: non-canonical seeds (outside 42..241),
# chosen only so latch clears and re-entries occur in a few short matches.
_SYNTHETIC_BASE = dict(
    matches=6,
    base_seed=910_000,
    bottom_behavior=BottomBehavior.ESCAPE,
    initial_clock=300,
    interval_seconds=5,
    top_stamina=100,
    bottom_behavior_mode=BatchBehaviorMode.RECOVER,
    bottom_responder_mode=BatchResponderMode.INFORMED,
    enable_v02_setup=True,
    enable_v03_submissions=True,
    enable_v04_commitment_semantics=True,
)

_SYNTHETIC_FIXTURES = (
    (
        "public MATCH, Exhausted start",
        dict(
            _SYNTHETIC_BASE,
            top_behavior=TopBehavior.HOLD,
            commitment=Commitment.LOW,
            starting_axis=3.00,
            bottom_stamina=20,
            response_commitment_mode=BatchResponseCommitmentMode.MATCH,
            enable_v04b_recognition=False,
        ),
    ),
    (
        "Recognition, fresh start",
        dict(
            _SYNTHETIC_BASE,
            top_behavior=TopBehavior.PRESSURE,
            commitment=Commitment.MEDIUM,
            starting_axis=1.50,
            bottom_stamina=100,
            response_commitment_mode=BatchResponseCommitmentMode.RECOGNITION,
            enable_v04b_recognition=True,
        ),
    ),
)

_SETTLEMENT_VARIANTS = (
    {},
    {"enable_unfunded_responder_cost_waiver": True},
    {
        "enable_unfunded_responder_cost_waiver": True,
        "enable_supplemental_hold_settlement": True,
    },
)


class ObserverSamplingCompletenessTests(unittest.TestCase):
    def test_audit_detects_two_transitions_between_samples(self):
        # Negative control: an engine that cleared and re-exhausted inside
        # one operation would be reported, so the audit is not vacuous.
        violations, _ = _audit_timeline(
            [
                ("start", True),
                ("transition", 5, False),
                ("transition", 5, True),
                ("sample", 5, True),
                ("finish",),
            ]
        )
        self.assertEqual(len(violations), 1)

    def test_fixed_samples_see_every_mutation_level_transition(self):
        clears = 0
        reexhaustions = 0
        cases = [
            (fixture, mode, settlement, real_stalling)
            for fixture in _SYNTHETIC_FIXTURES
            for mode in RecoveryInitiationMode
            for settlement in _SETTLEMENT_VARIANTS
            for real_stalling in (False, True)
        ]
        for (label, fixture), mode, settlement, real_stalling in cases:
            with self.subTest(
                fixture=label,
                mode=mode.value,
                settlement=tuple(settlement),
                real_stalling=real_stalling,
            ):
                summary, events = _traced_batch(
                    dict(
                        fixture,
                        **settlement,
                        recovery_initiation_mode=mode,
                        enable_v03b_stalling=real_stalling,
                    )
                )
                violations, reference = _audit_timeline(events)
                self.assertEqual(violations, [])

                observed: dict[int, list[tuple]] = {}
                for episode in summary.reexhaustion_handoffs.episodes:
                    observed.setdefault(
                        episode.match_index, []
                    ).append(
                        (
                            episode.clear_elapsed_seconds,
                            episode.reexhausted_elapsed_seconds,
                        )
                    )
                self.assertEqual(len(reference), summary.matches)
                for match_index, expected in enumerate(reference):
                    self.assertEqual(
                        observed.get(match_index, []),
                        expected,
                        match_index,
                    )
                    clears += len(expected)
                    reexhaustions += sum(
                        1 for _, again in expected if again is not None
                    )
        # The synthetic fixture must actually exercise both transitions.
        self.assertGreater(clears, 0)
        self.assertGreater(reexhaustions, 0)


class HistoricalRecoverySurfaceObserverInertnessTests(unittest.TestCase):
    """Observer OFF/ON replay on the frozen 100-seed recovery surfaces.

    Uses the exact `_candidate_kwargs` surfaces behind the recovery-policy
    candidate matrix (Surface E, base_seed=42, 100 matches, Rule 1 + Rule 2).
    Gameplay only: A9 observer output is dropped before any comparison.
    """

    CONFIGS = (
        ("stalling OFF + shadow", dict(stalling=False, shadow=True)),
        ("stalling OFF plain", dict(stalling=False, shadow=False)),
        ("stalling ON", dict(stalling=True, shadow=False)),
    )

    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for mode in RecoveryInitiationMode:
            for label, config in cls.CONFIGS:
                kwargs = _candidate_kwargs(mode, **config)
                cls.runs[(mode, label)] = (
                    _run_gameplay_only(kwargs, observer=False),
                    _run_gameplay_only(kwargs, observer=True),
                )

    def test_surfaces_are_the_frozen_historical_population(self):
        for mode in RecoveryInitiationMode:
            for label, config in self.CONFIGS:
                kwargs = _candidate_kwargs(mode, **config)
                self.assertEqual(kwargs["matches"], 100)
                self.assertEqual(kwargs["base_seed"], 42)
                self.assertIs(kwargs["recovery_initiation_mode"], mode)
                self.assertTrue(kwargs["enable_unfunded_responder_cost_waiver"])
                self.assertTrue(kwargs["enable_supplemental_hold_settlement"])

    def test_observer_off_on_gameplay_identical_per_match(self):
        for (mode, label), (off, on) in self.runs.items():
            with self.subTest(mode=mode.value, config=label):
                off_summary, off_matches, off_observer = off
                on_summary, on_matches, on_observer = on
                self.assertFalse(off_observer)
                self.assertTrue(on_observer)
                self.assertEqual(len(off_matches), 100)
                self.assertEqual(len(on_matches), 100)
                diverged = [
                    index
                    for index, (left, right) in enumerate(
                        zip(off_matches, on_matches)
                    )
                    if left != right
                ]
                self.assertEqual(diverged, [])

    def test_observer_off_on_summaries_identical(self):
        for (mode, label), (off, on) in self.runs.items():
            with self.subTest(mode=mode.value, config=label):
                off_summary = off[0]
                on_summary = on[0]
                # Canonical recovery-policy gameplay signature.
                self.assertEqual(
                    _gameplay_summary_signature(off_summary),
                    _gameplay_summary_signature(on_summary),
                )
                # Stronger: recovery-policy trajectories, shadow-stalling
                # events, and stamina-economy accounting also identical.
                self.assertEqual(
                    off_summary.recovery_policy,
                    on_summary.recovery_policy,
                )
                self.assertEqual(
                    off_summary.stamina_economy,
                    on_summary.stamina_economy,
                )
                self.assertEqual(off_summary, on_summary)

    def test_observer_off_matches_cached_historical_surfaces(self):
        cached = {
            (cell.mode, cell.stalling_enabled): cell.summary
            for cell in recovery_candidate_matrix()
        }
        for mode in RecoveryInitiationMode:
            with self.subTest(mode=mode.value):
                self.assertEqual(
                    self.runs[(mode, "stalling OFF + shadow")][0][0],
                    cached[(mode, False)],
                )
                self.assertEqual(
                    self.runs[(mode, "stalling ON")][0][0],
                    cached[(mode, True)],
                )

    def test_stalling_off_on_identity_preserved_with_observer_on(self):
        # Frozen recovery result: OFF/ON gameplay identical=True,
        # diverged matches CURRENT/RESET/LOW=0/0/0.
        for mode in RecoveryInitiationMode:
            with self.subTest(mode=mode.value):
                self.assertEqual(matched_first_divergence_times(mode), ())
                off = self.runs[(mode, "stalling OFF + shadow")][1][0]
                on = self.runs[(mode, "stalling ON")][1][0]
                diverged = [
                    value
                    for off_record, on_record in zip(
                        off.recovery_policy.matches,
                        on.recovery_policy.matches,
                    )
                    if (
                        value := _first_divergence_for_match(
                            off_record, on_record
                        )
                    )
                    is not None
                ]
                self.assertEqual(diverged, [])


class HistoricalRecoveryCandidateOutcomePinTests(unittest.TestCase):
    """Pin previously published recovery-candidate results (stalling OFF).

    These are the authoritative prior-slice anchors (CURRENT/RESET/LOW with
    both settlement rules); they come from the existing recovery-policy
    collector, not from the A9 observer.
    """

    EXPECTED = {
        RecoveryInitiationMode.CURRENT: dict(
            taps=5, half_guard=7, open_guard=8, reversal=5, timeouts=75,
            bottom_final_median=6.0, bottom_latch_clears=0,
            exhausted_setup_builder_attempts=1326,
            shadow_bottom_resets_with_route=7,
        ),
        RecoveryInitiationMode.RESET_WHILE_EXHAUSTED: dict(
            taps=5, half_guard=69, open_guard=2, reversal=1, timeouts=23,
            bottom_final_median=19.0, bottom_latch_clears=234,
            exhausted_setup_builder_attempts=0,
            shadow_bottom_resets_with_route=983,
        ),
        RecoveryInitiationMode.LOW_WHILE_EXHAUSTED: dict(
            taps=5, half_guard=31, open_guard=15, reversal=5, timeouts=44,
            bottom_final_median=26.0, bottom_latch_clears=67,
            exhausted_setup_builder_attempts=1114,
            shadow_bottom_resets_with_route=7,
        ),
    }

    def test_recovery_candidate_outcomes_unchanged(self):
        cells = {
            cell.mode: cell
            for cell in recovery_candidate_matrix()
            if not cell.stalling_enabled
        }
        for mode, expected in self.EXPECTED.items():
            for field, value in expected.items():
                with self.subTest(mode=mode.value, field=field):
                    self.assertEqual(getattr(cells[mode], field), value)


if __name__ == "__main__":
    unittest.main()
