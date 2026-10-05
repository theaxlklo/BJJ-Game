"""D2 v1e implementation tests (written before the frozen measurement).

Pins the semantics frozen in docs/HANDOFF_OSCILLATION_D2_PREREGISTRATION_V1E.md
(c4a9c3369b53911eda4d47dd9d814d385470ba8a). Integration checks use synthetic
fixtures only: a non-canonical seed range, a non-canonical Top/Bottom starting
stamina, and invariants rather than outcome metrics. No frozen E-PROD seed
batch is run here.
"""

from dataclasses import fields
from functools import lru_cache
import random
import unittest
from unittest import mock

from bjj_game.diagnostics.stamina_adoption_candidate import _surface_e_prod_kwargs
from bjj_game.diagnostics.stamina_adoption_verification import _run_captured
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, RunHistory, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import BatchBehaviorMode, run_escape_first_batch
from bjj_game.interfaces.handoff_policy import (
    V1E_BEHAVIOR_RESERVE,
    HandoffDecisionKind,
    ModeTransition,
    PostClearHandoffController,
    PostClearHandoffMode,
    reserve_safe,
)
from bjj_game.interfaces.production_policy import GATE_G_STAMINA_RECOVERY_POLICY
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode
from bjj_game.positions.mount.rules import MAX_AXIS

V1E = PostClearHandoffMode.V1E_PERSISTENT_CONSERVE_HOLD
SYNTHETIC_SEED = 900_000


def _match(*, stamina: int, stalling: bool = False) -> MountMatch:
    match = MountMatch(
        initial_clock=300,
        starting_axis=1.5,
        interval_seconds=5,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v03b_stalling=stalling,
        enable_v04_commitment_semantics=True,
        enable_v04b_recognition=True,
        enable_unfunded_responder_cost_waiver=True,
    )
    match.bottom.stamina.set_current(stamina)
    match.initiator = Side.BOTTOM
    return match


def _synthetic_kwargs(*, v1e: bool, measure: bool = True, stalling: bool = False,
                      top_stamina: int = 0, matches: int = 12) -> dict:
    kwargs = _surface_e_prod_kwargs(
        stalling=stalling,
        shadow=not stalling,
        base_seed=SYNTHETIC_SEED,
    )
    kwargs.update(
        matches=matches,
        top_stamina=top_stamina,
        bottom_stamina=20,
        measure_post_clear_handoff=measure,
    )
    if not measure:
        kwargs.update(
            measure_stamina_economy=False,
            measure_recovery_policy=False,
            measure_reexhaustion_handoffs=False,
            shadow_stalling=False,
        )
    if v1e:
        kwargs["post_clear_handoff_mode"] = V1E
    return kwargs


@lru_cache(maxsize=None)
def _synthetic(v1e: bool = True, top_stamina: int = 0):
    return run_escape_first_batch(**_synthetic_kwargs(v1e=v1e, top_stamina=top_stamina))


def _bottom_windows(record):
    return [e for e in record.events if e["k"] == "win" and e["side"] == "bottom"]


def _cycles(record):
    """Split a match event log into recovery-hold cycles (ENTER .. end)."""
    cycles = []
    current = None
    for event in record.events:
        if event["k"] == "win" and event["side"] == "bottom":
            if event["tr"] == ModeTransition.ENTER.value:
                current = {"windows": [event], "end": None}
                cycles.append(current)
                continue
            if current is not None and current["end"] is None:
                current["windows"].append(event)
                if event["tr"] in {
                    ModeTransition.RELEASE.value,
                    ModeTransition.CLEARED_BY_EXHAUSTION.value,
                }:
                    current["end"] = event
        elif event["k"] == "mode_end" and current is not None and current["end"] is None:
            current["end"] = event
    return cycles


