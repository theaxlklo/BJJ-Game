class_name BjjD3BController
extends RefCounted

# interfaces/handoff_policy.py::D3BTokenLockoutController. No timer, RNG,
# behavior override or stamina mutation. Observe every successful advance.
var armed: bool = false
var token_consumed: bool = false
var previous_exhausted: bool = false
var initialized: bool = false

class Creation extends RefCounted:
    var error: String = ""
    var controller: BjjD3BController
    func ok() -> bool:
        return error.is_empty() and controller != null

class Decision extends RefCounted:
    var error: String = "incomplete_decision"
    var kind: String = ""
    var mode_before: bool = false
    var mode_after: bool = false
    var hold: bool:
        get: return kind == "LOCKOUT_HOLD"
    func ok() -> bool:
        return error.is_empty() and not kind.is_empty()
    func fields() -> Dictionary:
        if not ok():
            return {"error":error}
        return {"kind":kind, "requested_commitment":null, "transition":null,
            "mode_before":mode_before, "mode_after":mode_after}

static func create(match_state: BjjMountExchange) -> Creation:
    var result := Creation.new()
    if match_state == null or match_state.bottom == null:
        result.error = "missing_match_or_bottom"
        return result
    result.controller = BjjD3BController.new()
    result.controller.previous_exhausted = match_state.bottom.band == "Exhausted"
    result.controller.initialized = true
    return result

func observe_advance(match_state: BjjMountExchange) -> String:
    if not initialized or match_state == null or match_state.bottom == null:
        return "uninitialized_or_missing_match"
    var exhausted := match_state.bottom.band == "Exhausted"
    if previous_exhausted and not exhausted:
        armed = true
        token_consumed = false
    previous_exhausted = exhausted
    return ""

func decide(match_state: BjjMountExchange) -> Decision:
    var result := Decision.new()
    if not initialized or match_state == null or match_state.bottom == null:
        result.error = "uninitialized_or_missing_match"
        return result
    if match_state.initiator != "bottom":
        result.error = "bottom_window_required"
        return result
    var exhausted := match_state.bottom.band == "Exhausted"
    previous_exhausted = exhausted
    if not armed:
        result.kind = "UNARMED"
    elif not exhausted:
        result.kind = "ARMED_NORMAL"
    elif not token_consumed:
        token_consumed = true
        result.kind = "TOKEN"
        result.mode_after = true
    elif token_consumed:
        result.kind = "LOCKOUT_HOLD"
        result.mode_before = true
        result.mode_after = true
    result.error = ""
    return result

func pre_advance_bottom_behavior(chosen: String) -> String:
    return chosen

func pending(match_state: BjjMountExchange) -> bool:
    return initialized and match_state != null and match_state.bottom != null and armed and match_state.bottom.band == "Exhausted"

func fields() -> Dictionary:
    return {"armed":armed, "token_consumed":token_consumed, "previous_exhausted":previous_exhausted,
        "recovery_hold_mode":armed and token_consumed}
