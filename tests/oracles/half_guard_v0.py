"""Independent, test-only Half Guard v0 oracle (B1b checkpoint).

Written from ``GODOT_V1/docs/HALF_GUARD_V0_RULES.md`` -- not from any GDScript and not from the Mount
engine. Standard library only: no ``bjj_game`` import, no file or network access, no randomness, no
clock. Plain dictionaries in, plain dictionaries out; every refusal leaves the state untouched.

This module is a *specification executor* for the provisional v0 prototype baseline. It is not a
claim about game balance. Section numbers (``S5.3`` ...) refer to the rules sheet.
"""
import copy
import hashlib
import json
import math

POSITION_ID = "half_guard"
MAXIMUM_EXACT = 9007199254740991
AXIS_MIN, AXIS_MAX, ENTRY_AXIS, ENTRY_BAND = -40, 40, 5, 0
STEP_TENTHS = 10
PASS_LINE, ESCAPE_LINE = 30, -30
COMMITMENTS = ("LOW", "MEDIUM", "HIGH")
COSTS = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
RANK = {"": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
TIER_NAMES = ("None", "Partial", "Ready")
BAND_NAMES = {-2: "BOTTOM_CONTROL", -1: "BOTTOM_EDGE", 0: "CONTESTED", 1: "TOP_EDGE", 2: "TOP_CONTROL"}
GRADE_NAMES = {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"}
# Godot's String.strip_edges (the engine behind BjjPositionContract.fighter_ids_error) strips exactly the code points 0x01..0x20 at
# either end; 0x7f, 0x85, 0xa0, the Unicode spaces and 0xfeff are NOT stripped (measured with Godot 4.7.2). A Godot String cannot hold NUL.
STRIP_EDGES_CHARACTERS = "".join(chr(code) for code in range(1, 33))
DEFAULT_COMMITMENT = "MEDIUM"

# ---- Catalog (S3) ---------------------------------------------------------------------------
TOP_ACTIONS = ("half_guard.top.crossface", "half_guard.top.flatten", "half_guard.top.knee_slice")
BOTTOM_ACTIONS = ("half_guard.bottom.underhook", "half_guard.bottom.recover_guard")
BOTTOM_RESPONSES = ("half_guard.bottom_response.hip_frame", "half_guard.bottom_response.underhook_fight",
                    "half_guard.bottom_response.knee_shield")
TOP_RESPONSES = ("half_guard.top_response.head_control", "half_guard.top_response.hip_pressure",
                 "half_guard.top_response.knee_pin")
ACTIONS = {"top": TOP_ACTIONS, "bottom": BOTTOM_ACTIONS}
RESPONSES = {"top": TOP_RESPONSES, "bottom": BOTTOM_RESPONSES}  # responses *owned by* that side
KNEE_SLICE, RECOVER_GUARD = TOP_ACTIONS[2], BOTTOM_ACTIONS[1]
KNEE_SHIELD, KNEE_PIN = BOTTOM_RESPONSES[2], TOP_RESPONSES[2]
BREAK_CAPABLE = (KNEE_SLICE, RECOVER_GUARD)
TECHNIQUE_NAMES = {TOP_ACTIONS[0]: "Crossface", TOP_ACTIONS[1]: "Flatten", KNEE_SLICE: "Knee Slice",
                   BOTTOM_ACTIONS[0]: "Underhook", RECOVER_GUARD: "Recover Guard"}
EXIT_DESTINATION_IDS = {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"}

# C1 grid (S3): initiator side -> action -> response -> raw grade from the initiator's point of view.
RAW = {
    "top": {
        TOP_ACTIONS[0]: {BOTTOM_RESPONSES[0]: 1, BOTTOM_RESPONSES[1]: -1, BOTTOM_RESPONSES[2]: 0},
        TOP_ACTIONS[1]: {BOTTOM_RESPONSES[0]: -1, BOTTOM_RESPONSES[1]: 1, BOTTOM_RESPONSES[2]: 1},
        TOP_ACTIONS[2]: {BOTTOM_RESPONSES[0]: 1, BOTTOM_RESPONSES[1]: 2, BOTTOM_RESPONSES[2]: -2},
    },
    "bottom": {
        BOTTOM_ACTIONS[0]: {TOP_RESPONSES[0]: -1, TOP_RESPONSES[1]: 0, TOP_RESPONSES[2]: 1},
        BOTTOM_ACTIONS[1]: {TOP_RESPONSES[0]: 2, TOP_RESPONSES[1]: 1, TOP_RESPONSES[2]: -2},
    },
}
OWN_TRACK = {"top": "top_base", "bottom": "bottom_frame"}  # the track a side's fighter owns
# Governed responses: response id -> the track of the *responder* it reads (option M).
GOVERNED = {KNEE_SHIELD: "bottom_frame", KNEE_PIN: "top_base"}
ATTACK_SHIFT = {2: 1, 1: 0, 0: -1}   # N-3
DEFENSE_SHIFT = {2: -1, 1: 0, 0: 2}  # N-4
# Builders / weakeners on final >= Success (N-5): action -> (track, delta)
BUILD = {TOP_ACTIONS[0]: ("bottom_frame", -1), TOP_ACTIONS[1]: ("top_base", 1),
         BOTTOM_ACTIONS[0]: ("bottom_frame", 1), RECOVER_GUARD: ("top_base", -1)}


def shift(grade, steps):
    return max(-2, min(2, grade + steps))


# ---- Axis and bands (S2) ----------------------------------------------------------------------
def initial_band(axis):
    magnitude = abs(axis)
    level = 0 if magnitude < 10 else (1 if magnitude < 25 else 2)
    return level if axis >= 0 else -level


def band_step(axis, band):
    """One hysteresis rule application, or None when no rule matches."""
    if band == 0:
        if axis >= 12:
            return 1
        if axis <= -12:
            return -1
    elif band == 1:
        if axis >= 27:
            return 2
        if axis <= 8:
            return 0
    elif band == 2:
        if axis <= 23:
            return 1
    elif band == -1:
        if axis >= -8:
            return 0
        if axis <= -27:
            return -2
    elif band == -2:
        if axis >= -23:
            return -1
    return None


def band_update(axis, band):
    while True:
        nxt = band_step(axis, band)
        if nxt is None:
            return band
        band = nxt


def legal_pair(axis, band):
    return {0: -12 < axis < 12, 1: 8 < axis < 27, 2: axis > 23, -1: -27 < axis < -8, -2: axis < -23}.get(band, False)


def transition_for(label):
    """The accepted BjjPositionContract.Transition.fields() dictionary for a Half Guard exit label ('' = no transition)."""
    if label == "":
        return {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": False}
    return {"kind": "exit", "raw_destination": label, "destination_position_id": EXIT_DESTINATION_IDS.get(label, ""),
            "resolved": label in EXIT_DESTINATION_IDS}


def authority_of(axis, role_map):
    if axis > 0:
        return role_map["top"]
    if axis < 0:
        return role_map["bottom"]
    return ""


# ---- Stamina (S2, frozen float formulas restated literally) ----------------------------------
def enter_threshold(maximum):
    return math.floor(maximum * 0.25)


def recover_threshold(maximum):
    return math.ceil(maximum * 0.35)


def latch_after(current, maximum, latched):
    """Literal two-state hysteresis model; independent of any pool object."""
    if latched:
        return not (current >= recover_threshold(maximum))
    return current <= enter_threshold(maximum)


def stamina_band(current, maximum, latched):
    if latched:
        return "Exhausted"
    ratio = current / maximum
    if ratio > 0.75:
        return "Fresh"
    if ratio > 0.50:
        return "Working"
    return "Tired"


def determine(requested, current):
    """Highest tier <= requested whose cost is affordable; returns (effective, cost)."""
    for tier in reversed(COMMITMENTS[: COMMITMENTS.index(requested) + 1]):
        if COSTS[tier] <= current:
            return tier, COSTS[tier]
    return "", 0


def magnitude_modifier(effective, grade):
    if effective == "HIGH":
        if grade == 1:
            return 1
        if grade == -1:
            return -1
    if effective in ("LOW", ""):
        if grade == 2:
            return -1
        if grade == -2:
            return 1
    return 0


def undercommitment_modifier(initiator_effective, responder_effective):
    return 1 if RANK[responder_effective] < RANK[initiator_effective] else 0


def exhaustion_modifier(initiator_band, responder_band):
    return (-1 if initiator_band == "Exhausted" else 0) + (1 if responder_band == "Exhausted" else 0)


# ---- Entry (S4) ----------------------------------------------------------------------------------
def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _padded(identifier):
    return identifier != identifier.strip(STRIP_EDGES_CHARACTERS)


def validate_entry(request):
    """Pure. Returns the first failing code or ''. Builds nothing."""
    if not isinstance(request, dict):
        return "entry_not_a_dictionary"
    if set(request) != {"role_map", "fighters", "clock", "window", "interval_seconds"}:
        return "entry_malformed"
    role_map, fighters, clock, window = request["role_map"], request["fighters"], request["clock"], request["window"]
    if not (isinstance(role_map, dict) and set(role_map) == {"top", "bottom"}
            and all(isinstance(role_map[r], str) for r in role_map)):
        return "entry_malformed"
    if not isinstance(fighters, dict) or not all(isinstance(k, str) for k in fighters):
        return "entry_malformed"
    if not (isinstance(clock, dict) and set(clock) == {"initial_seconds", "remaining_seconds"}
            and _is_int(clock["initial_seconds"]) and _is_int(clock["remaining_seconds"])):
        return "entry_malformed"
    if not (isinstance(window, dict) and set(window) == {"last_issued_id"} and _is_int(window["last_issued_id"])):
        return "entry_malformed"
    if not _is_int(request["interval_seconds"]):
        return "entry_malformed"
    shape = {"stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"}
    for key in fighters:
        record = fighters[key]
        if not (isinstance(record, dict) and set(record) == shape and _is_int(record["stamina_current"])
                and _is_int(record["stamina_maximum"]) and isinstance(record["exhaustion_latched"], bool)
                and _is_int(record["behavior_remainder_units"])):
            return "entry_malformed"
    ids = [role_map["top"], role_map["bottom"]]
    if any(not i or _padded(i) for i in ids) or ids[0] == ids[1]:
        return "invalid_fighter_id"
    if set(fighters) != set(ids):
        return "fighters_mismatch"
    for fid in ids:
        if not 1 <= fighters[fid]["stamina_maximum"] <= MAXIMUM_EXACT:
            return "invalid_stamina_maximum"
    for fid in ids:
        if not 0 <= fighters[fid]["stamina_current"] <= fighters[fid]["stamina_maximum"]:
            return "invalid_stamina_current"
    for fid in ids:
        f = fighters[fid]
        if f["stamina_current"] <= enter_threshold(f["stamina_maximum"]) and not f["exhaustion_latched"]:
            return "inconsistent_exhaustion_latch"
        if f["stamina_current"] >= recover_threshold(f["stamina_maximum"]) and f["exhaustion_latched"]:
            return "inconsistent_exhaustion_latch"
    for fid in ids:
        if abs(fighters[fid]["behavior_remainder_units"]) > MAXIMUM_EXACT:
            return "invalid_behavior_remainder"
    if not 1 <= clock["initial_seconds"] <= MAXIMUM_EXACT or not 1 <= clock["remaining_seconds"] <= clock["initial_seconds"]:
        return "invalid_clock"
    if not 0 <= window["last_issued_id"] <= MAXIMUM_EXACT:
        return "invalid_window_id"
    if not 1 <= request["interval_seconds"] <= MAXIMUM_EXACT:
        return "invalid_interval"
    return ""


def _empty_history():
    return {"initiated_action_history": [], "response_history": [], "raw_grade_history": [], "modified_grade_history": [],
            "initiator_effective_commitment_history": [], "responder_effective_commitment_history": [],
            "response_charge_history": [], "response_waived_history": [], "band_change_history": [],
            "readiness_change_history": [], "reset_window_history": [], "top_initiation_count": 0,
            "bottom_initiation_count": 0}


# ---- Context (S8) ------------------------------------------------------------------------------
def validate_context(state):
    if not isinstance(state, dict):
        return "missing_state"
    try:
        for fid in (state["role_map"]["top"], state["role_map"]["bottom"]):
            f = state["fighters"][fid]
            if not (_is_int(f["stamina_maximum"]) and 1 <= f["stamina_maximum"] <= MAXIMUM_EXACT
                    and _is_int(f["stamina_current"]) and 0 <= f["stamina_current"] <= f["stamina_maximum"]):
                return "invalid_stamina_state"
        for fid in (state["role_map"]["top"], state["role_map"]["bottom"]):
            f = state["fighters"][fid]
            if f["exhaustion_latched"] != latch_after(f["stamina_current"], f["stamina_maximum"], f["exhaustion_latched"]):
                return "invalid_exhaustion_latch"
        if state["initiator"] not in ("top", "bottom"):
            return "invalid_initiator"
        if not (_is_int(state["clock_seconds"]) and _is_int(state["initial_clock"]) and _is_int(state["interval_seconds"])
                and 1 <= state["initial_clock"] <= MAXIMUM_EXACT and 0 <= state["clock_seconds"] <= state["initial_clock"]
                and 1 <= state["interval_seconds"] <= MAXIMUM_EXACT):
            return "invalid_clock_context"
        if state["clock_seconds"] == 0 or state["exit_destination"] != "":
            return "terminal_exchange"
        if not (_is_int(state["axis_tenths"]) and AXIS_MIN <= state["axis_tenths"] <= AXIS_MAX
                and _is_int(state["band"]) and legal_pair(state["axis_tenths"], state["band"])
                and all(_is_int(state[t]) and 0 <= state[t] <= 2 for t in ("top_base", "bottom_frame"))):
            return "invalid_half_guard_context"
    except (KeyError, TypeError):
        return "invalid_half_guard_context"
    return ""


def _ended(state):
    return state["clock_seconds"] == 0 or state["exit_destination"] != ""


class HalfGuard:
    """One Half Guard match. ``snapshot()`` is the canonical state; refusals never change it."""

    def __init__(self, state):
        self.s = state

    # -- construction ------------------------------------------------------------------------
    @staticmethod
    def from_entry(request):
        error = validate_entry(request)
        if error:
            return None, error
        fighters = {fid: {k: request["fighters"][fid][k] for k in ("stamina_current", "stamina_maximum",
                                                                    "exhaustion_latched", "behavior_remainder_units")}
                    for fid in (request["role_map"]["top"], request["role_map"]["bottom"])}
        state = {"position_id": POSITION_ID,
                 "role_map": {"top": request["role_map"]["top"], "bottom": request["role_map"]["bottom"]},
                 "fighters": fighters, "axis_tenths": ENTRY_AXIS, "band": ENTRY_BAND, "initiator": "top",
                 "top_base": 1, "bottom_frame": 1, "initial_clock": request["clock"]["initial_seconds"],
                 "clock_seconds": request["clock"]["remaining_seconds"], "interval_seconds": request["interval_seconds"],
                 "window_id": request["window"]["last_issued_id"], "window_open": False, "window_side": "",
                 "exit_destination": "", "exit_reason": "", "history": _empty_history()}
        return HalfGuard(state), ""

    @staticmethod
    def from_snapshot(snapshot):
        return HalfGuard(copy.deepcopy(snapshot))

    def snapshot(self):
        return copy.deepcopy(self.s)

    # -- views ---------------------------------------------------------------------------------
    def role_of(self, fighter_id):
        for role in ("top", "bottom"):
            if self.s["role_map"][role] == fighter_id:
                return role
        return ""

    def state_fields(self):
        s = self.s
        out = {"axis_tenths": s["axis_tenths"], "axis": s["axis_tenths"] / 10, "band": s["band"],
               "band_name": BAND_NAMES[s["band"]], "authority": authority_of(s["axis_tenths"], s["role_map"]),
               "initiator": s["initiator"], "top_base": s["top_base"], "bottom_frame": s["bottom_frame"],
               "top_base_name": TIER_NAMES[s["top_base"]], "bottom_frame_name": TIER_NAMES[s["bottom_frame"]],
               "clock_seconds": s["clock_seconds"], "initial_clock": s["initial_clock"],
               "exit_destination": s["exit_destination"], "exit_reason": s["exit_reason"], "ended": _ended(s),
               "submission_tapped": False}
        for role in ("top", "bottom"):
            f = s["fighters"][s["role_map"][role]]
            out[role + "_stamina"], out[role + "_maximum"] = f["stamina_current"], f["stamina_maximum"]
            out[role + "_band"] = stamina_band(f["stamina_current"], f["stamina_maximum"], f["exhaustion_latched"])
            out[role + "_latched"] = f["exhaustion_latched"]
        return out

    # -- windows (S7) ---------------------------------------------------------------------------
    def open_window(self, duration=None):
        s = self.s
        if s["window_open"]:
            return {"error": "window_already_open"}
        error = validate_context(s)
        if error:
            return {"error": error}
        if duration is not None and not _is_int(duration):
            return {"error": "invalid_duration"}
        if duration is not None and duration < 0:
            return {"error": "invalid_window_request"}
        seconds = s["interval_seconds"] if duration is None else duration
        elapsed = min(seconds, s["clock_seconds"])
        s["clock_seconds"] -= elapsed
        report = {"error": "", "free": False, "advance": {"elapsed_seconds": elapsed, "clock_seconds": s["clock_seconds"]}}
        if s["clock_seconds"] == 0:
            if s["exit_destination"] == "":
                s["exit_reason"] = "TIMEOUT — Half Guard retained"
            report.update({"closed": True, "window_open": False, "window_id": s["window_id"], "state": self.state_fields()})
            return report
        s["window_id"] += 1
        s["window_open"], s["window_side"] = True, s["initiator"]
        report.update({"closed": False, "window_open": True, "window_id": s["window_id"],
                       "fighter_id": s["role_map"][s["initiator"]], "role": s["initiator"],
                       "commitment": DEFAULT_COMMITMENT, "state": self.state_fields()})
        return report

    def _admission(self, window_id, fighter_id, action_id, response_id, commitment, response_commitment):
        s = self.s
        if not s["window_open"]:
            return "no_open_window"
        if window_id != s["window_id"] or isinstance(window_id, bool):
            return "stale_window"
        context = validate_context(s)
        if context:
            return context
        if s["initiator"] != s["window_side"]:
            return "window_initiator_changed"
        if fighter_id == "":
            return "missing_fighter_id"
        role = self.role_of(fighter_id)
        if role == "":
            return "unknown_fighter"
        if role != s["window_side"]:
            return "not_initiator"
        if action_id == "" and response_id != "":
            return "response_without_action"
        if action_id == "" and (commitment != "" or response_commitment != ""):
            return "commitment_without_action"
        return ""

    def submit(self, window_id, fighter_id, action_id="", response_id="", commitment="", response_commitment=""):
        s = self.s
        error = self._admission(window_id, fighter_id, action_id, response_id, commitment, response_commitment)
        if error:
            return {"error": error}
        side = s["window_side"]
        if action_id == "":
            s["window_open"], s["window_side"] = False, ""
            s["initiator"] = "bottom" if side == "top" else "top"
            s["history"]["reset_window_history"].append(side)
            detail = {"settlement": {"kind": "reset", "initiator": side, "next_initiator": s["initiator"]}}
            return {"error": "", "window_id": window_id, "fighter_id": fighter_id, "role": side, "kind": "reset",
                    "detail": detail, "transition": transition_for(s["exit_destination"]), "ended": _ended(s),
                    "state": self.state_fields()}
        record = self.attempt(action_id, response_id, DEFAULT_COMMITMENT if commitment == "" else commitment, response_commitment)
        if record["error"]:
            return {"error": record["error"]}
        s["window_open"], s["window_side"] = False, ""
        return {"error": "", "window_id": window_id, "fighter_id": fighter_id, "role": side, "kind": "exchange",
                "detail": {"settlement": record}, "transition": transition_for(s["exit_destination"]), "ended": _ended(s),
                "state": self.state_fields()}

    # -- the exchange (S5, S6) -------------------------------------------------------------------
    def _shape_error(self, action_id, response_id, commitment, response_commitment):
        s = self.s
        if commitment not in COMMITMENTS:
            return "invalid_commitment"
        if response_commitment != "" and response_commitment not in COMMITMENTS:
            return "invalid_response_commitment"
        everything = TOP_ACTIONS + BOTTOM_ACTIONS + TOP_RESPONSES + BOTTOM_RESPONSES
        if action_id not in everything:
            return "unknown_action"
        if action_id not in ACTIONS[s["initiator"]]:
            return "incorrect_action_side_or_kind"
        if response_id not in everything:
            return "unknown_response"
        responder = "bottom" if s["initiator"] == "top" else "top"
        if response_id not in RESPONSES[responder]:
            return "incorrect_response_side_or_kind"
        return ""

    def attempt(self, action_id, response_id, commitment, response_commitment=""):
        s = self.s
        error = validate_context(s)
        if not error and isinstance(action_id, str) and isinstance(response_id, str):
            error = self._shape_error(action_id, response_id, commitment, response_commitment)
        elif not error:
            error = "unknown_action" if not isinstance(action_id, str) else "unknown_response"
        if error:
            return {"error": error}
        side = s["initiator"]
        other = "bottom" if side == "top" else "top"
        init_f, resp_f = s["fighters"][s["role_map"][side]], s["fighters"][s["role_map"][other]]
        # S5.2 capture
        init_band = stamina_band(init_f["stamina_current"], init_f["stamina_maximum"], init_f["exhaustion_latched"])
        resp_band = stamina_band(resp_f["stamina_current"], resp_f["stamina_maximum"], resp_f["exhaustion_latched"])
        tiers_before = {"top_base": s["top_base"], "bottom_frame": s["bottom_frame"]}
        axis_before, band_before = s["axis_tenths"], s["band"]
        # S5.3 funding and grading
        requested_response = DEFAULT_COMMITMENT if response_commitment == "" else response_commitment
        init_eff, init_cost = determine(commitment, init_f["stamina_current"])
        resp_eff, resp_cost = determine(requested_response, resp_f["stamina_current"])
        raw = RAW[side][action_id][response_id]
        positional = -1 if (side == "top" and band_before == -2) or (side == "bottom" and band_before == 2) else 0
        g1 = shift(raw, positional)
        own_tier = tiers_before[OWN_TRACK[side]]
        attack_shift = ATTACK_SHIFT[own_tier] if action_id in BREAK_CAPABLE else 0
        g2 = shift(g1, attack_shift)
        strength_tier, defense_shift = None, 0
        if response_id in GOVERNED:
            track_tier = tiers_before[GOVERNED[response_id]]
            strength_tier = 0 if resp_eff in ("LOW", "") else track_tier
            defense_shift = DEFENSE_SHIFT[strength_tier]
        g3 = shift(g2, defense_shift)
        exhaustion = exhaustion_modifier(init_band, resp_band)
        g4 = shift(g3, exhaustion)
        magnitude = magnitude_modifier(init_eff, g4)
        g5 = shift(g4, magnitude)
        under = undercommitment_modifier(init_eff, resp_eff)
        final = shift(g5, under)
        # S5.4 axis, exit, initiative
        delta = STEP_TENTHS * final if side == "top" else -STEP_TENTHS * final
        proposed = axis_before + delta
        exit_label = ""
        if final >= 1:
            if action_id == KNEE_SLICE and proposed >= PASS_LINE:
                exit_label = "Side Control"
            elif action_id == RECOVER_GUARD and proposed <= ESCAPE_LINE:
                exit_label = "Open Guard" if final == 1 else "Closed Guard"
        axis_after = max(AXIS_MIN, min(AXIS_MAX, proposed))
        band_after = band_update(axis_after, band_before)
        # S5.5 charges: initiator first, then responder unless Rule 1 waives
        init_charged = min(init_f["stamina_current"], init_cost)
        waived = resp_cost if init_eff == "" else 0
        resp_requested_charge = resp_cost - waived
        resp_charged = min(resp_f["stamina_current"], resp_requested_charge)
        # S5.6
        paid = resp_cost > 0 and resp_charged >= resp_cost
        # S5.7 readiness
        tiers = dict(tiers_before)
        changes = []

        def change(track, delta_tier):
            before = tiers[track]
            tiers[track] = max(0, min(2, before + delta_tier))
            if tiers[track] != before:
                changes.append("%s:%s->%s:%s" % (track, TIER_NAMES[before], TIER_NAMES[tiers[track]], action_id.rsplit(".", 1)[1]))

        if action_id in BREAK_CAPABLE and tiers[OWN_TRACK[side]] == 2:
            change(OWN_TRACK[side], -1)
        if response_id in GOVERNED and resp_eff not in ("LOW", ""):
            wears = (final != 0) if (resp_eff == "MEDIUM" or not paid) else (final >= 1)
            if wears:
                change(GOVERNED[response_id], -1)
        if final >= 1 and action_id in BUILD:
            track, delta_tier = BUILD[action_id]
            change(track, delta_tier)
        # ---- commit (everything above is pure) ----
        init_f["stamina_current"] -= init_charged
        init_f["exhaustion_latched"] = latch_after(init_f["stamina_current"], init_f["stamina_maximum"], init_f["exhaustion_latched"])
        resp_f["stamina_current"] -= resp_charged
        resp_f["exhaustion_latched"] = latch_after(resp_f["stamina_current"], resp_f["stamina_maximum"], resp_f["exhaustion_latched"])
        s["axis_tenths"], s["band"] = axis_after, band_after
        s["top_base"], s["bottom_frame"] = tiers["top_base"], tiers["bottom_frame"]
        if exit_label:
            verb = "pass" if action_id == KNEE_SLICE else "escape"
            s["exit_destination"] = exit_label
            s["exit_reason"] = "%s reached the %s line with final grade %s" % (TECHNIQUE_NAMES[action_id], verb, GRADE_NAMES[final])
        else:
            s["initiator"] = other
        h = s["history"]
        h["initiated_action_history"].append(action_id)
        h["response_history"].append(response_id)
        h["raw_grade_history"].append(GRADE_NAMES[raw])
        h["modified_grade_history"].append(GRADE_NAMES[final])
        h["initiator_effective_commitment_history"].append(init_eff)
        h["responder_effective_commitment_history"].append(resp_eff)
        h["response_charge_history"].append(resp_charged)
        h["response_waived_history"].append(waived)
        if band_after != band_before:
            h["band_change_history"].append("%d->%d" % (band_before, band_after))
        h["readiness_change_history"].extend(changes)
        h[side + "_initiation_count"] += 1
        return {"error": "", "kind": "exchange", "initiator": side, "action_id": action_id, "response_id": response_id,
                "commitment_requested": commitment, "response_commitment_requested": requested_response,
                "initiator_band": init_band, "responder_band": resp_band, "exhaustion_modifier": exhaustion,
                "initiator_effective": init_eff, "responder_effective": resp_eff,
                "initiator_effective_cost": init_cost, "responder_effective_cost": resp_cost,
                "initiator_charged": init_charged, "responder_charged": resp_charged, "responder_waived": waived,
                "paid_effort": paid, "raw_grade": raw, "positional_modifier": positional,
                "attack_readiness_shift": attack_shift, "defense_strength_tier": strength_tier,
                "defense_readiness_shift": defense_shift, "grade_after_positional": g1, "grade_after_attack": g2,
                "grade_after_defense": g3, "grade_after_exhaustion": g4, "magnitude_modifier": magnitude,
                "grade_after_magnitude": g5, "undercommitment_modifier": under, "final_grade": final,
                "axis_before": axis_before, "axis_proposed": proposed, "axis_after": axis_after,
                "band_before": band_before, "band_after": band_after, "exit_destination": exit_label,
                "tiers_before": tiers_before, "tiers_after": dict(tiers), "readiness_changes": changes}


# ---- Replay (S9) ---------------------------------------------------------------------------------
def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def replay(entry, commands):
    """Run a command list from an entry request. Deterministic; JSON-able output."""
    match, error = HalfGuard.from_entry(entry)
    if error:
        return {"entry_error": error, "results": [], "final": None}
    results = []
    for command in commands:
        op = command["op"]
        if op == "open":
            results.append(match.open_window(command.get("duration")))
        elif op == "submit":
            results.append(match.submit(command["window_id"], command["fighter_id"], command.get("action_id", ""),
                                        command.get("response_id", ""), command.get("commitment", ""),
                                        command.get("response_commitment", "")))
        elif op == "attempt":
            results.append(match.attempt(command["action_id"], command["response_id"], command["commitment"],
                                         command.get("response_commitment", "")))
        else:
            raise ValueError("unknown replay operation: %r" % (op,))
    return {"entry_error": "", "results": results, "final": match.snapshot()}
