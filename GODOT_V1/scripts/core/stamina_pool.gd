class_name BjjStaminaPool
extends RefCounted

# Python domain/stamina.py. Call create(); new() is a valid default pool.
# GDScript has no private members: underscore fields are implementation-only.
# Public properties have no backing mutable simulation state.
const MAXIMUM_EXACT: int = 9007199254740991 # Largest exact JSON/double integer.
const BANDS: Array[String] = ["Fresh", "Working", "Tired", "Exhausted"]

var _current: int = 100
var _maximum: int = 100
var _exhausted_latched: bool = false

var current: int:
    get: return _current
    set(_value): _reject_property_write("current")
var maximum: int:
    get: return _maximum
    set(_value): _reject_property_write("maximum")
var exhaustion_enter_threshold: int:
    get: return floori(float(_maximum) * 0.25)
    set(_value): _reject_property_write("exhaustion_enter_threshold")
var exhaustion_recover_threshold: int:
    get: return ceili(float(_maximum) * 0.35)
    set(_value): _reject_property_write("exhaustion_recover_threshold")
var ratio: float:
    get: return float(_current) / float(_maximum)
    set(_value): _reject_property_write("ratio")
var band: String:
    get:
        if _exhausted_latched:
            return "Exhausted"
        if ratio > 0.75:
            return "Fresh"
        if ratio > 0.50:
            return "Working"
        return "Tired"
    set(_value): _reject_property_write("band")

func _reject_property_write(property: String) -> void:
    push_error("read_only_property: %s; use controlled pool methods" % property)

class Creation extends RefCounted:
    var pool: BjjStaminaPool
    var error: String = ""
    func ok() -> bool:
        return error.is_empty()

class Change extends RefCounted:
    var error: String = ""
    var before: int = 0
    var requested: int = 0
    var charged: int = 0
    var shortfall: int = 0
    var recovered: int = 0
    var overflow: int = 0
    var after: int = 0
    var fully_paid: bool:
        get: return error.is_empty() and shortfall == 0
    func ok() -> bool:
        return error.is_empty()
    func spend_fields() -> Dictionary:
        return {"before": before, "requested": requested, "charged": charged,
            "shortfall": shortfall, "after": after, "fully_paid": fully_paid}
    func recovery_fields() -> Dictionary:
        return {"before": before, "requested": requested, "recovered": recovered,
            "overflow": overflow, "after": after}

static func create(start: int = 100, capacity: int = 100) -> Creation:
    var r := Creation.new()
    if capacity <= 0:
        r.error = "maximum_must_be_positive"
        return r
    if capacity > MAXIMUM_EXACT:
        r.error = "maximum_outside_exact_numeric_range"
        return r
    if start < 0 or start > capacity:
        r.error = "current_out_of_range"
        return r
    r.pool = BjjStaminaPool.new()
    r.pool._maximum = capacity
    r.pool._current = start
    r.pool._exhausted_latched = start <= r.pool.exhaustion_enter_threshold
    return r

func _refresh_latch() -> void:
    if _exhausted_latched:
        if _current >= exhaustion_recover_threshold:
            _exhausted_latched = false
    elif _current <= exhaustion_enter_threshold:
        _exhausted_latched = true

func set_current(value: int) -> String:
    if value < 0 or value > _maximum:
        return "current_out_of_range"
    _current = value
    _refresh_latch()
    return ""

func spend_up_to(requested: int) -> Change:
    var r := Change.new()
    r.before = _current
    r.after = _current
    r.requested = requested
    if requested < 0:
        r.error = "negative_expenditure"
        return r
    r.charged = mini(_current, requested)
    r.shortfall = requested - r.charged
    _current -= r.charged
    _refresh_latch()
    r.after = _current
    return r

func recover_up_to(requested: int) -> Change:
    var r := Change.new()
    r.before = _current
    r.after = _current
    r.requested = requested
    if requested < 0:
        r.error = "negative_recovery"
        return r
    r.recovered = mini(_maximum - _current, requested)
    r.overflow = requested - r.recovered
    _current += r.recovered
    _refresh_latch()
    r.after = _current
    return r