class ReserveRuleTests(unittest.TestCase):
    def test_frozen_constants(self):
        self.assertEqual(V1E_BEHAVIOR_RESERVE, 2)
        match = _match(stamina=50)
        self.assertEqual(match.stamina_cost_policy.cost(Commitment.LOW), 3)
        self.assertEqual(match.stamina_cost_policy.cost(Commitment.MEDIUM), 7)
        self.assertEqual(match.bottom.stamina.exhaustion_enter_threshold, 25)
        self.assertEqual(match.bottom.stamina.exhaustion_recover_threshold, 35)

    def test_boundaries(self):
        safe = lambda s, c: reserve_safe(stamina=s, cost=c, enter_threshold=25)
        self.assertTrue(safe(35, 7))
        self.assertFalse(safe(34, 7))
        self.assertTrue(safe(31, 3))
        self.assertFalse(safe(30, 3))


class ControllerTests(unittest.TestCase):
    def decide(self, controller, stamina, *, armed=True):
        return controller.decide(_match(stamina=stamina), armed=armed)

    def test_unarmed_and_exhausted_are_adopted_paths(self):
        controller = PostClearHandoffController()
        self.assertIs(self.decide(controller, 26, armed=False).kind, HandoffDecisionKind.UNARMED)
        self.assertIs(self.decide(controller, 20).kind, HandoffDecisionKind.EXHAUSTED)
        self.assertFalse(controller.recovery_hold_mode)

    def test_ordinary_decision_outside_mode(self):
        controller = PostClearHandoffController()
        decision = self.decide(controller, 35)
        self.assertIs(decision.kind, HandoffDecisionKind.ORDINARY_MEDIUM)
        self.assertIs(decision.requested_commitment, Commitment.MEDIUM)
        for stamina in (31, 32, 33, 34):
            decision = self.decide(controller, stamina)
            self.assertIs(decision.kind, HandoffDecisionKind.ORDINARY_LOW)
            self.assertIs(decision.requested_commitment, Commitment.LOW)
        self.assertFalse(controller.recovery_hold_mode)

    def test_entry_hold_and_release_only_on_medium_safe(self):
        controller = PostClearHandoffController()
        entry = self.decide(controller, 30)
        self.assertIs(entry.kind, HandoffDecisionKind.ENTER_HOLD)
        self.assertIs(entry.transition, ModeTransition.ENTER)
        self.assertTrue(entry.hold)
        self.assertTrue(controller.recovery_hold_mode)
        for stamina in (26, 30, 31, 33, 34):  # LOW-safe 31-34 never releases
            decision = self.decide(controller, stamina)
            self.assertIs(decision.kind, HandoffDecisionKind.HOLD)
            self.assertIsNone(decision.requested_commitment)
            self.assertTrue(controller.recovery_hold_mode)
        release = self.decide(controller, 35)
        self.assertIs(release.kind, HandoffDecisionKind.RELEASE_MEDIUM)
        self.assertIs(release.transition, ModeTransition.RELEASE)
        self.assertIs(release.requested_commitment, Commitment.MEDIUM)
        self.assertFalse(controller.recovery_hold_mode)

    def test_reexhaustion_clears_mode(self):
        controller = PostClearHandoffController()
        self.decide(controller, 26)
        decision = self.decide(controller, 24)
        self.assertIs(decision.kind, HandoffDecisionKind.EXHAUSTED)
        self.assertIs(decision.transition, ModeTransition.CLEARED_BY_EXHAUSTION)
        self.assertFalse(controller.recovery_hold_mode)

    def test_persistent_pre_advance_conserve(self):
        controller = PostClearHandoffController()
        self.assertIs(controller.pre_advance_bottom_behavior(BottomBehavior.ESCAPE), BottomBehavior.ESCAPE)
        self.decide(controller, 26)
        for _ in range(3):
            self.assertIs(
                controller.pre_advance_bottom_behavior(BottomBehavior.ESCAPE),
                BottomBehavior.CONSERVE,
            )

    def test_decide_rejects_top_window(self):
        match = _match(stamina=26)
        match.initiator = Side.TOP
        with self.assertRaises(RuntimeError):
            PostClearHandoffController().decide(match, armed=True)


