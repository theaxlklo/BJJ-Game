"""Focused unit tests for the independent Half Guard v0 oracle (B1b checkpoint).

Expected values are hand-computed from ``GODOT_V1/docs/HALF_GUARD_V0_RULES.md`` and written out literally; the
oracle is never used to generate its own expectation except in *property* tests (invariants over its outputs) and
in the clearly labelled measured structural searches. The frozen Python reference is imported **only** to
cross-check position-independent settlement helpers; Half Guard itself never runs a Mount match.

Scope: oracle only. No GDScript Half Guard class exists yet. These tests describe a provisional v0 prototype baseline
(C1 raw grades); they are not a balance claim.
"""
import ast
import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from oracles import half_guard_v0 as O  # noqa: E402
from oracles import half_guard_v0_scenarios as S  # noqa: E402

A, R = S.A, S.R
TOP, BOT = S.TOP_ID, S.BOTTOM_ID
MEASURED = {"assertions": 0, "scenario_rows_checked": 0, "frozen_comparisons": 0, "searches": {}}
_DEPTH = [0]


def _counting(name):
    original = getattr(unittest.TestCase, name)

    def wrapper(self, *args, **kwargs):
        if _DEPTH[0] == 0:
            MEASURED["assertions"] += 1
        _DEPTH[0] += 1
        try:
            return original(self, *args, **kwargs)
        finally:
            _DEPTH[0] -= 1
    return wrapper


class Counted(unittest.TestCase):
    """TestCase that counts top-level assertion calls (measured, never declared)."""


for _name in ("assertEqual", "assertNotEqual", "assertTrue", "assertFalse", "assertIn", "assertNotIn", "assertIs",
              "assertIsNone", "assertIsNotNone", "assertLess", "assertLessEqual", "assertGreater",
              "assertGreaterEqual", "assertRaises", "assertCountEqual"):
    setattr(Counted, _name, _counting(_name))


def tearDownModule():
    print("\n[half_guard_oracle] measured: assertions=%d scenario_rows_checked=%d frozen_comparisons=%d searches=%s"
          % (MEASURED["assertions"], MEASURED["scenario_rows_checked"], MEASURED["frozen_comparisons"], MEASURED["searches"]))


def fresh(**kwargs):
    match, error = O.HalfGuard.from_entry(S.entry(**kwargs))
    assert not error, error
    return match


def at(**overrides):
    return O.HalfGuard.from_snapshot(S.state_with(**overrides))


def attempt(match, action, response, commitment="MEDIUM", response_commitment="MEDIUM"):
    return match.attempt(action, response, commitment, response_commitment)


