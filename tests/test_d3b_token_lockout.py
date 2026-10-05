"""D3-B implementation tests (written before the frozen measurement).

Pins the semantics frozen in docs/BURST_RECOVERY_LOCKOUT_D3B_PREREGISTRATION.md
(dc4fc16947546dc3277d75dc1fbbd2e3d7a88310). Integration checks use synthetic
fixtures only (non-canonical seed range and starting stamina) and assert
invariants, never outcome metrics. No frozen E-PROD seed batch is run here.
"""

from dataclasses import fields
from functools import lru_cache
import random
import unittest
from unittest import mock

from bjj_game.diagnostics.stamina_adoption_candidate import (
    _surface_ab_kwargs,
    _surface_e_prod_kwargs,
)
from bjj_game.diagnostics.stamina_adoption_verification import _run_captured
from bjj_game.domain.action import Commitment
from bjj_game.domain.model import BottomBehavior, Side, TopBehavior
from bjj_game.domain.stamina import StaminaBand
from bjj_game.engine.match import MountMatch
from bjj_game.interfaces.batch import (
    AdaptiveBehaviorPolicy,
    BatchBehaviorMode,
    run_escape_first_batch,
)
from bjj_game.interfaces.handoff_policy import (
    D3BTokenLockoutController,
    HandoffDecisionKind,
    PostClearHandoffMode,
)
from bjj_game.interfaces.recovery_policy import RecoveryInitiationMode

D3B = PostClearHandoffMode.D3B_EXHAUSTED_TOKEN_LOCKOUT
SYNTHETIC_SEED = 910_000
GAMEPLAY_KEYS = ("k", "t", "bs", "bx", "ts", "ax", "band", "side", "free",
                 "action", "eff", "grade", "resp_charged", "exit", "behavior",
                 "bnet", "outcome", "b_before", "route", "offense")


def _kwargs(*, d3b: bool, measure: bool = True, top_stamina: int = 0,
            matches: int = 12, stalling: bool = False) -> dict:
    kwargs = _surface_e_prod_kwargs(stalling=stalling, shadow=not stalling,
                                    base_seed=SYNTHETIC_SEED)
    kwargs.update(matches=matches, top_stamina=top_stamina, bottom_stamina=20,
                  measure_post_clear_handoff=measure)
    if not measure:
        kwargs.update(measure_stamina_economy=False, measure_recovery_policy=False,
                      measure_reexhaustion_handoffs=False, shadow_stalling=False)
    if d3b:
        kwargs["post_clear_handoff_mode"] = D3B
    return kwargs


@lru_cache(maxsize=None)
def _run(d3b: bool = True, top_stamina: int = 0):
    return run_escape_first_batch(**_kwargs(d3b=d3b, top_stamina=top_stamina))


def _projection(event):
    return {k: event.get(k) for k in GAMEPLAY_KEYS}


def _annotate(record):
    """Yield (event, armed, episode_index) using only latch transitions."""
    armed = False
    prev = None
    episode = -1
    out = []
    for event in record.events:
        if "bx" in event and prev is not None:
            if prev and not event["bx"]:
                armed = True
            elif not prev and event["bx"] and armed:
                episode += 1
        if "bx" in event:
            prev = event["bx"]
        out.append((event, armed, episode))
    return out


# ---------------------------------------------------------------------------
# Scripted engine driver (Top PRESSURE + UNFUNDED, alternating initiative)
# ---------------------------------------------------------------------------


def _match():
    match = MountMatch(
        initial_clock=300,
        starting_axis=1.5,
        interval_seconds=5,
        enable_v02_setup=True,
        enable_v03_submissions=True,
        enable_v04_commitment_semantics=True,
        enable_unfunded_responder_cost_waiver=True,
    )
    match.top.stamina.set_current(0)
    return match


def _non_exit_pair(match):
    for action_id in match.legal_action_ids():
        for response_id in match.legal_response_ids(action_id):
            preview = match.preview_attempt_resolution(
                action_id=action_id, response_id=response_id,
                commitment=Commitment.LOW, response_commitment=Commitment.MEDIUM)
            if preview.exit_destination is None:
                return action_id, response_id
    raise AssertionError("no non-exit Bottom attempt available")


