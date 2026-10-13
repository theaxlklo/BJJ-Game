"""Focused unit tests for the Half Guard feint extension of the independent oracle (B1h checkpoint).

Expected values are hand-computed from ``GODOT_V1/docs/HALF_GUARD_V0_RULES.md`` section 13 and written out literally (the
arithmetic is shown in comments); the oracle is used to generate an expectation only in clearly labelled *property* tests
(invariants over its outputs). Scope: oracle only. They describe provisional prototype rules, not a balance claim.
"""
import ast
import copy
import hashlib
import inspect
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from oracles import half_guard_v0 as O  # noqa: E402
from oracles import half_guard_v0_feint_scenarios as F  # noqa: E402
from oracles import half_guard_v0_scenarios as S  # noqa: E402

A, R = S.ACTION, S.RESPONSE
TOP, BOT = S.TOP_ID, S.BOTTOM_ID
REPO = os.path.dirname(HERE)
RULES = os.path.join(REPO, "GODOT_V1", "docs", "HALF_GUARD_V0_RULES.md")
# The B1g-qualified direct-technique fixture digest (generate_half_guard_reference.py at 11565b2): must never change.
DIRECT_FIXTURE_SHA256 = "62da68057bcb427fb4d356a4af95907d39e1e4394529779b9373da01c3a517fb"


def state(side="top", axis=5, band=0, top_base=1, bottom_frame=1, initiator_stamina=100, responder_stamina=100, maximum=100):
    top_current, bottom_current = (initiator_stamina, responder_stamina) if side == "top" else (responder_stamina, initiator_stamina)
    snapshot = S.state_with(initiator=side, axis_tenths=axis, band=band, top_base=top_base, bottom_frame=bottom_frame,
                            top_current=top_current, bottom_current=bottom_current)
    return snapshot


def feint(snapshot, response, commitment="MEDIUM", response_commitment="MEDIUM", apparent=None, real=None):
    side = snapshot["initiator"]
    pair = {"top": (A["cf"], A["ks"]), "bottom": (A["uh"], A["rg"])}[side]
    match = O.HalfGuard.from_snapshot(snapshot)
    result = match.attempt(apparent or pair[0], response, commitment, response_commitment, real or pair[1])
    return match, result


def direct(snapshot, action, response, commitment="MEDIUM", response_commitment="MEDIUM"):
    match = O.HalfGuard.from_snapshot(snapshot)
    return match, match.attempt(action, response, commitment, response_commitment)


class PairTableTests(unittest.TestCase):
    def test_exactly_two_explicit_pairs_with_the_published_conditions(self):
        self.assertEqual(set(O.FEINT_PAIRS), {A["cf"], A["uh"]})
        self.assertEqual(O.FEINT_PAIRS[A["cf"]], {"id": "FP-1", "real": A["ks"], "track": "top_base", "minimum_tier": 1, "bite": R["uf"]})
        self.assertEqual(O.FEINT_PAIRS[A["uh"]], {"id": "FP-2", "real": A["rg"], "track": "bottom_frame", "minimum_tier": 1, "bite": R["hc"]})

    def test_flatten_to_knee_slice_is_excluded(self):
        self.assertNotIn(A["fl"], O.FEINT_PAIRS)
        _, result = feint(state(), R["hf"], apparent=A["fl"], real=A["ks"])
        self.assertEqual(result, {"error": "feint_not_supported"})

    def test_every_pair_obeys_the_published_requirements(self):
        for apparent, pair in O.FEINT_PAIRS.items():
            self.assertNotEqual(apparent, pair["real"])
            side = "top" if apparent in O.TOP_ACTIONS else "bottom"
            self.assertIn(pair["real"], O.ACTIONS[side])
            self.assertIn(pair["real"], O.BREAK_CAPABLE)
            self.assertNotIn(apparent, O.BREAK_CAPABLE)
            self.assertIn(pair["bite"], O.RESPONSES["bottom" if side == "top" else "top"])

    def test_eligibility_is_the_pair_table_crossed_with_the_own_track_tier(self):
        # FP-1 reads top_base only, FP-2 reads bottom_frame only; Partial (1) and Ready (2) qualify, None (0) does not.
        for tier, expected in ((0, []), (1, [A["ks"]]), (2, [A["ks"]])):
            self.assertEqual(O.eligible_real_ids(state("top", top_base=tier, bottom_frame=0), A["cf"]), expected)
            self.assertEqual(O.eligible_real_ids(state("top", top_base=0, bottom_frame=tier), A["cf"]), [])
        for tier, expected in ((0, []), (1, [A["rg"]]), (2, [A["rg"]])):
            self.assertEqual(O.eligible_real_ids(state("bottom", top_base=0, bottom_frame=tier), A["uh"]), expected)
            self.assertEqual(O.eligible_real_ids(state("bottom", top_base=tier, bottom_frame=0), A["uh"]), [])
        for apparent in (A["fl"], A["ks"], A["rg"]):
            self.assertEqual(O.eligible_real_ids(state("top", top_base=2, bottom_frame=2), apparent), [])

    def test_eligibility_ignores_stamina_and_funding(self):
        for stamina in (0, 2, 5, 6, 100):
            self.assertEqual(O.eligible_real_ids(state("top", initiator_stamina=stamina), A["cf"]), [A["ks"]])


