"""Tests for the independent Side Control v0 oracle (B2b-2).

Order matters and is deliberate (negative-first): refusals and atomicity come first, positive behavior second, replay and
independence last. Expected values are hand-computed from ``GODOT_V1/docs/SIDE_CONTROL_V0_RULES.md`` and written out
literally with their arithmetic in comments; the oracle is never used to produce its own expectation except in clearly
labelled *property* tests and in the measured structural search, which is test-only evidence and NOT engine parity.

There is no Godot Side Control engine yet, so nothing here claims Python-to-Godot parity for this position (that is B2c).
"""
import ast
import copy
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from oracles import side_control_v0 as O  # noqa: E402
from oracles import side_control_v0_scenarios as S  # noqa: E402

A, R = S.A, S.R
TOP, BOT = S.TOP_ID, S.BOTTOM_ID
SHEET_PATH = os.path.join(ROOT, "GODOT_V1", "docs", "SIDE_CONTROL_V0_RULES.md")

# Measured evidence for the fixture, pinned: a changed rule or scenario family must change these deliberately.
PINNED_FIXTURE = {
    "scenarios": 19259, "operations": 21350, "comparisons": 1456324,
    "families": {"band_update": 405, "break_grid": 3996, "entry": 26, "exchange_grid": 14580, "refusal": 188, "trajectory": 64},
    "sha256": "cc15ff424ead11fa24c902d7e2c58fa20e8b2989c622d6f5a5150dc24ddb9554",
}
MEASURED = {"structural_search": {}, "rows_checked_against_model": 0}


def tearDownModule():
    print("\n[side_control_oracle] measured (test-only, not engine parity): %s" % json.dumps(MEASURED, sort_keys=True))


@functools.lru_cache(maxsize=1)
def cached_rows():
    """The whole fixture, generated once per test run (about three seconds)."""
    return S.all_rows()


def snap_bytes(match):
    return O.canonical_bytes(match.snapshot())


def fresh(**kwargs):
    return S.fresh(**kwargs)


def exchange(state, action, response, commitment="MEDIUM", response_commitment="MEDIUM"):
    """Run one window-less exchange on a snapshot; returns (report, post-snapshot)."""
    match = O.SideControl.from_snapshot(state)
    report = match.attempt(A.get(action, action), R.get(response, response), commitment, response_commitment)
    assert report["error"] == "", report
    return report, match.snapshot()


# =====================================================================================================================
# 1. NEGATIVE-FIRST: entry
# =====================================================================================================================
def _entry_with(**changes):
    request = S.entry()
    request.update(changes)
    return request


def _pools(top=None, bottom=None):
    return _entry_with(fighters={TOP: top or S.pool(100), BOT: bottom or S.pool(100)})


def _set_pool(fighter_id, **pool_args):
    return lambda request: request["fighters"].update({fighter_id: S.pool(**pool_args)})


# (code, resources touched, modifier of a valid request that breaks ONLY that rule). Two modifiers can be applied together
# unless they touch the same resource. ``entry_not_a_dictionary`` replaces the whole request, so it is tested separately.
ENTRY_VIOLATIONS = [
    ("entry_malformed", {"extra"}, lambda r: r.update(tiers={"top_pin": 2})),
    ("invalid_fighter_id", {"ids"}, lambda r: r.update(role_map={"top": TOP, "bottom": TOP})),
    ("fighters_mismatch", {"top_pool", "bottom_pool"}, lambda r: r.update(fighters={TOP: S.pool(100), "stranger": S.pool(100)})),
    ("invalid_initiator", {"initiator"}, lambda r: r.update(initiator="middle")),
    ("invalid_stamina_maximum", {"top_pool"}, _set_pool(TOP, current=0, maximum=0)),
    ("invalid_stamina_current", {"bottom_pool"}, _set_pool(BOT, current=101)),
    ("inconsistent_exhaustion_latch", {"top_pool"}, _set_pool(TOP, current=25, latched=False)),
    ("invalid_behavior_remainder", {"bottom_pool"}, _set_pool(BOT, current=50, remainder=9007199254740992)),
    ("invalid_clock", {"clock"}, lambda r: r.update(clock={"initial_seconds": 5, "remaining_seconds": 6})),
    ("invalid_window_id", {"window"}, lambda r: r.update(window={"last_issued_id": -1})),
    ("invalid_interval", {"interval"}, lambda r: r.update(interval_seconds=0)),
]


def _violating(violations):
    request = S.entry()
    for _code, _touches, modify in violations:
        modify(request)
    return request


class NegativeEntryTests(unittest.TestCase):
    def test_the_violation_table_covers_exactly_the_documented_codes_in_order(self):
        self.assertEqual(["entry_not_a_dictionary"] + [code for code, _, _ in ENTRY_VIOLATIONS], list(O.ENTRY_ERROR_ORDER))

    def test_every_refusal_code_builds_nothing_and_never_touches_the_request(self):
        for request in (["not", "a", "dict"], None, 7, "entry"):
            self.assertEqual(O.SideControl.from_entry(request), (None, "entry_not_a_dictionary"))
        for violation in ENTRY_VIOLATIONS:
            request = _violating([violation])
            before = copy.deepcopy(request)
            self.assertEqual(O.SideControl.from_entry(request), (None, violation[0]), violation[0])
            self.assertEqual(request, before, violation[0])

    def test_every_malformed_shape_is_refused_as_malformed(self):
        base = S.entry()

        def drop(path):
            request = copy.deepcopy(base)
            target = request
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
            return request

        def put(path, value):
            request = copy.deepcopy(base)
            target = request
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return request

        cases = [drop(("role_map",)), drop(("initiator",)), drop(("fighters",)), drop(("clock",)), drop(("window",)), drop(("interval_seconds",)),
                 drop(("role_map", "top")), drop(("clock", "initial_seconds")), drop(("window", "last_issued_id")),
                 drop(("fighters", TOP, "stamina_current")), drop(("fighters", BOT, "behavior_remainder_units")),
                 put(("role_map", "extra"), TOP), put(("clock", "extra"), 1), put(("window", "extra"), 1), put(("fighters", TOP, "extra"), 1),
                 put(("interval_seconds",), 10.0), put(("interval_seconds",), True), put(("interval_seconds",), "10"),
                 put(("fighters", TOP, "stamina_current"), True), put(("fighters", TOP, "stamina_current"), 50.0),
                 put(("fighters", TOP, "stamina_maximum"), "100"), put(("fighters", TOP, "exhaustion_latched"), 0),
                 put(("fighters", TOP, "behavior_remainder_units"), 0.0), put(("clock", "initial_seconds"), 300.0),
                 put(("window", "last_issued_id"), None), put(("role_map", "top"), 7), put(("initiator",), 1), put(("fighters",), []),
                 put(("fighters", 5), S.pool(1)), put(("axis_tenths",), 10), put(("top_pin",), 2)]
        for request in cases:
            self.assertEqual(O.SideControl.from_entry(request), (None, "entry_malformed"), request)

    def test_every_adjacent_pair_is_combinable_and_the_earlier_code_wins(self):
        combinable = {(first[0], second[0]) for first, second in S.compatible_pairs(ENTRY_VIOLATIONS)}
        for index in range(len(ENTRY_VIOLATIONS) - 1):
            pair = (ENTRY_VIOLATIONS[index][0], ENTRY_VIOLATIONS[index + 1][0])
            self.assertIn(pair, combinable)  # no adjacent precedence is left untested
            self.assertEqual(O.SideControl.from_entry(_violating(ENTRY_VIOLATIONS[index:index + 2]))[1], pair[0], pair)

    def test_every_pair_of_independent_violations_reports_the_earlier_code(self):
        pairs = S.compatible_pairs(ENTRY_VIOLATIONS)
        for first, second in pairs:
            self.assertEqual(O.SideControl.from_entry(_violating([first, second]))[1], first[0], (first[0], second[0]))
        # 11 rules give 55 pairs; 6 share a resource: fighters_mismatch with the four pool rules, maximum with latch (top pool),
        # current with remainder (bottom pool)
        self.assertEqual(len(pairs), 55 - 6)

    def test_fighter_id_validation_matches_the_godot_strip_edges_set(self):
        for code in range(0x01, 0x21):
            for padded in (chr(code) + "a", "a" + chr(code)):
                request = _entry_with(role_map={"top": padded, "bottom": BOT}, fighters={padded: S.pool(100), BOT: S.pool(100)})
                self.assertEqual(O.SideControl.from_entry(request)[1], "invalid_fighter_id", hex(code))
        for ok in ("a b", "\x7fa", "\x85a", "\xa0a", "a ", "﻿a", "　a"):  # not stripped by Godot 4.7.2: valid
            request = _entry_with(role_map={"top": ok, "bottom": BOT}, fighters={ok: S.pool(100), BOT: S.pool(100)})
            self.assertEqual(O.SideControl.from_entry(request)[1], "", repr(ok))
        empty = _entry_with(role_map={"top": "", "bottom": BOT}, fighters={"": S.pool(100), BOT: S.pool(100)})
        self.assertEqual(O.SideControl.from_entry(empty)[1], "invalid_fighter_id")

    def test_latch_consistency_boundaries_by_capacity(self):
        # enter = floor(max/4), recover = ceil(35*max/100) written with exact integers (exact for these small capacities).
        for maximum in (1, 2, 3, 4, 7, 10, 29, 30, 99, 100, 101, 1000):
            enter, recover = maximum // 4, -(-35 * maximum // 100)
            self.assertEqual((O.enter_threshold(maximum), O.recover_threshold(maximum)), (enter, recover), maximum)
            for current, latched, valid in ((enter, False, False), (enter, True, True), (recover, True, False), (recover, False, True)):
                request = _pools(top=S.pool(current, maximum, latched=latched))
                self.assertEqual(O.SideControl.from_entry(request)[1] == "", valid, (maximum, current, latched))
            for current in range(enter + 1, recover):  # strictly between: either latch is accepted and carried
                for latched in (False, True):
                    match, error = O.SideControl.from_entry(_pools(top=S.pool(current, maximum, latched=latched)))
                    self.assertEqual(error, "")
                    self.assertEqual(match.snapshot()["fighters"][TOP]["exhaustion_latched"], latched)

    def test_a_request_with_no_time_left_and_extreme_values_are_judged_exactly(self):
        top = O.MAX_INT
        for request, code in ((_entry_with(clock={"initial_seconds": 10, "remaining_seconds": 0}), "invalid_clock"),
                              (_entry_with(clock={"initial_seconds": top + 1, "remaining_seconds": 1}), "invalid_clock"),
                              (_entry_with(window={"last_issued_id": top + 1}), "invalid_window_id"),
                              (_entry_with(interval_seconds=top + 1), "invalid_interval"),
                              (_pools(top=S.pool(0, top + 1)), "invalid_stamina_maximum")):
            self.assertEqual(O.SideControl.from_entry(request)[1], code)
        self.assertEqual(O.SideControl.from_entry(_entry_with(clock={"initial_seconds": top, "remaining_seconds": top},
                                                              window={"last_issued_id": top}, interval_seconds=top))[1], "")


