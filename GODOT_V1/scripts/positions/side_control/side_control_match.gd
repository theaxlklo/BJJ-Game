class_name BjjSideControlMatch
extends RefCounted

# The single mutable owner of standalone Side Control v0 simulation state (SIDE_CONTROL_V0_RULES.md). Everything that can change a Side
# Control result lives here: axis (signed integer tenths), band, initiative, the two stamina records (state belongs to the FIGHTER ID;
# "top"/"bottom" are labels over the role map), the two readiness tiers, the clock, the window counter and one decision history.
# Settlement is one ordered, uniform path for every accepted exchange, exits included:
#   admission -> capture -> grade (pre-exchange tiers) -> axis / band / exit -> stamina charges -> readiness (consume, wear, build)
#   -> history -> initiative (flips unless the exchange exited) -> terminal fields.
# A PASS is the only other accepted decision: no stamina, no grade, no extra clock; only initiative flips.
# Every refusal happens BEFORE any mutation, so a rejected command leaves the whole state byte-identical.
# This is a transition prototype with no submissions: the four exits are declared but unsupported, so reaching one ends the segment.
# Standalone by design (B2c): no contract adapter, graph receiver or UI exists yet, and Mount / Half Guard are never referenced.
const MAXIMUM: int = BjjStaminaPool.MAXIMUM_EXACT
const DEFAULT_COMMITMENT: String = BjjCommitment.MEDIUM
const ROLES: Array[String] = ["top", "bottom"]

# One fighter's stamina state as plain values, so a corrupted snapshot (an out-of-range value, an inconsistent latch) can be held
# and REPORTED as a context error instead of being silently repaired by the shared pool, which refuses such values.
class Fighter extends RefCounted:
    var current: int = 0
    var maximum: int = 1
    var latched: bool = false
    var remainder: int = 0  # carried and never changed by v0

    static func from_record(record: Dictionary) -> Fighter:
        var fighter := Fighter.new()
        fighter.current = int(record["stamina_current"])
        fighter.maximum = int(record["stamina_maximum"])
        fighter.latched = record["exhaustion_latched"]
        fighter.remainder = int(record["behavior_remainder_units"])
        return fighter

    func record() -> Dictionary:
        return {"stamina_current": current, "stamina_maximum": maximum, "exhaustion_latched": latched, "behavior_remainder_units": remainder}

class Creation extends RefCounted:
    var error: String = ""
    var match_state: BjjSideControlMatch
    func ok() -> bool:
        return error.is_empty() and match_state != null

# Detached result of one operation: `error` is a stable code, `values` the oracle-shaped payload (without the "error" key).
class Result extends RefCounted:
    var error: String = ""
    var values: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()

var position_id: String = BjjSideControlRules.POSITION_ID
var top_id: String = ""
var bottom_id: String = ""
var initiator: String = "top"
var axis_tenths: int = BjjSideControlRules.ENTRY_AXIS
var band: int = BjjSideControlRules.ENTRY_BAND
var top_pin: int = BjjSideControlRules.ENTRY_TIER
var bottom_space: int = BjjSideControlRules.ENTRY_TIER
var top: Fighter = Fighter.new()
var bottom: Fighter = Fighter.new()
var initial_seconds: int = 0
var clock_seconds: int = 0
var interval_seconds: int = 0
var window_id: int = 0
var window_open: bool = false
var window_initiator: String = ""
var exit_destination: String = ""
var exit_reason: String = ""
var decision_history: Array = []
# A snapshot whose SHAPE cannot be held in typed fields is kept verbatim: every operation then fails closed with `missing_state`, and
# `snapshot()` returns it unchanged. `_window_id_known` mirrors the oracle's "an absent window id is stale for every command".
var _quarantined: bool = false
var _raw: Dictionary = {}
var _window_id_known: bool = true

static func _fail(code: String) -> Result:
    var result := Result.new()
    result.error = code
    return result

static func _opposite(role: String) -> String:
    return "bottom" if role == "top" else "top"

# --- Construction ---------------------------------------------------------------------------------

# The only way to build a match from a request. A valid entry never fails here; the checks live in BjjSideControlEntry.validate.
static func from_entry(request: Variant) -> Creation:
    var created := Creation.new()
    created.error = BjjSideControlEntry.validate(request)
    if not created.error.is_empty():
        return created
    var state := BjjSideControlMatch.new()
    state.top_id = str(request["role_map"]["top"])
    state.bottom_id = str(request["role_map"]["bottom"])
    state.initiator = str(request["initiator"])
    state.top = Fighter.from_record(request["fighters"][state.top_id])
    state.bottom = Fighter.from_record(request["fighters"][state.bottom_id])
    state.initial_seconds = int(request["clock"]["initial_seconds"])
    state.clock_seconds = int(request["clock"]["remaining_seconds"])
    state.interval_seconds = int(request["interval_seconds"])
    state.window_id = int(request["window"]["last_issued_id"])
    created.match_state = state
    return created

