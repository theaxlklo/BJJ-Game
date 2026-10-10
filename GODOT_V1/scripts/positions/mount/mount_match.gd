class_name BjjMountMatch
extends BjjMountExchange

# Headless lifecycle around the proven exchange slice. Simulated integer seconds
# only; presentation and decision deadlines never drive this clock.
var interval_seconds: int = BjjMountRules.DEFAULT_INTERVAL_SECONDS
var behavior_policy: BjjBehaviorStaminaPolicy = BjjBehaviorStaminaPolicy.defaults()
var top_meter: BjjBehaviorStaminaPolicy.Meter = BjjBehaviorStaminaPolicy.Meter.new()
var bottom_meter: BjjBehaviorStaminaPolicy.Meter = BjjBehaviorStaminaPolicy.Meter.new()
var recover_enabled: bool = false
var bottom_baseline: String = "ESCAPE"
var baseline_commitment: String = "MEDIUM"

class Status extends RefCounted:
    var error: String = ""
    func ok() -> bool:
        return error.is_empty()

class Advance extends RefCounted:
    var error: String = "incomplete_advance"
    var drift: Dictionary = {}
    var top_stamina: BjjBehaviorStaminaPolicy.Flow
    var bottom_stamina: BjjBehaviorStaminaPolicy.Flow
    func ok() -> bool:
        return error.is_empty() and top_stamina != null and bottom_stamina != null
    func fields() -> Dictionary:
        if not ok():
            return {"error":error}
        return {"drift":drift.duplicate(true), "top_stamina":top_stamina.fields(), "bottom_stamina":bottom_stamina.fields()}

var ended: bool:
    get: return clock_seconds <= 0 or position.broken or submission_tapped
var elapsed_simulated_time: int:
    get: return initial_clock - clock_seconds

class Creation extends RefCounted:
    var error: String = ""
    var match_state: BjjMountMatch
    func ok() -> bool:
        return error.is_empty() and match_state != null

static func create(configuration: Dictionary) -> Creation:
    var result := Creation.new()
    const KEYS: Array[String] = ["clock", "interval", "axis", "top_stamina", "bottom_stamina", "capacity", "rules", "production"]
    for key: Variant in configuration:
        if not key is String or not KEYS.has(key):
            result.error = "unknown_match_configuration"
            return result
    for key: String in ["clock", "interval", "top_stamina", "bottom_stamina", "capacity"]:
        if configuration.has(key) and not configuration[key] is int:
            result.error = "match_integer_required"
            return result
    var clock: int = configuration.get("clock", 300)
    var interval: int = configuration.get("interval", 5)
    var capacity: int = configuration.get("capacity", 100)
    var axis_value: Variant = configuration.get("axis", 1.5)
    if not (axis_value is int or axis_value is float) or not is_finite(float(axis_value)):
        result.error = "finite_axis_required"
        return result
    var axis: float = float(axis_value)
    if clock <= 0 or clock > BjjStaminaPool.MAXIMUM_EXACT or interval <= 0 or axis < BjjMountRules.MIN_AXIS or axis > BjjMountRules.MAX_AXIS:
        result.error = "match_configuration_out_of_range"
        return result
    var settings: Variant = configuration.get("rules", {})
    var production: Variant = configuration.get("production", false)
    if not settings is Dictionary or not production is bool:
        result.error = "invalid_match_policy_configuration"
        return result
    var rules_result := BjjExchangeRules.build(settings)
    var top_result := BjjStaminaPool.create(configuration.get("top_stamina", capacity), capacity)
    var bottom_result := BjjStaminaPool.create(configuration.get("bottom_stamina", capacity), capacity)
    if not rules_result.ok() or not top_result.ok() or not bottom_result.ok():
        result.error = "invalid_rules_or_fighter_stamina"
        return result
    var state := BjjMountMatch.new()
    state.initial_clock = clock
    state.clock_seconds = clock
    state.interval_seconds = interval
    state.position = BjjMountPosition.new(axis)
    state.rules = rules_result.rules
    state.top = top_result.pool
    state.bottom = bottom_result.pool
    if production:
        var selected := state.configure_production()
        if not selected.ok():
            result.error = selected.error
            return result
    result.match_state = state
    return result

func configure_recover(enabled: bool, baseline: String = "ESCAPE", commitment: String = "MEDIUM") -> Status:
    var result := Status.new()
    if d3b != null and (not enabled or baseline != "ESCAPE" or commitment != "MEDIUM"):
        result.error = "active_production_configuration_is_fixed"
        return result
    if not ["ESCAPE", "PROTECT", "CONSERVE"].has(baseline) or not BjjCommitment.valid(commitment):
        result.error = "invalid_recovery_configuration"
        return result
    recover_enabled = enabled
    bottom_baseline = baseline
    baseline_commitment = commitment
    return result