# =====================================================================================================
class TableTests(Counted):
    LITERAL_C1 = {
        ("top", "crossface", "hip_frame"): 1, ("top", "crossface", "underhook_fight"): -1, ("top", "crossface", "knee_shield"): 0,
        ("top", "flatten", "hip_frame"): -1, ("top", "flatten", "underhook_fight"): 1, ("top", "flatten", "knee_shield"): 1,
        ("top", "knee_slice", "hip_frame"): 1, ("top", "knee_slice", "underhook_fight"): 2, ("top", "knee_slice", "knee_shield"): -2,
        ("bottom", "underhook", "head_control"): -1, ("bottom", "underhook", "hip_pressure"): 0, ("bottom", "underhook", "knee_pin"): 1,
        ("bottom", "recover_guard", "head_control"): 2, ("bottom", "recover_guard", "hip_pressure"): 1, ("bottom", "recover_guard", "knee_pin"): -2,
    }
    PREFIX = {"top": "half_guard.top.", "bottom": "half_guard.bottom."}
    RESPONSE_PREFIX = {"hip_frame": "half_guard.bottom_response.", "underhook_fight": "half_guard.bottom_response.",
                       "knee_shield": "half_guard.bottom_response.", "head_control": "half_guard.top_response.",
                       "hip_pressure": "half_guard.top_response.", "knee_pin": "half_guard.top_response."}

    def test_catalog_ids_sides_and_break_capability(self):
        self.assertEqual(set(O.TOP_ACTIONS), {"half_guard.top.crossface", "half_guard.top.flatten", "half_guard.top.knee_slice"})
        self.assertEqual(set(O.BOTTOM_ACTIONS), {"half_guard.bottom.underhook", "half_guard.bottom.recover_guard"})
        self.assertEqual(set(O.BOTTOM_RESPONSES), {"half_guard.bottom_response." + n for n in ("hip_frame", "underhook_fight", "knee_shield")})
        self.assertEqual(set(O.TOP_RESPONSES), {"half_guard.top_response." + n for n in ("head_control", "hip_pressure", "knee_pin")})
        self.assertEqual(set(O.BREAK_CAPABLE), {"half_guard.top.knee_slice", "half_guard.bottom.recover_guard"})
        self.assertEqual(set(O.GOVERNED), {"half_guard.bottom_response.knee_shield", "half_guard.top_response.knee_pin"})
        self.assertEqual(O.GOVERNED["half_guard.bottom_response.knee_shield"], "bottom_frame")
        self.assertEqual(O.GOVERNED["half_guard.top_response.knee_pin"], "top_base")
        self.assertEqual(O.EXIT_DESTINATION_IDS, {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"})

    def test_all_fifteen_raw_cells_are_the_c1_table(self):
        flat = {(side, a.rsplit(".", 1)[1], r.rsplit(".", 1)[1]): g
                for side, row in O.RAW.items() for a, cells in row.items() for r, g in cells.items()}
        self.assertEqual(len(flat), 15)
        self.assertEqual(flat, self.LITERAL_C1)
        # C1: the only change from the proposal-stage table is Knee Slice vs Hip Frame (was 0, is +1).
        self.assertEqual(flat[("top", "knee_slice", "hip_frame")], 1)

    def test_every_matchup_at_the_neutral_entry_state_resolves_to_the_raw_grade(self):
        for (side, action, response), raw in self.LITERAL_C1.items():
            match = at(initiator=side)
            result = attempt(match, self.PREFIX[side] + action, self.RESPONSE_PREFIX[response] + response)
            self.assertEqual(result["error"], "")
            self.assertEqual(result["raw_grade"], raw)
            self.assertEqual(result["final_grade"], raw)  # Partial/Partial, fresh, MEDIUM/MEDIUM: no modifier applies
            delta = 10 * raw if side == "top" else -10 * raw
            self.assertEqual(result["axis_proposed"], 5 + delta)
            MEASURED["scenario_rows_checked"] += 1

    def test_c1_knee_slice_against_hip_frame(self):
        match = fresh()
        result = attempt(match, A["ks"], R["hf"])
        self.assertEqual((result["raw_grade"], result["final_grade"], result["axis_after"], result["band_after"]), (1, 1, 15, 1))
        self.assertEqual(match.snapshot()["history"]["raw_grade_history"], ["Success"])
        # With Knee Shield the same technique is still the decisive failure.
        self.assertEqual(attempt(fresh(), A["ks"], R["ks"])["final_grade"], -2)


# =====================================================================================================
class AxisAndBandTests(Counted):
    def test_initial_band_over_all_axes(self):
        for axis in range(-40, 41):
            if -9 <= axis <= 9:
                expected = 0
            elif 10 <= axis <= 24:
                expected = 1
            elif 25 <= axis <= 40:
                expected = 2
            elif -24 <= axis <= -10:
                expected = -1
            else:
                expected = -2
            self.assertEqual(O.initial_band(axis), expected)

    HYSTERESIS = [  # (from band, axis, expected band) at and one tenth either side of every threshold
        (0, 12, 1), (0, 11, 0), (1, 27, 2), (1, 26, 1), (-1, -8, 0), (-1, -9, -1), (-2, -23, -1), (-2, -24, -2),
        (2, 23, 1), (2, 24, 2), (1, 8, 0), (1, 9, 1), (0, -12, -1), (0, -11, 0), (-1, -27, -2), (-1, -26, -1),
        # multi-band jumps
        (0, 30, 2), (0, 40, 2), (2, -30, -2), (-2, 40, 2), (1, -40, -2), (-1, 12, 1), (2, 0, 0), (-2, 0, 0),
        # hysteresis holds the band inside the overlap
        (1, 10, 1), (0, 10, 0), (2, 25, 2), (1, 25, 1), (-1, -10, -1), (0, -10, 0),
    ]

    def test_every_hysteresis_rule_and_jump(self):
        for band, axis, expected in self.HYSTERESIS:
            self.assertEqual(O.band_update(axis, band), expected)

    def test_legal_pairs_and_closure(self):
        for axis in range(-40, 41):
            legal = {0: -11 <= axis <= 11, 1: 9 <= axis <= 26, 2: 24 <= axis, -1: -26 <= axis <= -9, -2: axis <= -24}
            for band in (-2, -1, 0, 1, 2):
                self.assertEqual(O.legal_pair(axis, band), legal[band])
                # every start band, even an illegal one, settles on a legal pair
                self.assertTrue(O.legal_pair(axis, O.band_update(axis, band)))
            self.assertTrue(O.legal_pair(axis, O.initial_band(axis)))
        self.assertFalse(O.legal_pair(5, 3))   # an unknown band is never legal (the axis range is a separate context check)
        self.assertTrue(O.validate_context(S.state_with(axis_tenths=41, band=2)) == "invalid_half_guard_context")

    def test_entry_values_and_authority(self):
        match = fresh()
        fields = match.state_fields()
        self.assertEqual((fields["axis_tenths"], fields["band"], fields["band_name"], fields["initiator"]), (5, 0, "CONTESTED", "top"))
        self.assertEqual(fields["authority"], TOP)
        for axis, expected in ((0, ""), (1, TOP), (-1, BOT), (40, TOP), (-40, BOT)):
            self.assertEqual(at(axis_tenths=axis, band=O.initial_band(axis)).state_fields()["authority"], expected)
        self.assertEqual(fields["axis"], 0.5)
        self.assertEqual(O.BAND_NAMES, {-2: "BOTTOM_CONTROL", -1: "BOTTOM_EDGE", 0: "CONTESTED", 1: "TOP_EDGE", 2: "TOP_CONTROL"})

    def test_clamping_at_the_axis_limits_without_exit(self):
        top = at(axis_tenths=35, band=2)
        result = attempt(top, A["cf"], R["hf"])  # +1 -> proposed 45 -> clamp 40
        self.assertEqual((result["axis_proposed"], result["axis_after"], result["exit_destination"]), (45, 40, ""))
        bottom = at(axis_tenths=-35, band=-2, initiator="bottom")
        result = attempt(bottom, A["uh"], R["kp"])  # +1 for Bottom -> proposed -45 -> clamp -40
        self.assertEqual((result["axis_proposed"], result["axis_after"], result["exit_destination"]), (-45, -40, ""))
        self.assertEqual(O.HalfGuard.from_snapshot(bottom.snapshot()).snapshot()["axis_tenths"], -40)

    def test_axis_band_grid_matches_literal_threshold_rule(self):
        for row in S.band_rows():
            if row["family"] == "band_update":
                expected = row["band"]
                axis = row["axis"]
                # an independent re-statement: apply the eight rules until none fires
                while True:
                    if expected == 0 and axis >= 12:
                        expected = 1
                    elif expected == 1 and axis >= 27:
                        expected = 2
                    elif expected == -1 and axis >= -8:
                        expected = 0
                    elif expected == -2 and axis >= -23:
                        expected = -1
                    elif expected == 2 and axis <= 23:
                        expected = 1
                    elif expected == 1 and axis <= 8:
                        expected = 0
                    elif expected == 0 and axis <= -12:
                        expected = -1
                    elif expected == -1 and axis <= -27:
                        expected = -2
                    else:
                        break
                self.assertEqual(row["expected"], expected)
                MEASURED["scenario_rows_checked"] += 1


# =====================================================================================================
class EntryTests(Counted):
    EXPECTED_REFUSALS = [
        "entry_not_a_dictionary", "entry_malformed", "entry_malformed", "entry_malformed", "entry_malformed", "entry_malformed",
        "entry_malformed", "entry_malformed", "invalid_fighter_id", "invalid_fighter_id", "invalid_fighter_id", "invalid_fighter_id",
        "fighters_mismatch", "invalid_stamina_maximum", "invalid_stamina_maximum", "invalid_stamina_current", "invalid_stamina_current",
        "inconsistent_exhaustion_latch", "inconsistent_exhaustion_latch", "invalid_behavior_remainder", "invalid_clock", "invalid_clock",
        "invalid_clock", "invalid_window_id", "invalid_interval", "invalid_interval",
        "invalid_clock",            # precedence: clock before window id before interval
        "invalid_fighter_id",       # precedence: fighter ids before stamina
    ]

    def test_every_refusal_code_and_precedence(self):
        requests = S.refusal_entries()
        self.assertEqual(len(requests), len(self.EXPECTED_REFUSALS))
        for request, expected in zip(requests, self.EXPECTED_REFUSALS):
            before = copy.deepcopy(request)
            self.assertEqual(O.validate_entry(request), expected)
            self.assertEqual(O.HalfGuard.from_entry(request), (None, expected))
            self.assertEqual(request, before)  # pure: the request is never modified
            MEASURED["scenario_rows_checked"] += 1

    def test_valid_entries_build_state_by_fighter_id(self):
        match = fresh(top_current=40, bottom_current=20, last_issued=7, clock=123, interval=9, top_remainder=-3, bottom_remainder=11)
        state = match.snapshot()
        self.assertEqual(state["fighters"][TOP], {"stamina_current": 40, "stamina_maximum": 100, "exhaustion_latched": False, "behavior_remainder_units": -3})
        self.assertEqual(state["fighters"][BOT], {"stamina_current": 20, "stamina_maximum": 100, "exhaustion_latched": True, "behavior_remainder_units": 11})
        self.assertEqual((state["window_id"], state["clock_seconds"], state["initial_clock"], state["interval_seconds"]), (7, 123, 123, 9))
        self.assertEqual((state["top_base"], state["bottom_frame"], state["initiator"], state["window_open"], state["exit_destination"]), (1, 1, "top", False, ""))
        self.assertEqual(state["history"], O._empty_history())

    def test_swapped_role_map_follows_the_fighter_id(self):
        base = fresh(top_current=40, bottom_current=20)
        swapped = fresh(top_current=40, bottom_current=20, swap=True)
        self.assertEqual(base.snapshot()["fighters"], swapped.snapshot()["fighters"])  # state is keyed by id
        self.assertEqual(swapped.snapshot()["role_map"], {"top": BOT, "bottom": TOP})
        fields = swapped.state_fields()
        self.assertEqual((fields["top_stamina"], fields["bottom_stamina"]), (20, 40))
        self.assertEqual((fields["top_latched"], fields["bottom_latched"]), (True, False))
        self.assertEqual(fields["authority"], BOT)  # axis +5 favors whoever holds the Top role

    def test_latch_consistency_boundaries_by_capacity(self):
        table = {1: (0, 1), 2: (0, 1), 3: (0, 2), 4: (1, 2), 7: (1, 3), 20: (5, 7), 37: (9, 13), 64: (16, 23), 100: (25, 35)}
        for capacity, (enter, recover) in table.items():
            self.assertEqual((O.enter_threshold(capacity), O.recover_threshold(capacity)), (enter, recover))
            for current in range(0, min(capacity, 100) + 1):
                forced_true, forced_false = current <= enter, current >= recover
                for latched in (False, True):
                    request = S.entry(maximum=capacity, top_current=current, bottom_current=current)
                    request["fighters"][TOP]["exhaustion_latched"] = latched
                    request["fighters"][BOT]["exhaustion_latched"] = latched
                    error = O.validate_entry(request)
                    wrong = (forced_true and not latched) or (forced_false and latched)
                    self.assertEqual(error, "inconsistent_exhaustion_latch" if wrong else "")

    def test_literal_hysteresis_model(self):
        # capacity 100: enter at <= 25, recover at >= 35
        self.assertFalse(O.latch_after(26, 100, False))
        self.assertTrue(O.latch_after(25, 100, False))
        self.assertTrue(O.latch_after(34, 100, True))
        self.assertFalse(O.latch_after(35, 100, True))
        self.assertTrue(O.latch_after(30, 100, True))   # between the thresholds the state is remembered
        self.assertFalse(O.latch_after(30, 100, False))
        self.assertTrue(O.latch_after(0, 1, False))
        self.assertFalse(O.latch_after(1, 1, True))
        big = O.MAXIMUM_EXACT
        self.assertEqual(O.enter_threshold(big), 2251799813685247)
        self.assertEqual(O.recover_threshold(big), 3152519739159347)


# =====================================================================================================
class GradePipelineTests(Counted):
    def test_saturation_order_raw_minus_two_with_unprepared_attacker_and_defender(self):
        # raw -2, attacker None (-1 -> stays -2), defender None (+2) -> 0, NOT -1.
        result = attempt(at(top_base=0, bottom_frame=0), A["ks"], R["ks"])
        self.assertEqual((result["raw_grade"], result["grade_after_attack"], result["grade_after_defense"], result["final_grade"]), (-2, -2, 0, 0))
        self.assertEqual((result["attack_readiness_shift"], result["defense_readiness_shift"], result["defense_strength_tier"]), (-1, 2, 0))

    def test_prepared_attacker_against_unprepared_defender_succeeds(self):
        match = at(top_base=2, bottom_frame=0)
        result = attempt(match, A["ks"], R["ks"])
        self.assertEqual((result["grade_after_attack"], result["grade_after_defense"], result["final_grade"]), (-1, 1, 1))
        self.assertEqual((result["axis_after"], result["tiers_after"]), (15, {"top_base": 1, "bottom_frame": 0}))
        self.assertEqual(result["readiness_changes"], ["top_base:Ready->Partial:knee_slice"])

    def test_defense_ready_is_stronger_only_below_the_saturation_floor(self):
        # Ready defender shifts -1 toward the defender: Crossface vs Knee Shield 0 -> -1; Flatten +1 -> 0.
        self.assertEqual(attempt(at(bottom_frame=2), A["cf"], R["ks"])["final_grade"], -1)
        self.assertEqual(attempt(at(bottom_frame=2), A["fl"], R["ks"])["final_grade"], 0)
        # raw -2 stays -2
        self.assertEqual(attempt(at(bottom_frame=2), A["ks"], R["ks"])["final_grade"], -2)

    def test_non_governed_responses_ignore_readiness(self):
        for tier in range(3):
            self.assertEqual(attempt(at(bottom_frame=tier), A["cf"], R["hf"])["defense_readiness_shift"], 0)
            self.assertEqual(attempt(at(bottom_frame=tier), A["cf"], R["uf"])["final_grade"], -1)
            self.assertEqual(attempt(at(top_base=tier, initiator="bottom"), A["uh"], R["hc"])["defense_strength_tier"], None)

    def test_attack_readiness_applies_only_to_break_capable_actions(self):
        for tier, shift in ((0, -1), (1, 0), (2, 1)):
            self.assertEqual(attempt(at(top_base=tier), A["ks"], R["hf"])["attack_readiness_shift"], shift)
            self.assertEqual(attempt(at(bottom_frame=tier, initiator="bottom"), A["rg"], R["hp"])["attack_readiness_shift"], shift)
            self.assertEqual(attempt(at(top_base=tier), A["cf"], R["hf"])["attack_readiness_shift"], 0)
        # the attacker's own track is read, never the opponent's
        self.assertEqual(attempt(at(top_base=2, bottom_frame=0), A["ks"], R["hf"])["attack_readiness_shift"], 1)

    def test_positional_modifier_against_the_opposing_control_band(self):
        top_against_band = attempt(at(axis_tenths=-30, band=-2), A["cf"], R["hf"])
        self.assertEqual((top_against_band["positional_modifier"], top_against_band["final_grade"]), (-1, 0))
        bottom_against_band = attempt(at(axis_tenths=30, band=2, initiator="bottom"), A["uh"], R["kp"])
        self.assertEqual((bottom_against_band["positional_modifier"], bottom_against_band["final_grade"]), (-1, 0))
        # not against its own control band, nor against the edge band
        self.assertEqual(attempt(at(axis_tenths=30, band=2), A["cf"], R["hf"])["positional_modifier"], 0)
        self.assertEqual(attempt(at(axis_tenths=-15, band=-1), A["cf"], R["hf"])["positional_modifier"], 0)

    def test_exhaustion_modifiers(self):
        self.assertEqual(attempt(at(top_current=20), A["cf"], R["hf"])["final_grade"], 0)               # attacker Exhausted: +1 -> 0
        self.assertEqual(attempt(at(bottom_current=20), A["cf"], R["uf"])["final_grade"], 0)            # responder Exhausted: -1 -> 0
        both = attempt(at(top_current=20, bottom_current=20), A["cf"], R["hf"])
        self.assertEqual((both["exhaustion_modifier"], both["final_grade"]), (0, 1))
        self.assertEqual((both["initiator_band"], both["responder_band"]), ("Exhausted", "Exhausted"))

    def test_magnitude_and_undercommitment_in_sequence(self):
        # HIGH presses a Success up: Crossface vs Hip Frame +1 -> +2; a Failure down: Flatten vs Hip Frame -1 -> -2, then +1 undercommitment.
        self.assertEqual(attempt(fresh(), A["cf"], R["hf"], "HIGH", "MEDIUM")["final_grade"], 2)
        flatten = attempt(fresh(), A["fl"], R["hf"], "HIGH", "MEDIUM")
        self.assertEqual((flatten["magnitude_modifier"], flatten["undercommitment_modifier"], flatten["final_grade"]), (-1, 1, -1))
        # LOW softens a Strong Success: Knee Slice vs Underhook Fight +2 -> +1; and a Strong Failure is lifted.
        self.assertEqual(attempt(fresh(), A["ks"], R["uf"], "LOW", "LOW")["final_grade"], 1)
        # A LOW defender is counted as unprepared (strength tier None, +2): raw -2 -> 0, so the Strong Failure is lifted to Contested here.
        self.assertEqual(attempt(fresh(), A["ks"], R["ks"], "LOW", "LOW")["final_grade"], 0)
        # responder funded below the initiator gives +1; equal or above does not
        self.assertEqual(attempt(fresh(), A["cf"], R["uf"], "MEDIUM", "LOW")["undercommitment_modifier"], 1)
        self.assertEqual(attempt(fresh(), A["cf"], R["uf"], "MEDIUM", "HIGH")["undercommitment_modifier"], 0)
        self.assertEqual(attempt(fresh(), A["cf"], R["uf"], "MEDIUM", "MEDIUM")["undercommitment_modifier"], 0)

    def test_unfunded_initiator_inherits_the_low_ceiling_and_waives_nothing_for_grading(self):
        result = attempt(at(top_current=2), A["ks"], R["uf"], "MEDIUM", "MEDIUM")
        self.assertEqual((result["initiator_effective"], result["exhaustion_modifier"], result["grade_after_exhaustion"], result["final_grade"]), ("", -1, 1, 1))

    def test_best_final_grade_from_a_decisive_counter_by_readiness(self):
        """Fresh derivation over the C1 baseline: no stamina effect / with every exhaustion, magnitude, commitment lift.
        The defender is assumed to make the defensive effort (response commitment MEDIUM or HIGH); a LOW response is tested separately."""
        def best(attacker_tier, defender_tier, lifts):
            top = -9
            for commitment in (O.COMMITMENTS if lifts else ("MEDIUM",)):
                for response_commitment in (("MEDIUM", "HIGH") if lifts else ("MEDIUM",)):
                    for init_cur, resp_cur in (((100, 100), (20, 100), (100, 20), (20, 20), (2, 100)) if lifts else ((100, 100),)):
                        match = at(top_base=attacker_tier, bottom_frame=defender_tier, top_current=init_cur, bottom_current=resp_cur)
                        top = max(top, attempt(match, A["ks"], R["ks"], commitment, response_commitment)["final_grade"])
            return top
        # Hand-checked cells: (attacker Partial, defender Partial, lifts): raw -2, defense 0, responder Exhausted +1 -> -1, HIGH presses a
        # Failure to -2, undercommitment +1 -> -1 (no coherent combination reaches 0). (Ready, Partial, lifts): -1 +1 -> 0, +1 undercommitment -> +1.
        # The B1a proposal listed 0 for the Ready/Partial-defender columns because it also combined stamina lifts that cannot co-occur
        # (for example an unfunded attacker who is not Exhausted); the oracle's coherent state space gives -1.
        expected = {(0, 2): (-2, -1), (0, 1): (-2, -1), (0, 0): (0, 2), (1, 2): (-2, -1), (1, 1): (-2, -1), (1, 0): (0, 2),
                    (2, 2): (-2, -1), (2, 1): (-1, 1), (2, 0): (1, 2)}
        for (attacker, defender), (plain, lifted) in expected.items():
            self.assertEqual(best(attacker, defender, False), plain)
            self.assertEqual(best(attacker, defender, True), lifted)

    def test_a_low_response_is_unprepared_even_against_a_ready_structure(self):
        # Ready frame, attacker with no base: raw -2, attacker None -1 (stays -2); LOW response -> strength None -> +2 -> 0; undercommitment +1 -> +1.
        result = attempt(at(top_base=0, bottom_frame=2), A["ks"], R["ks"], "MEDIUM", "LOW")
        self.assertEqual((result["defense_strength_tier"], result["defense_readiness_shift"], result["final_grade"]), (0, 2, 1))
        # The same defender at MEDIUM keeps the Ready shift (-1): -2 stays -2.
        medium = attempt(at(top_base=0, bottom_frame=2), A["ks"], R["ks"], "MEDIUM", "MEDIUM")
        self.assertEqual((medium["defense_strength_tier"], medium["defense_readiness_shift"], medium["final_grade"]), (2, -1, -2))

    def test_funding_boundaries_literal(self):
        def literal(requested, current):
            if requested == "HIGH" and current >= 12:
                return "HIGH"
            if requested in ("HIGH", "MEDIUM") and current >= 7:
                return "MEDIUM"
            if current >= 3:
                return "LOW"
            return ""
        for requested in ("LOW", "MEDIUM", "HIGH"):
            for current in range(0, 16):
                self.assertEqual(O.determine(requested, current)[0], literal(requested, current))
        self.assertEqual({t: O.COSTS[t] for t in O.COMMITMENTS}, {"LOW": 3, "MEDIUM": 7, "HIGH": 12})
        self.assertEqual(O.determine("HIGH", 11), ("MEDIUM", 7))
        self.assertEqual(O.determine("HIGH", 2), ("", 0))


# =====================================================================================================
class ReadinessTests(Counted):
    NEUTRAL_CASES = [  # (initiator side, action, response, tiers (base, frame) before, tiers after, history) -- MEDIUM/MEDIUM, fresh
        ("top", "cf", "hf", (1, 1), (1, 0), ["bottom_frame:Partial->None:crossface"]),        # +1: weakens the Bottom frame
        ("top", "cf", "uf", (1, 1), (1, 1), []),                                              # -1: nothing
        ("top", "cf", "ks", (1, 1), (1, 1), []),                                              # 0, contested: no wear, no build
        ("top", "fl", "uf", (1, 1), (2, 1), ["top_base:Partial->Ready:flatten"]),            # +1: establishes
        ("top", "fl", "ks", (1, 1), (2, 0), ["bottom_frame:Partial->None:flatten", "top_base:Partial->Ready:flatten"]),  # wear, then build
        ("top", "fl", "hf", (1, 1), (1, 1), []),                                              # -1
        ("top", "ks", "hf", (1, 1), (1, 1), []),                                              # +1, but Knee Slice builds nothing
        ("top", "ks", "ks", (1, 1), (1, 0), ["bottom_frame:Partial->None:knee_slice"]),       # -2: the decisive defense wears the frame
        ("bottom", "uh", "kp", (1, 1), (0, 2), ["top_base:Partial->None:underhook", "bottom_frame:Partial->Ready:underhook"]),
        ("bottom", "uh", "hc", (1, 1), (1, 1), []),
        ("bottom", "rg", "hp", (1, 1), (0, 1), ["top_base:Partial->None:recover_guard"]),
        ("bottom", "rg", "hc", (1, 1), (0, 1), ["top_base:Partial->None:recover_guard"]),
        ("bottom", "rg", "kp", (1, 1), (0, 1), ["top_base:Partial->None:recover_guard"]),    # -2: worn by the Knee Pin response
    ]

    def test_build_weaken_wear_transitions_at_neutral(self):
        for side, a, r, before, after, history in self.NEUTRAL_CASES:
            match = at(top_base=before[0], bottom_frame=before[1], initiator=side)
            result = attempt(match, A[a], R[r])
            self.assertEqual((result["tiers_after"]["top_base"], result["tiers_after"]["bottom_frame"]), after)
            self.assertEqual(result["readiness_changes"], history)
            self.assertEqual(match.snapshot()["history"]["readiness_change_history"], history)

    def test_floors_and_ceilings_record_no_change(self):
        top_ceiling = attempt(at(top_base=2), A["fl"], R["uf"])
        self.assertEqual((top_ceiling["tiers_after"]["top_base"], top_ceiling["readiness_changes"]), (2, []))
        frame_floor = attempt(at(bottom_frame=0), A["cf"], R["hf"])
        self.assertEqual((frame_floor["tiers_after"]["bottom_frame"], frame_floor["readiness_changes"]), (0, []))
        frame_ceiling = attempt(at(bottom_frame=2, top_base=1, initiator="bottom"), A["uh"], R["hc"])  # -1: no build
        self.assertEqual(frame_ceiling["tiers_after"]["bottom_frame"], 2)
        ceiling_success = attempt(at(bottom_frame=2, initiator="bottom"), A["uh"], R["kp"])  # success at the ceiling
        self.assertEqual(ceiling_success["tiers_after"]["bottom_frame"], 2)

    def test_consumption_of_a_prepared_technique_at_ready_whatever_the_result(self):
        for action, response, own_track, side in ((A["ks"], R["hf"], "top_base", "top"), (A["ks"], R["ks"], "top_base", "top"),
                                                  (A["rg"], R["hc"], "bottom_frame", "bottom"), (A["rg"], R["kp"], "bottom_frame", "bottom")):
            ready = attempt(at(**{own_track: 2, "initiator": side}), action, response)
            self.assertTrue(any(c.startswith(own_track + ":Ready->Partial") for c in ready["readiness_changes"]))
            partial = attempt(at(**{own_track: 1, "initiator": side}), action, response)
            self.assertFalse(any(c.startswith(own_track + ":Ready->") for c in partial["readiness_changes"]))
            none = attempt(at(**{own_track: 0, "initiator": side}), action, response)
            self.assertFalse(any(c.startswith(own_track + ":None->") for c in none["readiness_changes"]))

    def test_non_prepared_techniques_never_consume(self):
        for action, response, track, side in ((A["cf"], R["uf"], "top_base", "top"), (A["fl"], R["hf"], "top_base", "top"),
                                              (A["uh"], R["hc"], "bottom_frame", "bottom")):
            result = attempt(at(**{track: 2, "initiator": side}), action, response)  # failed attempts: no build either
            self.assertEqual(result["tiers_after"][track], 2)
            self.assertEqual(result["readiness_changes"], [])

    def test_double_touch_in_one_exchange_follows_the_update_order(self):
        # HIGH Crossface vs a Ready Knee Shield defender who is Exhausted but still funded MEDIUM: final +1.
        match = at(bottom_frame=2, bottom_current=20)
        result = attempt(match, A["cf"], R["ks"], "HIGH", "MEDIUM")
        self.assertEqual(result["final_grade"], 1)
        self.assertEqual(result["readiness_changes"], ["bottom_frame:Ready->Partial:crossface", "bottom_frame:Partial->None:crossface"])
        self.assertEqual(result["tiers_after"]["bottom_frame"], 0)

    def test_wear_depends_on_commitment_and_outcome(self):
        def frame_after(response_commitment, bottom_current, **tiers):
            match = at(bottom_current=bottom_current, **tiers)
            return attempt(match, A["ks"], R["ks"], "MEDIUM", response_commitment)["tiers_after"]["bottom_frame"]
        self.assertEqual(frame_after("MEDIUM", 100), 0)    # decisive defense at MEDIUM wears (final -2... != 0)
        self.assertEqual(frame_after("HIGH", 100), 1)      # HIGH paid and the defense succeeded: preserved
        self.assertEqual(frame_after("LOW", 100), 1)       # LOW: counted as None, no wear
        self.assertEqual(frame_after("HIGH", 6), 1)        # HIGH funded down to LOW: no wear
        self.assertEqual(frame_after("HIGH", 2), 1)        # unfunded responder: no wear
        # Failed defense (Flatten +1 vs Knee Shield) wears at HIGH too.
        failed = attempt(at(), A["fl"], R["ks"], "MEDIUM", "HIGH")
        self.assertEqual(failed["final_grade"], 1)
        self.assertEqual(failed["tiers_after"]["bottom_frame"], 0)
        # Contested result (Crossface vs Knee Shield 0): no wear at MEDIUM or HIGH. (LOW is excluded on purpose: a LOW defense is
        # counted as unprepared, so the same Crossface *succeeds* and weakens the frame as a builder, not as wear.)
        for commitment in ("MEDIUM", "HIGH"):
            self.assertEqual(attempt(at(), A["cf"], R["ks"], "MEDIUM", commitment)["tiers_after"]["bottom_frame"], 1)
        low = attempt(at(), A["cf"], R["ks"], "MEDIUM", "LOW")
        self.assertEqual((low["final_grade"], low["tiers_after"]["bottom_frame"], low["readiness_changes"]), (2, 0, ["bottom_frame:Partial->None:crossface"]))

    def test_readiness_invariants_over_the_whole_exchange_grid(self):
        rows = S.exchange_rows()
        for row in rows:
            result = row["expected"]
            self.assertEqual(result["error"], "")
            before, after = result["tiers_before"], result["tiers_after"]
            action, side = result["action_id"], result["initiator"]
            for track in ("top_base", "bottom_frame"):
                self.assertTrue(0 <= after[track] <= 2)
            own = O.OWN_TRACK[side]
            opponent = "bottom_frame" if side == "top" else "top_base"
            allowed = {opponent} if action not in O.BREAK_CAPABLE else set()
            if action in O.BUILD:
                allowed.add(O.BUILD[action][0])
            if action in O.BREAK_CAPABLE:
                allowed.add(own)
            if result["response_id"] in O.GOVERNED:
                allowed.add(O.GOVERNED[result["response_id"]])
            for track in ("top_base", "bottom_frame"):
                if after[track] != before[track]:
                    self.assertIn(track, allowed)
            if result["final_grade"] < 1 and action not in O.BREAK_CAPABLE:
                self.assertEqual(after[own], before[own])
            self.assertEqual(result["readiness_changes"] == [], after == before)
            MEASURED["scenario_rows_checked"] += 1
        MEASURED["searches"]["exchange_grid_rows"] = len(rows)


# =====================================================================================================
class StaminaAndRuleOneTests(Counted):
    def test_charges_initiator_then_responder_and_updates_latches(self):
        match = at(top_current=30, bottom_current=40)
        result = attempt(match, A["cf"], R["hf"], "MEDIUM", "MEDIUM")
        self.assertEqual((result["initiator_charged"], result["responder_charged"], result["responder_waived"]), (7, 7, 0))
        fields = match.state_fields()
        self.assertEqual((fields["top_stamina"], fields["bottom_stamina"]), (23, 33))
        self.assertEqual((fields["top_latched"], fields["bottom_latched"]), (True, False))  # 23 <= 25 latches; 33 stays unlatched

    def test_a_latched_fighter_stays_latched_between_thresholds_and_unlatching_needs_recovery_that_does_not_exist(self):
        match = at(top_current=30)
        self.assertTrue(match.snapshot()["fighters"][TOP]["exhaustion_latched"] is False)
        attempt(match, A["cf"], R["hf"], "MEDIUM", "MEDIUM")   # 30 -> 23: latched
        self.assertTrue(match.snapshot()["fighters"][TOP]["exhaustion_latched"])
        for _ in range(2):
            match.s["initiator"] = "top"
            attempt(match, A["cf"], R["hf"], "LOW", "LOW")
        self.assertTrue(match.snapshot()["fighters"][TOP]["exhaustion_latched"])

    RULE_ONE_CASES = [
        # (attacker stamina, requested attacker, defender stamina, requested defender) -> (resp_eff, charged, waived, paid, frame after)
        ((2, "HIGH", 100, "HIGH"), ("HIGH", 0, 12, False, 0)),    # unfunded attacker: HIGH waived -> NOT preserved (wear as MEDIUM)
        ((5, "LOW", 100, "HIGH"), ("HIGH", 12, 0, True, 1)),      # funded attacker: HIGH paid -> preserved
        ((100, "MEDIUM", 100, "HIGH"), ("HIGH", 12, 0, True, 1)),
        ((100, "MEDIUM", 11, "HIGH"), ("MEDIUM", 7, 0, True, 0)),  # HIGH funded down to MEDIUM: gap 5, wears
        ((100, "MEDIUM", 7, "HIGH"), ("MEDIUM", 7, 0, True, 0)),
        ((100, "MEDIUM", 6, "HIGH"), ("LOW", 3, 0, True, 1)),      # LOW: counted as None, no wear
        ((100, "MEDIUM", 2, "HIGH"), ("", 0, 0, False, 1)),        # unfunded responder
        ((2, "MEDIUM", 100, "MEDIUM"), ("MEDIUM", 0, 7, False, 0)),  # MEDIUM waived still wears
        ((2, "HIGH", 100, "LOW"), ("LOW", 0, 3, False, 1)),
    ]

    def test_rule_one_waiver_and_the_paid_effort_distinction(self):
        for (attacker_stamina, attacker_request, defender_stamina, defender_request), expected in self.RULE_ONE_CASES:
            match = at(top_current=attacker_stamina, bottom_current=defender_stamina)
            result = attempt(match, A["ks"], R["ks"], attacker_request, defender_request)
            self.assertEqual((result["responder_effective"], result["responder_charged"], result["responder_waived"], result["paid_effort"],
                              result["tiers_after"]["bottom_frame"]), expected)
            self.assertEqual(match.snapshot()["fighters"][BOT]["stamina_current"], defender_stamina - expected[1])
            self.assertEqual(match.snapshot()["history"]["response_waived_history"], [expected[2]])

    def test_a_waiver_never_changes_the_grade(self):
        waived = attempt(at(top_current=2), A["ks"], R["ks"], "HIGH", "HIGH")
        paid = attempt(at(top_current=5), A["ks"], R["ks"], "LOW", "HIGH")
        for key in ("grade_after_exhaustion", "grade_after_magnitude", "final_grade", "responder_effective", "undercommitment_modifier"):
            self.assertEqual(waived[key], paid[key])
        self.assertEqual((waived["final_grade"], waived["paid_effort"], paid["paid_effort"]), (-1, False, True))

    def test_expected_wear_table_over_the_grid(self):
        def expected_wear(responder_effective, paid, final):
            if responder_effective in ("", "LOW"):
                return False
            if responder_effective == "MEDIUM" or not paid:
                return final != 0
            return final >= 1
        rows = [r for r in S.exchange_rows() if r["expected"]["response_id"] in O.GOVERNED]
        for row in rows:
            result = row["expected"]
            track = O.GOVERNED[result["response_id"]]
            tier = result["tiers_before"][track]
            if expected_wear(result["responder_effective"], result["paid_effort"], result["final_grade"]):
                tier = max(0, tier - 1)
            action = result["action_id"]
            if result["final_grade"] >= 1 and action in O.BUILD and O.BUILD[action][0] == track:
                tier = max(0, min(2, tier + O.BUILD[action][1]))
            self.assertEqual(result["tiers_after"][track], tier)  # the initiator's own-track consumption never touches the governed track
            MEASURED["scenario_rows_checked"] += 1
        MEASURED["searches"]["governed_response_rows"] = len(rows)
        self.assertTrue(rows)

    def test_pass_and_refusal_charge_nothing(self):
        match = fresh()
        match.open_window()
        match.submit(1, TOP, "", "")
        fields = match.state_fields()
        self.assertEqual((fields["top_stamina"], fields["bottom_stamina"]), (100, 100))
        refused = fresh()
        snapshot = refused.snapshot()
        self.assertEqual(attempt(refused, "nope", R["hf"])["error"], "unknown_action")
        self.assertEqual(refused.snapshot(), snapshot)


# =====================================================================================================
class RulesSheetConsistencyTests(Counted):
    """The rules sheet is the specification the oracle was written from; its tables must not drift from the oracle."""

    SHEET = os.path.join(os.path.dirname(HERE), "GODOT_V1", "docs", "HALF_GUARD_V0_RULES.md")
    ACTION_BY_NAME = {"Crossface": "cf", "Flatten": "fl", "Knee Slice": "ks", "Underhook": "uh", "Recover Guard": "rg"}

    @staticmethod
    def number(token):
        return int(token.replace("*", "").replace("\u2212", "-").replace("+", "").strip())

    def rows(self):
        with open(self.SHEET, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.startswith("|")]

    def test_the_fifteen_raw_cells_in_the_sheet_equal_the_oracle_table(self):
        responses = {"top": ("hf", "uf", "ks"), "bottom": ("hc", "hp", "kp")}
        found = {}
        for line in self.rows():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells[0] in self.ACTION_BY_NAME and len(cells) == 4:
                key = self.ACTION_BY_NAME[cells[0]]
                side = "top" if key in ("cf", "fl", "ks") else "bottom"
                for response, token in zip(responses[side], cells[1:]):
                    found[(key, response)] = self.number(token)
        self.assertEqual(len(found), 15)
        for (key, response), grade in found.items():
            side = "top" if key in ("cf", "fl", "ks") else "bottom"
            self.assertEqual(O.RAW[side][A[key]][R[response]], grade)
        self.assertEqual(found[("ks", "hf")], 1)  # the C1 cell as printed in the sheet

    def test_the_hysteresis_table_in_the_sheet_equals_the_oracle_rules(self):
        parsed = []
        for line in self.rows():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 3 and cells[1].startswith("`a ") and cells[0].lstrip("+-\u2212").isdigit():
                operator = "ge" if "\u2265" in cells[1] else "le"
                threshold = self.number(cells[1].strip("`").split(" ")[-1])
                parsed.append((self.number(cells[0]), operator, threshold, self.number(cells[2])))
        self.assertEqual(len(parsed), 8)
        for band, operator, threshold, target in parsed:
            just_outside = threshold - 1 if operator == "ge" else threshold + 1
            self.assertEqual(O.band_step(threshold, band), target)          # the rule fires exactly at the printed threshold ...
            self.assertNotEqual(O.band_step(just_outside, band), target)    # ... and one tenth outside it does not
            self.assertTrue(O.legal_pair(threshold, O.band_update(threshold, band)))
            self.assertTrue(O.legal_pair(just_outside, O.band_update(just_outside, band)))

    def test_the_sheet_states_the_selected_constants(self):
        with open(self.SHEET, encoding="utf-8") as handle:
            text = handle.read()
        for needle in ("Ready `+1`, Partial `0`, None `\u22121`", "Ready `\u22121`, Partial `0`, None `+2`", "costs LOW 3 / MEDIUM 7 / HIGH 12",
                       "entry axis `+5`", "`proposed \u2265 +30`", "`proposed \u2264 \u221230`", "**C1**"):
            self.assertIn(needle, text)
        self.assertEqual((O.ATTACK_SHIFT, O.DEFENSE_SHIFT), ({2: 1, 1: 0, 0: -1}, {2: -1, 1: 0, 0: 2}))
        self.assertEqual((O.PASS_LINE, O.ESCAPE_LINE, O.STEP_TENTHS, O.ENTRY_AXIS, O.ENTRY_BAND), (30, -30, 10, 5, 0))


# =====================================================================================================
class ExitTests(Counted):
    def test_each_exit_destination_and_reason(self):
        side_control = attempt(at(axis_tenths=25, band=1), A["ks"], R["hf"])
        self.assertEqual((side_control["exit_destination"], side_control["axis_after"], side_control["band_after"]), ("Side Control", 35, 2))
        match = at(axis_tenths=25, band=1)
        attempt(match, A["ks"], R["uf"])
        self.assertEqual(match.s["exit_destination"], "Side Control")
        self.assertEqual(match.s["exit_reason"], "Knee Slice reached the pass line with final grade Strong Success")
        open_guard = at(axis_tenths=-25, band=-2, initiator="bottom")
        result = attempt(open_guard, A["rg"], R["hp"])
        self.assertEqual((result["final_grade"], result["exit_destination"]), (1, "Open Guard"))
        self.assertEqual(open_guard.s["exit_reason"], "Recover Guard reached the escape line with final grade Success")
        closed_guard = at(axis_tenths=-15, band=-1, initiator="bottom")
        result = attempt(closed_guard, A["rg"], R["hc"])
        self.assertEqual((result["final_grade"], result["axis_after"], result["exit_destination"]), (2, -35, "Closed Guard"))
        self.assertEqual(closed_guard.s["exit_reason"], "Recover Guard reached the escape line with final grade Strong Success")

    def test_break_line_threshold_is_inclusive_and_needs_a_success(self):
        self.assertEqual(attempt(at(axis_tenths=20, band=1), A["ks"], R["hf"])["exit_destination"], "Side Control")   # 20+10 = 30
        self.assertEqual(attempt(at(axis_tenths=19, band=1), A["ks"], R["hf"])["exit_destination"], "")               # 29
        self.assertEqual(attempt(at(axis_tenths=-20, band=-1, initiator="bottom"), A["rg"], R["hp"])["exit_destination"], "Open Guard")  # -30
        self.assertEqual(attempt(at(axis_tenths=-19, band=-1, initiator="bottom"), A["rg"], R["hp"])["exit_destination"], "")
        # a contested or failed break-capable attempt never exits, even past the line
        self.assertEqual(attempt(at(axis_tenths=35, band=2), A["ks"], R["ks"])["exit_destination"], "")
        # a non-break success past the line does not exit
        self.assertEqual(attempt(at(axis_tenths=35, band=2), A["cf"], R["hf"])["exit_destination"], "")

    def test_non_exit_success_flips_initiative_and_exit_does_not(self):
        match = fresh()
        attempt(match, A["ks"], R["hf"])
        self.assertEqual(match.s["initiator"], "bottom")
        exit_match = at(axis_tenths=25, band=1)
        attempt(exit_match, A["ks"], R["hf"])
        self.assertEqual(exit_match.s["initiator"], "top")
        self.assertTrue(exit_match.state_fields()["ended"])

    def test_exit_exchange_processes_readiness_like_any_other_exchange(self):
        match = at(axis_tenths=25, band=1, top_base=2, bottom_frame=1)
        # raw -2; attacker Ready +1 -> -1; defender at LOW counted as None +2 -> +1; HIGH presses a Success -> +2; undercommitment +1 saturates at +2.
        result = attempt(match, A["ks"], R["ks"], "HIGH", "LOW")
        self.assertEqual((result["final_grade"], result["exit_destination"]), (2, "Side Control"))
        self.assertEqual((result["tiers_after"]["top_base"], result["tiers_after"]["bottom_frame"]), (1, 1))  # consumption happened on the exit
        self.assertEqual(result["readiness_changes"], ["top_base:Ready->Partial:knee_slice"])
        self.assertEqual(match.state_fields()["top_base"], 1)
        # Recover Guard exit from a Ready frame: consumption and the Top-base weakening both apply on the exit exchange.
        bottom = at(axis_tenths=-25, band=-2, initiator="bottom", top_base=1, bottom_frame=2)
        result = attempt(bottom, A["rg"], R["hp"])  # raw +1, attacker Ready +1 -> +2: Strong Success
        self.assertEqual((result["final_grade"], result["exit_destination"]), (2, "Closed Guard"))
        self.assertEqual(result["tiers_after"], {"top_base": 0, "bottom_frame": 1})
        self.assertEqual(result["readiness_changes"], ["bottom_frame:Ready->Partial:recover_guard", "top_base:Partial->None:recover_guard"])

    def test_terminal_state_refuses_everything_without_mutation(self):
        match = at(axis_tenths=25, band=1)
        attempt(match, A["ks"], R["hf"])
        snapshot = match.snapshot()
        self.assertEqual(attempt(match, A["cf"], R["hf"])["error"], "terminal_exchange")
        self.assertEqual(match.open_window(), {"error": "terminal_exchange"})
        self.assertEqual(match.submit(1, TOP, A["cf"], R["hf"])["error"], "no_open_window")
        self.assertEqual(match.snapshot(), snapshot)

    def test_exit_state_divergence_from_mount_is_clamp_and_band_update(self):
        result = attempt(at(axis_tenths=30, band=2), A["ks"], R["uf"])   # +2 -> proposed 50, clamped to 40
        self.assertEqual((result["axis_proposed"], result["axis_after"], result["band_after"]), (50, 40, 2))
        result = attempt(at(axis_tenths=-20, band=-1, initiator="bottom"), A["rg"], R["hc"])  # -40 -> band -1 -> -2
        self.assertEqual((result["axis_after"], result["band_before"], result["band_after"]), (-40, -1, -2))

    def test_break_grid_rows_obey_the_exit_rule(self):
        rows = S.break_rows()
        exits = 0
        for row in rows:
            result = row["expected"]
            self.assertEqual(result["error"], "")
            action, final, proposed = result["action_id"], result["final_grade"], result["axis_proposed"]
            if action == O.KNEE_SLICE:
                label = "Side Control" if (final >= 1 and proposed >= 30) else ""
            else:
                label = ("Open Guard" if final == 1 else "Closed Guard") if (final >= 1 and proposed <= -30) else ""
            self.assertEqual(result["exit_destination"], label)
            exits += bool(label)
            MEASURED["scenario_rows_checked"] += 1
        MEASURED["searches"]["break_grid_rows"] = len(rows)
        MEASURED["searches"]["break_grid_exits"] = exits
        self.assertGreater(exits, 0)


# =====================================================================================================
class AdmissionTests(Counted):
    def test_every_command_refusal_in_precedence_order_and_no_mutation(self):
        cases = [  # (setup callable, command args) -> expected code, in the documented order
            (lambda m: None, (1, TOP, A["cf"], R["hf"]), "no_open_window"),
            (lambda m: m.open_window(), (9, TOP, A["cf"], R["hf"]), "stale_window"),
            (lambda m: m.open_window(), (1, "", A["cf"], R["hf"]), "missing_fighter_id"),
            (lambda m: m.open_window(), (1, "ghost", A["cf"], R["hf"]), "unknown_fighter"),
            (lambda m: m.open_window(), (1, BOT, A["uh"], R["hc"]), "not_initiator"),
            (lambda m: m.open_window(), (1, TOP, "", R["hf"]), "response_without_action"),
            (lambda m: m.open_window(), (1, TOP, "", "", "LOW"), "commitment_without_action"),
            (lambda m: m.open_window(), (1, TOP, "", "", "", "LOW"), "commitment_without_action"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], R["hf"], "EXTREME"), "invalid_commitment"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], R["hf"], "", "EXTREME"), "invalid_response_commitment"),
            (lambda m: m.open_window(), (1, TOP, "nope", R["hf"]), "unknown_action"),
            (lambda m: m.open_window(), (1, TOP, A["uh"], R["hf"]), "incorrect_action_side_or_kind"),
            (lambda m: m.open_window(), (1, TOP, R["hf"], R["hf"]), "incorrect_action_side_or_kind"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], "nope"), "unknown_response"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], ""), "unknown_response"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], R["hc"]), "incorrect_response_side_or_kind"),
            (lambda m: m.open_window(), (1, TOP, A["cf"], A["uh"]), "incorrect_response_side_or_kind"),
        ]
        for setup, args, expected in cases:
            match = fresh()
            setup(match)
            before = match.snapshot()
            self.assertEqual(match.submit(*args), {"error": expected})
            self.assertEqual(match.snapshot(), before)
            MEASURED["scenario_rows_checked"] += 1

    def test_pairwise_precedence_every_adjacent_pair(self):
        """Two simultaneous faults: the earlier code in the documented order always wins."""
        def run(args):
            match = fresh()
            match.open_window()
            return match.submit(*args)["error"]
        self.assertEqual(run((9, "ghost", "nope", "nope", "EXTREME", "EXTREME")), "stale_window")
        self.assertEqual(run((1, "", "nope", "nope", "EXTREME", "EXTREME")), "missing_fighter_id")
        self.assertEqual(run((1, "ghost", "nope", "nope", "EXTREME", "EXTREME")), "unknown_fighter")
        self.assertEqual(run((1, BOT, "nope", "nope", "EXTREME", "EXTREME")), "not_initiator")
        self.assertEqual(run((1, TOP, "", R["hf"], "LOW", "LOW")), "response_without_action")
        self.assertEqual(run((1, TOP, A["cf"], "nope", "EXTREME", "EXTREME")), "invalid_commitment")
        self.assertEqual(run((1, TOP, A["cf"], "nope", "", "EXTREME")), "invalid_response_commitment")
        self.assertEqual(run((1, TOP, "nope", "nope")), "unknown_action")
        self.assertEqual(run((1, TOP, A["uh"], "nope")), "incorrect_action_side_or_kind")
        self.assertEqual(run((1, TOP, A["cf"], "nope")), "unknown_response")
        # terminal context outranks every command-shape fault, and context outranks the initiator checks
        terminal = at(axis_tenths=25, band=1)
        attempt(terminal, A["ks"], R["hf"])
        self.assertEqual(terminal.submit(1, "ghost", "nope"), {"error": "no_open_window"})
        terminal.s["window_open"], terminal.s["window_side"], terminal.s["window_id"] = True, "top", 1
        self.assertEqual(terminal.submit(1, "ghost", "nope"), {"error": "terminal_exchange"})

    def test_match_level_attempt_codes_and_default_commitments(self):
        match = fresh()
        snapshot = match.snapshot()
        self.assertEqual(match.attempt(A["cf"], R["hf"], "")["error"], "invalid_commitment")  # match level needs a commitment
        self.assertEqual(match.attempt(A["cf"], R["hf"], "MEDIUM", "bogus")["error"], "invalid_response_commitment")
        self.assertEqual(match.attempt(A["cf"], R["hf"], "MEDIUM", "")["error"], "")           # empty response commitment is MEDIUM
        self.assertNotEqual(match.snapshot(), snapshot)
        self.assertEqual(match.s["history"]["response_charge_history"], [7])
        self.assertEqual(fresh().attempt(None, R["hf"], "MEDIUM")["error"], "unknown_action")
        self.assertEqual(fresh().attempt(A["cf"], 7, "MEDIUM")["error"], "unknown_response")

    def test_context_errors_in_documented_order(self):
        def broken(mutator):
            state = S.state_with()
            mutator(state)
            return O.validate_context(state)
        self.assertEqual(O.validate_context(None), "missing_state")
        self.assertEqual(broken(lambda s: s["fighters"][TOP].update(stamina_current=101)), "invalid_stamina_state")
        self.assertEqual(broken(lambda s: s["fighters"][TOP].update(stamina_maximum=0)), "invalid_stamina_state")
        self.assertEqual(broken(lambda s: s["fighters"][BOT].update(exhaustion_latched=True)), "invalid_exhaustion_latch")
        self.assertEqual(broken(lambda s: s.update(initiator="middle")), "invalid_initiator")
        self.assertEqual(broken(lambda s: s.update(clock_seconds=301)), "invalid_clock_context")
        self.assertEqual(broken(lambda s: s.update(interval_seconds=0)), "invalid_clock_context")
        self.assertEqual(broken(lambda s: s.update(clock_seconds=0)), "terminal_exchange")
        self.assertEqual(broken(lambda s: s.update(exit_destination="Side Control")), "terminal_exchange")
        self.assertEqual(broken(lambda s: s.update(axis_tenths=41)), "invalid_half_guard_context")
        self.assertEqual(broken(lambda s: s.update(axis_tenths=5, band=1)), "invalid_half_guard_context")
        self.assertEqual(broken(lambda s: s.update(top_base=3)), "invalid_half_guard_context")
        self.assertEqual(broken(lambda s: s.update(bottom_frame=-1)), "invalid_half_guard_context")
        # precedence between context faults
        self.assertEqual(broken(lambda s: (s.update(initiator="x"), s["fighters"][TOP].update(stamina_current=101))), "invalid_stamina_state")
        self.assertEqual(broken(lambda s: (s.update(clock_seconds=0), s.update(axis_tenths=41))), "terminal_exchange")
        self.assertEqual(broken(lambda s: (s.update(interval_seconds=0), s.update(clock_seconds=0))), "invalid_clock_context")
        # context errors reach the public commands without mutation
        match = O.HalfGuard.from_snapshot(S.state_with(top_base=3))
        snapshot = match.snapshot()
        self.assertEqual(match.attempt(A["cf"], R["hf"], "MEDIUM"), {"error": "invalid_half_guard_context"})
        self.assertEqual(match.open_window(), {"error": "invalid_half_guard_context"})
        self.assertEqual(match.snapshot(), snapshot)

    def test_window_initiator_changed_is_reachable_only_through_a_corrupted_snapshot(self):
        match = fresh()
        match.open_window()
        match.s["initiator"] = "bottom"
        before = match.snapshot()
        self.assertEqual(match.submit(1, TOP, A["cf"], R["hf"]), {"error": "window_initiator_changed"})
        self.assertEqual(match.snapshot(), before)