def _drive(entry: int, *, drain_entry: bool = False, max_steps: int = 30):
    """Armed episode from `entry`; returns the Bottom-window ledger and clear."""
    match = _match()
    controller = D3BTokenLockoutController(match)
    controller.armed = True
    match.bottom.stamina.set_current(entry)
    controller._exhausted = True
    assert match.bottom.stamina.band is StaminaBand.EXHAUSTED
    bottom_policy = AdaptiveBehaviorPolicy(side=Side.BOTTOM, baseline=BottomBehavior.ESCAPE,
                                           mode=BatchBehaviorMode.RECOVER)
    match.initiator = Side.BOTTOM if drain_entry else Side.TOP
    t0 = match.elapsed_simulated_time
    ledger = []
    first = drain_entry
    for _ in range(max_steps):
        if not first:
            match.set_behaviors(top=TopBehavior.PRESSURE,
                                bottom=controller.pre_advance_bottom_behavior(bottom_policy.choose(match)))
            match.advance()
            controller.observe_advance(match)
            match.set_behaviors(top=TopBehavior.PRESSURE, bottom=bottom_policy.choose(match))
            if match.bottom.stamina.band is not StaminaBand.EXHAUSTED:
                return {"ledger": ledger, "clear_t": match.elapsed_simulated_time - t0,
                        "clear_stamina": match.bottom.stamina.current,
                        "clear_before": match.initiator.value}
        first = False
        if match.initiator is Side.TOP:
            match.reset_window()
            continue
        decision = controller.decide(match, armed=True)
        stamina = match.bottom.stamina.current
        if decision.kind is HandoffDecisionKind.TOKEN:
            action_id, response_id = _non_exit_pair(match)
            match.attempt(action_id=action_id, response_id=response_id,
                          commitment=Commitment.LOW, response_commitment=Commitment.MEDIUM)
            ledger.append(("TOKEN", stamina, match.bottom.stamina.current))
        else:
            assert decision.kind is HandoffDecisionKind.LOCKOUT_HOLD, decision.kind
            match.recovery_hold()
            ledger.append(("HOLD", stamina))
    raise AssertionError("latch never cleared")


class ScriptedTraceTests(unittest.TestCase):
    """Section 3 of the preregistration, case by case."""

    def check(self, result, *, token, holds, clear_t, clear_stamina, before):
        self.assertEqual(result["ledger"][0], ("TOKEN",) + token)
        self.assertEqual([x[1] for x in result["ledger"][1:]], holds)
        self.assertTrue(all(x[0] == "HOLD" for x in result["ledger"][1:]))
        self.assertEqual(result["clear_t"], clear_t)
        self.assertEqual(result["clear_stamina"], clear_stamina)
        self.assertEqual(result["clear_before"], before)

    def test_entry_19(self):
        self.check(_drive(19), token=(23, 20), holds=[24, 28, 32], clear_t=50,
                   clear_stamina=36, before="bottom")

    def test_entry_20(self):
        self.check(_drive(20), token=(24, 21), holds=[25, 29, 33], clear_t=45,
                   clear_stamina=35, before="top")

    def test_entry_21(self):
        self.check(_drive(21), token=(25, 22), holds=[26, 30, 34], clear_t=45,
                   clear_stamina=36, before="top")

    def test_entry_22(self):
        self.check(_drive(22), token=(26, 23), holds=[27, 31], clear_t=40,
                   clear_stamina=35, before="bottom")

    def test_drain_entry_25(self):
        self.check(_drive(25, drain_entry=True), token=(25, 22), holds=[26, 30, 34],
                   clear_t=35, clear_stamina=36, before="top")