func configure_production_recover() -> Status:
    var result := Status.new()
    # E-PROD prerequisites from interfaces/batch.py. The production selector
    # never enables match features on the caller's behalf.
    if rules == null or not rules.setup or not rules.v04 or not rules.rule1 or rules.rule2:
        result.error = "unsupported_production_recovery_configuration"
        return result
    return configure_recover(true, "ESCAPE", "MEDIUM")

func recovery_behavior() -> String:
    return "CONSERVE" if recover_enabled and bottom.band == "Exhausted" else bottom_baseline

func selected_commitment() -> String:
    return "LOW" if recover_enabled and initiator == "bottom" and bottom.band == "Exhausted" else baseline_commitment

func _advance_error(duration: int) -> String:
    if d3b != null and not d3b.initialized:
        return "uninitialized_controller"
    if duration < 0 or interval_seconds <= 0:
        return "invalid_duration_or_interval"
    if behavior_policy == null or top_meter == null or bottom_meter == null or top_meter == bottom_meter:
        return "missing_or_aliased_behavior_state"
    return validate_context(true)

static func _copy_pool(pool: BjjStaminaPool) -> BjjStaminaPool:
    var copy := BjjStaminaPool.create(0 if pool.band == "Exhausted" else pool.current, pool.maximum).pool
    copy.set_current(pool.current)
    return copy

func advance(duration: int = interval_seconds) -> Advance:
    var result := Advance.new()
    result.error = _advance_error(duration)
    if not result.error.is_empty():
        return result
    var elapsed := mini(duration, clock_seconds)
    # Preflight both flows against detached pools and meters. Overflow in the
    # second fighter cannot leave drift or the first fighter partially committed.
    var top_flow := behavior_policy.apply(_copy_pool(top), top_behavior, elapsed, BjjBehaviorStaminaPolicy.Meter.new(top_meter.remainder_units))
    var bottom_flow := behavior_policy.apply(_copy_pool(bottom), bottom_behavior, elapsed, BjjBehaviorStaminaPolicy.Meter.new(bottom_meter.remainder_units))
    if not top_flow.ok() or not bottom_flow.ok():
        result.error = top_flow.error if not top_flow.ok() else bottom_flow.error
        return result
    result.drift = BjjMountDrift.simulate(position.axis, position.band, clock_seconds, duration, top_behavior, bottom_behavior)
    position.apply_control(float(result.drift.end_axis), int(result.drift.end_band))
    clock_seconds = int(result.drift.end_clock)
    history.top_behavior_history.append(top_behavior)
    history.bottom_behavior_history.append(bottom_behavior)
    if clock_seconds == 0 and exit_destination.is_empty():
        exit_reason = "TIMEOUT — Mount retained"
    result.top_stamina = behavior_policy.apply(top, top_behavior, elapsed, top_meter)
    result.bottom_stamina = behavior_policy.apply(bottom, bottom_behavior, elapsed, bottom_meter)
    history.top_behavior_stamina_history.append(result.top_stamina.net_change)
    history.bottom_behavior_stamina_history.append(result.bottom_stamina.net_change)
    if d3b != null:
        d3b.observe_advance(self)
    return result

func recovery_advance(duration: int = interval_seconds) -> Advance:
    # Batch RECOVER changes the pre-advance behavior, then re-chooses after clear.
    # Validate first so a rejected update cannot change even the chosen behavior.
    var error := _advance_error(duration)
    if not error.is_empty():
        var rejected := Advance.new()
        rejected.error = error
        return rejected
    var previous := bottom_behavior
    bottom_behavior = recovery_behavior()
    var result := advance(duration)
    if not result.ok():
        bottom_behavior = previous
    elif not ended:
        bottom_behavior = recovery_behavior()
    return result

func lifecycle_fields() -> Dictionary:
    var values := snapshot().fields()
    values["history"] = history.fields()
    values["top_behavior"] = top_behavior
    values["bottom_behavior"] = bottom_behavior
    values["top_remainder"] = top_meter.remainder_units
    values["bottom_remainder"] = bottom_meter.remainder_units
    values["free_pending"] = free_initiative_pending
    values["free_beneficiary"] = free_initiative_beneficiary
    return values

# Free-window ownership is an integration boundary for the optional stalling
# controller. No free window is manufactured by the ordinary Mount lifecycle.
var free_initiative_pending: bool = false
var free_initiative_beneficiary: String = ""
var d3b: BjjD3BController

class WindowResult extends RefCounted:
    var error: String = "incomplete_window"
    var values: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()
    func fields() -> Dictionary:
        return values.duplicate(true) if ok() else {"error":error}

class Selection extends RefCounted:
    var error: String = ""
    var ids: Array[String] = []
    func ok() -> bool:
        return error.is_empty()

func configure_production() -> Status:
    var result := Status.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    result = configure_production_recover()
    if not result.ok():
        return result
    # Repeated selection is idempotent: never grant a second token by rebuilding.
    if d3b == null:
        d3b = BjjD3BController.create(self).controller
    return result

