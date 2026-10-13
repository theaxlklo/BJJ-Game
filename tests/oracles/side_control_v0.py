"""Independent, test-only Side Control v0 oracle (B2b-2).

Written from ``GODOT_V1/docs/SIDE_CONTROL_V0_RULES.md`` (the canonical rules sheet) and from nothing else: it does not
import the Half Guard oracle, the frozen Python reference or any GDScript, and no Side Control engine exists yet. Every
constant below is a *provisional prototype constant* approved for B2b only; none is a balance claim. The table-consistency
tests parse the sheet and fail if this file and the sheet disagree.

Design rules that matter when reading the code:

* Authoritative state is plain integers, strings and booleans in one dictionary whose layout *is* the snapshot, so a
  detached copy is trivially canonical and a refusal can be proved byte-identical.
* Every operation validates completely before it mutates anything; the settlement then runs on local values and is committed
  last. That is why a refused command can never leave a half-applied exchange behind.
* Nothing reads a clock, randomness, the environment or dictionary iteration order into a result (determinism invariant).
"""
import copy
import json
import math

POSITION_ID = "side_control"
TOP, BOTTOM = "top", "bottom"
ROLES = (TOP, BOTTOM)
MAX_INT = 9007199254740991  # 2**53 - 1: the largest integer a Godot float/JSON number holds exactly

AXIS_MIN, AXIS_MAX = -40, 40
STEP = 10  # tenths of axis per final-grade step
ENTRY_AXIS, ENTRY_BAND, ENTRY_TIER = 10, 1, 1
EXIT_LINE = 30  # Top: proposed >= +30; Bottom: proposed <= -30