class FundingTests(unittest.TestCase):
    L, M, H = "LOW", "MEDIUM", "HIGH"
    # Hand-written from the specification: stamina -> {requested: (effective, total)}; ("", 0) is a refusal.
    TABLE = {
        0: {"HIGH": ("", 0), "MEDIUM": ("", 0), "LOW": ("", 0)},
        2: {"HIGH": ("", 0), "MEDIUM": ("", 0), "LOW": ("", 0)},
        3: {"HIGH": ("", 0), "MEDIUM": ("", 0), "LOW": ("", 0)},
        5: {"HIGH": ("", 0), "MEDIUM": ("", 0), "LOW": ("", 0)},
        6: {"HIGH": ("LOW", 6), "MEDIUM": ("LOW", 6), "LOW": ("LOW", 6)},
        8: {"HIGH": ("LOW", 6), "MEDIUM": ("LOW", 6), "LOW": ("LOW", 6)},
        9: {"HIGH": ("LOW", 6), "MEDIUM": ("LOW", 6), "LOW": ("LOW", 6)},
        10: {"HIGH": ("MEDIUM", 10), "MEDIUM": ("MEDIUM", 10), "LOW": ("LOW", 6)},
        12: {"HIGH": ("MEDIUM", 10), "MEDIUM": ("MEDIUM", 10), "LOW": ("LOW", 6)},
        14: {"HIGH": ("MEDIUM", 10), "MEDIUM": ("MEDIUM", 10), "LOW": ("LOW", 6)},
        15: {"HIGH": ("HIGH", 15), "MEDIUM": ("MEDIUM", 10), "LOW": ("LOW", 6)},
        16: {"HIGH": ("HIGH", 15), "MEDIUM": ("MEDIUM", 10), "LOW": ("LOW", 6)},
    }

    def test_the_boundary_table_literal(self):
        for stamina, row in self.TABLE.items():
            for requested, expected in row.items():
                self.assertEqual(O.feint_funding(stamina, requested), expected, (stamina, requested))

    def test_the_full_attempt_agrees_with_the_table_and_charges_once(self):
        for stamina, row in self.TABLE.items():
            for requested, (effective, total) in row.items():
                snapshot = state("top", initiator_stamina=stamina)
                match, result = feint(snapshot, R["hf"], requested, "MEDIUM")
                if total == 0:
                    self.assertEqual(result, {"error": "feint_requires_funding"}, (stamina, requested))
                    self.assertEqual(match.snapshot(), snapshot)  # all-or-nothing: nothing charged, nothing moved
                    continue
                self.assertEqual((result["initiator_effective"], result["initiator_charged"], result["initiator_effective_cost"]),
                                 (effective, total, total - 3), (stamina, requested))
                self.assertEqual(result["feint"]["surcharge"], 3)
                self.assertEqual(result["feint"]["surcharge_charged"], 3)
                self.assertEqual(result["feint"]["total_cost"], total)
                self.assertEqual(match.snapshot()["fighters"][TOP]["stamina_current"], stamina - total)  # charged exactly once
                self.assertEqual(result["responder_charged"], 7)  # the normal response policy: no surcharge for the responder
                self.assertEqual(result["responder_waived"], 0)

    def test_a_direct_technique_keeps_its_costs_and_the_feint_is_the_surcharge_above_it(self):
        self.assertEqual({k: O.COSTS[k] for k in O.COMMITMENTS}, {"LOW": 3, "MEDIUM": 7, "HIGH": 12})
        for requested, direct_cost, feint_cost in (("LOW", 3, 6), ("MEDIUM", 7, 10), ("HIGH", 12, 15)):
            _, d = direct(state(), A["ks"], R["hf"], requested)
            _, f = feint(state(), R["hf"], requested)
            self.assertEqual((d["initiator_charged"], f["initiator_charged"]), (direct_cost, feint_cost))

    def test_an_unfunded_attacker_may_attack_directly_but_cannot_feint(self):
        for stamina in (3, 4, 5):  # LOW is affordable: a funded direct technique, not a waiver
            snapshot = state("top", initiator_stamina=stamina)
            _, d = direct(snapshot, A["cf"], R["hf"], "HIGH")
            self.assertEqual((d["initiator_effective"], d["initiator_charged"], d["responder_waived"]), ("LOW", 3, 0))
            self.assertEqual(feint(snapshot, R["hf"], "HIGH")[1], {"error": "feint_requires_funding"})
        snapshot = state("top", initiator_stamina=2)
        _, d = direct(snapshot, A["cf"], R["hf"], "HIGH")
        self.assertEqual((d["initiator_effective"], d["initiator_charged"], d["responder_waived"]), ("", 0, 7))  # Rule 1 applies only here
        self.assertEqual(feint(snapshot, R["hf"], "HIGH")[1], {"error": "feint_requires_funding"})

    def test_a_funded_feint_never_triggers_the_rule_one_waiver(self):
        for stamina in range(6, 41):
            for requested in O.COMMITMENTS:
                result = feint(state("top", initiator_stamina=stamina), R["hf"], requested)[1]
                self.assertEqual(result["responder_waived"], 0)
                self.assertNotEqual(result["initiator_effective"], "")

    def test_latch_edges_are_crossed_by_the_combined_spend(self):
        # LOW feint costs 6: from 31 the attacker lands on 25 (<= 25, latched); from 32 on 26 (not latched).
        low = feint(state("top", initiator_stamina=31), R["hf"], "LOW")[0].snapshot()["fighters"][TOP]
        self.assertEqual((low["stamina_current"], low["exhaustion_latched"]), (25, True))
        high = feint(state("top", initiator_stamina=32), R["hf"], "LOW")[0].snapshot()["fighters"][TOP]
        self.assertEqual((high["stamina_current"], high["exhaustion_latched"]), (26, False))

    def test_exhaustion_is_captured_before_the_charge_and_shifts_the_real_grade(self):
        # attacker 31 is Tired (not Exhausted) before a LOW feint that latches it: no exhaustion modifier this exchange.
        _, tired = feint(state("top", initiator_stamina=31), R["hf"], "LOW")
        self.assertEqual((tired["initiator_band"], tired["exhaustion_modifier"]), ("Tired", 0))
        # an attacker already latched at 20 (Exhausted) takes -1; a latched responder gives the attacker +1.
        _, exhausted = feint(state("top", initiator_stamina=20), R["hf"], "MEDIUM")
        self.assertEqual((exhausted["initiator_band"], exhausted["exhaustion_modifier"]), ("Exhausted", -1))
        _, helped = feint(state("top", responder_stamina=20), R["hf"], "MEDIUM")
        self.assertEqual((helped["responder_band"], helped["exhaustion_modifier"]), ("Exhausted", 1))