func reset_window() -> WindowResult:
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    var side := initiator
    initiator = "bottom" if side == "top" else "top"
    result.values = {"initiator":side, "next_initiator":initiator,
        "clock_seconds":clock_seconds, "axis":position.reported_axis(), "band":position.band,
        "stamina":top.current if side == "top" else bottom.current,
        "progress_route_available":false, "advancement_clock_seconds":0,
        "stalling_offense":false, "stalling_consequence":null, "penalty_axis_before":null,
        "penalty_axis_after":null, "position_reset":false, "position_reset_axis_before":null,
        "position_reset_axis_after":null, "free_initiative_window":false}
    history.reset_window_history.append(side)
    return result

func recovery_hold() -> WindowResult:
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if initiator != "bottom":
        result.error = "bottom_window_required"
        return result
    result.values = {"side":"bottom", "next_initiator":"top", "elapsed_seconds":elapsed_simulated_time,
        "clock_seconds":clock_seconds, "stamina":bottom.current}
    history.recovery_hold_history.append("bottom@%ds:stamina=%d" % [elapsed_simulated_time, bottom.current])
    initiator = "top"
    return result

func consume_free_window() -> WindowResult:
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if not free_initiative_pending:
        result.values = {"side":null}
        return result
    if not ["top", "bottom"].has(free_initiative_beneficiary) or initiator != free_initiative_beneficiary:
        result.error = "invalid_free_window_ownership"
        return result
    result.values = {"side":free_initiative_beneficiary}
    free_initiative_pending = false
    free_initiative_beneficiary = ""
    return result

func legal_actions(side: String = initiator) -> Selection:
    var result := Selection.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if not ["top", "bottom"].has(side):
        result.error = "invalid_side"
        return result
    for id: String in C.ENTITIES:
        var entity: Dictionary = C.ENTITIES[id]
        if entity.kind == "action" and entity.side == side and (not rules.setup or not _is_target(id) or _tier(id) == 2):
            result.ids.append(id)
    if rules.submissions and side == "top" and not submission_stage.is_empty():
        result.ids.append(FINISH)
    return result

func legal_responses(action_id: String) -> Selection:
    var result := Selection.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if not legal_actions().ids.has(action_id):
        result.error = "illegal_action"
        return result
    for id: String in C.ENTITIES:
        if C.ENTITIES[id].kind == "response" and _validate(BjjExchangeResult.Request.new(action_id, id, "MEDIUM")).is_empty():
            result.ids.append(id)
    return result

func next_window(duration: int = interval_seconds) -> WindowResult:
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if duration < 0 or (free_initiative_pending and (free_initiative_beneficiary != initiator)):
        result.error = "invalid_window_request"
        return result
    var free := consume_free_window()
    if not free.ok():
        return free
    var advance_result: Advance
    if free.values.side == null:
        advance_result = recovery_advance(duration) if recover_enabled else advance(duration)
        if not advance_result.ok():
            result.error = advance_result.error
            return result
    result.values = {"free":free.values.side != null, "closed":ended, "initiator":initiator,
        "commitment":selected_commitment(), "advance":advance_result.fields() if advance_result != null else null}
    return result

func bottom_decision(action_id: String = "", response_id: String = "", response_commitment: String = "") -> WindowResult:
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if initiator != "bottom":
        result.error = "bottom_window_required"
        return result
    if action_id.is_empty() and not response_id.is_empty():
        result.error = "response_without_action"
        return result
    var request := BjjExchangeResult.Request.new(action_id, response_id, selected_commitment(), response_commitment)
    if not action_id.is_empty():
        result.error = _validate(request)
        if not result.error.is_empty():
            return result
    var decision: BjjD3BController.Decision
    if d3b != null:
        decision = d3b.decide(self)
        if not decision.ok():
            result.error = decision.error
            return result
    var settlement: Dictionary
    if decision != null and decision.hold:
        settlement = recovery_hold().fields()
    elif action_id.is_empty():
        settlement = reset_window().fields()
    else:
        settlement = attempt(request).fields()
    result.values = {"decision":decision.fields() if decision != null else null, "settlement":settlement}
    return result

func decide_legacy(action_id: String, response_id: String) -> WindowResult:
    # Frozen Mount-v0 decision is stamina-free and does not apply modern setup,
    # submission, exhaustion or commitment transformations.
    var result := WindowResult.new()
    result.error = validate_context()
    if not result.error.is_empty():
        return result
    if not C.RAW_GRADES.has(action_id + "|" + response_id) or C.ENTITIES[action_id].side != initiator:
        result.error = "illegal_legacy_matchup"
        return result
    var resolution := BjjExchangeResult.Resolution.from_fields(BjjMountResolver.resolve_action(
        position.axis, position.band, initiator, action_id, response_id, top_behavior, bottom_behavior))
    _apply_resolution(resolution)
    result.values = resolution.fields()
    return result