COSTS = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
RANK = {"": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}  # "" is the unfunded commitment
GRADE_NAMES = {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"}

# (from band, comparison, axis threshold, to band): SC-N7 hysteresis. Each band has at most one applicable rule per axis,
# so repeated application terminates; the overlap between a band's "enter" and "leave" thresholds is the hysteresis.
BAND_RULES = (
    (0, "ge", 12, 1), (1, "ge", 27, 2), (-1, "ge", -8, 0), (-2, "ge", -23, -1),
    (2, "le", 23, 1), (1, "le", 8, 0), (0, "le", -12, -1), (-1, "le", -27, -2),
)

_P = "side_control."
# id -> side, break-capable, own readiness track (break-capable only), exit (label, destination id), technique name
ACTIONS = {
    _P + "top.stabilize": {"side": TOP, "break": False, "track": "", "exit": ("", ""), "name": "Stabilize"},
    _P + "top.advance_to_mount": {"side": TOP, "break": True, "track": "top_pin", "exit": ("Mount", "mount"), "name": "Advance to Mount"},
    _P + "top.expose_back": {"side": TOP, "break": True, "track": "top_pin", "exit": ("Back Control", "back_control"), "name": "Expose Back"},
    _P + "bottom.shrimp": {"side": BOTTOM, "break": False, "track": "", "exit": ("", ""), "name": "Shrimp"},
    _P + "bottom.recover_half_guard": {"side": BOTTOM, "break": True, "track": "bottom_space", "exit": ("Half Guard", "half_guard"), "name": "Recover Half Guard"},
    _P + "bottom.turn_to_knees": {"side": BOTTOM, "break": True, "track": "bottom_space", "exit": ("Turtle", "turtle"), "name": "Turn to Knees"},
}
# id -> owning side and the readiness track that governs it ("" when the response is not governed)
RESPONSES = {
    _P + "bottom_response.forearm_frame": {"side": BOTTOM, "track": ""},
    _P + "bottom_response.hip_escape": {"side": BOTTOM, "track": "bottom_space"},
    _P + "bottom_response.bridge_defense": {"side": BOTTOM, "track": ""},
    _P + "top_response.shoulder_pressure": {"side": TOP, "track": ""},
    _P + "top_response.hip_block": {"side": TOP, "track": "top_pin"},
    _P + "top_response.follow_the_hips": {"side": TOP, "track": ""},
}
EXIT_LABELS = ("Mount", "Back Control", "Half Guard", "Turtle")
EXIT_DESTINATIONS = {"Mount": "mount", "Back Control": "back_control", "Half Guard": "half_guard", "Turtle": "turtle"}

_RAW_ROWS = (  # (action, [grade vs response 1, 2, 3]) in the catalog order of RESPONSES for the opposing side
    ("top.stabilize", "bottom_response", (-1, 1, 0)),
    ("top.advance_to_mount", "bottom_response", (1, -2, 1)),
    ("top.expose_back", "bottom_response", (1, 0, -2)),
    ("bottom.shrimp", "top_response", (-1, 1, 0)),
    ("bottom.recover_half_guard", "top_response", (2, -1, 1)),
    ("bottom.turn_to_knees", "top_response", (0, 2, -2)),
)
_RESPONSE_ORDER = {
    "bottom_response": ("forearm_frame", "hip_escape", "bridge_defense"),
    "top_response": ("shoulder_pressure", "hip_block", "follow_the_hips"),
}
RAW = {
    (_P + action, _P + owner + "." + name): grade
    for action, owner, grades in _RAW_ROWS
    for name, grade in zip(_RESPONSE_ORDER[owner], grades)
}

# Defense readiness shift by the defender's strength tier (None +2 / Partial 0 / Ready -1), SC-N4
DEFENSE_SHIFT = {0: 2, 1: 0, 2: -1}

ENTRY_ERROR_ORDER = (
    "entry_not_a_dictionary", "entry_malformed", "invalid_fighter_id", "fighters_mismatch", "invalid_initiator",
    "invalid_stamina_maximum", "invalid_stamina_current", "inconsistent_exhaustion_latch", "invalid_behavior_remainder",
    "invalid_clock", "invalid_window_id", "invalid_interval",
)
CONTEXT_ERROR_ORDER = (
    "missing_state", "invalid_stamina_state", "invalid_exhaustion_latch", "invalid_initiator", "invalid_clock_context",
    "terminal_exchange", "invalid_side_control_context",
)
SUBMIT_ERROR_ORDER = (
    "malformed_command", "no_open_window", "stale_window", "<context>", "window_initiator_changed", "missing_fighter_id",
    "unknown_fighter", "not_initiator", "response_without_action", "commitment_without_action", "invalid_commitment",
    "invalid_response_commitment", "unknown_action", "incorrect_action_side_or_kind", "unknown_response",
    "incorrect_response_side_or_kind",
)
ATTEMPT_ERROR_ORDER = (
    "malformed_command", "window_already_open", "<context>", "invalid_commitment", "invalid_response_commitment",
    "unknown_action", "incorrect_action_side_or_kind", "unknown_response", "incorrect_response_side_or_kind",
)

# Godot 4.7.2 String.strip_edges strips exactly these code points, so an id padded by one of them is refused.
_STRIPPED = "".join(chr(code) for code in range(0x01, 0x21))
TIMEOUT_REASON = "TIMEOUT — Side Control retained"
_POOL_KEYS = ("stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units")


# ---------------------------------------------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------------------------------------------
def is_int(value):
    """True for an ``int`` that is not a ``bool`` (JSON has no bool-is-int; the Godot port must agree)."""
    return isinstance(value, int) and not isinstance(value, bool)


def shift(grade, amount):
    """Saturating grade shift. Saturating after *every* step makes the pipeline order part of the rule."""
    return max(-2, min(2, grade + amount))


def determine(requested, available):
    """Highest commitment tier not above ``requested`` whose cost fits ``available``; "" means unfunded."""
    for tier in ("HIGH", "MEDIUM", "LOW"):
        if RANK[tier] <= RANK[requested] and COSTS[tier] <= available:
            return tier
    return ""


def enter_threshold(maximum):
    return math.floor(maximum * 0.25)


def recover_threshold(maximum):
    return math.ceil(maximum * 0.35)


def refresh_latch(pool):
    """Exhaustion hysteresis: latch at or below the enter threshold, release only at or above the recover threshold."""
    if pool["exhaustion_latched"]:
        if pool["stamina_current"] >= recover_threshold(pool["stamina_maximum"]):
            pool["exhaustion_latched"] = False
    elif pool["stamina_current"] <= enter_threshold(pool["stamina_maximum"]):
        pool["exhaustion_latched"] = True


def spend_up_to(pool, cost):
    """Charge as much of ``cost`` as the pool holds; returns the amount actually charged."""
    charged = min(pool["stamina_current"], cost)
    pool["stamina_current"] -= charged
    refresh_latch(pool)
    return charged


def stamina_band(pool):
    if pool["exhaustion_latched"]:
        return "Exhausted"
    ratio = pool["stamina_current"] / pool["stamina_maximum"]
    if ratio > 0.75:
        return "Fresh"
    return "Working" if ratio > 0.50 else "Tired"


def band_update(axis, band):
    """Apply the SC-N7 hysteresis rules until none matches."""
    changed = True
    while changed:
        changed = False
        for source, comparison, threshold, target in BAND_RULES:
            if band == source and (axis >= threshold if comparison == "ge" else axis <= threshold):
                band, changed = target, True
                break
    return band


def legal_pair(axis, band):
    """The (axis, band) pairs the hysteresis rules can leave behind."""
    return {0: -12 < axis < 12, 1: 8 < axis < 27, 2: axis > 23, -1: -27 < axis < -8, -2: axis < -23}.get(band, False)


def authority_id(axis, role_map):
    """Reported control authority (no mechanical effect): the side of the axis, or "" at zero."""
    return role_map[TOP] if axis > 0 else role_map[BOTTOM] if axis < 0 else ""


def transition_fields(label):
    """Detached transition view; ``resolved`` means a declared position id, never that a receiver exists."""
    if not label:
        return {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": False}
    return {"kind": "exit", "raw_destination": label, "destination_position_id": EXIT_DESTINATIONS[label], "resolved": True}


def canonical_bytes(value):
    """Canonical JSON text of a snapshot or report: sorted keys, no spaces, ASCII only."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _refusal(code):
    return {"error": code}


def _opposite(role):
    return BOTTOM if role == TOP else TOP


# ---------------------------------------------------------------------------------------------------------------
# Entry validation
# ---------------------------------------------------------------------------------------------------------------
def _is_str_key_dict(value, keys):
    return isinstance(value, dict) and set(value) == set(keys)


def _entry_is_malformed(entry):
    if not _is_str_key_dict(entry, ("role_map", "initiator", "fighters", "clock", "window", "interval_seconds")):
        return True
    role_map, fighters = entry["role_map"], entry["fighters"]
    if not _is_str_key_dict(role_map, ROLES) or not all(isinstance(role_map[role], str) for role in ROLES):
        return True
    if not isinstance(entry["initiator"], str) or not isinstance(fighters, dict):
        return True
    for key, pool in fighters.items():
        if not isinstance(key, str) or not _is_str_key_dict(pool, _POOL_KEYS):
            return True
        if not (is_int(pool["stamina_current"]) and is_int(pool["stamina_maximum"])
                and isinstance(pool["exhaustion_latched"], bool) and is_int(pool["behavior_remainder_units"])):
            return True
    clock, window = entry["clock"], entry["window"]
    if not _is_str_key_dict(clock, ("initial_seconds", "remaining_seconds")) or not all(is_int(v) for v in clock.values()):
        return True
    if not _is_str_key_dict(window, ("last_issued_id",)) or not is_int(window["last_issued_id"]):
        return True
    return not is_int(entry["interval_seconds"])


def _fighter_id_is_invalid(fighter_id):
    return fighter_id == "" or fighter_id != fighter_id.strip(_STRIPPED)


def validate_entry(entry):
    """Pure entry validation: the first failing code of ``ENTRY_ERROR_ORDER``, or "". Nothing is built here."""
    if not isinstance(entry, dict):
        return "entry_not_a_dictionary"
    if _entry_is_malformed(entry):
        return "entry_malformed"
    ids = [entry["role_map"][role] for role in ROLES]
    if any(_fighter_id_is_invalid(fighter_id) for fighter_id in ids) or ids[0] == ids[1]:
        return "invalid_fighter_id"
    if set(entry["fighters"]) != set(ids):
        return "fighters_mismatch"
    if entry["initiator"] not in ROLES:
        return "invalid_initiator"
    pools = [entry["fighters"][fighter_id] for fighter_id in ids]  # role order: top, then bottom
    if not all(1 <= p["stamina_maximum"] <= MAX_INT for p in pools):
        return "invalid_stamina_maximum"
    if not all(0 <= p["stamina_current"] <= p["stamina_maximum"] for p in pools):
        return "invalid_stamina_current"
    for p in pools:
        # Between the thresholds either latch value is legitimate and is carried, which preserves hysteresis.
        if p["stamina_current"] <= enter_threshold(p["stamina_maximum"]) and not p["exhaustion_latched"]:
            return "inconsistent_exhaustion_latch"
        if p["stamina_current"] >= recover_threshold(p["stamina_maximum"]) and p["exhaustion_latched"]:
            return "inconsistent_exhaustion_latch"
    if not all(abs(p["behavior_remainder_units"]) <= MAX_INT for p in pools):
        return "invalid_behavior_remainder"
    clock = entry["clock"]
    if not (1 <= clock["initial_seconds"] <= MAX_INT and 1 <= clock["remaining_seconds"] <= clock["initial_seconds"]):
        return "invalid_clock"
    if not 0 <= entry["window"]["last_issued_id"] <= MAX_INT:
        return "invalid_window_id"
    if not 1 <= entry["interval_seconds"] <= MAX_INT:
        return "invalid_interval"
    return ""


# ---------------------------------------------------------------------------------------------------------------
# The position
# ---------------------------------------------------------------------------------------------------------------
class SideControl:
    """One Side Control position. Build it with ``from_entry`` (or ``from_snapshot`` for corrupted/mid-state tests)."""

    def __init__(self, state):
        self._s = state

    @classmethod
    def from_entry(cls, entry):
        """Return ``(position, "")`` or ``(None, error_code)``. The request is never modified."""
        error = validate_entry(entry)
        if error:
            return None, error
        ids = {role: entry["role_map"][role] for role in ROLES}
        state = {
            "position_id": POSITION_ID,
            "role_map": ids,
            "initiator": entry["initiator"],
            "axis_tenths": ENTRY_AXIS,
            "band": ENTRY_BAND,
            "top_pin": ENTRY_TIER,
            "bottom_space": ENTRY_TIER,  # fresh tiers: nothing earned in a previous position carries over
            "fighters": copy.deepcopy(entry["fighters"]),
            "initial_seconds": entry["clock"]["initial_seconds"],
            "clock_seconds": entry["clock"]["remaining_seconds"],
            "interval_seconds": entry["interval_seconds"],
            "window_id": entry["window"]["last_issued_id"],
            "window_open": False,
            "window_initiator": "",
            "exit_destination": "",
            "exit_reason": "",
            "decision_history": [],
        }
        return cls(state), ""

    @classmethod
    def from_snapshot(cls, snapshot):
        """Rebuild from a detached snapshot WITHOUT validating it: operations report corruption as a context error."""
        return cls(copy.deepcopy(snapshot))

    def snapshot(self):
        """Canonical detached snapshot; mutating it never affects the position."""
        return copy.deepcopy(self._s)

    # -- derived views (never stored) ---------------------------------------------------------------------------
    @property
    def ended(self):
        return self._s["clock_seconds"] == 0 or self._s["exit_destination"] != ""

    @property
    def authority_id(self):
        return authority_id(self._s["axis_tenths"], self._s["role_map"])

    # -- context -------------------------------------------------------------------------------------------------
    def _shape_is_valid(self):
        s = self._s
        if not isinstance(s, dict):
            return False
        ints = ("axis_tenths", "band", "top_pin", "bottom_space", "initial_seconds", "clock_seconds", "interval_seconds", "window_id")
        strings = ("position_id", "initiator", "window_initiator", "exit_destination", "exit_reason")
        if not all(is_int(s.get(key)) for key in ints) or not all(isinstance(s.get(key), str) for key in strings):
            return False
        if not isinstance(s.get("window_open"), bool) or not isinstance(s.get("decision_history"), list):
            return False
        role_map, fighters = s.get("role_map"), s.get("fighters")
        if not _is_str_key_dict(role_map, ROLES) or not all(isinstance(role_map[role], str) for role in ROLES):
            return False
        if not isinstance(fighters, dict) or any(role_map[role] not in fighters for role in ROLES):
            return False
        return all(_is_str_key_dict(fighters[role_map[role]], _POOL_KEYS) and is_int(fighters[role_map[role]]["stamina_current"])
                   and is_int(fighters[role_map[role]]["stamina_maximum"])
                   and isinstance(fighters[role_map[role]]["exhaustion_latched"], bool) for role in ROLES)

    def context_error(self):
        """First failing context code of ``CONTEXT_ERROR_ORDER``, or ""."""
        if not self._shape_is_valid():
            return "missing_state"
        s = self._s
        pools = [s["fighters"][s["role_map"][role]] for role in ROLES]
        if not all(1 <= p["stamina_maximum"] <= MAX_INT and 0 <= p["stamina_current"] <= p["stamina_maximum"] for p in pools):
            return "invalid_stamina_state"
        for p in pools:
            if (p["stamina_current"] <= enter_threshold(p["stamina_maximum"]) and not p["exhaustion_latched"]) or (
                    p["stamina_current"] >= recover_threshold(p["stamina_maximum"]) and p["exhaustion_latched"]):
                return "invalid_exhaustion_latch"
        if s["initiator"] not in ROLES:
            return "invalid_initiator"
        if not (1 <= s["initial_seconds"] <= MAX_INT and 1 <= s["interval_seconds"] <= MAX_INT
                and 0 <= s["clock_seconds"] <= s["initial_seconds"]):
            return "invalid_clock_context"
        if self.ended:
            return "terminal_exchange"
        if (s["position_id"] != POSITION_ID or not AXIS_MIN <= s["axis_tenths"] <= AXIS_MAX
                or not legal_pair(s["axis_tenths"], s["band"]) or not 0 <= s["top_pin"] <= 2 or not 0 <= s["bottom_space"] <= 2
                or s["exit_destination"] not in ("",) + EXIT_LABELS or not 0 <= s["window_id"] <= MAX_INT
                or s["window_initiator"] not in ("",) + ROLES):
            return "invalid_side_control_context"
        return ""

    # -- windows -------------------------------------------------------------------------------------------------
    def open_window(self, duration=None):
        """Open the next decision window, consuming simulated time; opening is the ONLY place the clock moves."""
        s = self._s
        if s.get("window_open") is True:
            return _refusal("window_already_open")
        error = self.context_error()
        if error:
            return _refusal(error)
        if duration is not None and not is_int(duration):
            return _refusal("invalid_duration")
        if duration is not None and duration < 0:
            return _refusal("invalid_window_request")
        elapsed = min(s["interval_seconds"] if duration is None else duration, s["clock_seconds"])
        s["clock_seconds"] -= elapsed
        if s["clock_seconds"] == 0:
            # The clock ran out before a window could open: terminal, never an exit, and the window id does not advance.
            s["exit_reason"] = TIMEOUT_REASON
            return {"error": "", "status": "closed", "window_id": s["window_id"], "initiator": "", "elapsed_seconds": elapsed, "clock_seconds": 0}
        s["window_id"] += 1
        s["window_open"], s["window_initiator"] = True, s["initiator"]
        return {"error": "", "status": "opened", "window_id": s["window_id"], "initiator": s["initiator"], "elapsed_seconds": elapsed,
                "clock_seconds": s["clock_seconds"]}

    # -- decisions -----------------------------------------------------------------------------------------------
    def submit(self, window_id, fighter_id, action_id, response_id, commitment="", response_commitment=""):
        """One window decision: an exchange, or a PASS when ``action_id`` is empty. Atomic; closes the window."""
        s = self._s
        if not is_int(window_id) or not all(isinstance(v, str) for v in (fighter_id, action_id, response_id, commitment, response_commitment)):
            return _refusal("malformed_command")
        if s.get("window_open") is not True:
            return _refusal("no_open_window")
        if s.get("window_id") != window_id:
            return _refusal("stale_window")
        error = self.context_error()
        if error:
            return _refusal(error)
        if s["window_initiator"] != s["initiator"]:
            return _refusal("window_initiator_changed")
        if fighter_id == "":
            return _refusal("missing_fighter_id")
        role = next((r for r in ROLES if s["role_map"][r] == fighter_id), "")
        if role == "":
            return _refusal("unknown_fighter")
        if role != s["initiator"]:
            return _refusal("not_initiator")
        if action_id == "":
            if response_id != "":
                return _refusal("response_without_action")
            if commitment != "" or response_commitment != "":
                return _refusal("commitment_without_action")
            return self._pass(role)
        error = self._command_error(action_id, response_id, commitment, response_commitment)
        return _refusal(error) if error else self._exchange(action_id, response_id, commitment or "MEDIUM", response_commitment or "MEDIUM")

    def attempt(self, action_id, response_id, commitment="", response_commitment=""):
        """Window-less exchange for the current initiator (used by exchange grids); it can never pass."""
        s = self._s
        if not all(isinstance(v, str) for v in (action_id, response_id, commitment, response_commitment)):
            return _refusal("malformed_command")
        if s.get("window_open") is True:
            return _refusal("window_already_open")
        error = self.context_error() or self._command_error(action_id, response_id, commitment, response_commitment)
        return _refusal(error) if error else self._exchange(action_id, response_id, commitment or "MEDIUM", response_commitment or "MEDIUM")

    def _command_error(self, action_id, response_id, commitment, response_commitment):
        """Shape checks shared by submit and attempt, in sheet order; the initiator's side comes from the state."""
        if commitment not in ("", "LOW", "MEDIUM", "HIGH"):
            return "invalid_commitment"
        if response_commitment not in ("", "LOW", "MEDIUM", "HIGH"):
            return "invalid_response_commitment"
        if action_id not in ACTIONS and action_id not in RESPONSES:
            return "unknown_action"
        if action_id not in ACTIONS or ACTIONS[action_id]["side"] != self._s["initiator"]:
            return "incorrect_action_side_or_kind"
        if response_id not in ACTIONS and response_id not in RESPONSES:
            return "unknown_response"
        if response_id not in RESPONSES or RESPONSES[response_id]["side"] != _opposite(self._s["initiator"]):
            return "incorrect_response_side_or_kind"
        return ""

    def _pass(self, role):
        """PASS: no stamina, no grade, no extra clock; only initiative flips. Recorded as its own decision kind."""
        s = self._s
        record = {"kind": "pass", "window_id": s["window_id"], "fighter_id": s["role_map"][role], "role": role}
        s["decision_history"].append(record)
        s["initiator"] = _opposite(role)
        s["window_open"], s["window_initiator"] = False, ""
        return {"error": "", "kind": "pass", "record": copy.deepcopy(record), "transition": transition_fields("")}

    def _exchange(self, action_id, response_id, commitment, response_commitment):
        """Settle one accepted exchange in the sheet's fixed order. Validation is complete, so this cannot fail midway."""
        s = self._s
        role = s["initiator"]
        initiator_id, responder_id = s["role_map"][role], s["role_map"][_opposite(role)]
        initiator, responder = s["fighters"][initiator_id], s["fighters"][responder_id]
        action, response = ACTIONS[action_id], RESPONSES[response_id]
        tiers = {"top_pin": s["top_pin"], "bottom_space": s["bottom_space"]}

        # Capture everything the grade depends on BEFORE any charge, so a charge cannot change its own exchange's grade.
        initiator_band, responder_band = stamina_band(initiator), stamina_band(responder)
        axis_before, band_before = s["axis_tenths"], s["band"]
        initiator_effective = determine(commitment, initiator["stamina_current"])
        responder_effective = determine(response_commitment, responder["stamina_current"])

        raw = RAW[(action_id, response_id)]
        facing_control = (role == TOP and band_before == -2) or (role == BOTTOM and band_before == 2)
        grade = shift(raw, -1 if facing_control else 0)
        if action["break"]:
            grade = shift(grade, tiers[action["track"]] - 1)  # Ready +1 / Partial 0 / None -1
        if response["track"]:
            # A LOW or unfunded defender is only token resistance, so it is evaluated as if the structure were None.
            strength = 0 if responder_effective in ("", "LOW") else tiers[response["track"]]
            grade = shift(grade, DEFENSE_SHIFT[strength])
        grade = shift(grade, (-1 if initiator_band == "Exhausted" else 0) + (1 if responder_band == "Exhausted" else 0))
        if initiator_effective == "HIGH":
            grade = shift(grade, 1 if grade == 1 else -1 if grade == -1 else 0)
        elif initiator_effective in ("", "LOW"):
            grade = shift(grade, -1 if grade == 2 else 1 if grade == -2 else 0)
        final = shift(grade, 1 if RANK[responder_effective] < RANK[initiator_effective] else 0)

        proposed = axis_before + (STEP * final if role == TOP else -STEP * final)
        crossed = proposed >= EXIT_LINE if role == TOP else proposed <= -EXIT_LINE
        label = action["exit"][0] if action["break"] and final >= 1 and crossed else ""
        axis_after = max(AXIS_MIN, min(AXIS_MAX, proposed))  # clamp and band update also happen on an exit
        band_after = band_update(axis_after, band_before)

        # Charges: initiator first, then the responder unless Rule 1 waives it (an unfunded initiator waives the response cost).
        initiator_charged = spend_up_to(initiator, COSTS.get(initiator_effective, 0))
        waived = COSTS.get(responder_effective, 0) if initiator_effective == "" else 0
        responder_charged = spend_up_to(responder, 0 if initiator_effective == "" else COSTS.get(responder_effective, 0))
        responder_paid = responder_effective != "" and initiator_effective != ""

        changes = []

        def move(track, delta, cause):
            before = tiers[track]
            after = max(0, min(2, before + delta))
            if after != before:
                tiers[track] = after
                changes.append({"track": track, "before": before, "after": after, "cause": cause})

        # Readiness, only here and always in this order: consume, wear, build. They touch different tracks (see the sheet).
        if action["break"] and tiers[action["track"]] == 2:
            move(action["track"], -1, "consume")
        if response["track"] and responder_effective in ("MEDIUM", "HIGH"):
            if responder_effective == "HIGH" and responder_paid:
                worn = final >= 1  # a paid HIGH defense is preserved unless it failed
            else:
                worn = final != 0  # MEDIUM, and an unpaid (waived) HIGH, wear on any decided result
            if worn:
                move(response["track"], -1, "wear")
        if final >= 1 and not action["break"]:
            move("top_pin" if role == TOP else "bottom_space", 1, "build")

        record = {
            "kind": "exchange", "window_id": s["window_id"], "fighter_id": initiator_id, "role": role, "responder_id": responder_id,
            "action_id": action_id, "response_id": response_id,
            "commitment_requested": commitment, "response_commitment_requested": response_commitment,
            "initiator_effective": initiator_effective, "responder_effective": responder_effective,
            "initiator_charged": initiator_charged, "responder_charged": responder_charged, "responder_waived": waived,
            "raw_grade": raw, "final_grade": final,
            "axis_before": axis_before, "axis_after": axis_after, "band_before": band_before, "band_after": band_after,
            "exit_destination": label, "readiness_changes": changes,
        }
        s["top_pin"], s["bottom_space"] = tiers["top_pin"], tiers["bottom_space"]
        s["axis_tenths"], s["band"] = axis_after, band_after
        s["decision_history"].append(record)
        s["window_open"], s["window_initiator"] = False, ""
        if label:
            line = "advance" if role == TOP else "escape"
            s["exit_destination"] = label
            s["exit_reason"] = "%s reached the %s line with final grade %s" % (action["name"], line, GRADE_NAMES[final])
        else:
            s["initiator"] = _opposite(role)  # an exit leaves initiative where it was
        return {"error": "", "kind": "exchange", "record": copy.deepcopy(record), "transition": transition_fields(label)}


def replay(entry, operations):
    """Run an entry and an operation list; the result is a pure function of its arguments (determinism)."""
    match, error = SideControl.from_entry(entry)
    if error:
        return {"entry_error": error, "results": [], "snapshot": None}
    results = []
    for operation in operations:
        kind = operation.get("op")
        if kind == "open_window":
            results.append(match.open_window(operation.get("duration")))
        elif kind == "submit":
            results.append(match.submit(operation.get("window_id"), operation.get("fighter_id"), operation.get("action_id"),
                                        operation.get("response_id"), operation.get("commitment", ""), operation.get("response_commitment", "")))
        elif kind == "attempt":
            results.append(match.attempt(operation.get("action_id"), operation.get("response_id"), operation.get("commitment", ""),
                                         operation.get("response_commitment", "")))
        else:
            results.append(_refusal("unknown_operation"))
    return {"entry_error": "", "results": results, "snapshot": match.snapshot()}