class RecoveryHoldEngineTests(unittest.TestCase):
    def test_hold_semantics(self):
        match = _match(stamina=26, stalling=True)
        match.advance()
        before = (
            match.bottom.stamina.current, match.top.stamina.current,
            match.clock_seconds, match.axis, match.band,
            repr(match.setup_state), repr(match.submission_state),
            repr(match.stalling_tracker), match.free_initiative_pending,
            match.bottom_behavior_stamina_meter,
        )
        history_before = {
            f.name: list(getattr(match.history, f.name))
            for f in fields(RunHistory)
            if isinstance(getattr(match.history, f.name), list)
            and f.name != "recovery_hold_history"
        }
        result = match.recovery_hold()
        after = (
            match.bottom.stamina.current, match.top.stamina.current,
            match.clock_seconds, match.axis, match.band,
            repr(match.setup_state), repr(match.submission_state),
            repr(match.stalling_tracker), match.free_initiative_pending,
            match.bottom_behavior_stamina_meter,
        )
        self.assertEqual(before, after)
        for name, value in history_before.items():
            self.assertEqual(getattr(match.history, name), value, name)
        self.assertIs(match.initiator, Side.TOP)
        self.assertIs(result.next_initiator, Side.TOP)
        self.assertEqual(
            match.history.recovery_hold_history,
            [f"bottom@{result.elapsed_seconds}s:stamina={match.bottom.stamina.current}"],
        )

    def test_hold_is_bottom_only_and_not_after_timeout(self):
        match = _match(stamina=26)
        match.initiator = Side.TOP
        with self.assertRaises(RuntimeError):
            match.recovery_hold()
        match = _match(stamina=26)
        match.clock_seconds = 0
        with self.assertRaises(RuntimeError):
            match.recovery_hold()

    def test_history_field_defaults_empty(self):
        self.assertEqual(RunHistory().recovery_hold_history, [])


class ConfigurationTests(unittest.TestCase):
    def test_v1e_rejected_outside_its_surface(self):
        base = _synthetic_kwargs(v1e=True, matches=1)
        invalid = [
            {"bottom_behavior_mode": BatchBehaviorMode.FIXED,
             "recovery_initiation_mode": RecoveryInitiationMode.CURRENT},
            {"recovery_initiation_mode": RecoveryInitiationMode.CURRENT},
            {"recovery_initiation_mode": RecoveryInitiationMode.RESET_WHILE_EXHAUSTED},
            {"enable_unfunded_responder_cost_waiver": False},
            {"enable_supplemental_hold_settlement": True},
            {"enable_stamina_settlement_rules": True},
            {"commitment": Commitment.HIGH},
            {"enable_v02_setup": False, "enable_v03_submissions": False,
             "enable_v03b_stalling": False},
        ]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                run_escape_first_batch(**{**base, **change})

    def test_canonical_policy_and_defaults_unchanged(self):
        settings = GATE_G_STAMINA_RECOVERY_POLICY.batch_settings(
            bottom_behavior_mode=BatchBehaviorMode.RECOVER
        )
        self.assertNotIn("post_clear_handoff_mode", settings)
        import inspect
        defaults = inspect.signature(run_escape_first_batch).parameters
        self.assertIs(defaults["post_clear_handoff_mode"].default, PostClearHandoffMode.NONE)
        self.assertIs(defaults["measure_post_clear_handoff"].default, False)


