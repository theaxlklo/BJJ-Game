class_name BjjHalfGuardMatch
extends RefCounted

# The single mutable owner of Half Guard v0 simulation state (HALF_GUARD_V0_RULES.md). Everything that can change a
# Half Guard result lives here: axis (signed integer tenths), band, initiative, the two stamina pools (state belongs
# to the fighter id; "top"/"bottom" are labels over the role map), the two readiness integers, the clock, the window
# counter and the histories. Settlement is one ordered, uniform path for every accepted exchange, exits included:
#   admission -> capture -> grade (pre-exchange tiers) -> axis / band / exit / initiative -> stamina charges -> readiness
#   updates (consume, wear, build) -> histories -> terminal fields.
# Rejections happen before any mutation. No behaviors, drift or recovery exist in v0. B1h adds one optional input to the same path: an
# explicit feint (HALF_GUARD_V0_RULES.md section 13): the real technique settles through this same pipeline; the sealed-intent protocol is a
# separate wrapper and is never referenced here.
# Shared stamina and commitment primitives are reused unchanged.
const DEFAULT_COMMITMENT: String = BjjCommitment.MEDIUM

var top_id: String = ""
var bottom_id: String = ""
var top: BjjStaminaPool
var bottom: BjjStaminaPool
var top_meter: BjjBehaviorStaminaPolicy.Meter
var bottom_meter: BjjBehaviorStaminaPolicy.Meter
var cost_policy: BjjStaminaCostPolicy = BjjStaminaCostPolicy.defaults()
var axis_tenths: int = BjjHalfGuardRules.ENTRY_AXIS
var band: int = BjjHalfGuardRules.ENTRY_BAND
var initiator: String = "top"
var top_base: int = BjjHalfGuardRules.ENTRY_TIER
var bottom_frame: int = BjjHalfGuardRules.ENTRY_TIER
var initial_clock: int = 0
var clock_seconds: int = 0
var interval_seconds: int = 0
var window_id: int = 0
var window_open: bool = false
var window_side: String = ""
var exit_destination: String = ""
var exit_reason: String = ""
var history: Dictionary = {}

class Creation extends RefCounted:
    var error: String = ""
    var match_state: BjjHalfGuardMatch
    func ok() -> bool:
        return error.is_empty() and match_state != null

# Detached result of one operation: `error` is a stable code, `values` the oracle-shaped payload.
class Result extends RefCounted:
    var error: String = ""
    var values: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()

static func _fail(code: String) -> Result:
    var result := Result.new()
    result.error = code
    return result

static func empty_history() -> Dictionary:
    return {"initiated_action_history": [], "response_history": [], "raw_grade_history": [], "modified_grade_history": [],
        "initiator_effective_commitment_history": [], "responder_effective_commitment_history": [],
        "response_charge_history": [], "response_waived_history": [], "band_change_history": [],
        "readiness_change_history": [], "reset_window_history": [], "top_initiation_count": 0, "bottom_initiation_count": 0}

# The only construction path. A valid entry never fails here; the checks live in BjjHalfGuardEntry.validate.
static func from_entry(request: Variant) -> Creation:
    var created := Creation.new()
    created.error = BjjHalfGuardEntry.validate(request)
    if not created.error.is_empty():
        return created
    var state := BjjHalfGuardMatch.new()
    state.top_id = str(request["role_map"]["top"])
    state.bottom_id = str(request["role_map"]["bottom"])
    var top_record: Dictionary = request["fighters"][state.top_id]
    var bottom_record: Dictionary = request["fighters"][state.bottom_id]
    state.top = _restore_pool(top_record)
    state.bottom = _restore_pool(bottom_record)
    state.top_meter = BjjBehaviorStaminaPolicy.Meter.new(int(top_record["behavior_remainder_units"]))
    state.bottom_meter = BjjBehaviorStaminaPolicy.Meter.new(int(bottom_record["behavior_remainder_units"]))
    state.initial_clock = int(request["clock"]["initial_seconds"])
    state.clock_seconds = int(request["clock"]["remaining_seconds"])
    state.interval_seconds = int(request["interval_seconds"])
    state.window_id = int(request["window"]["last_issued_id"])
    state.history = empty_history()
    created.match_state = state
    return created