class GradePipelineLiteralTests(unittest.TestCase):
    def pick(self, result, *keys):
        return {key: result[key] for key in keys}

    def test_fp1_at_the_neutral_state_against_each_response(self):
        # Hip Frame: raw 1; positional 0; attack (Partial) 0 -> 1; no defense; not a bite -1 -> 0; no exhaustion; MEDIUM no magnitude; no undercommitment.
        match, result = feint(state(), R["hf"])
        self.assertEqual(self.pick(result, "action_id", "raw_grade", "grade_after_positional", "grade_after_attack", "grade_after_defense",
                                   "grade_after_exhaustion", "grade_after_magnitude", "final_grade", "axis_after", "band_after", "exit_destination"),
                         {"action_id": A["ks"], "raw_grade": 1, "grade_after_positional": 1, "grade_after_attack": 1, "grade_after_defense": 1,
                          "grade_after_exhaustion": 0, "grade_after_magnitude": 0, "final_grade": 0, "axis_after": 5, "band_after": 0, "exit_destination": ""})
        self.assertEqual(result["feint"], {"apparent_action_id": A["cf"], "real_action_id": A["ks"], "bite_response_id": R["uf"], "bit": False,
                                           "modifier": -1, "grade_before": 1, "grade_after": 0, "surcharge": 3, "surcharge_charged": 3,
                                           "total_cost": 10, "exit_capped": False})
        self.assertEqual((result["initiator_charged"], result["responder_charged"]), (10, 7))
        self.assertEqual(match.snapshot()["fighters"][TOP]["stamina_current"], 90)
        self.assertEqual(match.snapshot()["fighters"][BOT]["stamina_current"], 93)
        # Underhook Fight (the bite): raw 2; +1 saturates at 2; final 2; axis 5 + 20 = 25 (below the pass line 30: no exit).
        match, result = feint(state(), R["uf"])
        self.assertEqual(self.pick(result, "raw_grade", "grade_after_defense", "grade_after_exhaustion", "final_grade", "axis_after", "band_after",
                                   "exit_destination", "readiness_changes"),
                         {"raw_grade": 2, "grade_after_defense": 2, "grade_after_exhaustion": 2, "final_grade": 2, "axis_after": 25, "band_after": 1,
                          "exit_destination": "", "readiness_changes": []})
        self.assertEqual((result["feint"]["bit"], result["feint"]["modifier"], result["feint"]["grade_after"]), (True, 1, 2))
        # Knee Shield (a call): raw -2; defense (MEDIUM, bottom_frame Partial) 0; -1 saturates at -2; final -2; axis -15 (band -1);
        # the governed MEDIUM defense wears bottom_frame because final != 0.
        match, result = feint(state(), R["ks"])
        self.assertEqual(self.pick(result, "raw_grade", "defense_strength_tier", "defense_readiness_shift", "final_grade", "axis_after", "band_after",
                                   "readiness_changes"),
                         {"raw_grade": -2, "defense_strength_tier": 1, "defense_readiness_shift": 0, "final_grade": -2, "axis_after": -15,
                          "band_after": -1, "readiness_changes": ["bottom_frame:Partial->None:knee_slice"]})
        self.assertEqual(match.snapshot()["initiator"], "bottom")  # initiative flips once

    def test_fp2_at_the_neutral_state_against_each_response(self):
        snapshot = state("bottom")
        # Head Control (the bite): raw 2, +1 saturates at 2, final 2; Bottom axis 5 - 20 = -15 (band -1); Recover Guard builds: top_base -1.
        _, result = feint(snapshot, R["hc"])
        self.assertEqual(self.pick(result, "action_id", "raw_grade", "final_grade", "axis_after", "band_after", "exit_destination", "readiness_changes"),
                         {"action_id": A["rg"], "raw_grade": 2, "final_grade": 2, "axis_after": -15, "band_after": -1, "exit_destination": "",
                          "readiness_changes": ["top_base:Partial->None:recover_guard"]})
        # Hip Pressure: raw 1, not a bite -1 -> 0; axis unchanged.
        _, result = feint(snapshot, R["hp"])
        self.assertEqual(self.pick(result, "raw_grade", "grade_after_defense", "final_grade", "axis_after", "readiness_changes"),
                         {"raw_grade": 1, "grade_after_defense": 1, "final_grade": 0, "axis_after": 5, "readiness_changes": []})
        # Knee Pin (a call): raw -2, defense 0 (Partial), -1 saturates at -2; axis 5 + 20 = 25; the governed defense wears top_base.
        _, result = feint(snapshot, R["kp"])
        self.assertEqual(self.pick(result, "raw_grade", "final_grade", "axis_after", "band_after", "readiness_changes"),
                         {"raw_grade": -2, "final_grade": -2, "axis_after": 25, "band_after": 1,
                          "readiness_changes": ["top_base:Partial->None:recover_guard"]})

    def test_sequential_saturation_not_a_combined_modifier(self):
        # An Exhausted (20) attacker at Ready (top_base 2) feints into the bite: raw 2 -> attack +1 saturates at 2 -> feint +1 saturates at 2
        # -> exhaustion -1 gives 1. A single combined modifier (+1 +1 -1 = +1 on raw 2 -> 3 -> 2) would give 2.
        snapshot = state("top", top_base=2, initiator_stamina=20)
        match, result = feint(snapshot, R["uf"])
        self.assertEqual(self.pick(result, "raw_grade", "attack_readiness_shift", "grade_after_attack", "grade_after_defense", "exhaustion_modifier",
                                   "grade_after_exhaustion", "final_grade"),
                         {"raw_grade": 2, "attack_readiness_shift": 1, "grade_after_attack": 2, "grade_after_defense": 2, "exhaustion_modifier": -1,
                          "grade_after_exhaustion": 1, "final_grade": 1})
        self.assertEqual((result["feint"]["grade_before"], result["feint"]["grade_after"]), (2, 2))
        self.assertEqual((result["axis_after"], result["readiness_changes"]), (15, ["top_base:Ready->Partial:knee_slice"]))  # consumption of one tier
        self.assertEqual(match.snapshot()["fighters"][TOP], {"stamina_current": 10, "stamina_maximum": 100, "exhaustion_latched": True,
                                                              "behavior_remainder_units": 0})

    def test_the_modifier_lands_after_readiness_and_before_exhaustion_in_the_floor_direction(self):
        # Floor: raw -2 (Knee Shield, Ready bottom_frame -1 shift is toward the initiator...) is checked via the record's step grades.
        snapshot = state("top", bottom_frame=2)
        _, result = feint(snapshot, R["ks"])
        # raw -2; defense Ready (MEDIUM paid) -> shift -1 -> -3 saturates at -2; feint -1 -> -2; final -2.
        self.assertEqual(self.pick(result, "grade_after_attack", "defense_readiness_shift", "grade_after_defense", "final_grade"),
                         {"grade_after_attack": -2, "defense_readiness_shift": -1, "grade_after_defense": -2, "final_grade": -2})

    def test_a_direct_technique_receives_no_feint_modifier(self):
        for response in (R["hf"], R["uf"], R["ks"]):
            _, direct_result = direct(state(), A["ks"], response)
            self.assertNotIn("feint", direct_result)
            self.assertEqual(direct_result["grade_after_defense"], direct_result["grade_after_exhaustion"])

    def test_the_real_technique_reads_its_own_readiness_not_the_apparent_ones(self):
        # Ready top_base: Knee Slice (real) gets +1 and consumes a tier; a direct Crossface would not.
        _, result = feint(state("top", top_base=2), R["hf"])
        self.assertEqual((result["attack_readiness_shift"], result["readiness_changes"]), (1, ["top_base:Ready->Partial:knee_slice"]))
        # A direct Crossface is not prepared: no attack shift, no consumption; its success weakens the opponent's frame instead.
        _, crossface = direct(state("top", top_base=2), A["cf"], R["hf"])
        self.assertEqual((crossface["attack_readiness_shift"], crossface["readiness_changes"]), (0, ["bottom_frame:Partial->None:crossface"]))

    def test_the_apparent_technique_never_resolves_builds_or_appears_in_the_history(self):
        match, _ = feint(state(), R["uf"])
        history = match.snapshot()["history"]
        self.assertEqual(history["initiated_action_history"], [A["ks"]])
        self.assertEqual(history["raw_grade_history"], ["Strong Success"])
        # Crossface would weaken bottom_frame on a success; the feint (real Knee Slice) builds nothing.
        self.assertEqual(match.snapshot()["bottom_frame"], 1)
        self.assertEqual(history["readiness_change_history"], [])