# =====================================================================================================
class WindowTests(Counted):
    def test_ids_continue_from_the_entry_and_alternate(self):
        match = fresh(last_issued=9)
        report = match.open_window()
        self.assertEqual((report["window_id"], report["fighter_id"], report["role"], report["commitment"]), (10, TOP, "top", "MEDIUM"))
        self.assertEqual(report["advance"], {"elapsed_seconds": 5, "clock_seconds": 295})
        self.assertEqual(match.submit(10, TOP, A["cf"], R["uf"])["kind"], "exchange")
        report = match.open_window()
        self.assertEqual((report["window_id"], report["fighter_id"], report["role"]), (11, BOT, "bottom"))
        self.assertEqual(match.submit(11, BOT)["kind"], "reset")  # either side may pass
        self.assertEqual(match.open_window()["role"], "top")
        history = match.snapshot()["history"]
        self.assertEqual((history["reset_window_history"], history["top_initiation_count"], history["bottom_initiation_count"]), (["bottom"], 1, 0))

    def test_pass_costs_nothing_and_flips_initiative_only(self):
        match = fresh()
        match.open_window()
        before = match.snapshot()
        report = match.submit(1, TOP)
        after = match.snapshot()
        self.assertEqual((report["error"], report["kind"]), ("", "reset"))
        self.assertEqual(after["initiator"], "bottom")
        for key in ("fighters", "axis_tenths", "band", "top_base", "bottom_frame", "exit_destination"):
            self.assertEqual(before[key], after[key])
        self.assertEqual(after["history"]["initiated_action_history"], [])
        self.assertFalse(after["window_open"])

    def test_one_window_one_decision_and_stale_commands(self):
        match = fresh()
        match.open_window()
        self.assertEqual(match.open_window(), {"error": "window_already_open"})
        self.assertEqual(match.submit(1, TOP, A["cf"], R["hf"])["error"], "")
        snapshot = match.snapshot()
        self.assertEqual(match.submit(1, TOP, A["cf"], R["hf"]), {"error": "no_open_window"})  # replayed command
        self.assertEqual(match.snapshot(), snapshot)
        match.open_window()
        self.assertEqual(match.submit(1, BOT, A["uh"], R["hc"]), {"error": "stale_window"})  # old window id
        self.assertEqual(match.submit(True, BOT, A["uh"], R["hc"]), {"error": "stale_window"})  # bool is never an id
        self.assertEqual(match.submit(2, BOT, A["uh"], R["hc"])["error"], "")

    def test_duration_validation_zero_time_and_clamping(self):
        match = fresh(clock=10)
        for duration, expected in ((-1, "invalid_window_request"), (True, "invalid_duration"), ("5", "invalid_duration"), (2.5, "invalid_duration"), ([], "invalid_duration")):
            snapshot = match.snapshot()
            self.assertEqual(match.open_window(duration), {"error": expected})
            self.assertEqual(match.snapshot(), snapshot)
        report = match.open_window(0)
        self.assertEqual((report["window_open"], report["advance"]["elapsed_seconds"], report["advance"]["clock_seconds"]), (True, 0, 10))
        match.submit(1, TOP, A["cf"], R["hf"])
        report = match.open_window(99)  # clamped to the remaining clock: the match ends, no window opens
        self.assertEqual((report["closed"], report["window_open"], report["window_id"]), (True, False, 1))
        self.assertEqual(report["advance"], {"elapsed_seconds": 10, "clock_seconds": 0})
        self.assertEqual(match.s["exit_reason"], "TIMEOUT — Half Guard retained")
        self.assertEqual((match.s["exit_destination"], match.state_fields()["ended"]), ("", True))

    def test_timeout_at_the_exact_interval_boundary_and_after(self):
        match = fresh(clock=10, interval=5)
        self.assertTrue(match.open_window()["window_open"])
        match.submit(1, TOP)
        report = match.open_window()          # 5 -> 0
        self.assertTrue(report["closed"])
        self.assertEqual(match.open_window(), {"error": "terminal_exchange"})
        self.assertEqual(match.submit(1, BOT, A["uh"], R["hc"]), {"error": "no_open_window"})
        self.assertEqual(match.attempt(A["uh"], R["hc"], "MEDIUM"), {"error": "terminal_exchange"})

    def test_a_window_opened_with_an_exit_pending_is_impossible_and_exit_leaves_the_clock_alone(self):
        match = at(axis_tenths=25, band=1)
        match.open_window()
        clock = match.s["clock_seconds"]
        match.submit(1, TOP, A["ks"], R["hf"])
        self.assertEqual(match.s["clock_seconds"], clock)
        self.assertEqual(match.open_window(), {"error": "terminal_exchange"})