# Restores a detached snapshot WITHOUT validating its rules: corruption (an out-of-range axis, an inconsistent latch, a terminal exit) is
# reported by the next operation as a context error, never a crash. Only a snapshot that cannot be held in typed fields is quarantined.
# Unknown top-level keys, a third fighter, equal role ids and non-int values (including a non-int behavior remainder and a float/bool
# window id, which the oracle compares with Python equality) all count as "cannot be held": stricter than the oracle, and the rules sheet
# defines no such input. None of these can come from an entry or from this engine's own snapshot().
static func from_snapshot(snapshot: Variant) -> Creation:
    var created := Creation.new()
    if typeof(snapshot) != TYPE_DICTIONARY:
        created.error = "snapshot_not_a_dictionary"
        return created
    var raw: Dictionary = snapshot
    var state := BjjSideControlMatch.new()
    created.match_state = state
    if not _shape_ok(raw):
        state._quarantined = true
        state._raw = raw.duplicate(true)
        state.window_open = typeof(raw.get("window_open")) == TYPE_BOOL and raw["window_open"]
        state._window_id_known = BjjSideControlEntry.is_int(raw.get("window_id"))
        state.window_id = int(raw["window_id"]) if state._window_id_known else 0
        return created
    state.position_id = raw["position_id"]
    state.top_id = raw["role_map"]["top"]
    state.bottom_id = raw["role_map"]["bottom"]
    state.initiator = raw["initiator"]
    state.axis_tenths = raw["axis_tenths"]
    state.band = raw["band"]
    state.top_pin = raw["top_pin"]
    state.bottom_space = raw["bottom_space"]
    state.top = Fighter.from_record(raw["fighters"][state.top_id])
    state.bottom = Fighter.from_record(raw["fighters"][state.bottom_id])
    state.initial_seconds = raw["initial_seconds"]
    state.clock_seconds = raw["clock_seconds"]
    state.interval_seconds = raw["interval_seconds"]
    state.window_id = raw["window_id"]
    state.window_open = raw["window_open"]
    state.window_initiator = raw["window_initiator"]
    state.exit_destination = raw["exit_destination"]
    state.exit_reason = raw["exit_reason"]
    state.decision_history = (raw["decision_history"] as Array).duplicate(true)
    return created

static func _shape_ok(raw: Dictionary) -> bool:
    var keys: Array[String] = ["position_id", "role_map", "initiator", "axis_tenths", "band", "top_pin", "bottom_space", "fighters",
        "initial_seconds", "clock_seconds", "interval_seconds", "window_id", "window_open", "window_initiator", "exit_destination",
        "exit_reason", "decision_history"]
    if not BjjSideControlEntry.exact_keys(raw, keys):
        return false
    for key: String in ["axis_tenths", "band", "top_pin", "bottom_space", "initial_seconds", "clock_seconds", "interval_seconds", "window_id"]:
        if not BjjSideControlEntry.is_int(raw[key]):
            return false
    for key: String in ["position_id", "initiator", "window_initiator", "exit_destination", "exit_reason"]:
        if typeof(raw[key]) != TYPE_STRING:
            return false
    if typeof(raw["window_open"]) != TYPE_BOOL or typeof(raw["decision_history"]) != TYPE_ARRAY:
        return false
    var role_keys: Array[String] = ["top", "bottom"]
    var role_map: Variant = raw["role_map"]
    if not BjjSideControlEntry.exact_keys(role_map, role_keys) or typeof(role_map["top"]) != TYPE_STRING or typeof(role_map["bottom"]) != TYPE_STRING:
        return false
    var fighters: Variant = raw["fighters"]
    if typeof(fighters) != TYPE_DICTIONARY or role_map["top"] == role_map["bottom"] or fighters.size() != 2:
        return false
    for role: String in role_keys:
        if not fighters.has(role_map[role]) or not BjjSideControlEntry.pool_shape_ok(fighters[role_map[role]]):
            return false
    return true

# --- Views (detached) -----------------------------------------------------------------------------