class ExitCapTests(unittest.TestCase):
    def edge(self):
        return state("top", axis=20, band=1)

    def test_a_low_effective_feint_cannot_exit_but_still_moves_the_axis_and_flips_initiative(self):
        # raw 2 (Underhook Fight); bite keeps 2; LOW magnitude on Strong Success -1 -> 1; MEDIUM defender not under-committed; final 1;
        # proposed 20 + 10 = 30 reaches the pass line, but the cap removes the exit. Clamp keeps 30; band 1 -> 2.
        match, result = feint(self.edge(), R["uf"], "LOW", "MEDIUM")
        self.assertEqual((result["initiator_effective"], result["final_grade"], result["axis_proposed"], result["axis_after"], result["band_after"]),
                         ("LOW", 1, 30, 30, 2))
        self.assertEqual((result["exit_destination"], result["feint"]["exit_capped"]), ("", True))
        snapshot = match.snapshot()
        self.assertEqual((snapshot["exit_destination"], snapshot["exit_reason"], snapshot["initiator"]), ("", "", "bottom"))
        self.assertEqual(match.open_window()["error"], "")  # the segment continues

    def test_the_same_attack_as_a_direct_low_technique_still_exits(self):
        _, result = direct(self.edge(), A["ks"], R["uf"], "LOW", "MEDIUM")
        self.assertEqual((result["final_grade"], result["exit_destination"]), (1, "Side Control"))

    def test_medium_and_high_feints_follow_the_normal_exit_rules(self):
        for commitment, total in (("MEDIUM", 10), ("HIGH", 15)):
            match, result = feint(self.edge(), R["uf"], commitment, "MEDIUM")
            self.assertEqual((result["final_grade"], result["axis_after"], result["exit_destination"], result["initiator_charged"]),
                             (2, 40, "Side Control", total))
            self.assertFalse(result["feint"]["exit_capped"])
            self.assertEqual(match.snapshot()["exit_reason"], "Knee Slice reached the pass line with final grade Strong Success")
            self.assertEqual(match.snapshot()["initiator"], "top")  # an exit does not flip initiative

    def test_a_downgraded_feint_is_capped_by_its_funded_effective_commitment_not_its_request(self):
        # requested HIGH from stamina 8 is funded as LOW (8 - 3 = 5): the cap applies to the effective commitment.
        _, result = feint(state("top", axis=20, band=1, initiator_stamina=8), R["uf"], "HIGH", "MEDIUM")
        self.assertEqual((result["commitment_requested"], result["initiator_effective"], result["exit_destination"]), ("HIGH", "LOW", ""))
        # ...and a LOW request from fresh stamina is capped too.
        _, again = feint(self.edge(), R["uf"], "LOW", "MEDIUM")
        self.assertEqual(again["exit_destination"], "")

    def test_the_cap_applies_to_the_bottom_pair_as_well(self):
        # Bottom at axis -20 band -1: Recover Guard vs Head Control (bite): final 2 -> proposed -40: MEDIUM escapes (Closed Guard at Strong Success).
        medium = feint(state("bottom", axis=-20, band=-1), R["hc"], "MEDIUM", "MEDIUM")[1]
        self.assertEqual((medium["final_grade"], medium["exit_destination"]), (2, "Closed Guard"))
        low = feint(state("bottom", axis=-20, band=-1), R["hc"], "LOW", "MEDIUM")[1]
        # LOW magnitude on Strong Success -1 -> 1; proposed -30 reaches the escape line but the cap removes the exit.
        self.assertEqual((low["final_grade"], low["axis_proposed"], low["exit_destination"], low["feint"]["exit_capped"]), (1, -30, "", True))