# Exhaustion-latch restoration with the public pool API only (the pattern BjjMountMatch._copy_pool already uses):
# a latched fighter is built at zero (always latched) and then moved to its current value, so the hysteresis between
# the enter and recover thresholds is remembered; an unlatched fighter is built directly at its current value.
static func _restore_pool(record: Dictionary) -> BjjStaminaPool:
    var current := int(record["stamina_current"])
    var maximum := int(record["stamina_maximum"])
    var latched: bool = record["exhaustion_latched"]
    var pool := BjjStaminaPool.create(0 if latched else current, maximum).pool
    if latched:
        pool.set_current(current)
    return pool

# --- Views (detached) ---------------------------------------------------------------------

func _fighter_id(role: String) -> String:
    return top_id if role == "top" else bottom_id if role == "bottom" else ""

func role_of(fighter_id: String) -> String:
    if fighter_id.is_empty():
        return ""
    return "top" if fighter_id == top_id else "bottom" if fighter_id == bottom_id else ""

func _pool_of(role: String) -> BjjStaminaPool:
    return top if role == "top" else bottom

func is_ended() -> bool:
    return clock_seconds == 0 or not exit_destination.is_empty()

func selected_commitment() -> String:
    return DEFAULT_COMMITMENT

func authority_id() -> String:
    return BjjHalfGuardRules.authority_id(axis_tenths, top_id, bottom_id)

func state_fields() -> Dictionary:
    var fields := {"axis_tenths": axis_tenths, "axis": float(axis_tenths) / 10.0, "band": band,
        "band_name": BjjHalfGuardRules.BAND_NAMES.get(band, ""), "authority": authority_id(), "initiator": initiator,
        "top_base": top_base, "bottom_frame": bottom_frame, "top_base_name": BjjHalfGuardRules.tier_name(top_base),
        "bottom_frame_name": BjjHalfGuardRules.tier_name(bottom_frame), "clock_seconds": clock_seconds,
        "initial_clock": initial_clock, "exit_destination": exit_destination, "exit_reason": exit_reason,
        "ended": is_ended(), "submission_tapped": false}
    for role: String in ["top", "bottom"]:
        var pool := _pool_of(role)
        fields[role + "_stamina"] = pool.current
        fields[role + "_maximum"] = pool.maximum
        fields[role + "_band"] = pool.band
        fields[role + "_latched"] = pool.band == "Exhausted"
    return fields

func history_fields() -> Dictionary:
    return history.duplicate(true)

# The canonical detached snapshot (same shape as the oracle's `snapshot()`).
func snapshot() -> Dictionary:
    var fighters := {}
    for role: String in ["top", "bottom"]:
        var pool := _pool_of(role)
        var meter := top_meter if role == "top" else bottom_meter
        fighters[_fighter_id(role)] = {"stamina_current": pool.current, "stamina_maximum": pool.maximum,
            "exhaustion_latched": pool.band == "Exhausted", "behavior_remainder_units": meter.remainder_units}
    return {"position_id": BjjHalfGuardRules.POSITION_ID, "role_map": {"top": top_id, "bottom": bottom_id}, "fighters": fighters,
        "axis_tenths": axis_tenths, "band": band, "initiator": initiator, "top_base": top_base, "bottom_frame": bottom_frame,
        "initial_clock": initial_clock, "clock_seconds": clock_seconds, "interval_seconds": interval_seconds,
        "window_id": window_id, "window_open": window_open, "window_side": window_side,
        "exit_destination": exit_destination, "exit_reason": exit_reason, "history": history.duplicate(true)}

# --- Context (precedes every command-shape check) -----------------------------------------

# Order: missing state, stamina state, exhaustion latch, initiator, clock, terminal, Half Guard context. Pool values cannot be
# out of range (the pool refuses them), so an invalid stamina state means a missing or aliased pool.
func validate_context() -> String:
    if top == null or bottom == null or top == bottom or top_meter == null or bottom_meter == null:
        return "invalid_stamina_state"
    if initiator != "top" and initiator != "bottom":
        return "invalid_initiator"
    if initial_clock < 1 or clock_seconds < 0 or clock_seconds > initial_clock or interval_seconds < 1:
        return "invalid_clock_context"
    if is_ended():
        return "terminal_exchange"
    if top_id.is_empty() or bottom_id.is_empty() or top_id == bottom_id:
        return "invalid_half_guard_context"
    if axis_tenths < BjjHalfGuardRules.AXIS_MIN or axis_tenths > BjjHalfGuardRules.AXIS_MAX or not BjjHalfGuardRules.legal_pair(axis_tenths, band):
        return "invalid_half_guard_context"
    if top_base < 0 or top_base > BjjHalfGuardRules.TIER_MAX or bottom_frame < 0 or bottom_frame > BjjHalfGuardRules.TIER_MAX:
        return "invalid_half_guard_context"
    return ""