class SyntheticIntegrationTests(unittest.TestCase):
    """Invariants on a synthetic fixture (Top starts unfunded at 0)."""

    @classmethod
    def setUpClass(cls):
        cls.summary = _synthetic(True)
        cls.records = cls.summary.post_clear_handoff.matches

    def test_fixture_exercises_the_mode(self):
        windows = [w for r in self.records for w in _bottom_windows(r)]
        kinds = {w["kind"] for w in windows}
        for kind in ("ENTER_HOLD", "HOLD", "RELEASE_MEDIUM", "ORDINARY_MEDIUM"):
            self.assertIn(kind, kinds)

    def test_entry_hold_release_boundaries(self):
        for record in self.records:
            for w in _bottom_windows(record):
                if w["kind"] == "ENTER_HOLD":
                    self.assertLessEqual(w["bs"], 30)
                    self.assertFalse(w["bx"])
                if w["kind"] == "HOLD":
                    self.assertLessEqual(w["bs"], 34)
                if w["kind"] == "RELEASE_MEDIUM":
                    self.assertGreaterEqual(w["bs"], 35)
                    self.assertEqual(w["req"], "MEDIUM")
                if w["kind"] == "ORDINARY_LOW":
                    self.assertTrue(31 <= w["bs"] <= 34)
                    self.assertFalse(w["mode_before"])
                if w["mode_before"]:
                    self.assertIn(w["kind"], {"HOLD", "RELEASE_MEDIUM", "EXHAUSTED"})
                if not w["armed"]:
                    self.assertIn(w["kind"], {"UNARMED", "EXHAUSTED"})

    def test_traced_recovery_path_26_30_34_38(self):
        """Unfunded Top: every cycle entered at 26 recovers +4 per 10 s."""
        checked = 0
        for record in self.records:
            for cycle in _cycles(record):
                staminas = [w["bs"] for w in cycle["windows"]]
                if staminas[0] == 26 and cycle["end"] is not None and cycle["end"].get("tr") == "RELEASE":
                    self.assertEqual(staminas, [26, 30, 34, 38])
                    self.assertEqual(cycle["windows"][-1]["t"] - cycle["windows"][0]["t"], 30)
                    checked += 1
                # Any cycle: +4 between consecutive Bottom windows.
                for a, b in zip(staminas, staminas[1:]):
                    self.assertEqual(b - a, 4)
        self.assertGreater(checked, 0)

    def test_release_then_medium_attempt_and_cyclic_reentry(self):
        seen = 0
        for record in self.records:
            events = record.events
            for i, e in enumerate(events):
                if e["k"] == "win" and e.get("kind") == "RELEASE_MEDIUM":
                    following = events[i + 1]
                    self.assertIn(following["k"], {"att", "reset"})
                    if following["k"] == "att":
                        self.assertEqual(following["side"], "bottom")
                        self.assertEqual(following["req"], "MEDIUM")
                        self.assertEqual(following["b_before"] - following["bs"], 7)
                    seen += 1
        self.assertGreater(seen, 0)

    def test_persistent_conserve_and_rechoice(self):
        forced = 0
        for record in self.records:
            for e in record.events:
                if e["k"] == "adv" and e["mode"]:
                    self.assertEqual(e["behavior"], "CONSERVE")
                    if not e["b0"]["bx"]:
                        self.assertEqual(e["bnet"], 2)
                        forced += 1
                if e["k"] == "adv" and not e["mode"]:
                    self.assertEqual(e["behavior"], e["policy_behavior"])
                if e["k"] == "win" and not e["free"]:
                    # Resolution sees the unchanged post-advance re-choice.
                    self.assertEqual(e["seen_behavior"], e["policy_behavior"])
                    if not e["bx"]:
                        self.assertEqual(e["seen_behavior"], "ESCAPE")
        self.assertGreater(forced, 0)

    def test_forced_conserve_drift_is_protect_drift(self):
        checked = 0
        for record in self.records:
            for e in record.events:
                if e["k"] == "adv" and e["mode"] and e["t"] - e["b0"]["t"] == 5:
                    start = e["b0"]["ax"]
                    self.assertAlmostEqual(e["ax"], min(MAX_AXIS, start + 0.75), places=9)
                    self.assertAlmostEqual(e["escape_axis"], min(MAX_AXIS, start + 0.50), places=9)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_hold_passes_initiative_and_is_not_reset(self):
        for record in self.records:
            events = record.events
            holds = 0
            for i, e in enumerate(events):
                if e["k"] == "win" and e["side"] == "bottom" and e["kind"] in {"ENTER_HOLD", "HOLD"}:
                    self.assertEqual(events[i + 1]["k"], "hold")
                    self.assertEqual(events[i + 1]["next"], "top")
                    self.assertEqual(events[i + 1]["bs"], e["bs"])
                    self.assertEqual(events[i + 1]["t"], e["t"])
                    later = [x for x in events[i + 2:] if x["k"] == "win"]
                    if later:
                        self.assertEqual(later[0]["side"], "top")
                    holds += 1
            self.assertEqual(
                holds,
                sum(1 for e in events if e["k"] == "hold"),
            )
        resets = sum(1 for r in self.records for e in r.events
                     if e["k"] == "reset" and e["side"] == "bottom")
        self.assertEqual(resets, self.summary.bottom_reset_count)

    def test_mode_ends_with_release_exhaustion_or_pending(self):
        for record in self.records:
            for cycle in _cycles(record):
                self.assertIsNotNone(cycle["end"])
                self.assertIn(cycle["end"]["tr"], {"RELEASE", "CLEARED_BY_EXHAUSTION", "PENDING_AT_END"})
            trs = [e["tr"] for e in record.events if e.get("tr")]
            if trs and trs[-1] == "ENTER":
                self.fail("mode left active without PENDING_AT_END")

    def test_preclear_identical_to_adopted(self):
        adopted = _synthetic(False).post_clear_handoff.matches
        for a, v in zip(adopted, self.records):
            def prefix(record):
                out = []
                for e in record.events:
                    if e["k"] == "win" and e["side"] == "bottom" and e["armed"]:
                        break
                    out.append({k: x for k, x in e.items() if k not in {"kind", "req", "tr", "mode_before", "mode_after", "mode", "forced"}})
                return out
            self.assertEqual(prefix(a), prefix(v))