# =====================================================================================================
class ReplayAndRemapTests(Counted):
    def test_every_trajectory_replays_identically_twice_and_roundtrips(self):
        trajectories = S.trajectories()
        self.assertGreaterEqual(len(trajectories), 10)
        for name, (request, commands) in trajectories.items():
            first = O.replay(copy.deepcopy(request), copy.deepcopy(commands))
            second = O.replay(copy.deepcopy(request), copy.deepcopy(commands))
            self.assertEqual(O.canonical_json(first), O.canonical_json(second), name)
            self.assertEqual(O.digest(first), O.digest(second))
            self.assertEqual(json.loads(O.canonical_json(first)), first)
            if first["final"] is not None:
                self.assertEqual(O.HalfGuard.from_snapshot(first["final"]).snapshot(), first["final"])
            MEASURED["scenario_rows_checked"] += 1
        MEASURED["searches"]["trajectories"] = len(trajectories)

    def errors(self, name):
        return [r["error"] for r in O.replay(*S.trajectories()[name])["results"]]

    def test_trajectory_literals(self):
        self.assertEqual(self.errors("refusal_matrix"), [
            "no_open_window", "", "stale_window", "missing_fighter_id", "unknown_fighter", "not_initiator", "response_without_action",
            "commitment_without_action", "commitment_without_action", "invalid_commitment", "invalid_response_commitment", "unknown_action",
            "incorrect_action_side_or_kind", "incorrect_action_side_or_kind", "unknown_response", "unknown_response",
            "incorrect_response_side_or_kind", "incorrect_response_side_or_kind", ""])
        self.assertEqual(self.errors("double_open_and_stale"), ["", "window_already_open", "stale_window", "not_initiator", "", "no_open_window"])
        self.assertEqual(self.errors("timeout_exact_boundary"), ["", "terminal_exchange", "no_open_window"])
        self.assertEqual(self.errors("zero_time_window"), ["invalid_window_request", "invalid_duration", "invalid_duration", "invalid_duration", "", "", ""])
        self.assertEqual(self.errors("pass_pass_timeout"), ["", "", "", "", "", "", "", "terminal_exchange", "no_open_window"])
        run = O.replay(*S.trajectories()["pass_pass_timeout"])
        self.assertEqual(run["results"][6]["closed"], True)
        self.assertEqual(run["final"]["history"]["reset_window_history"], ["top", "bottom", "top"])
        self.assertEqual(run["final"]["exit_reason"], "TIMEOUT \u2014 Half Guard retained")
        zero = O.replay(*S.trajectories()["zero_time_window"])
        self.assertEqual(zero["results"][4]["advance"], {"elapsed_seconds": 0, "clock_seconds": 10})
        self.assertEqual(zero["results"][6]["closed"], True)
        coop = O.replay(*S.trajectories()["cooperative_exit_side_control"])
        self.assertEqual(coop["results"][5]["detail"]["settlement"]["exit_destination"], "Side Control")
        self.assertEqual(coop["final"]["exit_destination"], "Side Control")
        self.assertTrue(all(r["error"] for r in coop["results"][6:]))
        self.assertEqual(self.errors("post_exit_refusals")[-3:], ["terminal_exchange", "terminal_exchange", "no_open_window"])
        opening = O.replay(*S.trajectories()["opening_and_alternation"])
        self.assertEqual([r["window_id"] for r in opening["results"] if r.get("window_open")], [10, 11, 12, 13])
        self.assertEqual([r.get("role") for r in opening["results"] if r.get("window_open")], ["top", "bottom", "top", "bottom"])
        waiver = O.replay(*S.trajectories()["rule1_waiver_high_unpaid"])["results"][1]["detail"]["settlement"]
        self.assertEqual((waiver["responder_waived"], waiver["responder_charged"], waiver["paid_effort"]), (12, 0, False))
        paid = O.replay(*S.trajectories()["rule1_paid_high_preserved"])["results"][1]["detail"]["settlement"]
        self.assertEqual((paid["responder_waived"], paid["responder_charged"], paid["paid_effort"]), (0, 12, True))

    def test_replay_of_a_refused_entry_and_unknown_operation(self):
        bad = S.entry()
        bad["interval_seconds"] = 0
        self.assertEqual(O.replay(bad, [{"op": "open"}]), {"entry_error": "invalid_interval", "results": [], "final": None})
        with self.assertRaises(ValueError):
            O.replay(S.entry(), [{"op": "teleport"}])

    def test_role_remapping_keeps_stamina_and_latch_with_the_fighter(self):
        """Fighter A starts latched Exhausted (20), fighter B fresh (100). Map 1 puts A on top; map 2 puts B on top."""
        matches = []
        for swap in (False, True):
            match = O.HalfGuard.from_entry(S.entry(top_current=20, bottom_current=100, swap=swap))[0]
            match.open_window()
            self.assertEqual(match.submit(1, match.s["role_map"]["top"], A["cf"], R["hf"], "MEDIUM", "MEDIUM")["error"], "")
            matches.append(match)
        one, two = matches
        for match in matches:  # per-fighter stamina and latch are identical in both maps: both fighters paid 7
            self.assertEqual((match.s["fighters"][TOP]["stamina_current"], match.s["fighters"][TOP]["exhaustion_latched"]), (13, True))
            self.assertEqual((match.s["fighters"][BOT]["stamina_current"], match.s["fighters"][BOT]["exhaustion_latched"]), (93, False))
        # The role views follow the role map.
        self.assertEqual((one.state_fields()["top_latched"], one.state_fields()["bottom_latched"]), (True, False))
        self.assertEqual((two.state_fields()["top_latched"], two.state_fields()["bottom_latched"]), (False, True))
        # Grading uses the occupant of each role: an Exhausted attacker (+1 -1 = Contested) versus an Exhausted responder (+1 +1 = Strong Success).
        self.assertEqual(one.s["history"]["modified_grade_history"], ["Contested"])
        self.assertEqual(two.s["history"]["modified_grade_history"], ["Strong Success"])
        # Readiness belongs to the role's current occupant: the Strong Success weakens the frame of whoever holds the Bottom role.
        self.assertEqual((one.s["top_base"], one.s["bottom_frame"]), (1, 1))
        self.assertEqual((two.s["top_base"], two.s["bottom_frame"]), (1, 0))
        self.assertEqual((one.s["axis_tenths"], two.s["axis_tenths"]), (5, 25))
        self.assertEqual(two.state_fields()["authority"], BOT)