# --- Windows ---------------------------------------------------------------------------------

# `duration` is trusted simulated seconds (null = the interval), never wall-clock or frames. 0 is a legal zero-time window.
func open_window_for(duration: Variant) -> Result:
    if window_open:
        return _fail("window_already_open")
    var context := validate_context()
    if not context.is_empty():
        return _fail(context)
    if duration != null and typeof(duration) != TYPE_INT:
        return _fail("invalid_duration")
    if duration != null and int(duration) < 0:
        return _fail("invalid_window_request")
    var seconds: int = interval_seconds if duration == null else int(duration)
    var elapsed := mini(seconds, clock_seconds)
    clock_seconds -= elapsed
    var result := Result.new()
    result.values = {"free": false, "advance": {"elapsed_seconds": elapsed, "clock_seconds": clock_seconds}}
    if clock_seconds == 0:
        if exit_destination.is_empty():
            exit_reason = BjjHalfGuardRules.TIMEOUT_REASON
        result.values.merge({"closed": true, "window_open": false, "window_id": window_id, "state": state_fields()})
        return result
    window_id += 1
    window_open = true
    window_side = initiator
    result.values.merge({"closed": false, "window_open": true, "window_id": window_id, "fighter_id": _fighter_id(initiator),
        "role": initiator, "commitment": DEFAULT_COMMITMENT, "state": state_fields()})
    return result

func _admission_error(requested_window_id: int, fighter_id: String, action_id: String, response_id: String,
        commitment: String, response_commitment: String, real_action_id: String = "") -> String:
    if not window_open:
        return "no_open_window"
    if requested_window_id != window_id:
        return "stale_window"
    var context := validate_context()
    if not context.is_empty():
        return context
    if initiator != window_side:
        return "window_initiator_changed"
    if fighter_id.is_empty():
        return "missing_fighter_id"
    var role := role_of(fighter_id)
    if role.is_empty():
        return "unknown_fighter"
    if role != window_side:
        return "not_initiator"
    if action_id.is_empty() and not response_id.is_empty():
        return "response_without_action"
    if action_id.is_empty() and not (commitment.is_empty() and response_commitment.is_empty()):
        return "commitment_without_action"
    if action_id.is_empty() and not real_action_id.is_empty():
        return "feint_without_action"
    return ""

# One decision for the open window: an empty action is a pass, anything else an exchange. Everything is checked before any mutation.
func decide(requested_window_id: int, fighter_id: String, action_id: String = "", response_id: String = "",
        commitment: String = "", response_commitment: String = "", real_action_id: String = "") -> Result:
    var error := _admission_error(requested_window_id, fighter_id, action_id, response_id, commitment, response_commitment, real_action_id)
    if not error.is_empty():
        return _fail(error)
    var side := window_side
    var result := Result.new()
    if action_id.is_empty():
        window_open = false
        window_side = ""
        initiator = "bottom" if side == "top" else "top"
        history["reset_window_history"].append(side)
        result.values = {"window_id": requested_window_id, "fighter_id": fighter_id, "role": side, "kind": "reset",
            "detail": {"settlement": {"kind": "reset", "initiator": side, "next_initiator": initiator}},
            "transition": BjjHalfGuardCatalog.transition_fields(exit_destination), "ended": is_ended(), "state": state_fields()}
        return result
    var attempted := attempt(action_id, response_id, DEFAULT_COMMITMENT if commitment.is_empty() else commitment, response_commitment, real_action_id)
    if not attempted.ok():
        return _fail(attempted.error)
    window_open = false
    window_side = ""
    result.values = {"window_id": requested_window_id, "fighter_id": fighter_id, "role": side, "kind": "exchange",
        "detail": {"settlement": attempted.values}, "transition": BjjHalfGuardCatalog.transition_fields(exit_destination),
        "ended": is_ended(), "state": state_fields()}
    return result

# --- The exchange ------------------------------------------------------------------------------

func _shape_error(action_id: String, response_id: String, commitment: String, response_commitment: String) -> String:
    if not BjjCommitment.valid(commitment):
        return "invalid_commitment"
    if not response_commitment.is_empty() and not BjjCommitment.valid(response_commitment):
        return "invalid_response_commitment"
    if not BjjHalfGuardCatalog.ENTITIES.has(action_id):
        return "unknown_action"
    var action: Dictionary = BjjHalfGuardCatalog.ENTITIES[action_id]
    if str(action.kind) != "action" or str(action.side) != initiator:
        return "incorrect_action_side_or_kind"
    if not BjjHalfGuardCatalog.ENTITIES.has(response_id):
        return "unknown_response"
    var responder := "bottom" if initiator == "top" else "top"
    var response: Dictionary = BjjHalfGuardCatalog.ENTITIES[response_id]
    if str(response.kind) != "response" or str(response.side) != responder:
        return "incorrect_response_side_or_kind"
    return ""