class InertnessTests(unittest.TestCase):
    def _gameplay(self, summary):
        measurement_fields = {
            "stamina_economy", "recovery_policy", "reexhaustion_handoffs",
            "post_clear_handoff",
        }
        return tuple(
            (f.name, getattr(summary, f.name))
            for f in fields(summary)
            if f.name not in measurement_fields
        )

    def test_v1e_observers_on_off_identical_and_replay_deterministic(self):
        on_summary, on_matches = _run_captured(_synthetic_kwargs(v1e=True, measure=True, matches=6))
        off_summary, off_matches = _run_captured(_synthetic_kwargs(v1e=True, measure=False, matches=6))
        again_summary, again_matches = _run_captured(_synthetic_kwargs(v1e=True, measure=True, matches=6))
        self.assertEqual(self._gameplay(on_summary), self._gameplay(off_summary))
        self.assertEqual(on_matches, off_matches)
        self.assertEqual(on_summary, again_summary)
        self.assertEqual(on_matches, again_matches)
        self.assertTrue(any(m[0].recovery_hold_history for m in on_matches))

    def test_no_recovery_hold_outside_v1e(self):
        calls = []
        original = MountMatch.recovery_hold

        def counting(match):
            calls.append(1)
            return original(match)

        with mock.patch.object(MountMatch, "recovery_hold", counting):
            plain, plain_matches = _run_captured(_synthetic_kwargs(v1e=False, measure=False, matches=4))
            observed, observed_matches = _run_captured(_synthetic_kwargs(v1e=False, measure=True, matches=4))
        self.assertEqual(calls, [])
        self.assertEqual(self._gameplay(plain), self._gameplay(observed))
        self.assertEqual(plain_matches, observed_matches)
        self.assertTrue(all(not m[0].recovery_hold_history for m in plain_matches))

    def test_holds_consume_no_rng(self):
        counter = [0]
        log = []
        originals = {
            name: getattr(random.Random, name) for name in ("random", "getrandbits")
        }

        def counted(name):
            def wrapper(self, *args, **kwargs):
                counter[0] += 1
                return originals[name](self, *args, **kwargs)
            return wrapper

        def op(name):
            original = getattr(MountMatch, name)

            def wrapper(match, *args, **kwargs):
                start = counter[0]
                result = original(match, *args, **kwargs)
                log.append((name, start, counter[0]))
                return result
            return wrapper

        patches = [mock.patch.object(random.Random, n, counted(n)) for n in originals]
        patches += [mock.patch.object(MountMatch, n, op(n))
                    for n in ("advance", "attempt", "reset_window", "recovery_hold")]
        for p in patches:
            p.start()
        try:
            run_escape_first_batch(**_synthetic_kwargs(v1e=True, measure=True, matches=4))
        finally:
            for p in patches:
                p.stop()
        holds = 0
        for index, (name, start, end) in enumerate(log):
            if name != "recovery_hold":
                continue
            holds += 1
            self.assertEqual(start, end)
            self.assertEqual(log[index - 1][2], start)  # nothing since previous op
            if index + 1 < len(log):
                self.assertEqual(log[index + 1][1], end)  # nothing before next op
        self.assertGreater(holds, 0)


if __name__ == "__main__":
    unittest.main()