func fighter_id(role: String) -> String:
    return top_id if role == "top" else bottom_id if role == "bottom" else ""

func role_of(id: String) -> String:
    if id.is_empty():
        return ""
    return "top" if id == top_id else "bottom" if id == bottom_id else ""

func _fighter(role: String) -> Fighter:
    return top if role == "top" else bottom

# True when a snapshot of the wrong shape was kept verbatim (see from_snapshot). The public typed fields are then placeholders with no
# meaning: read snapshot() and context_error() instead, never the fields.
func is_quarantined() -> bool:
    return _quarantined

func is_ended() -> bool:
    return clock_seconds == 0 or not exit_destination.is_empty()

func authority_id() -> String:
    return BjjSideControlRules.authority_id(axis_tenths, top_id, bottom_id)

# The canonical detached snapshot (same shape as the oracle's `snapshot()`). Authority, `ended` and the transition view are derived.
func snapshot() -> Dictionary:
    if _quarantined:
        return _raw.duplicate(true)
    return {"position_id": position_id, "role_map": {"top": top_id, "bottom": bottom_id}, "initiator": initiator,
        "axis_tenths": axis_tenths, "band": band, "top_pin": top_pin, "bottom_space": bottom_space,
        "fighters": {top_id: top.record(), bottom_id: bottom.record()},
        "initial_seconds": initial_seconds, "clock_seconds": clock_seconds, "interval_seconds": interval_seconds,
        "window_id": window_id, "window_open": window_open, "window_initiator": window_initiator,
        "exit_destination": exit_destination, "exit_reason": exit_reason, "decision_history": decision_history.duplicate(true)}

# --- Context (precedes every command-shape check) -------------------------------------------------

# Order: missing state, stamina state, exhaustion latch, initiator, clock, terminal, Side Control context. Returns "" when the state is usable.
func context_error() -> String:
    if _quarantined:
        return "missing_state"
    for fighter: Fighter in [top, bottom]:
        if fighter.maximum < 1 or fighter.maximum > MAXIMUM or fighter.current < 0 or fighter.current > fighter.maximum:
            return "invalid_stamina_state"
    for fighter: Fighter in [top, bottom]:
        if BjjSideControlEntry.latch_inconsistent(fighter.current, fighter.maximum, fighter.latched):
            return "invalid_exhaustion_latch"
    if not ROLES.has(initiator):
        return "invalid_initiator"
    if initial_seconds < 1 or initial_seconds > MAXIMUM or interval_seconds < 1 or interval_seconds > MAXIMUM \
            or clock_seconds < 0 or clock_seconds > initial_seconds:
        return "invalid_clock_context"
    if is_ended():
        return "terminal_exchange"
    if position_id != BjjSideControlRules.POSITION_ID or axis_tenths < BjjSideControlRules.AXIS_MIN or axis_tenths > BjjSideControlRules.AXIS_MAX \
            or not BjjSideControlRules.legal_pair(axis_tenths, band) or top_pin < 0 or top_pin > BjjSideControlRules.TIER_MAX \
            or bottom_space < 0 or bottom_space > BjjSideControlRules.TIER_MAX \
            or not (exit_destination.is_empty() or BjjSideControlCatalog.EXIT_DESTINATIONS.has(exit_destination)) \
            or window_id < 0 or window_id > MAXIMUM or not (window_initiator.is_empty() or ROLES.has(window_initiator)):
        return "invalid_side_control_context"
    return ""

# --- Windows --------------------------------------------------------------------------------------

# `duration` is trusted simulated seconds (null = the interval), never wall-clock or frames. 0 is a legal zero-time window. Opening a
# window is the ONLY place the simulated clock moves (a PASS never freezes it).
func open_window(duration: Variant = null) -> Result:
    if window_open:
        return _fail("window_already_open")
    var context := context_error()
    if not context.is_empty():
        return _fail(context)
    if duration != null and typeof(duration) != TYPE_INT:
        return _fail("invalid_duration")
    if duration != null and int(duration) < 0:
        return _fail("invalid_window_request")
    var elapsed := mini(interval_seconds if duration == null else int(duration), clock_seconds)
    clock_seconds -= elapsed
    var result := Result.new()
    if clock_seconds == 0:
        # The clock ran out before a window could open: terminal, never an exit, and the window id does not advance.
        exit_reason = BjjSideControlRules.TIMEOUT_REASON
        result.values = {"status": "closed", "window_id": window_id, "initiator": "", "elapsed_seconds": elapsed, "clock_seconds": 0}
        return result
    window_id += 1
    window_open = true
    window_initiator = initiator
    result.values = {"status": "opened", "window_id": window_id, "initiator": initiator, "elapsed_seconds": elapsed, "clock_seconds": clock_seconds}
    return result