class TimeoutFallbackTests(unittest.TestCase):
    def test_the_published_fallback_by_defender_role(self):
        self.assertEqual(O.TIMEOUT_FALLBACK, {"bottom": (R["hf"], "LOW"), "top": (R["hp"], "LOW")})

    def test_undercommitment_comes_only_from_the_existing_mechanics(self):
        # Top attacks Crossface; the bottom defender times out into Hip Frame at LOW. Raw 1, no shifts:
        # attacker LOW vs LOW: no bonus -> 1; MEDIUM vs LOW: +1 -> 2; HIGH vs LOW: magnitude +1 (Success) then +1 saturates -> 2.
        expected = {"LOW": (0, 1, 3), "MEDIUM": (1, 2, 7), "HIGH": (1, 2, 12)}
        for commitment, (under, final, charged) in expected.items():
            _, result = direct(state(), A["cf"], R["hf"], commitment, "LOW")
            self.assertEqual((result["undercommitment_modifier"], result["final_grade"], result["initiator_charged"], result["responder_charged"]),
                             (under, final, charged, 3), commitment)
        # Bottom attacks Underhook; the top defender times out into Hip Pressure at LOW: raw 0 -> MEDIUM +1 -> 1.
        _, result = direct(state("bottom"), A["uh"], R["hp"], "MEDIUM", "LOW")
        self.assertEqual((result["raw_grade"], result["undercommitment_modifier"], result["final_grade"]), (0, 1, 1))

    def test_the_fallback_adds_no_second_bonus_and_matches_an_active_identical_response(self):
        for side, apparent in (("top", A["cf"]), ("bottom", A["uh"])):
            defender = "bottom" if side == "top" else "top"
            response, commitment = O.TIMEOUT_FALLBACK[defender]
            for requested in O.COMMITMENTS:
                snapshot = state(side)
                _, defaulted = direct(snapshot, apparent, response, requested, commitment)
                _, active = direct(snapshot, apparent, response, requested, "LOW")
                self.assertEqual(defaulted, active)  # a defaulted response is indistinguishable in the engine: no timeout-specific rule exists
                # the only difference from a MEDIUM response of the same technique is the existing undercommitment step
                _, medium = direct(snapshot, apparent, response, requested, "MEDIUM")
                self.assertLessEqual(defaulted["final_grade"] - medium["final_grade"], 1)
                self.assertEqual(defaulted["undercommitment_modifier"], 1 if O.RANK[requested] > 1 else 0)

    def test_the_fallback_does_not_touch_the_clock_the_window_or_initiative_beyond_an_ordinary_exchange(self):
        match = O.HalfGuard.from_snapshot(state())
        opened = match.open_window()
        clock = match.s["clock_seconds"]
        result = match.submit(opened["window_id"], TOP, A["cf"], R["hf"], "MEDIUM", "LOW")
        self.assertEqual(match.s["clock_seconds"], clock)
        self.assertEqual((match.s["window_open"], match.s["initiator"], result["kind"]), (False, "bottom", "exchange"))
        self.assertEqual(match.s["history"]["reset_window_history"], [])

    def test_the_fallback_against_a_feint_follows_the_same_bite_rules(self):
        # FP-1 against Hip Frame (not a bite): raw 1 -1 -> 0; attacker MEDIUM vs LOW +1 -> 1; charges 10 / 3.
        _, result = feint(state(), R["hf"], "MEDIUM", "LOW")
        self.assertEqual((result["final_grade"], result["undercommitment_modifier"], result["initiator_charged"], result["responder_charged"]), (1, 1, 10, 3))
        self.assertFalse(result["feint"]["bit"])
        # FP-2 against Hip Pressure: raw 1 -1 -> 0; +1 -> 1.
        _, result = feint(state("bottom"), R["hp"], "MEDIUM", "LOW")
        self.assertEqual((result["final_grade"], result["undercommitment_modifier"], result["feint"]["bit"]), (1, 1, False))

    def test_an_unfundable_fallback_follows_the_existing_unfunded_handling(self):
        # The defender has 2 stamina: LOW (3) is unaffordable -> unfunded, charged 0 (no free stamina), rank 0 < MEDIUM -> +1 once.
        _, result = direct(state(responder_stamina=2), A["cf"], R["hf"], "MEDIUM", "LOW")
        self.assertEqual((result["responder_effective"], result["responder_effective_cost"], result["responder_charged"], result["responder_waived"],
                          result["undercommitment_modifier"]), ("", 0, 0, 0, 1))