# =====================================================================================================================
# 2. NEGATIVE-FIRST: commands, context, windows, terminal states (a refusal changes NOTHING)
# =====================================================================================================================
class NegativeCommandTests(unittest.TestCase):
    def assertRefused(self, runner, state, args, code, label=""):
        match = O.SideControl.from_snapshot(state)
        before = snap_bytes(match)
        result = runner(match, args)
        self.assertEqual(result, {"error": code}, (label, result))
        self.assertEqual(snap_bytes(match), before, "a refusal changed the state: %s" % label)

    def test_tables_follow_the_documented_precedence(self):
        # ``terminal_exchange`` stands for the whole context group at its place in the order
        as_context = lambda table: [("<context>" if c == "terminal_exchange" else c) for c, _, _ in table]
        self.assertEqual(as_context(S.SUBMIT_VIOLATIONS), list(O.SUBMIT_ERROR_ORDER))
        self.assertEqual(as_context(S.ATTEMPT_VIOLATIONS), list(O.ATTEMPT_ERROR_ORDER))
        self.assertEqual([c for c, _, _ in S.CONTEXT_VIOLATIONS], list(O.CONTEXT_ERROR_ORDER))

    def test_every_submit_refusal_alone_and_in_every_compatible_pair(self):
        base, args0 = S.base_open_state(), S.base_submit_args()
        self.assertEqual(O.SideControl.from_snapshot(base).submit(**args0)["error"], "")  # the ground truth is itself legal
        for violation in S.SUBMIT_VIOLATIONS:
            state, args = S._violated([violation], base, args0)
            self.assertRefused(lambda m, a: m.submit(**a), state, args, violation[0], violation[0])
        pairs = S.compatible_pairs(S.SUBMIT_VIOLATIONS)
        for first, second in pairs:
            state, args = S._violated([first, second], base, args0)
            self.assertRefused(lambda m, a: m.submit(**a), state, args, first[0], "%s+%s" % (first[0], second[0]))
        # 120 pairs minus 17 that share an input (window id 1, window state 1, fighter 3, action 6, response 6 via the pass rules and 1 pair)
        self.assertEqual(len(pairs), 103)

    def test_the_only_adjacent_submit_pairs_that_cannot_be_combined_are_explicit(self):
        codes = [c for c, _, _ in S.SUBMIT_VIOLATIONS]
        combinable = {(a[0], b[0]) for a, b in S.compatible_pairs(S.SUBMIT_VIOLATIONS)}
        skipped = [(codes[i], codes[i + 1]) for i in range(len(codes) - 1) if (codes[i], codes[i + 1]) not in combinable]
        # Each pair shares one input, so one rule makes the other unobservable (it is not an untested exception).
        self.assertEqual(skipped, [("missing_fighter_id", "unknown_fighter"), ("unknown_fighter", "not_initiator"),
                                   ("response_without_action", "commitment_without_action"), ("commitment_without_action", "invalid_commitment"),
                                   ("unknown_action", "incorrect_action_side_or_kind"), ("unknown_response", "incorrect_response_side_or_kind")])

    def test_every_attempt_refusal_alone_and_in_every_compatible_pair(self):
        base, args0 = S.fresh().snapshot(), S.base_attempt_args()
        self.assertEqual(O.SideControl.from_snapshot(base).attempt(**args0)["error"], "")
        for violation in S.ATTEMPT_VIOLATIONS:
            state, args = S._violated([violation], base, args0)
            self.assertRefused(lambda m, a: m.attempt(**a), state, args, violation[0], violation[0])
        for first, second in S.compatible_pairs(S.ATTEMPT_VIOLATIONS):
            state, args = S._violated([first, second], base, args0)
            self.assertRefused(lambda m, a: m.attempt(**a), state, args, first[0], "%s+%s" % (first[0], second[0]))

    def test_every_corrupted_snapshot_is_a_context_error_for_every_operation_in_order(self):
        base = S.fresh().snapshot()
        operations = (lambda m, a: m.attempt(**a), lambda m, a: m.open_window(), lambda m, a: m.open_window(5))
        for violation in S.CONTEXT_VIOLATIONS:
            state, args = S._violated([violation], base, S.base_attempt_args())
            for operation in operations:
                self.assertRefused(operation, state, args, violation[0], violation[0])
        for first, second in S.compatible_pairs(S.CONTEXT_VIOLATIONS):
            state, args = S._violated([first, second], base, S.base_attempt_args())
            self.assertRefused(lambda m, a: m.attempt(**a), state, args, first[0], "%s+%s" % (first[0], second[0]))
        # a submit on an open window reaches the same context codes (shape errors included) before any fighter check
        open_state = S.base_open_state()
        for violation in S.CONTEXT_VIOLATIONS:
            state, args = S._violated([violation], open_state, S.base_submit_args())
            self.assertRefused(lambda m, a: m.submit(**a), state, args, violation[0], violation[0])

    def test_unusable_snapshot_shapes_are_missing_state_not_crashes(self):
        base = S.fresh().snapshot()
        broken = []
        for key in base:
            state = copy.deepcopy(base)
            del state[key]
            broken.append(state)
        for key, value in (("axis_tenths", "10"), ("axis_tenths", 10.0), ("window_open", 1), ("fighters", []), ("role_map", {"top": TOP}),
                           ("decision_history", {}), ("band", True)):
            state = copy.deepcopy(base)
            state[key] = value
            broken.append(state)
        state = copy.deepcopy(base)
        state["fighters"][TOP] = {"stamina_current": 1}
        broken.append(state)
        for state in broken:
            self.assertRefused(lambda m, a: m.attempt(**a), state, S.base_attempt_args(), "missing_state")

    def test_window_requests_are_validated_and_refused_atomically(self):
        for duration, code in (("5", "invalid_duration"), (5.0, "invalid_duration"), (True, "invalid_duration"), ([], "invalid_duration"),
                               (-1, "invalid_window_request")):
            self.assertRefused(lambda m, a: m.open_window(a), S.fresh().snapshot(), duration, code, repr(duration))
        self.assertRefused(lambda m, a: m.open_window(a), S.base_open_state(), 5, "window_already_open")
        self.assertRefused(lambda m, a: m.attempt(**a), S.base_open_state(), S.base_attempt_args(), "window_already_open")

    def test_terminal_states_refuse_everything_before_any_tier_is_read(self):
        timeout = fresh(initial=10, interval=10)
        self.assertEqual(timeout.open_window()["status"], "closed")
        exited = O.SideControl.from_snapshot(S.state_with(axis=20, band=1, top_pin=2))
        self.assertEqual(exited.attempt(A["advance_to_mount"], R["bridge_defense"], "HIGH", "MEDIUM")["transition"]["kind"], "exit")
        for terminal in (timeout, exited):
            self.assertTrue(terminal.ended)
            for runner, code in ((lambda m: m.open_window(), "terminal_exchange"), (lambda m: m.open_window(0), "terminal_exchange"),
                                 (lambda m: m.attempt(**S.base_attempt_args()), "terminal_exchange"),
                                 (lambda m: m.submit(**S.base_submit_args()), "no_open_window")):
                before = snap_bytes(terminal)
                self.assertEqual(runner(terminal), {"error": code})
                self.assertEqual(snap_bytes(terminal), before)

    def test_wrong_side_wrong_initiative_reserved_and_foreign_ids_are_refused(self):
        base = S.base_open_state()
        for patch, code in (({"fighter_id": BOT}, "not_initiator"),  # Bottom may not act while the Top holds initiative
                            ({"action_id": A["shrimp"]}, "incorrect_action_side_or_kind"),  # Top submitting a Bottom technique
                            ({"action_id": R["hip_block"]}, "incorrect_action_side_or_kind"),  # a response given as an action
                            ({"response_id": A["stabilize"]}, "incorrect_response_side_or_kind"),  # an action given as a response
                            ({"response_id": R["forearm_frame"].replace("bottom_response", "top_response")}, "unknown_response"),
                            ({"action_id": "side_control.top.kimura_route"}, "unknown_action"),  # reserved, not in v0
                            ({"action_id": "side_control.top.armbar_route"}, "unknown_action"),
                            ({"action_id": "half_guard.top.knee_slice"}, "unknown_action"),
                            ({"action_id": "mount.top.americana"}, "unknown_action"),
                            ({"response_id": "half_guard.bottom_response.knee_shield"}, "unknown_response"),
                            ({"action_id": "side_control.top.reversal"}, "unknown_action")):
            self.assertRefused(lambda m, a: m.submit(**a), base, dict(S.base_submit_args(), **patch), code, str(patch))
        # a Bottom fighter with the initiative may act, and then the Top is the one refused
        bottom = O.SideControl.from_snapshot(S.state_with(initiator="bottom"))
        self.assertEqual(bottom.open_window()["initiator"], "bottom")
        self.assertEqual(bottom.submit(1, TOP, A["stabilize"], R["forearm_frame"], "", "")["error"], "not_initiator")
        self.assertEqual(bottom.submit(1, BOT, A["shrimp"], R["shoulder_pressure"], "", "")["error"], "")

    def test_duplicate_and_stale_delivery_changes_nothing(self):
        match = fresh()
        match.open_window()
        self.assertEqual(match.submit(1, TOP, A["stabilize"], R["forearm_frame"])["error"], "")
        before = snap_bytes(match)
        self.assertEqual(match.submit(1, TOP, A["stabilize"], R["forearm_frame"]), {"error": "no_open_window"})  # duplicate
        self.assertEqual(snap_bytes(match), before)
        match.open_window()
        before = snap_bytes(match)
        self.assertEqual(match.submit(1, BOT, A["shrimp"], R["shoulder_pressure"]), {"error": "stale_window"})  # the consumed id
        self.assertEqual(match.submit(3, BOT, A["shrimp"], R["shoulder_pressure"]), {"error": "stale_window"})  # a future id
        self.assertEqual(snap_bytes(match), before)

    def test_a_refusal_never_changes_any_category_of_state(self):
        # Spelled out per category (the byte comparison above subsumes it; this documents what "unchanged" means).
        match = O.SideControl.from_snapshot(S.state_with(axis=-20, band=-1, top_pin=2, bottom_space=0, initiator_current=20))
        match.open_window()
        before = match.snapshot()
        for args in (dict(S.base_submit_args(), window_id=9), dict(S.base_submit_args(), commitment="EXTREME"),
                     dict(S.base_submit_args(), fighter_id="nobody"), dict(S.base_submit_args(), action_id="nope")):
            self.assertNotEqual(match.submit(**args)["error"], "")
            after = match.snapshot()
            for key in ("fighters", "clock_seconds", "window_id", "window_open", "window_initiator", "initiator", "top_pin", "bottom_space",
                        "axis_tenths", "band", "decision_history", "exit_destination", "exit_reason"):
                self.assertEqual(after[key], before[key], key)

    def test_a_returned_snapshot_and_report_are_detached_copies(self):
        match = fresh()
        match.open_window()
        report = match.submit(1, TOP, A["stabilize"], R["bridge_defense"], "HIGH", "LOW")
        before = snap_bytes(match)
        report["record"]["final_grade"] = 99
        report["record"]["readiness_changes"].append("x")
        snapshot = match.snapshot()
        snapshot["fighters"][TOP]["stamina_current"] = 0
        snapshot["decision_history"].clear()
        self.assertEqual(snap_bytes(match), before)
        request = S.entry()
        built, _ = O.SideControl.from_entry(request)
        request["fighters"][TOP]["stamina_current"] = 1
        self.assertEqual(built.snapshot()["fighters"][TOP]["stamina_current"], 100)


# =====================================================================================================================
# 3. Rules-sheet consistency (the sheet is parsed; the oracle must agree with it)
# =====================================================================================================================
def sheet_text():
    with open(SHEET_PATH, encoding="utf-8") as handle:
        return handle.read()