# --- Decisions ------------------------------------------------------------------------------------

# One decision for the open window: an exchange, or a PASS when `action_id` is empty. Arguments cross the boundary as Variant so that a
# wrongly typed command is a typed `malformed_command` refusal, not an engine error. Atomic; closes the window on success.
func submit(requested_window_id: Variant, requested_fighter_id: Variant, action_id: Variant, response_id: Variant,
        commitment: Variant = "", response_commitment: Variant = "") -> Result:
    if not BjjSideControlEntry.is_int(requested_window_id) or not _all_strings([requested_fighter_id, action_id, response_id, commitment, response_commitment]):
        return _fail("malformed_command")
    if not window_open:
        return _fail("no_open_window")
    if not _window_id_known or window_id != int(requested_window_id):
        return _fail("stale_window")
    var context := context_error()
    if not context.is_empty():
        return _fail(context)
    if window_initiator != initiator:
        return _fail("window_initiator_changed")
    var fighter_id_text := str(requested_fighter_id)
    if fighter_id_text.is_empty():
        return _fail("missing_fighter_id")
    var role := role_of(fighter_id_text)
    if role.is_empty():
        return _fail("unknown_fighter")
    if role != initiator:
        return _fail("not_initiator")
    if str(action_id).is_empty():
        if not str(response_id).is_empty():
            return _fail("response_without_action")
        if not str(commitment).is_empty() or not str(response_commitment).is_empty():
            return _fail("commitment_without_action")
        return _pass(role)
    var error := _command_error(str(action_id), str(response_id), str(commitment), str(response_commitment))
    if not error.is_empty():
        return _fail(error)
    return _exchange(str(action_id), str(response_id), _or_default(str(commitment)), _or_default(str(response_commitment)))

# Window-less exchange for the current initiator (used by exchange grids). It can never pass and is refused while a window is open, so it
# cannot desynchronize a window from the initiator (R-5).
func attempt(action_id: Variant, response_id: Variant, commitment: Variant = "", response_commitment: Variant = "") -> Result:
    if not _all_strings([action_id, response_id, commitment, response_commitment]):
        return _fail("malformed_command")
    if window_open:
        return _fail("window_already_open")
    var error := context_error()
    if error.is_empty():
        error = _command_error(str(action_id), str(response_id), str(commitment), str(response_commitment))
    if not error.is_empty():
        return _fail(error)
    return _exchange(str(action_id), str(response_id), _or_default(str(commitment)), _or_default(str(response_commitment)))

static func _all_strings(values: Array) -> bool:
    for value: Variant in values:
        if typeof(value) != TYPE_STRING:
            return false
    return true

static func _or_default(commitment: String) -> String:
    return DEFAULT_COMMITMENT if commitment.is_empty() else commitment

# Shape checks shared by submit and attempt, in sheet order; the initiator's side comes from the state. A foreign id (a Mount or Half Guard
# technique, or the reserved kimura/armbar routes) is simply not one of the 12 catalog ids.
func _command_error(action_id: String, response_id: String, commitment: String, response_commitment: String) -> String:
    if not commitment.is_empty() and not BjjCommitment.valid(commitment):
        return "invalid_commitment"
    if not response_commitment.is_empty() and not BjjCommitment.valid(response_commitment):
        return "invalid_response_commitment"
    if not BjjSideControlCatalog.ENTITIES.has(action_id):
        return "unknown_action"
    if not BjjSideControlCatalog.is_action(action_id) or str(BjjSideControlCatalog.ENTITIES[action_id].side) != initiator:
        return "incorrect_action_side_or_kind"
    if not BjjSideControlCatalog.ENTITIES.has(response_id):
        return "unknown_response"
    if not BjjSideControlCatalog.is_response(response_id) or str(BjjSideControlCatalog.ENTITIES[response_id].side) != _opposite(initiator):
        return "incorrect_response_side_or_kind"
    return ""

func _close_window() -> void:
    window_open = false
    window_initiator = ""

func _pass(role: String) -> Result:
    var record := {"kind": "pass", "window_id": window_id, "fighter_id": fighter_id(role), "role": role}
    decision_history.append(record)
    initiator = _opposite(role)
    _close_window()
    var result := Result.new()
    result.values = {"kind": "pass", "record": record.duplicate(true), "transition": BjjSideControlCatalog.transition_fields("")}
    return result