# Feint admission, after the direct shape checks (section 13.6): equality, the real id's own shape, the pair table, the public condition on the
# acting side's own track, then funding. Pure. The same function backs the sealed protocol's seal check, so there is one authority.
func feint_error(apparent_id: String, real_id: String, commitment: String) -> String:
    if real_id == apparent_id:
        return "feint_real_equals_apparent"
    if not BjjHalfGuardCatalog.ENTITIES.has(real_id):
        return "unknown_action"
    var real: Dictionary = BjjHalfGuardCatalog.ENTITIES[real_id]
    if str(real.kind) != "action" or str(real.side) != initiator:
        return "incorrect_action_side_or_kind"
    if not BjjHalfGuardCatalog.FEINT_PAIRS.has(apparent_id) or str(BjjHalfGuardCatalog.FEINT_PAIRS[apparent_id].real) != real_id \
            or not BjjHalfGuardCatalog.is_break_capable(real_id):
        return "feint_not_supported"
    if BjjHalfGuardCatalog.eligible_real_ids(apparent_id, top_base, bottom_frame).is_empty():
        return "feint_not_eligible"
    if _feint_funding(_pool_of(initiator).current, commitment) == null:
        return "feint_requires_funding"
    return ""

# Surcharge first (all-or-nothing), then the existing funding policy on what remains. null = refused (nothing is ever partially funded).
func _feint_funding(available: int, requested: String) -> BjjStaminaCostPolicy.Funding:
    if available < BjjHalfGuardRules.FEINT_SURCHARGE:
        return null
    var funding := cost_policy.determine(requested, available - BjjHalfGuardRules.FEINT_SURCHARGE)
    return null if funding.effective == BjjCommitment.UNFUNDED else funding