def section(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def table_rows(block):
    rows = []
    for line in block.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[1:]  # drop the header


def clean(cell):
    return cell.replace("`", "").replace("**", "").strip()


def sheet_raw_grades():
    """The 18 raw grades parsed from the sheet's two matrices: {(action id, response id): grade}."""
    parsed = {}
    for block in section(sheet_text(), "### 3.3 Raw grades", "All 18 cells").split("\n\n"):
        lines = [line for line in block.splitlines() if line.startswith("|")]
        if lines:
            header = [clean(c) for c in lines[0].strip().strip("|").split("|")][1:]
            for row in table_rows(block):
                for response, grade in zip(header, [clean(c) for c in row[1:]]):
                    parsed[(clean(row[0]), response)] = int(grade)
    return parsed


class RulesSheetConsistencyTests(unittest.TestCase):
    def test_catalog_table_equals_oracle_ids_sides_break_capability_tracks_and_exits(self):
        rows = table_rows(section(sheet_text(), "### 3.1 Actions", "A Top action is answered"))
        self.assertEqual(len(rows), 12)
        seen = set()
        for identifier, side, kind, break_cell, track_cell, exit_cell in rows:
            identifier = clean(identifier)
            seen.add(identifier)
            if clean(kind) == "action":
                info = O.ACTIONS[identifier]
                self.assertEqual((clean(side), clean(break_cell) == "yes"), (info["side"], info["break"]), identifier)
                track = re.search(r"`(top_pin|bottom_space)`", track_cell)
                self.assertEqual(track.group(1) if info["break"] else "", info["track"], identifier)
                self.assertEqual(clean(exit_cell) if info["break"] else "—", info["exit"][0] or "—", identifier)
            else:
                info = O.RESPONSES[identifier]
                self.assertEqual(clean(side), info["side"], identifier)
                track = re.search(r"reads `(top_pin|bottom_space)`", track_cell)
                self.assertEqual(track.group(1) if track else "", info["track"], identifier)
        self.assertEqual(seen, set(O.ACTIONS) | set(O.RESPONSES))

    def test_both_raw_grade_matrices_equal_the_oracle_table(self):
        parsed = sheet_raw_grades()
        self.assertEqual(len(parsed), 18)
        self.assertEqual(parsed, O.RAW)

    def test_exit_map_equals_the_oracle(self):
        rows = table_rows(section(sheet_text(), "### 3.4 Exit map", "Every destination id"))
        self.assertEqual(len(rows), 4)
        by_name = {info["name"]: (aid, info) for aid, info in O.ACTIONS.items() if info["break"]}
        for technique, line, label, destination in rows:
            action_id, info = by_name[clean(technique)]
            self.assertEqual((clean(label), clean(destination)), info["exit"], technique)
            self.assertEqual(clean(line), "proposed >= +30" if info["side"] == "top" else "proposed <= -30")
        self.assertEqual({clean(r[2]) for r in rows}, set(O.EXIT_LABELS))
        self.assertEqual({clean(r[2]): clean(r[3]) for r in rows}, O.EXIT_DESTINATIONS)

    def test_hysteresis_table_equals_the_oracle_rules(self):
        rows = table_rows(section(sheet_text(), "* **Band update**", "The legal `(axis, band)` pairs"))
        parsed = []
        for source, rule, target in rows:
            match = re.match(r"a (>=|<=) (-?\d+)", clean(rule))
            parsed.append((int(clean(source)), "ge" if match.group(1) == ">=" else "le", int(match.group(2)), int(clean(target))))
        self.assertEqual(parsed, list(O.BAND_RULES))

    def test_wear_table_rows_state_the_documented_rules(self):
        rows = table_rows(section(sheet_text(), "2. *Wear* of the responder", "3. *Build:*"))
        self.assertEqual([(clean(a), clean(b)) for a, b in rows], [
            ("LOW or unfunded", "none"), ("MEDIUM", "-1 if final != 0"),
            ("HIGH and paid", "-1 only if final >= +1 (the defense failed); preserved on 0 and on a defense success"),
            ("HIGH and not paid (waived)", "as MEDIUM: -1 if final != 0")])

    def test_constants_stated_in_the_sheet_equal_the_oracle(self):
        text = sheet_text()
        self.assertIn("`LOW 3 / MEDIUM 7 / HIGH 12`", text)
        self.assertEqual(O.COSTS, {"LOW": 3, "MEDIUM": 7, "HIGH": 12})
        self.assertEqual((O.AXIS_MIN, O.AXIS_MAX, O.STEP, O.ENTRY_AXIS, O.ENTRY_BAND, O.EXIT_LINE), (-40, 40, 10, 10, 1, 30))
        for fragment in ("`-40 … +40`", "Entry axis **`+10`**, entry band **`+1`**", "Top `proposed >= +30`; Bottom `proposed <= -30`",
                         "`10` tenths per final-grade step", "`floor(maximum * 0.25)`", "`ceil(maximum * 0.35)`", "`current / maximum > 0.75`", "`> 0.50`",
                         "`top_pin = bottom_space = 1`", O.TIMEOUT_REASON, "9007199254740991", "ranks `unfunded 0, LOW 1, MEDIUM 2, HIGH 3`"):
            self.assertIn(fragment, text)
        self.assertEqual(O.DEFENSE_SHIFT, {2: -1, 1: 0, 0: 2})
        self.assertIn("{2: -1, 1: 0, 0: +2}", text)

    def test_entry_and_admission_precedence_in_the_sheet_equal_the_oracle(self):
        text = sheet_text()
        validation = section(text, "**Validation** is pure", "**Built state:**")
        codes = [m for m in re.findall(r"`([a-z_]+)`", validation) if re.match(r"(entry_|invalid_|inconsistent_|fighters_)", m)]
        self.assertEqual(codes, list(O.ENTRY_ERROR_ORDER))

        def order(block):
            result = []
            for segment in block.split("→"):
                code = re.match(r"\s*`([a-z_]+)`", segment)
                result.append(code.group(1) if code else "<context>")
            return result

        submit = section(text, "**`submit(window_id", "**`attempt(").split(":**", 1)[1]
        attempt = section(text, "**`attempt(action_id", "*Unknown* means").split(":**", 1)[1]
        self.assertEqual(order(submit), list(O.SUBMIT_ERROR_ORDER))
        self.assertEqual(order(attempt), list(O.ATTEMPT_ERROR_ORDER))
        context = section(text, "**Context** (`context_error`", "**`submit(window_id").split(":", 1)[1]
        self.assertEqual([re.match(r"\s*`([a-z_]+)`", part).group(1) for part in context.split(";")][:7], list(O.CONTEXT_ERROR_ORDER))

    def test_snapshot_and_record_fields_in_the_sheet_equal_the_oracle(self):
        text = sheet_text()
        block = section(text, "**`snapshot()`**", "Authority, `ended`")
        tokens = {t for t in re.findall(r"`([a-z_]+)`", block)}
        fighter_keys = set(O._POOL_KEYS)
        match = fresh()
        self.assertEqual(tokens, set(match.snapshot()) | fighter_keys)
        history = section(text, "**`decision_history`**", "**`snapshot()`**")
        fields = {t for t in re.findall(r"`([a-z_]+)`", history)} - {"decision_history", "consume", "wear", "build", "attempt", "cause"}
        match.open_window()
        record = match.submit(1, TOP, A["stabilize"], R["bridge_defense"])["record"]
        self.assertEqual(fields, set(record))
        self.assertEqual(fresh().snapshot()["decision_history"], [])  # nothing is stored until a decision
        match.open_window()
        self.assertEqual(set(match.submit(2, BOT, "", "")["record"]), {"kind", "window_id", "fighter_id", "role"})

    def test_the_sheet_states_its_exclusions_and_status(self):
        text = sheet_text()
        for fragment in ("transition prototype, not a finishing position", "provisional prototype constant", "`side_control.top.kimura_route`",
                         "No Python-to-Godot parity claim", "unresolved", "costs **no stamina**", "never a way to freeze simulated time"):
            self.assertIn(fragment, text.replace("\n", " ").replace("  ", " "))


# =====================================================================================================================
# 4. Catalog, axis and bands
# =====================================================================================================================
class TableTests(unittest.TestCase):
    LITERAL_RAW = {  # typed independently of the oracle (and of the sheet parser): initiator's point of view
        ("stabilize", "forearm_frame"): -1, ("stabilize", "hip_escape"): 1, ("stabilize", "bridge_defense"): 0,
        ("advance_to_mount", "forearm_frame"): 1, ("advance_to_mount", "hip_escape"): -2, ("advance_to_mount", "bridge_defense"): 1,
        ("expose_back", "forearm_frame"): 1, ("expose_back", "hip_escape"): 0, ("expose_back", "bridge_defense"): -2,
        ("shrimp", "shoulder_pressure"): -1, ("shrimp", "hip_block"): 1, ("shrimp", "follow_the_hips"): 0,
        ("recover_half_guard", "shoulder_pressure"): 2, ("recover_half_guard", "hip_block"): -1, ("recover_half_guard", "follow_the_hips"): 1,
        ("turn_to_knees", "shoulder_pressure"): 0, ("turn_to_knees", "hip_block"): 2, ("turn_to_knees", "follow_the_hips"): -2,
    }

    def test_all_eighteen_cells_are_the_approved_table(self):
        self.assertEqual({(a.split(".", 2)[2], r.split(".", 2)[2]): g for (a, r), g in O.RAW.items()}, self.LITERAL_RAW)

    def test_catalog_has_exactly_six_actions_and_six_responses_with_the_approved_exits(self):
        self.assertEqual(sorted(A), sorted(["stabilize", "advance_to_mount", "expose_back", "shrimp", "recover_half_guard", "turn_to_knees"]))
        self.assertEqual(sorted(R), sorted(["forearm_frame", "hip_escape", "bridge_defense", "shoulder_pressure", "hip_block", "follow_the_hips"]))
        exits = {name: O.ACTIONS[aid]["exit"] for name, aid in A.items() if O.ACTIONS[aid]["break"]}
        self.assertEqual(exits, {"advance_to_mount": ("Mount", "mount"), "expose_back": ("Back Control", "back_control"),
                                 "recover_half_guard": ("Half Guard", "half_guard"), "turn_to_knees": ("Turtle", "turtle")})
        self.assertEqual({n for n, aid in A.items() if not O.ACTIONS[aid]["break"]}, {"stabilize", "shrimp"})
        self.assertEqual({n: O.RESPONSES[rid]["track"] for n, rid in R.items() if O.RESPONSES[rid]["track"]},
                         {"hip_escape": "bottom_space", "hip_block": "top_pin"})

    def test_the_shape_of_both_grids_has_no_dominated_response_and_distinct_best_counters(self):
        for actions, responses in ((("stabilize", "advance_to_mount", "expose_back"), ("forearm_frame", "hip_escape", "bridge_defense")),
                                   (("shrimp", "recover_half_guard", "turn_to_knees"), ("shoulder_pressure", "hip_block", "follow_the_hips"))):
            grid = {(a, r): self.LITERAL_RAW[(a, r)] for a in actions for r in responses}
            self.assertEqual(len({min(responses, key=lambda r, a=a: grid[(a, r)]) for a in actions}), 3)
            for r in responses:
                column = [grid[(a, r)] for a in actions]
                self.assertTrue(min(column) <= 0 and max(column) >= 1, r)  # holds at least one action and loses to another
            for one in responses:
                for two in responses:
                    if one != two:
                        self.assertFalse(all(grid[(a, two)] <= grid[(a, one)] for a in actions) and any(grid[(a, two)] < grid[(a, one)] for a in actions))

    def test_funding_boundaries(self):
        for requested, available, expected in (("HIGH", 12, "HIGH"), ("HIGH", 11, "MEDIUM"), ("HIGH", 7, "MEDIUM"), ("HIGH", 6, "LOW"), ("HIGH", 3, "LOW"),
                                               ("HIGH", 2, ""), ("MEDIUM", 100, "MEDIUM"), ("MEDIUM", 6, "LOW"), ("MEDIUM", 2, ""),
                                               ("LOW", 100, "LOW"), ("LOW", 3, "LOW"), ("LOW", 2, ""), ("HIGH", 0, "")):
            self.assertEqual(O.determine(requested, available), expected, (requested, available))

    def test_shift_saturates(self):
        self.assertEqual([O.shift(g, k) for g, k in ((2, 1), (-2, -1), (1, 1), (-1, -1), (0, 2), (0, -2), (2, -1), (-2, 2))], [2, -2, 2, -2, 2, -2, 1, 0])


class AxisAndBandTests(unittest.TestCase):
    def test_every_axis_and_band_matches_a_literal_threshold_model(self):
        def model(axis, band):  # a second, differently-shaped statement of the same eight rules
            for _ in range(8):
                if band == 0 and axis >= 12: band = 1
                elif band == 1 and axis >= 27: band = 2
                elif band == -1 and axis >= -8: band = 0
                elif band == -2 and axis >= -23: band = -1
                elif band == 2 and axis <= 23: band = 1
                elif band == 1 and axis <= 8: band = 0
                elif band == 0 and axis <= -12: band = -1
                elif band == -1 and axis <= -27: band = -2
                else: break
            return band
        for axis in range(-45, 46):
            for band in (-2, -1, 0, 1, 2):
                self.assertEqual(O.band_update(axis, band), model(axis, band), (axis, band))

    def test_legal_pairs_are_fixed_points_and_illegal_pairs_move(self):
        legal = 0
        for axis in range(-40, 41):
            for band in (-2, -1, 0, 1, 2):
                if O.legal_pair(axis, band):
                    legal += 1
                    self.assertEqual(O.band_update(axis, band), band, (axis, band))
        self.assertEqual(legal, 23 + 18 + 17 + 18 + 17)  # band 0: -11..11, +-1: 9..26, +2: 24..40, -2: -40..-24
        self.assertTrue(O.legal_pair(10, 1))  # the entry pair
        for axis, band in ((0, 1), (12, 0), (-12, 0), (30, 1), (-30, -1)):
            self.assertFalse(O.legal_pair(axis, band))
            self.assertNotEqual(O.band_update(axis, band), band)

    def test_hysteresis_keeps_a_band_until_the_axis_leaves_it_by_a_margin(self):
        # +1 holds at 9..26 even though 0 holds below 12 and +2 starts above 23: the overlap is the memory.
        self.assertEqual([O.band_update(a, 1) for a in (8, 9, 26, 27)], [0, 1, 1, 2])
        self.assertEqual([O.band_update(a, 0) for a in (11, 12)], [0, 1])
        self.assertEqual([O.band_update(a, 2) for a in (23, 24)], [1, 2])
        self.assertEqual([O.band_update(a, -1) for a in (-8, -9, -26, -27)], [0, -1, -1, -2])

    def test_authority_is_reported_by_axis_sign_only(self):
        ids = {"top": TOP, "bottom": BOT}
        self.assertEqual([O.authority_id(a, ids) for a in (40, 1, 0, -1, -40)], [TOP, TOP, "", BOT, BOT])
        self.assertEqual(fresh().authority_id, TOP)

    def test_the_axis_clamps_at_the_limits_without_an_exit(self):
        # Top stabilize cannot exit; at axis 40 a Success changes nothing: proposed 50 clamps to 40 (band 2 stays).
        state = S.state_with(axis=40, band=2, top_pin=1)
        report, post = exchange(state, "stabilize", "hip_escape", "HIGH", "MEDIUM")
        self.assertEqual((report["transition"]["kind"], post["axis_tenths"], post["band"]), ("none", 40, 2))
        # Bottom at -40: shrimp success proposes -50, clamps to -40.
        state = S.state_with(initiator="bottom", axis=-40, band=-2, bottom_space=1)
        _, post = exchange(state, "shrimp", "hip_block", "HIGH", "MEDIUM")
        self.assertEqual((post["axis_tenths"], post["band"]), (-40, -2))


# =====================================================================================================================
# 5. Entry state
# =====================================================================================================================
class EntryStateTests(unittest.TestCase):
    def test_a_valid_entry_builds_exactly_the_documented_state(self):
        match, error = O.SideControl.from_entry(S.entry(initial=300, remaining=240, last_issued=7, interval=15,
                                                        top=S.pool(80, 100, remainder=4), bottom=S.pool(20, 100, remainder=-2)))
        self.assertEqual(error, "")
        self.assertEqual(match.snapshot(), {
            "position_id": "side_control", "role_map": {"top": TOP, "bottom": BOT}, "initiator": "top",
            "axis_tenths": 10, "band": 1, "top_pin": 1, "bottom_space": 1,
            "fighters": {TOP: {"stamina_current": 80, "stamina_maximum": 100, "exhaustion_latched": False, "behavior_remainder_units": 4},
                         BOT: {"stamina_current": 20, "stamina_maximum": 100, "exhaustion_latched": True, "behavior_remainder_units": -2}},
            "initial_seconds": 300, "clock_seconds": 240, "interval_seconds": 15, "window_id": 7, "window_open": False, "window_initiator": "",
            "exit_destination": "", "exit_reason": "", "decision_history": []})
        self.assertFalse(match.ended)

    def test_the_initiator_is_the_explicit_validated_input_and_never_derived(self):
        for initiator in ("top", "bottom"):
            match = fresh(initiator=initiator)
            self.assertEqual(match.snapshot()["initiator"], initiator)
            self.assertEqual(match.authority_id, TOP)  # authority stays the Top's at the +10 entry axis whoever opens
            self.assertEqual(match.open_window()["initiator"], initiator)

    def test_stamina_and_latch_follow_the_fighter_id_under_a_swapped_role_map(self):
        swapped = dict(S.entry(top=S.pool(20), bottom=S.pool(90)), role_map={"top": BOT, "bottom": TOP})
        match, error = O.SideControl.from_entry(swapped)
        self.assertEqual(error, "")
        fighters = match.snapshot()["fighters"]
        self.assertEqual((fighters[TOP]["stamina_current"], fighters[BOT]["stamina_current"]), (20, 90))
        self.assertEqual(match.authority_id, BOT)  # the role map says BOT is the Top
        self.assertEqual(match.open_window()["initiator"], "top")
        record = match.submit(1, BOT, A["stabilize"], R["bridge_defense"], "MEDIUM", "MEDIUM")["record"]
        self.assertEqual((record["fighter_id"], record["responder_id"]), (BOT, TOP))
        self.assertEqual(match.snapshot()["fighters"][BOT]["stamina_current"], 83)  # BOT acted as Top and paid 7 of 90

    def test_nothing_from_a_previous_position_can_be_supplied_or_carried(self):
        for key, value in (("top_pin", 2), ("bottom_space", 2), ("axis_tenths", 30), ("band", 2), ("decision_history", []), ("exit_destination", "")):
            self.assertEqual(O.SideControl.from_entry(dict(S.entry(), **{key: value})), (None, "entry_malformed"), key)


# =====================================================================================================================
# 6. Hand-computed pipeline literals
# =====================================================================================================================
class WorkedExampleTests(unittest.TestCase):
    """The four examples of the sheet, as literals with the arithmetic in comments."""

    def test_example_1_plain_exchange(self):
        # T Advance to Mount vs Forearm Frame, MEDIUM/MEDIUM, entry state (axis 10, band +1, tiers 1/1, 100/100).
        # raw +1; positional 0 (band +1); attack readiness tier 1 -> 1-1 = 0; forearm_frame not governed; exhaustion 0;
        # magnitude 0 (MEDIUM); undercommitment 0 (ranks equal) => final +1. proposed = 10 + 10 = 20 < 30: no exit.
        # axis 20, band +1 (20 < 27 and 20 > 8). Initiator flips. Charges 7 and 7 => 93/93. No tier changes.
        match = fresh()
        match.open_window()
        report = match.submit(1, TOP, A["advance_to_mount"], R["forearm_frame"], "MEDIUM", "MEDIUM")
        self.assertEqual(report, {"error": "", "kind": "exchange", "transition": O.transition_fields(""), "record": {
            "kind": "exchange", "window_id": 1, "fighter_id": TOP, "role": "top", "responder_id": BOT,
            "action_id": A["advance_to_mount"], "response_id": R["forearm_frame"],
            "commitment_requested": "MEDIUM", "response_commitment_requested": "MEDIUM",
            "initiator_effective": "MEDIUM", "responder_effective": "MEDIUM", "initiator_charged": 7, "responder_charged": 7,
            "responder_waived": 0, "raw_grade": 1, "final_grade": 1, "axis_before": 10, "axis_after": 20, "band_before": 1, "band_after": 1,
            "exit_destination": "", "readiness_changes": []}})
        post = match.snapshot()
        self.assertEqual((post["initiator"], post["top_pin"], post["bottom_space"]), ("bottom", 1, 1))
        self.assertEqual((post["fighters"][TOP]["stamina_current"], post["fighters"][BOT]["stamina_current"]), (93, 93))
        self.assertEqual((post["window_open"], post["clock_seconds"], post["exit_destination"]), (False, 290, ""))

    def test_example_2_exit(self):
        # axis 20 band +1, top_pin 2 (Ready). T Advance at HIGH vs Bridge Defense at MEDIUM.
        # raw +1; attack 2-1 = +1 -> +2; not governed; exhaustion 0; magnitude 0 (HIGH only acts on +-1 and g4 = +2);
        # undercommitment: MEDIUM rank 2 < HIGH rank 3 -> +1, saturates at +2 => final +2. proposed 20+20 = 40 >= 30: exit Mount.
        # axis clamps to 40 (no change), band +1 -> +2 (40 >= 27). Initiator does NOT flip. Consume: Ready break-capable -> top_pin 1.
        report, post = exchange(S.state_with(axis=20, band=1, top_pin=2), "advance_to_mount", "bridge_defense", "HIGH", "MEDIUM")
        self.assertEqual(report["transition"], {"kind": "exit", "raw_destination": "Mount", "destination_position_id": "mount", "resolved": True})
        record = report["record"]
        self.assertEqual((record["final_grade"], record["axis_before"], record["axis_after"], record["band_before"], record["band_after"]),
                         (2, 20, 40, 1, 2))
        self.assertEqual((record["initiator_charged"], record["responder_charged"]), (12, 7))
        self.assertEqual(record["readiness_changes"], [{"track": "top_pin", "before": 2, "after": 1, "cause": "consume"}])
        self.assertEqual((post["initiator"], post["exit_destination"], post["top_pin"], post["band"]), ("top", "Mount", 1, 2))
        self.assertEqual(post["exit_reason"], "Advance to Mount reached the advance line with final grade Strong Success")

    def test_example_3_defense_readiness(self):
        # T Advance vs Hip Escape, MEDIUM/MEDIUM, bottom_space 0 (None). raw -2; attack 1-1 = 0 -> -2; defense None -> +2 -> 0.
        # final 0 (Contested): axis unchanged; MEDIUM wear needs final != 0: none.
        report, post = exchange(S.state_with(bottom_space=0), "advance_to_mount", "hip_escape")
        self.assertEqual((report["record"]["final_grade"], post["axis_tenths"], report["record"]["readiness_changes"]), (0, 10, []))

    def test_example_4_unfunded_initiator_and_rule_one(self):
        # B has 2 of 100 (latched => Exhausted); requests MEDIUM Turn to Knees vs Shoulder Pressure (T 100, MEDIUM).
        # determine(MEDIUM, 2) = unfunded. raw 0; positional 0; attack 1-1 = 0; not governed; exhaustion -1 -> -1;
        # magnitude for an unfunded initiator acts only on +-2: 0; undercommitment: rank 2 < rank 0 is false: 0 => final -1.
        # Bottom delta = -10 * -1 = +10: axis 20. Rule 1: T's charge waived (7 recorded, 0 charged); B pays 0.
        report, post = exchange(S.state_with(initiator="bottom", initiator_current=2), "turn_to_knees", "shoulder_pressure")
        record = report["record"]
        self.assertEqual((record["initiator_effective"], record["responder_effective"]), ("", "MEDIUM"))
        self.assertEqual((record["final_grade"], record["axis_after"]), (-1, 20))
        self.assertEqual((record["initiator_charged"], record["responder_charged"], record["responder_waived"]), (0, 0, 7))
        self.assertEqual((post["fighters"][BOT]["stamina_current"], post["fighters"][TOP]["stamina_current"]), (2, 100))
        self.assertEqual(record["readiness_changes"], [])


class PipelineTests(unittest.TestCase):
    # name -> (state kwargs, action, response, commitment, response commitment, expected final grade, arithmetic)
    CASES = {
        "neutral": (dict(), "advance_to_mount", "forearm_frame", "MEDIUM", "MEDIUM", 1, "raw +1; tiers/exhaustion/magnitude/undercommit all 0"),
        "high_magnitude_success": (dict(), "advance_to_mount", "forearm_frame", "HIGH", "HIGH", 2, "g4 +1; HIGH magnitude +1 -> +2; ranks equal"),
        "high_magnitude_failure": (dict(), "stabilize", "forearm_frame", "HIGH", "HIGH", -2, "raw -1; HIGH magnitude -1 -> -2"),
        "high_leaves_a_contested_alone": (dict(), "stabilize", "bridge_defense", "HIGH", "HIGH", 0, "g4 0: magnitude 0; ranks equal"),
        "low_strong_success_is_capped": (dict(top_pin=2), "advance_to_mount", "forearm_frame", "LOW", "LOW", 1, "raw +1, attack +1 -> +2; LOW magnitude -1 -> +1"),
        "low_strong_failure_is_softened": (dict(), "expose_back", "bridge_defense", "LOW", "LOW", -1, "raw -2; LOW magnitude +1 -> -1"),
        "undercommitment_medium_vs_high": (dict(), "stabilize", "bridge_defense", "HIGH", "MEDIUM", 1, "g4 0; HIGH magnitude 0; responder rank 2 < 3: +1"),
        "undercommitment_low_vs_medium": (dict(), "stabilize", "bridge_defense", "MEDIUM", "LOW", 1, "responder rank 1 < 2: +1"),
        "no_undercommitment_when_responder_higher": (dict(), "stabilize", "bridge_defense", "LOW", "HIGH", 0, "responder rank 3 > 1: 0"),
        "initiator_exhausted": (dict(initiator_current=20), "stabilize", "bridge_defense", "MEDIUM", "MEDIUM", -1, "raw 0; exhaustion -1"),
        "responder_exhausted": (dict(responder_current=20), "stabilize", "bridge_defense", "MEDIUM", "MEDIUM", 1, "raw 0; exhaustion +1"),
        "both_exhausted_net_zero": (dict(initiator_current=20, responder_current=20), "stabilize", "bridge_defense", "MEDIUM", "MEDIUM", 0, "-1 + 1"),
        "saturation_before_the_next_step": (dict(top_pin=0, bottom_space=0), "advance_to_mount", "hip_escape", "MEDIUM", "MEDIUM", 0,
                                            "raw -2; attack None -1 saturates at -2; defense None +2 -> 0 (an unsaturated sum would be -1)"),
        "prepared_attacker_beats_unprepared_defender": (dict(top_pin=2, bottom_space=0), "advance_to_mount", "hip_escape", "MEDIUM", "MEDIUM", 1,
                                                        "raw -2; attack Ready +1 -> -1; defense None +2 -> +1"),
        "ready_defense_holds": (dict(bottom_space=2), "advance_to_mount", "hip_escape", "MEDIUM", "MEDIUM", -2, "raw -2; attack 0; defense Ready -1 saturates at -2"),
        "partial_defense_is_neutral": (dict(bottom_space=1), "advance_to_mount", "hip_escape", "MEDIUM", "MEDIUM", -2, "raw -2; Partial 0"),
        "low_response_is_unprepared_even_when_ready": (dict(bottom_space=2), "advance_to_mount", "hip_escape", "MEDIUM", "LOW", 1,
                                                       "raw -2; attack 0; LOW defender strength None +2 -> 0; undercommit +1 -> +1"),
        "attack_readiness_ignores_non_break_actions": (dict(top_pin=0), "stabilize", "bridge_defense", "MEDIUM", "MEDIUM", 0, "stabilize reads no track"),
        "non_governed_responses_ignore_tiers": (dict(bottom_space=0, top_pin=2), "advance_to_mount", "forearm_frame", "MEDIUM", "MEDIUM", 2,
                                                "raw +1; attack Ready +1 -> +2; forearm_frame reads no track"),
        "positional_modifier_top_vs_bottom_control": (dict(axis=-30, band=-2), "stabilize", "hip_escape", "MEDIUM", "MEDIUM", 0, "raw +1; positional -1 -> 0"),
        "no_positional_modifier_at_edge": (dict(axis=-20, band=-1), "stabilize", "hip_escape", "MEDIUM", "MEDIUM", 1, "band -1 is not a CONTROL band"),
        "positional_modifier_bottom_vs_top_control": (dict(initiator="bottom", axis=30, band=2), "shrimp", "hip_block", "MEDIUM", "MEDIUM", 0,
                                                      "raw +1; positional -1 -> 0 (defense Partial 0)"),
        "bottom_unprepared_attack": (dict(initiator="bottom", bottom_space=0), "recover_half_guard", "shoulder_pressure", "MEDIUM", "MEDIUM", 1,
                                     "raw +2; attack None -1 -> +1"),
    }

    def test_every_hand_computed_case(self):
        for name, (kwargs, action, response, commitment, response_commitment, expected, why) in self.CASES.items():
            report, _ = exchange(S.state_with(**kwargs), action, response, commitment, response_commitment)
            self.assertEqual(report["record"]["final_grade"], expected, "%s (%s)" % (name, why))

    def test_the_grade_is_decided_from_pre_exchange_state_not_from_the_charge(self):
        # A responder at 32 pays 7 and drops to 25 (latched), but it was not Exhausted when graded: no +1 for the initiator.
        report, post = exchange(S.state_with(responder_current=32), "stabilize", "bridge_defense")
        self.assertEqual(report["record"]["final_grade"], 0)
        self.assertEqual(post["fighters"][BOT]["exhaustion_latched"], True)  # the charge latched it for the NEXT exchange


class StaminaTests(unittest.TestCase):
    def test_charges_initiator_then_responder_and_latch_updates(self):
        report, post = exchange(S.state_with(initiator_current=30, responder_current=33), "stabilize", "bridge_defense", "HIGH", "MEDIUM")
        # initiator 30 funds HIGH (12) -> 18 (<= 25 latch); responder 33 funds MEDIUM (7) -> 26 (not latched: 26 > 25)
        self.assertEqual((report["record"]["initiator_charged"], report["record"]["responder_charged"]), (12, 7))
        self.assertEqual((post["fighters"][TOP]["stamina_current"], post["fighters"][TOP]["exhaustion_latched"]), (18, True))
        self.assertEqual((post["fighters"][BOT]["stamina_current"], post["fighters"][BOT]["exhaustion_latched"]), (26, False))

    def test_a_latched_fighter_stays_latched_between_the_thresholds(self):
        # 30 is between enter 25 and recover 35: a latched pool is carried, and nothing in v0 can recover stamina.
        state = S.state_with(initiator_current=30)
        state["fighters"][TOP] = S.pool(30, 100, latched=True)
        _, post = exchange(state, "stabilize", "bridge_defense", "LOW", "LOW")
        self.assertEqual((post["fighters"][TOP]["stamina_current"], post["fighters"][TOP]["exhaustion_latched"]), (27, True))

    def test_rule_one_waives_only_the_response_charge_and_never_the_grade(self):
        waived, _ = exchange(S.state_with(initiator_current=2), "stabilize", "bridge_defense")
        funded, _ = exchange(S.state_with(initiator_current=100), "stabilize", "bridge_defense")
        self.assertEqual(waived["record"]["responder_waived"], 7)
        self.assertEqual(waived["record"]["responder_charged"], 0)
        # unfunded initiator: raw 0, exhaustion -1 -> -1; the responder is not additionally rewarded for the waiver
        self.assertEqual((waived["record"]["final_grade"], funded["record"]["final_grade"]), (-1, 0))
        both_unfunded, _ = exchange(S.state_with(initiator_current=2, responder_current=1), "stabilize", "bridge_defense")
        self.assertEqual((both_unfunded["record"]["responder_waived"], both_unfunded["record"]["responder_charged"]), (0, 0))

    def test_partial_funding_downgrades_without_a_shortfall(self):
        report, post = exchange(S.state_with(initiator_current=9, responder_current=5), "stabilize", "bridge_defense", "HIGH", "HIGH")
        self.assertEqual((report["record"]["initiator_effective"], report["record"]["responder_effective"]), ("MEDIUM", "LOW"))
        self.assertEqual((post["fighters"][TOP]["stamina_current"], post["fighters"][BOT]["stamina_current"]), (2, 2))
        self.assertEqual((report["record"]["commitment_requested"], report["record"]["response_commitment_requested"]), ("HIGH", "HIGH"))

    def test_empty_commitments_default_to_medium(self):
        match = fresh()
        match.open_window()
        record = match.submit(1, TOP, A["stabilize"], R["bridge_defense"], "", "")["record"]
        self.assertEqual((record["commitment_requested"], record["response_commitment_requested"], record["initiator_charged"]), ("MEDIUM", "MEDIUM", 7))


# =====================================================================================================================
# 7. Readiness
# =====================================================================================================================
class ReadinessTests(unittest.TestCase):
    def test_a_break_capable_attempt_at_ready_spends_one_tier_whatever_the_result(self):
        # a success (Advance vs Bridge Defense: raw +1, Ready +1 -> +2) and a failure (Advance vs a Ready Hip Escape: -2, +1, -1 -> -2)
        for kwargs, response in ((dict(top_pin=2, bottom_space=0), "bridge_defense"), (dict(top_pin=2, bottom_space=2), "hip_escape")):
            report, post = exchange(S.state_with(**kwargs), "advance_to_mount", response)
            self.assertEqual(post["top_pin"], 1, response)
            self.assertIn({"track": "top_pin", "before": 2, "after": 1, "cause": "consume"}, report["record"]["readiness_changes"])
        for tier in (0, 1):  # not Ready: nothing to spend
            _, post = exchange(S.state_with(top_pin=tier), "advance_to_mount", "bridge_defense")
            self.assertEqual(post["top_pin"], tier)
        _, post = exchange(S.state_with(initiator="bottom", bottom_space=2), "turn_to_knees", "shoulder_pressure")
        self.assertEqual(post["bottom_space"], 1)

    def test_non_break_actions_never_consume(self):
        _, post = exchange(S.state_with(top_pin=2), "stabilize", "forearm_frame")
        self.assertEqual(post["top_pin"], 2)
        _, post = exchange(S.state_with(initiator="bottom", bottom_space=2), "shrimp", "shoulder_pressure")
        self.assertEqual(post["bottom_space"], 2)

    def test_wear_and_build_in_the_documented_order(self):
        # T Stabilize vs Hip Escape (MEDIUM both), tiers 1/1: raw +1, defense Partial 0 => final +1.
        # Wear (MEDIUM, final != 0): bottom_space 1 -> 0. Build (final >= +1): top_pin 1 -> 2. Wear is listed before build.
        report, post = exchange(S.state_with(), "stabilize", "hip_escape")
        self.assertEqual(report["record"]["final_grade"], 1)
        self.assertEqual(report["record"]["readiness_changes"], [{"track": "bottom_space", "before": 1, "after": 0, "cause": "wear"},
                                                                 {"track": "top_pin", "before": 1, "after": 2, "cause": "build"}])
        self.assertEqual((post["top_pin"], post["bottom_space"]), (2, 0))

    def test_build_needs_a_success_and_touches_only_its_own_track(self):
        _, failure = exchange(S.state_with(), "stabilize", "forearm_frame")  # raw -1: no build
        self.assertEqual((failure["top_pin"], failure["bottom_space"]), (1, 1))
        # HIGH + exhausted responder lifts Stabilize vs Bridge Defense (raw 0) to a success; no governed response, so no wear.
        report, post = exchange(S.state_with(responder_current=20), "stabilize", "bridge_defense", "HIGH", "MEDIUM")
        self.assertEqual(report["record"]["final_grade"], 2)  # 0 +1 exhausted responder, HIGH magnitude +1, undercommit +1 -> saturates 2
        self.assertEqual((post["top_pin"], post["bottom_space"]), (2, 1))
        shrimp, after = exchange(S.state_with(initiator="bottom"), "shrimp", "hip_block")  # raw +1
        self.assertEqual((shrimp["record"]["final_grade"], after["bottom_space"], after["top_pin"]), (1, 2, 0))  # build +1; Hip Block wears top_pin

    def test_tiers_saturate_at_the_floor_and_the_ceiling_without_recording_a_change(self):
        report, post = exchange(S.state_with(top_pin=2, bottom_space=0), "stabilize", "hip_escape")  # build at 2, wear at 0
        self.assertEqual(report["record"]["readiness_changes"], [])
        self.assertEqual((post["top_pin"], post["bottom_space"]), (2, 0))

    def test_wear_depends_on_the_responders_effective_commitment_and_the_result(self):
        # B Recover Half Guard vs Hip Block (Top defends, top_pin 1): raw -1; attack Partial 0; defense Partial 0 => final -1.
        def run(responder_commitment, initiator_current=100, responder_current=100):
            report, post = exchange(S.state_with(initiator="bottom", initiator_current=initiator_current, responder_current=responder_current),
                                    "recover_half_guard", "hip_block", "MEDIUM", responder_commitment)
            return report["record"]["final_grade"], post["top_pin"]
        self.assertEqual(run("LOW")[1], 1)  # LOW never wears
        self.assertEqual(run("MEDIUM")[1], 0)  # MEDIUM wears on any decided result (final != 0)
        self.assertEqual(run("HIGH")[1], 1)  # a paid HIGH defense that holds is preserved
        # same exchange, initiator unfunded (stamina 2): the HIGH charge is waived, so the HIGH defense is unpaid and wears like MEDIUM
        self.assertEqual(run("HIGH", initiator_current=2)[1], 0)
        self.assertEqual(run("LOW", initiator_current=2)[1], 1)
        # a HIGH defense that FAILS wears even when paid: B Turn to Knees vs Hip Block raw +2 => final +2
        _, post = exchange(S.state_with(initiator="bottom"), "turn_to_knees", "hip_block", "MEDIUM", "HIGH")
        self.assertEqual(post["top_pin"], 0)

    def test_a_contested_result_wears_nothing(self):
        report, post = exchange(S.state_with(bottom_space=0), "advance_to_mount", "hip_escape")  # example 3: final 0
        self.assertEqual((report["record"]["final_grade"], post["bottom_space"]), (0, 0))
        report, post = exchange(S.state_with(bottom_space=1, top_pin=1), "expose_back", "hip_escape")  # raw 0 => final 0
        self.assertEqual((report["record"]["final_grade"], post["bottom_space"], report["record"]["readiness_changes"]), (0, 1, []))


# =====================================================================================================================
# 8. Exits (all four are honestly unsupported: a terminal record, no successor)
# =====================================================================================================================
class ExitTests(unittest.TestCase):
    def test_each_exit_destination_reason_and_transition(self):
        cases = (
            # top exits: axis 20/band 1/top_pin 2, HIGH vs MEDIUM, final +2 => 40
            (dict(axis=20, band=1, top_pin=2), "advance_to_mount", "bridge_defense", "HIGH", "MEDIUM", "Mount", "mount",
             "Advance to Mount reached the advance line with final grade Strong Success"),
            (dict(axis=20, band=1, top_pin=2), "expose_back", "forearm_frame", "HIGH", "MEDIUM", "Back Control", "back_control",
             "Expose Back reached the advance line with final grade Strong Success"),
            # bottom exits: axis -20/band -1; Recover raw +2, final +2 => -40; Turn to Knees needs Ready: raw 0, +1 => final +1 => -30
            (dict(initiator="bottom", axis=-20, band=-1), "recover_half_guard", "shoulder_pressure", "MEDIUM", "MEDIUM", "Half Guard", "half_guard",
             "Recover Half Guard reached the escape line with final grade Strong Success"),
            (dict(initiator="bottom", axis=-20, band=-1, bottom_space=2), "turn_to_knees", "shoulder_pressure", "MEDIUM", "MEDIUM", "Turtle", "turtle",
             "Turn to Knees reached the escape line with final grade Success"))
        for kwargs, action, response, commitment, response_commitment, label, destination, reason in cases:
            report, post = exchange(S.state_with(**kwargs), action, response, commitment, response_commitment)
            self.assertEqual(report["transition"], {"kind": "exit", "raw_destination": label, "destination_position_id": destination, "resolved": True})
            self.assertEqual((post["exit_destination"], post["exit_reason"], report["record"]["exit_destination"]), (label, reason, label))
            self.assertEqual(post["initiator"], kwargs.get("initiator", "top"))  # an exit does not flip initiative
            self.assertEqual(post["window_open"], False)

    def test_the_line_is_inclusive_and_needs_a_success(self):
        # Entry axis 10, final +2 => proposed exactly 30: an exit (>=).
        report, post = exchange(S.state_with(top_pin=2), "advance_to_mount", "forearm_frame", "HIGH", "HIGH")  # +1 +1 attack +1 magnitude ->+2
        self.assertEqual((report["record"]["final_grade"], post["axis_tenths"], post["exit_destination"]), (2, 30, "Mount"))
        # axis 19, final +1 => 29: no exit. axis 20, final +1 => 30: exit.
        for axis, band, exits in ((19, 1, False), (20, 1, True)):
            report, post = exchange(S.state_with(axis=axis, band=band), "advance_to_mount", "forearm_frame")
            self.assertEqual((report["record"]["final_grade"], post["exit_destination"] != ""), (1, exits), axis)
        # at axis 30 a Contested break-capable attempt proposes 30 but is not a Success: no exit
        report, post = exchange(S.state_with(axis=30, band=2, bottom_space=0), "advance_to_mount", "hip_escape")
        self.assertEqual((report["record"]["final_grade"], post["exit_destination"]), (0, ""))
        # bottom mirror: axis -19 + success => -29: no exit; -20 => -30: exit
        for axis, band, exits in ((-19, -1, False), (-20, -1, True)):
            report, post = exchange(S.state_with(initiator="bottom", axis=axis, band=band, bottom_space=2), "turn_to_knees", "shoulder_pressure")
            self.assertEqual((report["record"]["final_grade"], post["exit_destination"] != ""), (1, exits), axis)

    def test_non_break_techniques_never_exit_even_across_the_line(self):
        report, post = exchange(S.state_with(axis=30, band=2), "stabilize", "hip_escape", "HIGH", "MEDIUM")
        self.assertEqual((report["record"]["final_grade"] >= 1, post["axis_tenths"], post["exit_destination"]), (True, 40, ""))
        self.assertEqual(post["initiator"], "bottom")
        _, post = exchange(S.state_with(initiator="bottom", axis=-30, band=-2), "shrimp", "hip_block", "HIGH", "MEDIUM")
        self.assertEqual((post["axis_tenths"], post["exit_destination"]), (-40, ""))

    def test_an_exit_still_settles_axis_band_stamina_and_readiness(self):
        report, post = exchange(S.state_with(axis=20, band=1, top_pin=2), "advance_to_mount", "bridge_defense", "HIGH", "MEDIUM")
        self.assertEqual((post["axis_tenths"], post["band"]), (40, 2))
        self.assertEqual((post["fighters"][TOP]["stamina_current"], post["fighters"][BOT]["stamina_current"]), (88, 93))
        self.assertEqual(post["top_pin"], 1)

    def test_an_exit_is_terminal_and_activates_no_successor(self):
        match = O.SideControl.from_snapshot(S.state_with(axis=20, band=1, top_pin=2))
        match.attempt(A["advance_to_mount"], R["bridge_defense"], "HIGH", "MEDIUM")
        self.assertTrue(match.ended)
        self.assertEqual(match.snapshot()["position_id"], "side_control")  # still the same, finished position: nothing took over
        self.assertEqual(match.open_window(), {"error": "terminal_exchange"})
        self.assertFalse(hasattr(O, "Mount") or hasattr(O, "HalfGuard") or hasattr(O, "Turtle"))
        for label in O.EXIT_LABELS:
            self.assertTrue(O.transition_fields(label)["resolved"])  # declared ids, not receivers

    def test_exits_never_use_reversal_and_unresolved_labels_do_not_exist(self):
        self.assertNotIn("Reversal", O.EXIT_LABELS)
        for name in ("reversal", "kimura_route", "armbar_route"):
            self.assertFalse(any(aid.endswith("." + name) for aid in O.ACTIONS))


# =====================================================================================================================
# 9. PASS, windows, clock, timeout
# =====================================================================================================================
class PassAndWindowTests(unittest.TestCase):
    def test_a_pass_costs_nothing_grades_nothing_and_only_flips_initiative(self):
        match = fresh(top=S.pool(61), bottom=S.pool(40))
        match.open_window()
        before = match.snapshot()
        report = match.submit(1, TOP, "", "", "", "")
        self.assertEqual(report, {"error": "", "kind": "pass", "record": {"kind": "pass", "window_id": 1, "fighter_id": TOP, "role": "top"},
                                  "transition": {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": False}})
        after = match.snapshot()
        for key in ("fighters", "axis_tenths", "band", "top_pin", "bottom_space", "clock_seconds", "window_id", "exit_destination"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual((before["initiator"], after["initiator"], after["window_open"]), ("top", "bottom", False))
        self.assertEqual(after["decision_history"], [report["record"]])

    def test_a_pass_adds_no_clock_beyond_the_window_that_offered_it(self):
        match = fresh(initial=60, interval=10)
        self.assertEqual(match.open_window()["clock_seconds"], 50)  # opening the window consumed the time
        match.submit(1, TOP, "", "", "", "")
        self.assertEqual(match.snapshot()["clock_seconds"], 50)  # the pass itself consumed none

    def test_passing_cannot_freeze_time_two_passing_fighters_run_to_the_clock(self):
        match = fresh(initial=60, interval=10)
        windows = 0
        for _ in range(100):  # bounded: a rule bug that never ends the match must fail, not hang
            opened = match.open_window()
            if opened["status"] == "closed":
                break
            windows += 1
            role = match.snapshot()["initiator"]
            self.assertEqual(match.submit(opened["window_id"], match.snapshot()["role_map"][role], "", "")["error"], "")
        self.assertEqual(windows, 5)  # 60 s at 10 s: windows at 50,40,30,20,10 s; the sixth open reaches 0 and closes
        snapshot = match.snapshot()
        self.assertEqual((snapshot["clock_seconds"], snapshot["exit_destination"], snapshot["exit_reason"], match.ended), (0, "", O.TIMEOUT_REASON, True))
        self.assertEqual([r["kind"] for r in snapshot["decision_history"]], ["pass"] * 5)
        self.assertEqual([r["role"] for r in snapshot["decision_history"]], ["top", "bottom", "top", "bottom", "top"])
        self.assertEqual({r["fighter_id"] for r in snapshot["decision_history"]}, {TOP, BOT})

    def test_either_role_may_pass_and_a_pass_is_its_own_decision_kind_with_the_fighter_id(self):
        match = fresh(initiator="bottom")
        match.open_window()
        self.assertEqual(match.submit(1, BOT, "", "")["record"], {"kind": "pass", "window_id": 1, "fighter_id": BOT, "role": "bottom"})
        match.open_window()
        match.submit(2, TOP, A["stabilize"], R["bridge_defense"])
        self.assertEqual([r["kind"] for r in match.snapshot()["decision_history"]], ["pass", "exchange"])

    def test_a_pass_with_a_commitment_a_response_or_through_attempt_is_refused(self):
        match = fresh()
        match.open_window()
        self.assertEqual(match.submit(1, TOP, "", "", "LOW", ""), {"error": "commitment_without_action"})
        self.assertEqual(match.submit(1, TOP, "", "", "", "LOW"), {"error": "commitment_without_action"})
        self.assertEqual(match.submit(1, TOP, "", R["bridge_defense"], "", ""), {"error": "response_without_action"})
        self.assertEqual(fresh().attempt("", ""), {"error": "unknown_action"})

    def test_the_position_owns_no_inactivity_stalling_momentum_or_heart_of_a_lion_state(self):
        keys = set(fresh().snapshot())
        for word in ("stall", "inactiv", "momentum", "heart", "lion", "rest", "score", "penalt", "streak", "turn_count"):
            self.assertFalse(any(word in key for key in keys), word)
        self.assertFalse(any("initiation" in key for key in keys))  # passes are not counted as initiations

    def test_window_ids_continue_from_the_entry_and_are_strictly_monotonic(self):
        match = fresh(last_issued=41)
        ids = []
        for _ in range(6):
            opened = match.open_window()
            ids.append(opened["window_id"])
            role = match.snapshot()["initiator"]
            match.submit(opened["window_id"], match.snapshot()["role_map"][role], "", "")
        self.assertEqual(ids, [42, 43, 44, 45, 46, 47])

    def test_zero_time_windows_clamping_and_the_interval_default(self):
        match = fresh(initial=100, interval=30)
        self.assertEqual(match.open_window(0), {"error": "", "status": "opened", "window_id": 1, "initiator": "top", "elapsed_seconds": 0, "clock_seconds": 100})
        match.submit(1, TOP, "", "")
        self.assertEqual(match.open_window()["elapsed_seconds"], 30)
        match.submit(2, BOT, "", "")
        self.assertEqual(match.open_window(500), {"error": "", "status": "closed", "window_id": 2, "initiator": "", "elapsed_seconds": 70, "clock_seconds": 0})

    def test_timeout_at_the_exact_boundary_never_opens_a_window_or_advances_the_id(self):
        match = fresh(initial=10, interval=10)
        self.assertEqual(match.open_window(), {"error": "", "status": "closed", "window_id": 0, "initiator": "", "elapsed_seconds": 10, "clock_seconds": 0})
        snapshot = match.snapshot()
        self.assertEqual((snapshot["window_open"], snapshot["window_id"], snapshot["exit_destination"], snapshot["exit_reason"]),
                         (False, 0, "", O.TIMEOUT_REASON))
        self.assertTrue(match.ended)

    def test_an_exit_leaves_the_clock_alone_and_a_one_second_remainder_still_times_out_normally(self):
        match = O.SideControl.from_snapshot(S.state_with(axis=20, band=1, top_pin=2, remaining=1))
        match.attempt(A["advance_to_mount"], R["bridge_defense"], "HIGH", "MEDIUM")
        self.assertEqual((match.snapshot()["clock_seconds"], match.snapshot()["exit_reason"].startswith("Advance")), (1, True))
        last = fresh(initial=300, remaining=1)
        self.assertEqual(last.open_window()["status"], "closed")
        self.assertEqual(last.snapshot()["exit_reason"], O.TIMEOUT_REASON)


# =====================================================================================================================
# 10. Differential model (test-only): an independently shaped statement of the sheet, run over the whole exchange fixture
# =====================================================================================================================
class ModelDifferentialTests(unittest.TestCase):
    """Re-derives every grid row from the SHEET-PARSED tables with differently shaped code; a mismatch is a bug in one of the two."""

    def model(self, raw_table, row):
        state, op = row["state"], row["operation"]
        role = state["initiator"]
        mine, theirs = state["role_map"][role], state["role_map"]["bottom" if role == "top" else "top"]
        sat = lambda v: max(-2, min(2, v))
        cost = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
        rank = {"": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}

        def effective(requested, stamina):
            return next((t for t in ("HIGH", "MEDIUM", "LOW") if rank[t] <= rank[requested] and cost[t] <= stamina), "")
        ie = effective(op["commitment"], state["fighters"][mine]["stamina_current"])
        re_ = effective(op["response_commitment"], state["fighters"][theirs]["stamina_current"])
        action, response = op["action_id"], op["response_id"]
        breaker = action.split(".")[-1] in ("advance_to_mount", "expose_back", "recover_half_guard", "turn_to_knees")
        own = state["top_pin"] if role == "top" else state["bottom_space"]
        defender_track = {"hip_escape": state["bottom_space"], "hip_block": state["top_pin"]}.get(response.split(".")[-1])
        exhausted = lambda who: state["fighters"][who]["exhaustion_latched"]
        g = raw_table[(action, response)]
        g = sat(g + (-1 if (role == "top" and state["band"] == -2) or (role == "bottom" and state["band"] == 2) else 0))
        g = sat(g + (own - 1 if breaker else 0))
        if defender_track is not None:
            g = sat(g + {0: 2, 1: 0, 2: -1}[0 if re_ in ("", "LOW") else defender_track])
        g = sat(g + (-1 if exhausted(mine) else 0) + (1 if exhausted(theirs) else 0))
        g = sat(g + (({1: 1, -1: -1}.get(g, 0)) if ie == "HIGH" else ({2: -1, -2: 1}.get(g, 0)) if ie in ("", "LOW") else 0))
        final = sat(g + (1 if rank[re_] < rank[ie] else 0))
        proposed = state["axis_tenths"] + (10 if role == "top" else -10) * final
        exits = breaker and final >= 1 and ((proposed >= 30) if role == "top" else (proposed <= -30))
        waived = cost.get(re_, 0) if ie == "" else 0
        paid = re_ != "" and ie != ""
        track_after = {"top_pin": state["top_pin"], "bottom_space": state["bottom_space"]}
        if breaker and own == 2:
            track_after["top_pin" if role == "top" else "bottom_space"] -= 1
        if defender_track is not None:
            name = "bottom_space" if response.endswith("hip_escape") else "top_pin"
            wear = (re_ == "MEDIUM" and final != 0) or (re_ == "HIGH" and ((final >= 1) if paid else final != 0))
            track_after[name] = max(0, track_after[name] - (1 if wear else 0))
        if final >= 1 and not breaker:
            name = "top_pin" if role == "top" else "bottom_space"
            track_after[name] = min(2, track_after[name] + 1)
        return {"final": final, "axis": max(-40, min(40, proposed)), "exit": exits, "waived": waived, "tiers": track_after,
                "charges": (cost.get(ie, 0), 0 if ie == "" else cost.get(re_, 0)), "initiator": role if exits else ("bottom" if role == "top" else "top")}

    def test_the_model_agrees_with_the_oracle_on_every_exchange_and_break_row(self):
        sheet_raw = sheet_raw_grades()
        self.assertEqual(sheet_raw, O.RAW)
        checked = 0
        for row in [r for r in cached_rows() if r["family"] in ("exchange_grid", "break_grid")]:
            expected = self.model(sheet_raw, row)
            record = row["expected"]["result"]["record"]
            post = row["expected"]["snapshot"]
            self.assertEqual((record["final_grade"], post["axis_tenths"], record["exit_destination"] != "", record["responder_waived"]),
                             (expected["final"], expected["axis"], expected["exit"], expected["waived"]), row["id"])
            self.assertEqual((post["top_pin"], post["bottom_space"]), (expected["tiers"]["top_pin"], expected["tiers"]["bottom_space"]), row["id"])
            self.assertEqual((record["initiator_charged"], record["responder_charged"]), expected["charges"], row["id"])
            self.assertEqual(post["initiator"], expected["initiator"], row["id"])
            checked += 1
        MEASURED["rows_checked_against_model"] = checked
        self.assertEqual(checked, PINNED_FIXTURE["families"]["exchange_grid"] + PINNED_FIXTURE["families"]["break_grid"])


# =====================================================================================================================
# 11. Replay, determinism, the pinned fixture
# =====================================================================================================================
class ReplayAndFixtureTests(unittest.TestCase):
    OPERATIONS = [{"op": "open_window"}, {"op": "submit", "window_id": 1, "fighter_id": TOP, "action_id": A["stabilize"],
                                          "response_id": R["bridge_defense"], "commitment": "MEDIUM", "response_commitment": "MEDIUM"},
                  {"op": "submit", "window_id": 1, "fighter_id": BOT, "action_id": "", "response_id": ""}, {"op": "bogus"},
                  {"op": "open_window", "duration": 0}, {"op": "submit", "window_id": 2, "fighter_id": BOT, "action_id": A["shrimp"],
                                                         "response_id": R["hip_block"]}, {"op": "open_window", "duration": "x"}]

    def test_a_replay_is_bit_identical_and_equals_the_live_run(self):
        first, second = O.replay(S.entry(), self.OPERATIONS), O.replay(S.entry(), self.OPERATIONS)
        self.assertEqual(O.canonical_bytes(first), O.canonical_bytes(second))
        live = fresh()
        live.open_window()
        live.submit(1, TOP, A["stabilize"], R["bridge_defense"], "MEDIUM", "MEDIUM")
        live.submit(1, BOT, "", "")
        live.open_window(0)
        live.submit(2, BOT, A["shrimp"], R["hip_block"])
        live.open_window("x")
        self.assertEqual(O.canonical_bytes(first["snapshot"]), snap_bytes(live))
        self.assertEqual([r["error"] for r in first["results"]], ["", "", "no_open_window", "unknown_operation", "", "", "invalid_duration"])

    def test_a_refused_entry_replays_to_the_same_refusal_and_nothing_else(self):
        outcome = O.replay(dict(S.entry(), initiator="middle"), self.OPERATIONS)
        self.assertEqual(outcome, {"entry_error": "invalid_initiator", "results": [], "snapshot": None})

    def test_a_json_round_trip_of_any_snapshot_continues_identically(self):
        for row in S.trajectory_rows(count=16, steps=30):
            snapshot = row["expected"]["snapshot"]
            twin = O.SideControl.from_snapshot(json.loads(json.dumps(snapshot)))
            self.assertEqual(snap_bytes(twin), O.canonical_bytes(snapshot))
            original = O.SideControl.from_snapshot(snapshot)
            self.assertEqual(twin.open_window(), original.open_window())
            self.assertEqual(snap_bytes(twin), snap_bytes(original))

    def test_every_trajectory_replays_identically_and_obeys_the_global_invariants(self):
        for row in S.trajectory_rows():
            again = O.replay(row["entry"], row["operations"])
            self.assertEqual(O.canonical_bytes(again["results"]), O.canonical_bytes(row["expected"]["results"]), row["id"])
            self.assertEqual(O.canonical_bytes(again["snapshot"]), O.canonical_bytes(row["expected"]["snapshot"]), row["id"])
            snapshot = again["snapshot"]
            self.assertTrue(O.legal_pair(snapshot["axis_tenths"], snapshot["band"]), row["id"])
            self.assertTrue(0 <= snapshot["top_pin"] <= 2 and 0 <= snapshot["bottom_space"] <= 2 and -40 <= snapshot["axis_tenths"] <= 40, row["id"])
            for pool in snapshot["fighters"].values():
                self.assertTrue(0 <= pool["stamina_current"] <= pool["stamina_maximum"], row["id"])
            ids = [r["window_id"] for r in snapshot["decision_history"]]
            self.assertEqual(ids, sorted(ids), row["id"])
            self.assertEqual(snapshot["exit_destination"] != "" or snapshot["clock_seconds"] == 0, O.SideControl.from_snapshot(snapshot).ended)

    def test_the_fixture_counts_and_digest_are_pinned_and_every_expectation_comes_from_a_refusal_free_family_or_a_declared_refusal(self):
        summary = S.summarize(rows=cached_rows())
        self.assertEqual(summary, PINNED_FIXTURE)
        # The pinned family sizes are re-derived here by arithmetic that does not run the oracle.
        legal_axes = [a for a in list(range(-40, 41, 5)) + [-31, -29, -21, -19, -11, -9, 9, 11, 19, 21, 29, 31]]
        legal_combos = sum(1 for a in legal_axes for b in (-2, -1, 0, 1, 2)
                           if (b == 0 and -12 < a < 12) or (b == 1 and 8 < a < 27) or (b == 2 and a > 23) or (b == -1 and -27 < a < -8) or (b == -2 and a < -23))
        self.assertEqual(PINNED_FIXTURE["families"]["band_update"], 81 * 5)  # every axis -40..40 x every band
        self.assertEqual(PINNED_FIXTURE["families"]["exchange_grid"], 6 * 3 * 9 * 9 * 10)  # actions x responses x tiers x commitments x stamina
        self.assertEqual(PINNED_FIXTURE["families"]["break_grid"], 4 * 3 * legal_combos * 3 * 3)  # break actions x responses x (axis, band) x tier x commitment
        # singles + compatible pairs: submit 16 + 103, attempt 9 + 32, context 7 + 21
        self.assertEqual(PINNED_FIXTURE["families"]["refusal"], (16 + 103) + (9 + 32) + (7 + 21))
        rows = S.refusal_rows()
        self.assertTrue(all(row["expected"]["result"]["error"] != "" for row in rows))
        self.assertTrue(all(O.canonical_bytes(row["expected"]["snapshot"]) == O.canonical_bytes(row["state"]) for row in rows))  # all atomic

    def test_the_fixture_is_byte_identical_under_three_distinct_hash_seeds(self):
        outputs = {}
        for seed in ("0", "1", "424242"):
            environment = dict(os.environ, PYTHONHASHSEED=seed)
            completed = subprocess.run([sys.executable, "-B", "-m", "oracles.side_control_v0_scenarios"], cwd=HERE, env=environment,
                                       capture_output=True, text=True, check=True)
            outputs[seed] = json.loads(completed.stdout)
        self.assertEqual(len({json.dumps(v, sort_keys=True) for v in outputs.values()}), 1, outputs)
        self.assertEqual(next(iter(outputs.values())), PINNED_FIXTURE)

    def test_the_generator_refuses_an_empty_fixture_and_writes_exactly_the_hashed_bytes(self):
        with self.assertRaises(SystemExit):
            S.summarize(rows=[])
        rows = S.entry_rows() + S.refusal_rows()[:5]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "side_control.jsonl")
            summary = S.summarize(rows=rows, path=path)
            with open(path, "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), summary["sha256"])


# =====================================================================================================================
# 12. Independence controls and test-only measurements
# =====================================================================================================================
def _parse(name):
    with open(os.path.join(HERE, "oracles", name), encoding="utf-8") as handle:
        return ast.parse(handle.read(), feature_version=(3, 11))


class IndependenceTests(unittest.TestCase):
    def test_the_oracle_imports_only_the_standard_library_and_never_a_half_guard_or_frozen_module(self):
        for name, allowed in (("side_control_v0.py", {"copy", "json", "math"}), ("side_control_v0_scenarios.py", {"copy", "hashlib", "json", "sys", ".", ".side_control_v0"})):
            imported = set()
            for node in ast.walk(_parse(name)):
                if isinstance(node, ast.Import):
                    imported |= {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    imported.add(("." if node.level else "") + (node.module or ""))
            self.assertTrue(imported <= allowed, (name, imported))
            self.assertFalse({i for i in imported if "half_guard" in i or "bjj_game" in i or "mount" in i.lower()}, name)

    def test_the_oracle_has_no_io_clock_randomness_environment_or_hidden_iteration_order(self):
        forbidden = {"open", "random", "time", "datetime", "os", "sys", "subprocess", "eval", "exec", "compile", "__import__", "bjj_game", "MountMatch",
                     "environ", "getenv", "hash", "id", "set_trace"}
        tree = _parse("side_control_v0.py")
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertEqual(used & forbidden, set())
        for node in ast.walk(tree):  # a set must never be iterated into an output (iteration order is hash-seed dependent)
            iterables = []
            if isinstance(node, (ast.For, ast.comprehension)):
                iterables.append(node.iter)
            for iterable in iterables:
                self.assertFalse(isinstance(iterable, ast.Set) or (isinstance(iterable, ast.Call) and getattr(iterable.func, "id", "") in ("set", "frozenset")))
        scenario_names = {n.id for n in ast.walk(_parse("side_control_v0_scenarios.py")) if isinstance(n, ast.Name)}
        self.assertEqual(scenario_names & {"random", "time", "datetime", "os", "subprocess", "bjj_game", "half_guard_v0"}, set())

    def test_no_godot_file_or_production_source_is_referenced_or_touched(self):
        for name in ("side_control_v0.py", "side_control_v0_scenarios.py"):
            with open(os.path.join(HERE, "oracles", name), encoding="utf-8") as handle:
                text = handle.read()
            self.assertNotIn("res://", text)
            self.assertNotIn(".gd", text)

    def test_this_test_module_is_discoverable_by_the_ci_loader(self):
        suite = unittest.defaultTestLoader.discover(HERE, pattern="test_side_control_oracle.py")
        self.assertGreater(sum(1 for _ in _flatten(suite)), 60)


class FrozenCrossCheckTests(unittest.TestCase):
    """Position-independent shared mechanics against the frozen reference (skipped without PYTHONPATH=src: a skip is NOT a pass)."""

    @classmethod
    def setUpClass(cls):
        try:
            from bjj_game.domain.action import Commitment
            from bjj_game.domain.stamina import StaminaBand, StaminaPool
            from bjj_game.engine.stamina import DEFAULT_EXHAUSTION_POLICY, DEFAULT_STAMINA_COST_POLICY
        except ImportError:
            raise unittest.SkipTest("frozen reference not importable (set PYTHONPATH=src); the frozen cross-check was NOT run")
        cls.Commitment, cls.Band, cls.Pool = Commitment, StaminaBand, StaminaPool
        cls.exhaustion, cls.costs = DEFAULT_EXHAUSTION_POLICY, DEFAULT_STAMINA_COST_POLICY

    def test_thresholds_bands_and_latch_transitions_match_the_frozen_pool(self):
        for maximum in (1, 3, 4, 7, 10, 20, 29, 30, 99, 100, 101, 1000, 2 ** 40, 2 ** 53 - 1):
            frozen = self.Pool(maximum, maximum)
            self.assertEqual((O.enter_threshold(maximum), O.recover_threshold(maximum)), (frozen.exhaustion_enter_threshold, frozen.exhaustion_recover_threshold))
        for maximum in (30, 100):
            for current in range(0, maximum + 1):
                frozen = self.Pool(current, maximum)
                mine = S.pool(current, maximum)
                self.assertEqual(O.stamina_band(mine), frozen.band.value, (current, maximum))
                for cost in (3, 7, 12):  # spending from every level reproduces the frozen latch, including hysteresis
                    spent = self.Pool(current, maximum)
                    spent.spend_up_to(cost)
                    twin = dict(mine)
                    O.spend_up_to(twin, cost)
                    self.assertEqual((twin["stamina_current"], twin["exhaustion_latched"]), (spent.current, spent.band is self.Band.EXHAUSTED), (current, cost))

    def test_funding_and_the_exhaustion_modifier_match_the_frozen_policies(self):
        for requested in ("LOW", "MEDIUM", "HIGH"):
            for available in range(0, 20):
                frozen = self.costs.effective_commitment(requested=self.Commitment[requested], available_stamina=available)
                self.assertEqual(O.determine(requested, available), frozen.name if frozen else "", (requested, available))
        for initiator in ("Fresh", "Exhausted"):
            for responder in ("Fresh", "Exhausted"):
                frozen = self.exhaustion.exchange_grade_modifier(initiator_band=self.Band(initiator), responder_band=self.Band(responder))
                self.assertEqual((-1 if initiator == "Exhausted" else 0) + (1 if responder == "Exhausted" else 0), frozen)


class StructuralSearchTests(unittest.TestCase):
    """TEST-ONLY MEASUREMENT, NOT PARITY EVIDENCE: cooperative reachability over the real oracle (MEDIUM commitments, passes allowed)."""

    def test_every_exit_is_reachable_under_cooperative_play_within_a_small_horizon(self):
        horizon = 6
        start = S.fresh(initial=3000).snapshot()
        frontier = {O.canonical_bytes(start): start}
        first_reached, explored = {}, 1
        for depth in range(1, horizon + 1):
            following = {}
            for snapshot in frontier.values():
                role = snapshot["initiator"]
                moves = [("", "")] + [(a, r) for a in O.ACTIONS if O.ACTIONS[a]["side"] == role for r in O.RESPONSES if O.RESPONSES[r]["side"] != role]
                for action, response in moves:
                    match = O.SideControl.from_snapshot(snapshot)
                    opened = match.open_window()
                    result = match.submit(opened["window_id"], snapshot["role_map"][role], action, response)
                    self.assertEqual(result["error"], "")
                    after = match.snapshot()
                    if after["exit_destination"]:
                        first_reached.setdefault(after["exit_destination"], depth)
                        continue
                    after["decision_history"] = []  # states are compared by position, not by how they were reached
                    following.setdefault(O.canonical_bytes(after), after)
            explored += len(following)
            frontier = following
        MEASURED["structural_search"] = {"horizon_windows": horizon, "states_explored": explored, "first_window_each_exit_is_reachable": first_reached}
        self.assertEqual(set(first_reached), set(O.EXIT_LABELS))


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


if __name__ == "__main__":
    unittest.main()