# =====================================================================================================
try:
    from bjj_game.domain.model import Grade as FrozenGrade
    from bjj_game.domain.action import Commitment as FrozenCommitment
    from bjj_game.domain.stamina import StaminaBand as FrozenBand, StaminaPool as FrozenPool
    from bjj_game.engine.match import MountMatch as FrozenMatch
    from bjj_game.engine.stamina import DEFAULT_EXHAUSTION_POLICY as FrozenExhaustion, DEFAULT_STAMINA_COST_POLICY as FrozenCost
    FROZEN_AVAILABLE = True
except ImportError:  # CI and local runs use PYTHONPATH=src; without it the cross-check cannot run and says so
    FROZEN_AVAILABLE = False


@unittest.skipUnless(FROZEN_AVAILABLE, "PYTHONPATH=src is required to import the frozen reference")
class FrozenSemanticsCrossCheckTests(Counted):
    """Position-independent settlement helpers are compared with the frozen Python reference.
    Half Guard itself never executes Mount gameplay: only static helpers and standalone pools are called."""

    CAPACITIES = (1, 2, 3, 4, 7, 20, 37, 64, 100, 2 ** 52 + 5, 2 ** 53 - 3, O.MAXIMUM_EXACT)

    def currents(self, capacity):
        enter, recover = O.enter_threshold(capacity), O.recover_threshold(capacity)
        points = {0, 1, 2, enter - 1, enter, enter + 1, recover - 1, recover, recover + 1, capacity // 2 - 1, capacity // 2,
                  capacity // 2 + 1, (3 * capacity) // 4 - 1, (3 * capacity) // 4, (3 * capacity) // 4 + 1, capacity - 1, capacity}
        if capacity <= 100:
            points |= set(range(capacity + 1))
        return sorted(p for p in points if 0 <= p <= capacity)

    def frozen_pool(self, current, capacity, latched):
        pool = FrozenPool(0, capacity) if latched else FrozenPool(capacity, capacity)  # build in the target latch state ...
        pool.set_current(current)                                                       # ... then move to `current` (hysteresis applies)
        return pool

    def test_thresholds_and_bands_match_the_frozen_pool(self):
        for capacity in self.CAPACITIES:
            pool = FrozenPool(capacity, capacity)
            self.assertEqual((O.enter_threshold(capacity), O.recover_threshold(capacity)), (pool.exhaustion_enter_threshold, pool.exhaustion_recover_threshold))
            for current in self.currents(capacity):
                for latched in (False, True):
                    if (current <= O.enter_threshold(capacity) and not latched) or (current >= O.recover_threshold(capacity) and latched):
                        continue   # a combination the entry validator refuses
                    frozen = self.frozen_pool(current, capacity, latched)
                    self.assertEqual(frozen.current, current)
                    self.assertEqual(frozen.band.value == "Exhausted", latched)
                    self.assertEqual(O.stamina_band(current, capacity, latched), frozen.band.value)
                    MEASURED["frozen_comparisons"] += 1

    def test_latch_transitions_after_spending_match_the_frozen_pool(self):
        for capacity in (1, 3, 4, 7, 20, 37, 64, 100, 2 ** 53 - 3):
            for current in self.currents(capacity):
                for latched in (False, True):
                    if (current <= O.enter_threshold(capacity) and not latched) or (current >= O.recover_threshold(capacity) and latched):
                        continue
                    for spend in (0, 1, 3, 7, 12):
                        frozen = self.frozen_pool(current, capacity, latched)
                        frozen.spend_up_to(spend)
                        after = current - min(current, spend)
                        self.assertEqual(frozen.current, after)
                        self.assertEqual(frozen.band.value == "Exhausted", O.latch_after(after, capacity, latched))
                        MEASURED["frozen_comparisons"] += 1

    def test_funding_matches_the_frozen_cost_policy(self):
        for requested in O.COMMITMENTS:
            for current in range(0, 40):
                frozen = FrozenCost.effective_commitment(requested=FrozenCommitment[requested], available_stamina=current)
                expected = "" if frozen is None else frozen.value
                self.assertEqual(O.determine(requested, current)[0], expected)
                if frozen is not None:
                    self.assertEqual(O.determine(requested, current)[1], FrozenCost.cost(frozen))
                MEASURED["frozen_comparisons"] += 1

    def test_exhaustion_modifier_matches_the_frozen_policy(self):
        for initiator_band in FrozenBand:
            for responder_band in FrozenBand:
                frozen = FrozenExhaustion.exchange_grade_modifier(initiator_band=initiator_band, responder_band=responder_band)
                self.assertEqual(O.exhaustion_modifier(initiator_band.value, responder_band.value), frozen)
                MEASURED["frozen_comparisons"] += 1

    def test_magnitude_and_undercommitment_match_the_frozen_static_helpers(self):
        def frozen(commitment):
            return None if commitment == "" else FrozenCommitment[commitment]
        for effective in ("", "LOW", "MEDIUM", "HIGH"):
            for grade in range(-2, 3):
                self.assertEqual(O.magnitude_modifier(effective, grade), FrozenMatch._initiator_commitment_modifier(frozen(effective), FrozenGrade(grade)))
                MEASURED["frozen_comparisons"] += 1
            for responder in ("", "LOW", "MEDIUM", "HIGH"):
                self.assertEqual(O.undercommitment_modifier(effective, responder), FrozenMatch._response_undercommitment_modifier(
                    initiator_commitment=frozen(effective), responder_commitment=frozen(responder)))
                MEASURED["frozen_comparisons"] += 1
        for grade in range(-2, 3):
            for steps in range(-4, 5):
                self.assertEqual(O.shift(grade, steps), int(FrozenGrade(grade).shift(steps)))
                MEASURED["frozen_comparisons"] += 1

    def test_the_sequential_grade_pipeline_matches_the_frozen_transform_when_no_readiness_applies(self):
        """At Partial tiers and without governed responses the Half Guard pipeline reduces to the frozen v0.4a sequence."""
        for effective_init in ("", "LOW", "MEDIUM", "HIGH"):
            for effective_resp in ("", "LOW", "MEDIUM", "HIGH"):
                for grade in range(-2, 3):
                    frozen_final, _, _ = FrozenMatch._commitment_grade_transform(
                        grade_after_exhaustion=FrozenGrade(grade),
                        initiator_commitment=None if effective_init == "" else FrozenCommitment[effective_init],
                        responder_commitment=None if effective_resp == "" else FrozenCommitment[effective_resp])
                    after_magnitude = O.shift(grade, O.magnitude_modifier(effective_init, grade))
                    mine = O.shift(after_magnitude, O.undercommitment_modifier(effective_init, effective_resp))
                    self.assertEqual(mine, int(frozen_final))
                    MEASURED["frozen_comparisons"] += 1


# =====================================================================================================
class StructuralSearchTests(Counted):
    """Reachability facts measured on the C1 oracle. These are structural; they are not balance claims."""

    def test_every_exit_is_reachable_under_cooperative_play(self):
        first, states = S.earliest_exits(max_windows=8)
        self.assertEqual(first, {"Side Control": 3, "Closed Guard": 4, "Open Guard": 4})
        MEASURED["searches"]["cooperative_earliest_exit_windows"] = first
        MEASURED["searches"]["cooperative_states_explored"] = states

    def test_known_property_matched_commitment_best_counter_defense_is_a_stalemate(self):
        """KNOWN PROPERTY (recorded, not a failure and not balance): a responder that always plays the best counter at the SAME
        commitment the attacker uses can never be exited on within the horizon, whatever the attacker's actions and passes."""
        for commitment in O.COMMITMENTS:
            exits, states = S.best_counter_earliest(max_windows=12, attacker_commitments=(commitment,), responder_commitment=commitment)
            self.assertEqual(exits, {})
            MEASURED["searches"]["stalemate_" + commitment.lower() + "_states"] = states

    def test_the_stalemate_is_not_robust_to_commitment_mismatch(self):
        """Measured counter-facts: a fixed-MEDIUM best-counter responder is exploitable by HIGH attacks, a fixed-LOW one by MEDIUM attacks."""
        high_vs_medium, _ = S.best_counter_earliest(max_windows=12, attacker_commitments=("HIGH",), responder_commitment="MEDIUM")
        self.assertEqual(high_vs_medium, {"Side Control": 5, "Open Guard": 6, "Closed Guard": 10})
        medium_vs_low, _ = S.best_counter_earliest(max_windows=12, attacker_commitments=("MEDIUM",), responder_commitment="LOW")
        self.assertEqual(medium_vs_low, {"Side Control": 5, "Open Guard": 8})
        low_vs_medium, _ = S.best_counter_earliest(max_windows=12, attacker_commitments=("LOW",), responder_commitment="MEDIUM")
        self.assertEqual(low_vs_medium, {})
        MEASURED["searches"]["mismatch_high_vs_medium"] = high_vs_medium
        MEASURED["searches"]["mismatch_medium_vs_low"] = medium_vs_low

    def test_every_action_has_a_counter_and_a_favorable_response(self):
        for side, row in O.RAW.items():
            for action, cells in row.items():
                self.assertLessEqual(min(cells.values()), -1)
                self.assertGreaterEqual(max(cells.values()), 1)

    def test_c1_removes_the_only_wear_free_hold_on_a_break_technique(self):
        """Responses that hold Knee Slice to <= 0 under C1: only the governed Knee Shield (the C0 table also let Hip Frame hold it)."""
        holding = [r for r, g in O.RAW["top"][O.KNEE_SLICE].items() if g <= 0]
        self.assertEqual(holding, [O.KNEE_SHIELD])
        holding_rg = [r for r, g in O.RAW["bottom"][O.RECOVER_GUARD].items() if g <= 0]
        self.assertEqual(holding_rg, [O.KNEE_PIN])


# =====================================================================================================
class GeneratorAndIndependenceTests(Counted):
    @staticmethod
    def load_generator():
        path = os.path.join(os.path.dirname(HERE), "GODOT_V1", "tests", "generate_half_guard_reference.py")
        spec = importlib.util.spec_from_file_location("generate_half_guard_reference", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_generator_is_deterministic_and_counts_are_measured(self):
        generator = self.load_generator()
        with tempfile.TemporaryDirectory() as directory:
            first = generator.write(os.path.join(directory, "a.jsonl"))
            second = generator.write(os.path.join(directory, "b.jsonl"))
            self.assertEqual(first, second)
            with open(os.path.join(directory, "a.jsonl"), "rb") as a, open(os.path.join(directory, "b.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            with open(os.path.join(directory, "a.jsonl"), encoding="ascii") as handle:
                lines = [json.loads(line) for line in handle]
        self.assertEqual(len(lines), first["scenarios"])
        self.assertEqual(first["scenarios"], len(S.all_rows()))
        self.assertGreater(first["comparisons"], first["scenarios"])
        families = {line["family"] for line in lines}
        self.assertEqual(families, {"initial_band", "band_update", "entry", "exchange_grid", "break_grid", "trajectory"})
        MEASURED["searches"]["fixture"] = first

    def test_generator_refuses_an_empty_fixture(self):
        generator = self.load_generator()
        with self.assertRaises(SystemExit):
            generator.write("/nonexistent-directory/never-written.jsonl", rows=[])

    def test_oracle_modules_import_only_the_standard_library(self):
        for name in ("half_guard_v0.py", "half_guard_v0_scenarios.py"):
            with open(os.path.join(HERE, "oracles", name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), feature_version=(3, 11))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported |= {alias.name.split(".")[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    imported.add(("." if node.level else "") + (node.module or ""))
            allowed = {"copy", "functools", "hashlib", "json", "math", ".", ".half_guard_v0"}
            self.assertTrue(imported <= allowed, (name, imported))
            self.assertNotIn("bjj_game", imported)

    def test_oracle_source_has_no_io_clock_randomness_or_mount_dependency(self):
        forbidden_names = {"open", "random", "time", "datetime", "os", "sys", "subprocess", "MountMatch", "eval", "exec", "compile", "__import__", "bjj_game"}
        for name in ("half_guard_v0.py", "half_guard_v0_scenarios.py"):
            with open(os.path.join(HERE, "oracles", name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), feature_version=(3, 11))
            docstrings = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                          and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
            used = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used.add(node.attr)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                    self.assertNotIn("res://", node.value)
                    self.assertFalse(node.value.endswith(".gd"))
            self.assertEqual(used & forbidden_names, set(), name)

    def test_oracle_tests_are_discoverable_by_the_ci_loader(self):
        suite = unittest.defaultTestLoader.discover(HERE, pattern="test_half_guard_oracle.py")
        count = sum(1 for _ in _flatten(suite))
        self.assertGreater(count, 40)


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


if __name__ == "__main__":
    unittest.main()