# Match-level exchange for the current initiator (no window). `commitment` must be valid; an empty response commitment is MEDIUM.
# A non-empty `real_action_id` makes it a feint: `action_id` is then the APPARENT technique (it never resolves) and the real technique
# settles everything below. An empty one is a direct technique and every line behaves exactly as before B1h.
func attempt(action_id: String, response_id: String, commitment: String, response_commitment: String = "", real_action_id: String = "") -> Result:
    var error := validate_context()
    if error.is_empty():
        error = _shape_error(action_id, response_id, commitment, response_commitment)
    var feint := not real_action_id.is_empty()
    if error.is_empty() and feint:
        error = feint_error(action_id, real_action_id, commitment)
    if not error.is_empty():
        return _fail(error)
    var apparent_id := action_id
    if feint:
        action_id = real_action_id
    var side := initiator
    var other := "bottom" if side == "top" else "top"
    var initiator_pool := _pool_of(side)
    var responder_pool := _pool_of(other)
    # Capture before any charge.
    var requested_response := DEFAULT_COMMITMENT if response_commitment.is_empty() else response_commitment
    var initiator_funding := _feint_funding(initiator_pool.current, commitment) if feint else cost_policy.determine(commitment, initiator_pool.current)
    var initiator_total_cost := initiator_funding.effective_cost + (BjjHalfGuardRules.FEINT_SURCHARGE if feint else 0)
    var responder_funding := cost_policy.determine(requested_response, responder_pool.current)
    var input := BjjHalfGuardResolver.Inputs.new()
    input.side = side
    input.action_id = action_id
    input.response_id = response_id
    input.axis_tenths = axis_tenths
    input.band = band
    input.top_base = top_base
    input.bottom_frame = bottom_frame
    input.initiator_band = initiator_pool.band
    input.responder_band = responder_pool.band
    input.initiator_effective = initiator_funding.effective
    input.responder_effective = responder_funding.effective
    input.feint_apparent_id = apparent_id if feint else ""
    var resolution := BjjHalfGuardResolver.resolve(input)
    var tiers_before := {"top_base": top_base, "bottom_frame": bottom_frame}
    var band_before := band
    var axis_before := axis_tenths
    # Stamina charges: the initiator first, then the responder unless Rule 1 waives the charge.
    var initiator_charge := initiator_pool.spend_up_to(initiator_total_cost)
    var waived := 0
    var responder_cost := responder_funding.effective_cost
    if BjjCommitmentSettlement.waives_response_cost(true, initiator_funding.effective):
        waived = responder_cost
        responder_cost = 0
    var responder_charge := responder_pool.spend_up_to(responder_cost)
    var paid := responder_funding.effective_cost > 0 and responder_charge.charged >= responder_funding.effective_cost
    var readiness := BjjHalfGuardResolver.update_readiness(input, resolution.final_grade, paid)
    # Commit.
    axis_tenths = resolution.axis_after
    band = resolution.band_after
    top_base = readiness.top_base
    bottom_frame = readiness.bottom_frame
    if not resolution.exit_destination.is_empty():
        exit_destination = resolution.exit_destination
        var verb := "pass" if action_id == BjjHalfGuardCatalog.TOP_KNEE_SLICE else "escape"
        exit_reason = "%s reached the %s line with final grade %s" % [BjjHalfGuardCatalog.technique_name(action_id), verb,
            BjjHalfGuardRules.GRADE_NAMES[resolution.final_grade]]
    else:
        initiator = other
    history["initiated_action_history"].append(action_id)
    history["response_history"].append(response_id)
    history["raw_grade_history"].append(BjjHalfGuardRules.GRADE_NAMES[resolution.raw_grade])
    history["modified_grade_history"].append(BjjHalfGuardRules.GRADE_NAMES[resolution.final_grade])
    history["initiator_effective_commitment_history"].append(initiator_funding.effective)
    history["responder_effective_commitment_history"].append(responder_funding.effective)
    history["response_charge_history"].append(responder_charge.charged)
    history["response_waived_history"].append(waived)
    if band != band_before:
        history["band_change_history"].append("%d->%d" % [band_before, band])
    for change: String in readiness.changes:
        history["readiness_change_history"].append(change)
    history[side + "_initiation_count"] = int(history[side + "_initiation_count"]) + 1
    var result := Result.new()
    result.values = {"kind": "exchange", "initiator": side, "action_id": action_id, "response_id": response_id,
        "commitment_requested": commitment, "response_commitment_requested": requested_response,
        "initiator_band": input.initiator_band, "responder_band": input.responder_band,
        "exhaustion_modifier": resolution.exhaustion_modifier,
        "initiator_effective": initiator_funding.effective, "responder_effective": responder_funding.effective,
        "initiator_effective_cost": initiator_funding.effective_cost, "responder_effective_cost": responder_funding.effective_cost,
        "initiator_charged": initiator_charge.charged, "responder_charged": responder_charge.charged, "responder_waived": waived,
        "paid_effort": paid, "raw_grade": resolution.raw_grade, "positional_modifier": resolution.positional_modifier,
        "attack_readiness_shift": resolution.attack_readiness_shift,
        "defense_strength_tier": resolution.defense_strength_tier if resolution.defense_strength_tier >= 0 else null,
        "defense_readiness_shift": resolution.defense_readiness_shift,
        "grade_after_positional": resolution.grade_after_positional, "grade_after_attack": resolution.grade_after_attack,
        "grade_after_defense": resolution.grade_after_defense, "grade_after_exhaustion": resolution.grade_after_exhaustion,
        "magnitude_modifier": resolution.magnitude_modifier, "grade_after_magnitude": resolution.grade_after_magnitude,
        "undercommitment_modifier": resolution.undercommitment_modifier, "final_grade": resolution.final_grade,
        "axis_before": axis_before, "axis_proposed": resolution.axis_proposed, "axis_after": resolution.axis_after,
        "band_before": band_before, "band_after": resolution.band_after, "exit_destination": resolution.exit_destination,
        "tiers_before": tiers_before, "tiers_after": {"top_base": top_base, "bottom_frame": bottom_frame},
        "readiness_changes": readiness.changes.duplicate()}
    if feint:
        result.values["feint"] = {"apparent_action_id": apparent_id, "real_action_id": action_id,
            "bite_response_id": str(BjjHalfGuardCatalog.FEINT_PAIRS[apparent_id].bite), "bit": resolution.feint_bit,
            "modifier": resolution.feint_modifier, "grade_before": resolution.grade_after_defense, "grade_after": resolution.grade_after_feint,
            "surcharge": BjjHalfGuardRules.FEINT_SURCHARGE, "surcharge_charged": BjjHalfGuardRules.FEINT_SURCHARGE,
            "total_cost": initiator_total_cost, "exit_capped": resolution.exit_capped}
    return result