# Exhaustion-latch restoration with the public pool API only: a latched fighter is built at zero (always latched) and then moved to its
# current value, so the hysteresis between the enter and recover thresholds is remembered. Valid only after context_error() passed.
static func _pool_of(fighter: Fighter) -> BjjStaminaPool:
    var pool := BjjStaminaPool.create(0 if fighter.latched else fighter.current, fighter.maximum).pool
    if fighter.latched:
        pool.set_current(fighter.current)
    return pool

# Settles one accepted exchange in the sheet's fixed order. Admission is complete, so this cannot fail midway.
func _exchange(action_id: String, response_id: String, commitment: String, response_commitment: String) -> Result:
    var role := initiator
    var other := _opposite(role)
    var policy := BjjStaminaCostPolicy.defaults()
    var initiator_fighter := _fighter(role)
    var responder_fighter := _fighter(other)
    var initiator_pool := _pool_of(initiator_fighter)
    var responder_pool := _pool_of(responder_fighter)
    # Capture before any charge: both bands, the pre-exchange tiers, axis and band, and the funding each side is granted.
    var input := BjjSideControlResolver.Inputs.new()
    input.side = role
    input.action_id = action_id
    input.response_id = response_id
    input.axis_tenths = axis_tenths
    input.band = band
    input.top_pin = top_pin
    input.bottom_space = bottom_space
    input.initiator_band = initiator_pool.band
    input.responder_band = responder_pool.band
    var initiator_funding := policy.determine(commitment, initiator_pool.current)
    var responder_funding := policy.determine(response_commitment, responder_pool.current)
    input.initiator_effective = initiator_funding.effective
    input.responder_effective = responder_funding.effective
    var resolution := BjjSideControlResolver.resolve(input)
    # Charges: initiator first, then the responder unless Rule 1 waives it (an unfunded initiator waives the response cost; Rule 2 does not exist).
    var initiator_charge := initiator_pool.spend_up_to(initiator_funding.effective_cost)
    var rule_one_waives := BjjCommitmentSettlement.waives_response_cost(true, initiator_funding.effective)
    var waived := responder_funding.effective_cost if rule_one_waives else 0
    var responder_charge := responder_pool.spend_up_to(0 if rule_one_waives else responder_funding.effective_cost)
    # Paid effort: the responder was funded AND Rule 1 did not waive it. Only HIGH *preservation* reads this (R-9).
    var paid := not responder_funding.effective.is_empty() and not rule_one_waives
    var readiness := BjjSideControlResolver.update_readiness(input, resolution.final_grade, paid)
    var record := {"kind": "exchange", "window_id": window_id, "fighter_id": fighter_id(role), "role": role, "responder_id": fighter_id(other),
        "action_id": action_id, "response_id": response_id, "commitment_requested": commitment, "response_commitment_requested": response_commitment,
        "initiator_effective": initiator_funding.effective, "responder_effective": responder_funding.effective,
        "initiator_charged": initiator_charge.charged, "responder_charged": responder_charge.charged, "responder_waived": waived,
        "raw_grade": resolution.raw_grade, "final_grade": resolution.final_grade,
        "axis_before": axis_tenths, "axis_after": resolution.axis_after, "band_before": band, "band_after": resolution.band_after,
        "exit_destination": resolution.exit_label, "readiness_changes": readiness.changes}
    # Commit (nothing above mutated the match; the pools were local copies).
    initiator_fighter.current = initiator_pool.current
    initiator_fighter.latched = initiator_pool.band == "Exhausted"
    responder_fighter.current = responder_pool.current
    responder_fighter.latched = responder_pool.band == "Exhausted"
    top_pin = readiness.top_pin
    bottom_space = readiness.bottom_space
    axis_tenths = resolution.axis_after
    band = resolution.band_after
    decision_history.append(record.duplicate(true))
    _close_window()
    if not resolution.exit_label.is_empty():
        # An exit leaves initiative where it was and grants no extra window or time.
        exit_destination = resolution.exit_label
        var line := "advance" if role == "top" else "escape"
        exit_reason = "%s reached the %s line with final grade %s" % [str(BjjSideControlCatalog.ENTITIES[action_id].name), line,
            BjjSideControlRules.GRADE_NAMES[resolution.final_grade]]
    else:
        initiator = other
    var result := Result.new()
    result.values = {"kind": "exchange", "record": record.duplicate(true), "transition": BjjSideControlCatalog.transition_fields(resolution.exit_label)}
    return result
