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

func configure_recover(enabled: bool, baseline: String = "ESCAPE", commitment: String = "MEDIUM") -> Status:
    var result := Status.new()
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
    return values
