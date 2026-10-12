class_name BjjBehaviorStaminaPolicy
extends RefCounted

const BEHAVIORS: Array[String] = ["PRESSURE", "HOLD", "ESCAPE", "PROTECT", "CONSERVE"]
const INT_MAX: int = 9223372036854775807
var _quantum_seconds: int = 5
var _rates: Dictionary[String, int] = {"PRESSURE": -1, "HOLD": 0, "ESCAPE": -1, "PROTECT": 0, "CONSERVE": 2}
var quantum_seconds: int:
    get: return _quantum_seconds

class Meter extends RefCounted:
    # Python permits preloaded carries, including outside (-quantum, quantum).
    var remainder_units: int = 0
    func _init(remainder: int = 0) -> void:
        remainder_units = remainder

class BuildResult extends RefCounted:
    var policy: BjjBehaviorStaminaPolicy
    var error: String = ""
    func ok() -> bool:
        return error.is_empty()

class Flow extends RefCounted:
    var error: String = ""
    var behavior: String = ""
    var duration_seconds: int = 0
    var quantum_seconds: int = 0
    var before: int = 0
    var spent: int = 0
    var spend_shortfall: int = 0
    var recovered: int = 0
    var recovery_overflow: int = 0
    var after: int = 0
    var remainder_before: int = 0
    var remainder_after: int = 0
    var net_change: int:
        get: return after - before
    func ok() -> bool:
        return error.is_empty()
    func fields() -> Dictionary:
        return {"behavior": behavior, "duration_seconds": duration_seconds,
            "quantum_seconds": quantum_seconds, "before": before, "spent": spent,
            "spend_shortfall": spend_shortfall, "recovered": recovered,
            "recovery_overflow": recovery_overflow, "after": after,
            "remainder_before": remainder_before, "remainder_after": remainder_after,
            "net_change": net_change}

static func defaults() -> BjjBehaviorStaminaPolicy:
    return BjjBehaviorStaminaPolicy.new()

static func build(quantum: int, rates: Dictionary) -> BuildResult:
    var r := BuildResult.new()
    if quantum <= 0:
        r.error = "quantum_must_be_positive"
        return r
    if rates.size() != BEHAVIORS.size():
        r.error = "behavior_keys_mismatch"
        return r
    var copied: Dictionary[String, int] = {}
    for id: String in BEHAVIORS:
        if not rates.has(id):
            r.error = "behavior_keys_mismatch"
            return r
        if not (rates[id] is int or rates[id] is bool) or int(rates[id]) < -INT_MAX:
            r.error = "rate_outside_supported_integer_range"
            return r
        # Match Python isinstance(bool, int); arithmetic naturally uses 0/1.
        copied[id] = int(rates[id])
    r.policy = BjjBehaviorStaminaPolicy.new()
    r.policy._quantum_seconds = quantum
    r.policy._rates = copied
    return r

func apply(pool: BjjStaminaPool, behavior: String, duration_seconds: int, meter: Meter) -> Flow:
    var r := Flow.new()
    if pool == null or meter == null:
        r.error = "missing_pool_or_meter"
        return r
    if duration_seconds < 0:
        r.error = "negative_duration"
        return r
    if not _rates.has(behavior):
        r.error = "invalid_behavior"
        return r
    # Validate all integer arithmetic before either mutable object changes.
    var rate: int = _rates[behavior]
    @warning_ignore("integer_division")
    if rate != 0 and duration_seconds > INT_MAX / absi(rate):
        r.error = "flow_product_overflow"
        return r
    var delta: int = rate * duration_seconds
    var carry: int = meter.remainder_units
    if (delta > 0 and carry > INT_MAX - delta) or (delta < 0 and carry < -INT_MAX - delta):
        r.error = "flow_sum_overflow"
        return r
    var units: int = carry + delta
    if units < -INT_MAX:
        r.error = "flow_units_outside_supported_range"
        return r
    r.behavior = behavior
    r.duration_seconds = duration_seconds
    r.quantum_seconds = _quantum_seconds
    r.before = pool.current
    r.remainder_before = carry
    if units <= -_quantum_seconds:
        @warning_ignore("integer_division")
        var requested: int = (-units) / _quantum_seconds
        units = -((-units) % _quantum_seconds)
        var spend := pool.spend_up_to(requested)
        r.spent = spend.charged
        r.spend_shortfall = spend.shortfall
    elif units >= _quantum_seconds:
        @warning_ignore("integer_division")
        var requested: int = units / _quantum_seconds
        units %= _quantum_seconds
        var recovery := pool.recover_up_to(requested)
        r.recovered = recovery.recovered
        r.recovery_overflow = recovery.overflow
    # Saturation discards whole units; the signed fractional carry survives.
    meter.remainder_units = units
    r.remainder_after = units
    r.after = pool.current
    return r
