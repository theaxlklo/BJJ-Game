class_name BjjHalfGuardEntry
extends RefCounted

# Neutral, fighter-id-keyed entry request validation (HALF_GUARD_V0_RULES.md section 4). Pure: it reads the request,
# builds nothing and mutates nothing. This is the only way a Half Guard match is built; it assumes no source position
# (a Mount edge adapter is a later slice) and carries no readiness field (an extra key is refused).
#
#   {"role_map": {"top": id, "bottom": id},
#    "fighters": {id: {"stamina_current": int, "stamina_maximum": int, "exhaustion_latched": bool, "behavior_remainder_units": int}},
#    "clock": {"initial_seconds": int, "remaining_seconds": int}, "window": {"last_issued_id": int}, "interval_seconds": int}
const KEYS: Array[String] = ["role_map", "fighters", "clock", "window", "interval_seconds"]
const FIGHTER_KEYS: Array[String] = ["stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"]
const MAXIMUM: int = BjjStaminaPool.MAXIMUM_EXACT

static func _exact_keys(value: Variant, expected: Array[String]) -> bool:
    if typeof(value) != TYPE_DICTIONARY:
        return false
    var dictionary: Dictionary = value
    if dictionary.size() != expected.size():
        return false
    for key: String in expected:
        if not dictionary.has(key):
            return false
    return true

static func _is_int(value: Variant) -> bool:
    return typeof(value) == TYPE_INT

# First failing code, or "" when the request is valid. Order is the rules sheet's order.
static func validate(request: Variant) -> String:
    if typeof(request) != TYPE_DICTIONARY:
        return "entry_not_a_dictionary"
    if not _exact_keys(request, KEYS):
        return "entry_malformed"
    var role_map: Variant = request["role_map"]
    var fighters: Variant = request["fighters"]
    var clock: Variant = request["clock"]
    var window: Variant = request["window"]
    var role_keys: Array[String] = ["top", "bottom"]
    if not _exact_keys(role_map, role_keys) or typeof(role_map["top"]) != TYPE_STRING or typeof(role_map["bottom"]) != TYPE_STRING:
        return "entry_malformed"
    if typeof(fighters) != TYPE_DICTIONARY:
        return "entry_malformed"
    for key: Variant in fighters:
        if typeof(key) != TYPE_STRING:
            return "entry_malformed"
    var clock_keys: Array[String] = ["initial_seconds", "remaining_seconds"]
    if not _exact_keys(clock, clock_keys) or not _is_int(clock["initial_seconds"]) or not _is_int(clock["remaining_seconds"]):
        return "entry_malformed"
    var window_keys: Array[String] = ["last_issued_id"]
    if not _exact_keys(window, window_keys) or not _is_int(window["last_issued_id"]):
        return "entry_malformed"
    if not _is_int(request["interval_seconds"]):
        return "entry_malformed"
    for key: String in fighters:
        var record: Variant = fighters[key]
        if not _exact_keys(record, FIGHTER_KEYS):
            return "entry_malformed"
        if not (_is_int(record["stamina_current"]) and _is_int(record["stamina_maximum"])
                and typeof(record["exhaustion_latched"]) == TYPE_BOOL and _is_int(record["behavior_remainder_units"])):
            return "entry_malformed"
    var top_id: String = role_map["top"]
    var bottom_id: String = role_map["bottom"]
    # Identity rules are the position contract's own (non-empty, no code point 0x01..0x20 at either end, distinct).
    var id_error := BjjPositionContract.fighter_ids_error(top_id, bottom_id)
    if not id_error.is_empty():
        return id_error
    if fighters.size() != 2 or not fighters.has(top_id) or not fighters.has(bottom_id):
        return "fighters_mismatch"
    var ids: Array[String] = [top_id, bottom_id]
    for id: String in ids:
        var maximum: int = fighters[id]["stamina_maximum"]
        if maximum < 1 or maximum > MAXIMUM:
            return "invalid_stamina_maximum"
    for id: String in ids:
        var current: int = fighters[id]["stamina_current"]
        if current < 0 or current > int(fighters[id]["stamina_maximum"]):
            return "invalid_stamina_current"
    for id: String in ids:
        var pool := BjjStaminaPool.create(int(fighters[id]["stamina_maximum"]), int(fighters[id]["stamina_maximum"])).pool
        var current_value: int = fighters[id]["stamina_current"]
        var latched: bool = fighters[id]["exhaustion_latched"]
        if current_value <= pool.exhaustion_enter_threshold and not latched:
            return "inconsistent_exhaustion_latch"
        if current_value >= pool.exhaustion_recover_threshold and latched:
            return "inconsistent_exhaustion_latch"
    for id: String in ids:
        if absi(int(fighters[id]["behavior_remainder_units"])) > MAXIMUM:
            return "invalid_behavior_remainder"
    var initial: int = clock["initial_seconds"]
    var remaining: int = clock["remaining_seconds"]
    if initial < 1 or initial > MAXIMUM or remaining < 1 or remaining > initial:
        return "invalid_clock"
    var last_issued: int = window["last_issued_id"]
    if last_issued < 0 or last_issued > MAXIMUM:
        return "invalid_window_id"
    var interval: int = request["interval_seconds"]
    if interval < 1 or interval > MAXIMUM:
        return "invalid_interval"
    return ""
