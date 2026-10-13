class_name BjjSideControlRules
extends RefCounted

# Side Control v0 constants and pure axis/band rules (SIDE_CONTROL_V0_RULES.md section 2). Provisional prototype baseline, not final game
# balance. The axis is a signed integer in tenths (positive favors the Top); no float is ever stored. It belongs to Side Control and is
# never converted from another position's axis. Nothing here mutates state.
const POSITION_ID: String = "side_control"
const AXIS_MIN: int = -40
const AXIS_MAX: int = 40
const ENTRY_AXIS: int = 10
const ENTRY_BAND: int = 1
const ENTRY_TIER: int = 1
const TIER_MAX: int = 2
const STEP_TENTHS: int = 10
const EXIT_LINE: int = 30
const NO_BAND_CHANGE: int = 99

# Defense readiness shift by the defender's strength tier (None +2 / Partial 0 / Ready -1).
const DEFENSE_SHIFT: Dictionary = {2: -1, 1: 0, 0: 2}
const GRADE_NAMES: Dictionary = {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"}
const TIMEOUT_REASON: String = "TIMEOUT — Side Control retained"

# One SC-N7 hysteresis rule application, or NO_BAND_CHANGE when none matches. Each band has at most one applicable rule per axis, so
# repeated application terminates; the overlap between a band's "enter" and "leave" thresholds is the hysteresis.
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

# The (axis, band) pairs the hysteresis rules can leave behind; anything else is a corrupted state.
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

# Reported only: no mechanical effect in v0 (SC-D3).
static func authority_id(axis: int, top_id: String, bottom_id: String) -> String:
    if axis > 0:
        return top_id
    if axis < 0:
        return bottom_id
    return ""