class AdmissionTests(unittest.TestCase):
    def test_every_refusal_is_the_documented_code_and_leaves_the_state_byte_identical(self):
        expected = {
            "real equals apparent (top)": "feint_real_equals_apparent", "real equals apparent (crossface)": "feint_real_equals_apparent",
            "flatten to knee slice is excluded": "feint_not_supported", "knee slice to crossface is not a pair": "feint_not_supported",
            "crossface to flatten (not break-capable) is not a pair": "feint_not_supported", "bottom real from the top side": "incorrect_action_side_or_kind",
            "unknown real": "unknown_action", "a response id as the real": "incorrect_action_side_or_kind",
            "underhook to knee slice crosses sides": "incorrect_action_side_or_kind",
            "underhook to recover guard eligible but recover to underhook is not": "feint_not_supported",
            "top apparent with None track": "feint_not_eligible", "bottom apparent with None track": "feint_not_eligible",
            "the other side's track does not help (top)": "feint_not_eligible", "the other side's track does not help (bottom)": "feint_not_eligible",
            "unfunded below the surcharge (top, 2)": "feint_requires_funding", "unfunded below the surcharge (top, 0)": "feint_requires_funding",
            "unfunded: commitment unaffordable after the surcharge (top, 5)": "feint_requires_funding",
            "unfunded: commitment unaffordable after the surcharge (bottom, 5)": "feint_requires_funding",
            "invalid commitment still reported first": "invalid_commitment", "invalid response commitment before the feint checks": "invalid_response_commitment",
            "unknown apparent before the feint checks": "unknown_action", "foreign apparent before the feint checks": "incorrect_action_side_or_kind",
            "unknown response before the feint checks": "unknown_response", "foreign response before the feint checks": "incorrect_response_side_or_kind",
            "equality before the real id's own shape": "feint_real_equals_apparent", "not supported before not eligible": "feint_not_supported",
            "not eligible before funding": "feint_not_eligible", "a terminal state refuses a feint": "terminal_exchange",
        }
        cases = F.refusal_cases()
        self.assertEqual({label for label, _, _ in cases}, set(expected))
        for label, snapshot, command in cases:
            match = O.HalfGuard.from_snapshot(snapshot)
            result = match.attempt(command["action_id"], command["response_id"], command["commitment"], command["response_commitment"], command["real_action_id"])
            self.assertEqual(result, {"error": expected[label]}, label)
            self.assertEqual(match.snapshot(), snapshot, label)

    def test_submit_level_refusals_and_a_refused_feint_keeps_the_window_open(self):
        match = O.HalfGuard.from_snapshot(state())
        window = match.open_window()["window_id"]
        before = match.snapshot()
        for args, code in (((window, TOP, "", "", "", "", A["ks"]), "feint_without_action"),
                           ((window, TOP, A["cf"], R["hf"], "MEDIUM", "MEDIUM", A["cf"]), "feint_real_equals_apparent"),
                           ((window, BOT, A["cf"], R["hf"], "MEDIUM", "MEDIUM", A["ks"]), "not_initiator"),
                           ((window + 1, TOP, A["cf"], R["hf"], "MEDIUM", "MEDIUM", A["ks"]), "stale_window"),
                           ((window, "", A["cf"], R["hf"], "MEDIUM", "MEDIUM", A["ks"]), "missing_fighter_id"),
                           ((window, TOP, "", R["hf"], "", "", A["ks"]), "response_without_action"),
                           ((window, TOP, "", "", "LOW", "", A["ks"]), "commitment_without_action")):
            self.assertEqual(match.submit(*args), {"error": code}, code)
            self.assertEqual(match.snapshot(), before, code)
        self.assertEqual(match.submit(window, TOP, A["cf"], R["hf"], "MEDIUM", "MEDIUM", A["ks"])["kind"], "exchange")

    def test_a_direct_command_never_takes_the_feint_path(self):
        for response in (R["hf"], R["uf"], R["ks"]):
            m1 = O.HalfGuard.from_snapshot(state())
            m2 = O.HalfGuard.from_snapshot(state())
            self.assertEqual(m1.attempt(A["ks"], response, "MEDIUM", "MEDIUM"), m2.attempt(A["ks"], response, "MEDIUM", "MEDIUM", ""))