class ControllerTests(unittest.TestCase):
    def _match(self, stamina):
        match = _match()
        match.bottom.stamina.set_current(stamina)
        match.initiator = Side.BOTTOM
        return match

    def test_unarmed_is_adopted(self):
        match = self._match(20)
        controller = D3BTokenLockoutController(match)
        self.assertIs(controller.decide(match, armed=True).kind, HandoffDecisionKind.UNARMED)
        self.assertFalse(controller.token_consumed)

    def test_arming_on_clear_and_token_reset(self):
        match = self._match(20)
        controller = D3BTokenLockoutController(match)
        match.bottom.stamina.set_current(35)
        controller.observe_advance(match)
        self.assertTrue(controller.armed)
        self.assertIs(controller.decide(match, armed=False).kind, HandoffDecisionKind.ARMED_NORMAL)
        match.bottom.stamina.set_current(19)
        controller.observe_advance(match)
        first = controller.decide(match, armed=False)
        self.assertIs(first.kind, HandoffDecisionKind.TOKEN)
        self.assertIsNone(first.requested_commitment)  # adopted LOW path
        self.assertFalse(first.hold)
        # Token is consumed whatever happens; no retry (attempt or RESET alike).
        for _ in range(3):
            self.assertIs(controller.decide(match, armed=False).kind, HandoffDecisionKind.LOCKOUT_HOLD)
        match.bottom.stamina.set_current(35)
        controller.observe_advance(match)
        self.assertFalse(controller.token_consumed)
        self.assertIs(controller.decide(match, armed=False).kind, HandoffDecisionKind.ARMED_NORMAL)
        match.bottom.stamina.set_current(20)
        controller.observe_advance(match)
        self.assertIs(controller.decide(match, armed=False).kind, HandoffDecisionKind.TOKEN)

    def test_behavior_never_overridden(self):
        controller = D3BTokenLockoutController(self._match(20))
        for behavior in BottomBehavior:
            self.assertIs(controller.pre_advance_bottom_behavior(behavior), behavior)

    def test_token_reset_then_lockout_and_free_window(self):
        match = self._match(19)
        controller = D3BTokenLockoutController(match)
        controller.armed = True
        self.assertIs(controller.decide(match, armed=True).kind, HandoffDecisionKind.TOKEN)
        match.reset_window()  # genuine RESET consumes the token's window
        self.assertIs(match.initiator, Side.TOP)
        match.reset_window()
        # Free initiative for Bottom while locked: consumed, hold, no time.
        match.free_initiative_pending = True
        match.free_initiative_beneficiary = Side.BOTTOM
        self.assertIs(match.consume_free_initiative_window(), Side.BOTTOM)
        clock, stamina = match.clock_seconds, match.bottom.stamina.current
        decision = controller.decide(match, armed=True)
        self.assertIs(decision.kind, HandoffDecisionKind.LOCKOUT_HOLD)
        match.recovery_hold()
        self.assertIs(match.initiator, Side.TOP)
        self.assertEqual((match.clock_seconds, match.bottom.stamina.current), (clock, stamina))
        self.assertTrue(controller.recovery_hold_mode)

    def test_token_on_free_window_is_consumed(self):
        match = self._match(19)
        controller = D3BTokenLockoutController(match)
        controller.armed = True
        match.free_initiative_pending = True
        match.free_initiative_beneficiary = Side.BOTTOM
        match.consume_free_initiative_window()
        self.assertIs(controller.decide(match, armed=True).kind, HandoffDecisionKind.TOKEN)
        self.assertIs(controller.decide(match, armed=True).kind, HandoffDecisionKind.LOCKOUT_HOLD)


