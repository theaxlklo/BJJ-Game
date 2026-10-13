class_name BjjSideControlEntry
extends RefCounted

# Neutral, fighter-id-keyed entry request validation (SIDE_CONTROL_V0_RULES.md section 4). Pure: it reads the request, builds nothing and
# mutates nothing. This is the only way a Side Control match is built. It assumes no source position (the Half Guard Knee Slice adapter
# is a later slice) and accepts no tier, axis or band key (an extra key is `entry_malformed`), so nothing earned elsewhere can carry in.
#
#   {"role_map": {"top": id, "bottom": id}, "initiator": "top" | "bottom",
#    "fighters": {id: {"stamina_current": int, "stamina_maximum": int, "exhaustion_latched": bool, "behavior_remainder_units": int}},
#    "clock": {"initial_seconds": int, "remaining_seconds": int}, "window": {"last_issued_id": int}, "interval_seconds": int}
const KEYS: Array[String] = ["role_map", "initiator", "fighters", "clock", "window", "interval_seconds"]
const FIGHTER_KEYS: Array[String] = ["stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"]
const MAXIMUM: int = BjjStaminaPool.MAXIMUM_EXACT

static func exact_keys(value: Variant, expected: Array[String]) -> bool:
    if typeof(value) != TYPE_DICTIONARY:
        return false
    var dictionary: Dictionary = value
    if dictionary.size() != expected.size():
        return false
    for key: String in expected:
        if not dictionary.has(key):
            return false
    return true

# A bool is not an int and a float is not an int (JSON's single number type is resolved by the caller before this boundary).
static func is_int(value: Variant) -> bool:
    return typeof(value) == TYPE_INT

# The shape of one fighter record (`exhaustion_latched` is a bool). Shared with the snapshot restore boundary.
static func pool_shape_ok(record: Variant) -> bool:
    return exact_keys(record, FIGHTER_KEYS) and is_int(record["stamina_current"]) and is_int(record["stamina_maximum"]) \
        and typeof(record["exhaustion_latched"]) == TYPE_BOOL and is_int(record["behavior_remainder_units"])

# True when `current` and `latched` contradict the exhaustion thresholds of `maximum` (at or below enter must be latched; at or above
# recover must not be). Strictly between them either value is accepted and carried, which preserves hysteresis across a boundary.
static func latch_inconsistent(current: int, maximum: int, latched: bool) -> bool:
    var pool := BjjStaminaPool.create(maximum, maximum).pool
    return (current <= pool.exhaustion_enter_threshold and not latched) or (current >= pool.exhaustion_recover_threshold and latched)

# First failing code, or "" when the request is valid. The order is the rules sheet's order.
static func validate(request: Variant) -> String:
    if typeof(request) != TYPE_DICTIONARY:
        return "entry_not_a_dictionary"
    if not exact_keys(request, KEYS):
        return "entry_malformed"
    var role_map: Variant = request["role_map"]
    var fighters: Variant = request["fighters"]
    var clock: Variant = request["clock"]
    var window: Variant = request["window"]
    var role_keys: Array[String] = ["top", "bottom"]
    if not exact_keys(role_map, role_keys) or typeof(role_map["top"]) != TYPE_STRING or typeof(role_map["bottom"]) != TYPE_STRING:
        return "entry_malformed"
    if typeof(request["initiator"]) != TYPE_STRING or typeof(fighters) != TYPE_DICTIONARY:
        return "entry_malformed"
    for key: Variant in fighters:
        if typeof(key) != TYPE_STRING or not pool_shape_ok(fighters[key]):
            return "entry_malformed"
    var clock_keys: Array[String] = ["initial_seconds", "remaining_seconds"]
    if not exact_keys(clock, clock_keys) or not is_int(clock["initial_seconds"]) or not is_int(clock["remaining_seconds"]):
        return "entry_malformed"
    var window_keys: Array[String] = ["last_issued_id"]
    if not exact_keys(window, window_keys) or not is_int(window["last_issued_id"]) or not is_int(request["interval_seconds"]):
        return "entry_malformed"
    var top_id: String = role_map["top"]
    var bottom_id: String = role_map["bottom"]
    # Identity rules are the position contract's own (non-empty, no code point 0x01..0x20 at either end, distinct).
    var id_error := BjjPositionContract.fighter_ids_error(top_id, bottom_id)
    if not id_error.is_empty():
        return id_error
    if fighters.size() != 2 or not fighters.has(top_id) or not fighters.has(bottom_id):
        return "fighters_mismatch"
    if request["initiator"] != "top" and request["initiator"] != "bottom":
        return "invalid_initiator"
    var ids: Array[String] = [top_id, bottom_id]  # role order: top, then bottom, within each of the next four checks
    for id: String in ids:
        var maximum: int = fighters[id]["stamina_maximum"]
        if maximum < 1 or maximum > MAXIMUM:
            return "invalid_stamina_maximum"
    for id: String in ids:
        var current: int = fighters[id]["stamina_current"]
        if current < 0 or current > int(fighters[id]["stamina_maximum"]):
            return "invalid_stamina_current"
    for id: String in ids:
        if latch_inconsistent(int(fighters[id]["stamina_current"]), int(fighters[id]["stamina_maximum"]), fighters[id]["exhaustion_latched"]):
            return "inconsistent_exhaustion_latch"
    for id: String in ids:
        # Two comparisons, not absi(): absi(-2^63) overflows and would slip through for a typed (non-JSON) caller.
        var remainder: int = fighters[id]["behavior_remainder_units"]
        if remainder > MAXIMUM or remainder < -MAXIMUM:
            return "invalid_behavior_remainder"
    var initial: int = clock["initial_seconds"]
    var remaining: int = clock["remaining_seconds"]
    if initial < 1 or initial > MAXIMUM or remaining < 1 or remaining > initial:
        return "invalid_clock"
    if int(window["last_issued_id"]) < 0 or int(window["last_issued_id"]) > MAXIMUM:
        return "invalid_window_id"
    if int(request["interval_seconds"]) < 1 or int(request["interval_seconds"]) > MAXIMUM:
        return "invalid_interval"
    return ""