class PublicInformationTests(unittest.TestCase):
    def test_the_view_literal_for_a_top_and_a_bottom_initiator(self):
        self.assertEqual(O.public_intent_view(state(), A["cf"], "", 3),
                         {"position_id": "half_guard", "window_id": 0, "intent_serial": 3, "initiator_id": TOP, "responder_id": BOT,
                          "apparent_technique_id": A["cf"], "apparent_technique_name": "Crossface", "commitment_requested": "MEDIUM",
                          "eligible_real_ids": [A["ks"]], "response_ids": [R["hf"], R["uf"], R["ks"]]})
        self.assertEqual(O.public_intent_view(state("bottom", bottom_frame=2), A["uh"], "HIGH", 1),
                         {"position_id": "half_guard", "window_id": 0, "intent_serial": 1, "initiator_id": BOT, "responder_id": TOP,
                          "apparent_technique_id": A["uh"], "apparent_technique_name": "Underhook", "commitment_requested": "HIGH",
                          "eligible_real_ids": [A["rg"]], "response_ids": [R["hc"], R["hp"], R["kp"]]})
        self.assertEqual(O.public_intent_view(state(), A["fl"], "LOW", 1)["eligible_real_ids"], [])
        self.assertEqual(O.public_intent_view(state(top_base=0), A["cf"], "LOW", 1)["eligible_real_ids"], [])

    def test_the_view_cannot_depend_on_the_real_technique_the_flag_or_the_funding(self):
        parameters = list(inspect.signature(O.public_intent_view).parameters)
        self.assertEqual(parameters, ["state", "apparent", "commitment", "intent_serial"])
        view = O.public_intent_view(state(), A["cf"], "HIGH", 1)
        self.assertEqual(sorted(view), sorted(["position_id", "window_id", "intent_serial", "initiator_id", "responder_id", "apparent_technique_id",
                                               "apparent_technique_name", "commitment_requested", "eligible_real_ids", "response_ids"]))

    def test_a_direct_command_and_an_eligible_feint_are_indistinguishable_in_every_public_state(self):
        # For every tier pair, requested commitment and initiator stamina the PUBLIC view of Crossface sealed as a direct command equals the view of
        # Crossface sealed as the FP-1 feint (the same pure function of public inputs), and so does every other public surface of the oracle state
        # before the exchange: the snapshot is untouched by sealing.
        for top_base in (0, 1, 2):
            for bottom_frame in (0, 1, 2):
                for stamina in (2, 8, 14, 100):
                    snapshot = state("top", top_base=top_base, bottom_frame=bottom_frame, initiator_stamina=stamina)
                    for commitment in ("", "LOW", "MEDIUM", "HIGH"):
                        as_direct = O.public_intent_view(snapshot, A["cf"], commitment, 4)
                        as_feint = O.public_intent_view(snapshot, A["cf"], commitment, 4)
                        self.assertEqual(as_direct, as_feint)
                        self.assertEqual(json.dumps(as_direct, sort_keys=True), json.dumps(as_feint, sort_keys=True))

    def test_the_menu_a_defender_sees_does_not_depend_on_the_hidden_real_technique(self):
        for response in O.RESPONSES["bottom"]:
            for real in ("", A["ks"]):
                match = O.HalfGuard.from_snapshot(state())
                errors = match.attempt(A["cf"], response, "MEDIUM", "MEDIUM", real)["error"]
                self.assertEqual(errors, "")  # every response in the public menu is legal against the direct and the feint command alike


class DirectCompatibilityTests(unittest.TestCase):
    def test_the_qualified_direct_fixture_is_byte_for_byte_unchanged(self):
        sys.path.insert(0, os.path.join(REPO, "GODOT_V1", "tests"))
        import generate_half_guard_reference as generator
        with tempfile.TemporaryDirectory() as directory:
            summary = generator.write(os.path.join(directory, "direct.jsonl"))
        self.assertEqual(summary["sha256"], DIRECT_FIXTURE_SHA256)
        self.assertEqual((summary["scenarios"], summary["operations"], summary["comparisons"]), (16858, 16437, 679622))

    def test_no_direct_record_gained_a_key(self):
        for row in S.exchange_rows()[:200] + S.break_rows()[:200]:
            self.assertNotIn("feint", row["expected"])