class ConfigurationTests(unittest.TestCase):
    def test_rejected_outside_e_prod(self):
        for label in ("A public MATCH", "B trusts reads"):
            with self.assertRaises(ValueError):
                run_escape_first_batch(**{**_surface_ab_kwargs(label), "matches": 1,
                                          "post_clear_handoff_mode": D3B})
        base = _kwargs(d3b=True, matches=1)
        for change in ({"recovery_initiation_mode": RecoveryInitiationMode.CURRENT},
                       {"enable_supplemental_hold_settlement": True},
                       {"enable_unfunded_responder_cost_waiver": False},
                       {"commitment": Commitment.HIGH}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run_escape_first_batch(**{**base, **change})


class SyntheticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = _run(True).post_clear_handoff.matches
        cls.adopted = _run(False).post_clear_handoff.matches

    def test_fixture_exercises_token_and_lockout(self):
        kinds = {e.get("kind") for r in self.records for e in r.events if e["k"] == "win"}
        self.assertTrue({"TOKEN", "LOCKOUT_HOLD", "ARMED_NORMAL", "UNARMED"} <= kinds)

    def test_token_and_lockout_exactness(self):
        """G2: first armed Exhausted window = TOKEN; later = LOCKOUT_HOLD."""
        for record in self.records:
            seen = set()
            for event, armed, episode in _annotate(record):
                if event["k"] != "win" or event["side"] != "bottom":
                    continue
                self.assertEqual(event["armed"], armed)
                if armed and event["bx"]:
                    expected = "LOCKOUT_HOLD" if episode in seen else "TOKEN"
                    self.assertEqual(event["kind"], expected)
                    seen.add(episode)
                else:
                    self.assertIn(event["kind"], {"UNARMED", "ARMED_NORMAL"})

    def test_no_initiation_after_token_and_holds_pass_initiative(self):
        """G1: no Bottom attempt or RESET after the token while Exhausted."""
        for record in self.records:
            events = record.events
            for i, event in enumerate(events):
                if event["k"] != "win" or event["side"] != "bottom":
                    continue
                nxt = events[i + 1]
                if event["kind"] == "LOCKOUT_HOLD":
                    self.assertEqual(nxt["k"], "hold")
                    self.assertEqual((nxt["next"], nxt["bs"], nxt["t"]), ("top", event["bs"], event["t"]))
                    self.assertIn("cf_action", event)
                elif event["kind"] == "TOKEN":
                    self.assertIn(nxt["k"], {"att", "reset"})
                    if nxt["k"] == "att":
                        self.assertEqual((nxt["side"], nxt["req"]), ("bottom", "LOW"))
                else:
                    self.assertNotEqual(nxt["k"], "hold")

    def test_clear_restores_ordinary_medium(self):
        checked = 0
        for record in self.records:
            annotated = _annotate(record)
            for i, (event, armed, _) in enumerate(annotated):
                if event["k"] == "win" and event["side"] == "bottom" and armed and not event["bx"]:
                    previous = [e for e, _, _ in annotated[:i] if e["k"] == "win" and e["side"] == "bottom"]
                    if previous and previous[-1]["bx"] and previous[-1]["armed"]:
                        nxt = annotated[i + 1][0]
                        self.assertEqual(event["kind"], "ARMED_NORMAL")
                        if nxt["k"] == "att":
                            self.assertEqual(nxt["req"], "MEDIUM")
                        checked += 1
        self.assertGreater(checked, 0)

    def test_traced_episode_timings(self):
        """Unfunded Top: measured entry->clear equals the section-3 trace."""
        expected = {(19, "bottom"): 50, (20, "bottom"): 45, (21, "bottom"): 45,
                    (22, "bottom"): 40, (25, "drain"): 35}
        seen = set()
        for record in self.records:
            events = record.events
            armed, prev, entry = False, None, None
            for i, event in enumerate(events):
                if "bx" not in event:
                    continue
                if prev is not None and prev and not event["bx"]:
                    if entry is not None:
                        key = entry[1]
                        if key in expected:
                            self.assertEqual(event["t"] - entry[0], expected[key], key)
                            seen.add(key)
                        entry = None
                    armed = True
                elif prev is not None and not prev and event["bx"] and armed:
                    kind = "drain" if event["k"] == "adv" else event.get("side")
                    entry = (event["t"], (event["bs"], kind))
                prev = event["bx"]
        self.assertTrue({(19, "bottom"), (20, "bottom"), (25, "drain")} <= seen, seen)

    def test_behavior_never_forced(self):
        for record in self.records:
            for event in record.events:
                if event["k"] == "adv":
                    self.assertEqual(event["behavior"], event["policy_behavior"])
                    self.assertFalse(event["forced"])

    def test_prefix_identity_with_adopted_through_first_token(self):
        for d3b, adopted in zip(self.records, self.adopted):
            events = [e for e in d3b.events if e["k"] != "mode_end"]
            adopted_events = [e for e in adopted.events if e["k"] != "mode_end"]
            cut = len(events)
            for i, event in enumerate(events):
                if event["k"] == "win" and event.get("kind") == "TOKEN":
                    cut = i + 2  # the token window and its attempt/RESET
                    break
            self.assertEqual([_projection(e) for e in events[:cut]],
                             [_projection(e) for e in adopted_events[:cut]])
            if cut == len(events):
                self.assertEqual(d3b.outcome, adopted.outcome)

    def test_pre_clear_exhausted_low_unchanged(self):
        lows = [e for r in self.records for e, armed, _ in _annotate(r)
                if e["k"] == "att" and e["side"] == "bottom" and e["bx_before"] and not armed]
        self.assertTrue(lows)
        self.assertTrue(all(e["req"] == "LOW" for e in lows))


class FundedTopResponseTests(unittest.TestCase):
    def test_defensive_responses_still_charged_during_lockout(self):
        records = _run(True, top_stamina=20).post_clear_handoff.matches
        adopted = _run(False, top_stamina=20).post_clear_handoff.matches
        top_attempts_in_lockout = 0
        for record in records:
            locked = False
            for event in record.events:
                if event["k"] == "win" and event["side"] == "bottom":
                    locked = event.get("kind") == "LOCKOUT_HOLD"
                if "bx" in event and not event["bx"]:
                    locked = False
                if locked and event["k"] == "att" and event["side"] == "top":
                    top_attempts_in_lockout += 1
        self.assertGreater(top_attempts_in_lockout, 0)
        # Response charging code path is shared with the adopted run (no override):
        charged = sum(e["resp_charged"] for r in records for e in r.events if e["k"] == "att")
        adopted_charged = sum(e["resp_charged"] for r in adopted for e in r.events if e["k"] == "att")
        self.assertGreater(charged, 0)
        self.assertGreater(adopted_charged, 0)


class InertnessTests(unittest.TestCase):
    def _gameplay(self, summary):
        skip = {"stamina_economy", "recovery_policy", "reexhaustion_handoffs", "post_clear_handoff"}
        return tuple((f.name, getattr(summary, f.name)) for f in fields(summary) if f.name not in skip)

    def test_observers_on_off_and_replay(self):
        on, on_m = _run_captured(_kwargs(d3b=True, measure=True, matches=6))
        off, off_m = _run_captured(_kwargs(d3b=True, measure=False, matches=6))
        again, again_m = _run_captured(_kwargs(d3b=True, measure=True, matches=6))
        self.assertEqual(self._gameplay(on), self._gameplay(off))
        self.assertEqual(on_m, off_m)
        self.assertEqual((on, on_m), (again, again_m))
        self.assertTrue(any(m[0].recovery_hold_history for m in on_m))

    def test_lockout_holds_consume_no_rng_and_no_reset(self):
        counter = [0]
        log = []
        originals = {n: getattr(random.Random, n) for n in ("random", "getrandbits")}

        def counted(name):
            def wrapper(self, *a, **k):
                counter[0] += 1
                return originals[name](self, *a, **k)
            return wrapper

        def op(name):
            original = getattr(MountMatch, name)

            def wrapper(match, *a, **k):
                start = counter[0]
                before = (len(match.history.reset_window_history),
                          len(match.history.stalling_progress_opportunity_history),
                          repr(match.stalling_tracker), repr(match.setup_state),
                          repr(match.submission_state), match.bottom.stamina.current)
                result = original(match, *a, **k)
                after = (len(match.history.reset_window_history),
                         len(match.history.stalling_progress_opportunity_history),
                         repr(match.stalling_tracker), repr(match.setup_state),
                         repr(match.submission_state), match.bottom.stamina.current)
                log.append((name, start, counter[0], before == after))
                return result
            return wrapper

        patches = [mock.patch.object(random.Random, n, counted(n)) for n in originals]
        patches += [mock.patch.object(MountMatch, n, op(n))
                    for n in ("advance", "attempt", "reset_window", "recovery_hold")]
        for p in patches:
            p.start()
        try:
            run_escape_first_batch(**_kwargs(d3b=True, matches=8))
        finally:
            for p in patches:
                p.stop()
        holds = 0
        for i, (name, start, end, unchanged) in enumerate(log):
            if name != "recovery_hold":
                continue
            holds += 1
            self.assertTrue(unchanged)
            self.assertEqual(start, end)
            self.assertEqual(log[i - 1][2], start)
            if i + 1 < len(log):
                self.assertEqual(log[i + 1][1], end)
        self.assertGreater(holds, 0)

    def test_no_recovery_hold_outside_candidates(self):
        calls = []
        original = MountMatch.recovery_hold

        def counting(match):
            calls.append(1)
            return original(match)

        with mock.patch.object(MountMatch, "recovery_hold", counting):
            run_escape_first_batch(**_kwargs(d3b=False, matches=4))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
