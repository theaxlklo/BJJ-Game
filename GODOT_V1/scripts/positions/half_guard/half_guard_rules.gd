class_name BjjHalfGuardRules
extends RefCounted

# Half Guard v0 constants and pure axis/band rules (HALF_GUARD_V0_RULES.md sections 2 and 3).
# Provisional prototype baseline, not final game balance. Nothing here mutates state.
# The axis is a signed integer in tenths (positive = Top passing advantage); no float is ever stored.
const POSITION_ID: String = "half_guard"
const AXIS_MIN: int = -40
const AXIS_MAX: int = 40
const ENTRY_AXIS: int = 5
const ENTRY_BAND: int = 0
const STEP_TENTHS: int = 10
const PASS_LINE: int = 30
const ESCAPE_LINE: int = -30
const NO_BAND_CHANGE: int = 99

# Readiness tiers (N-1): 0 None, 1 Partial, 2 Ready. Both tracks enter at Partial.
const TIER_NAMES: Array[String] = ["None", "Partial", "Ready"]
const TIER_MAX: int = 2
const ENTRY_TIER: int = 1
# N-3: attack readiness shift by the initiator's own track tier. N-4: defense readiness shift by the governed track tier.
const ATTACK_SHIFT: Dictionary = {2: 1, 1: 0, 0: -1}
const DEFENSE_SHIFT: Dictionary = {2: -1, 1: 0, 0: 2}

const BAND_NAMES: Dictionary = {-2: "BOTTOM_CONTROL", -1: "BOTTOM_EDGE", 0: "CONTESTED", 1: "TOP_EDGE", 2: "TOP_CONTROL"}
const GRADE_NAMES: Dictionary = {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"}
const TIMEOUT_REASON: String = "TIMEOUT — Half Guard retained"

static func initial_band(axis: int) -> int:
    var magnitude := absi(axis)
    var level := 0 if magnitude < 10 else (1 if magnitude < 25 else 2)
    return level if axis >= 0 else -level

# One hysteresis rule application, or NO_BAND_CHANGE when no rule matches.
static func band_step(axis: int, band: int) -> int:
    match band:
        0:
            if axis >= 12:
                return 1
            if axis <= -12:
                return -1
        1:
            if axis >= 27:
                return 2
            if axis <= 8:
                return 0
        2:
            if axis <= 23:
                return 1
        -1:
            if axis >= -8:
                return 0
            if axis <= -27:
                return -2
        -2:
            if axis >= -23:
                return -1
    return NO_BAND_CHANGE

static func band_update(axis: int, band: int) -> int:
    var current := band
    while true:
        var next := band_step(axis, current)
        if next == NO_BAND_CHANGE:
            return current
        current = next
    return current

static func legal_pair(axis: int, band: int) -> bool:
    match band:
        0:
            return axis > -12 and axis < 12
        1:
            return axis > 8 and axis < 27
        2:
            return axis > 23
        -1:
            return axis > -27 and axis < -8
        -2:
            return axis < -23
    return false

# Reported only: no mechanical effect in v0.
static func authority_id(axis: int, top_id: String, bottom_id: String) -> String:
    if axis > 0:
        return top_id
    if axis < 0:
        return bottom_id
    return ""

static func tier_name(tier: int) -> String:
    return TIER_NAMES[tier] if tier >= 0 and tier <= TIER_MAX else ""