class ReplayAndFixtureTests(unittest.TestCase):
    def test_every_feint_trajectory_replays_identically_twice(self):
        for name, entry, commands in F.trajectories():
            first = O.replay(copy.deepcopy(entry), copy.deepcopy(commands))
            second = O.replay(copy.deepcopy(entry), copy.deepcopy(commands))
            self.assertEqual(O.canonical_json(first), O.canonical_json(second), name)

    def test_trajectory_literals(self):
        rows = {row["name"]: row for row in F.trajectory_rows()}
        # A feint is one window, one exchange: window ids 1, 2, 3 with strict alternation and one history entry each.
        final = rows["feint_then_direct_then_bottom_feint"]["expected"]["final"]
        self.assertEqual(final["window_id"], 3)
        self.assertEqual(final["history"]["initiated_action_history"], [A["ks"], A["rg"], A["cf"]])
        self.assertEqual((final["history"]["top_initiation_count"], final["history"]["bottom_initiation_count"]), (2, 1))
        # Exits: a MEDIUM feint exits to Side Control, a LOW feint does not.
        self.assertEqual(rows["medium_feint_exits_to_side_control_from_a_prepared_edge"]["expected"]["final"]["exit_destination"], "Side Control")
        self.assertEqual(rows["low_feint_cannot_exit"]["expected"]["final"]["exit_destination"], "")
        self.assertEqual(rows["bottom_feint_exits_by_escape"]["expected"]["final"]["exit_destination"], "Closed Guard")
        # An unfunded attacker's feint is refused and then the same window accepts a direct attack.
        results = rows["unfunded_attacker_cannot_feint_but_can_attack_directly"]["expected"]["results"]
        self.assertEqual([r.get("error", "") for r in results], ["", "feint_requires_funding", ""])
        # The clock moves only when a window opens.
        clock = rows["clock_advances_only_when_a_window_opens"]["expected"]["final"]["clock_seconds"]
        self.assertEqual(clock, 0)

    def test_the_fixture_generator_is_byte_identical_across_runs_and_hash_seeds(self):
        sys.path.insert(0, os.path.join(REPO, "GODOT_V1", "tests"))
        import generate_half_guard_feint_reference as generator
        with tempfile.TemporaryDirectory() as directory:
            first, second = os.path.join(directory, "a.jsonl"), os.path.join(directory, "b.jsonl")
            summary_a, summary_b = generator.write(first), generator.write(second)
            self.assertEqual(summary_a, summary_b)
            with open(first, "rb") as a, open(second, "rb") as b:
                self.assertEqual(hashlib.sha256(a.read()).hexdigest(), hashlib.sha256(b.read()).hexdigest())
            self.assertGreater(summary_a["scenarios"], 6000)

    def test_every_grid_row_obeys_the_cap_funding_and_history_invariants(self):
        for row in F.grid_rows() + F.funding_rows():
            expected = row["expected"]
            if expected["error"]:
                self.assertEqual(row["final"], row["snapshot"])
                continue
            feint_record = expected["feint"]
            self.assertEqual(expected["initiator_charged"], feint_record["total_cost"])
            self.assertEqual(expected["responder_waived"], 0)
            self.assertEqual(feint_record["modifier"], 1 if feint_record["bit"] else -1)
            if expected["initiator_effective"] == "LOW":
                self.assertEqual(expected["exit_destination"], "")
            if feint_record["exit_capped"]:
                self.assertEqual(expected["initiator_effective"], "LOW")
                self.assertGreaterEqual(expected["final_grade"], 1)
            self.assertEqual(row["final"]["history"]["initiated_action_history"][-1], expected["action_id"])
            self.assertEqual(len(row["final"]["history"]["initiated_action_history"]), 1)
            self.assertEqual(row["final"]["window_id"], row["snapshot"]["window_id"])
            self.assertEqual(row["final"]["clock_seconds"], row["snapshot"]["clock_seconds"])


class RulesSheetAndIndependenceTests(unittest.TestCase):
    def sheet(self):
        with open(RULES, encoding="utf-8") as handle:
            return handle.read()

    def test_the_sheet_states_the_pairs_the_surcharge_the_cap_and_the_fallback(self):
        text = self.sheet()
        section = text[text.index("## 13."):]
        for needle in ("Crossface → Knee Slice", "Underhook → Recover Guard", "top_base ≥ 1", "bottom_frame ≥ 1", "half_guard.bottom_response.underhook_fight",
                       "half_guard.top_response.head_control", "`s = +3`", "feint_requires_funding", "cannot produce an exit", "half_guard.bottom_response.hip_frame",
                       "half_guard.top_response.hip_pressure", "no** timeout-specific modifier", "Flatten → Knee Slice"):
            self.assertIn(needle, section, needle)

    def test_the_sheets_funding_table_equals_the_oracle(self):
        section = self.sheet()[self.sheet().index("**13.3"):]
        rows = re.findall(r"^\| (\d+) (?:– (\d+)|\+) \| (.*?) \| (.*?) \| (.*?) \|$", section, re.M)
        self.assertEqual([(low, high) for low, high, _, _, _ in rows], [("0", "5"), ("6", "9"), ("10", "14"), ("15", "")])

        def parse(cell):
            return ("", 0) if cell == "refused" else (cell.split(",")[0], int(cell.split("total ")[1]))

        for low_bound, high_bound, high, medium, low in rows:
            for stamina in range(int(low_bound), (int(high_bound) if high_bound else 60) + 1):
                for requested, cell in (("HIGH", high), ("MEDIUM", medium), ("LOW", low)):
                    self.assertEqual(O.feint_funding(stamina, requested), parse(cell), (stamina, requested))

    def test_the_oracle_modules_import_only_the_standard_library(self):
        for name in ("half_guard_v0.py", "half_guard_v0_feint_scenarios.py"):
            with open(os.path.join(HERE, "oracles", name), encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name, {"copy", "hashlib", "json", "math", "functools"}, name)
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module or "", {"", "half_guard_v0", "half_guard_v0_scenarios"}, name)
                    self.assertEqual(node.level in (0, 1), True)

    def test_the_oracle_uses_no_clock_randomness_or_io(self):
        with open(os.path.join(HERE, "oracles", "half_guard_v0.py"), encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertEqual(used & {"random", "time", "datetime", "open", "os", "sys", "input", "print", "eval", "exec"}, set())

if __name__ == "__main__":
    unittest.main()
