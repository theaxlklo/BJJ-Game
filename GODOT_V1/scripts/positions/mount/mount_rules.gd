class_name BjjMountRules
extends RefCounted

# Direct, parity-oriented translation of positions/mount/rules.py.
# Bands are Mount-relative visible hysteresis states, not fighter IDs.
enum Band { LOOSE, STABLE, STRONG, LOCKED }

const MIN_AXIS = 0.10
const MAX_AXIS = 4.00
const DEFAULT_AXIS = 1.50
const DEFAULT_CLOCK_SECONDS = 300
const DEFAULT_INTERVAL_SECONDS = 5


static func round_ten(value: float) -> float:
    return roundf(value * 10000000000.0) / 10000000000.0


static func clamp_axis(axis: float) -> float:
    return round_ten(clampf(axis, MIN_AXIS, MAX_AXIS))


static func initial_band(axis: float) -> int:
    assert(axis >= MIN_AXIS and axis <= MAX_AXIS, "Mount axis out of bounds")
    if axis < 1.0:
        return Band.LOOSE
    if axis < 2.0:
        return Band.STABLE
    if axis < 3.0:
        return Band.STRONG
    return Band.LOCKED


# Every threshold below deliberately matches Python's history-dependent rules.
# A result can contain two band changes if an exchange crosses multiple bands.
static func update_band(axis: float, current: int) -> Dictionary:
    var band: int = current
    var changes: Array[Dictionary] = []
    while true:
        var next_band: int = -1
        if band == Band.LOOSE and axis >= 1.20:
            next_band = Band.STABLE
        elif band == Band.STABLE and axis >= 2.20:
            next_band = Band.STRONG
        elif band == Band.STRONG and axis >= 3.20:
            next_band = Band.LOCKED
        elif band == Band.LOCKED and axis <= 2.80:
            next_band = Band.STRONG
        elif band == Band.STRONG and axis <= 1.80:
            next_band = Band.STABLE
        elif band == Band.STABLE and axis <= 0.80:
            next_band = Band.LOOSE
        if next_band == -1:
            break
        changes.append({"before": band, "after": next_band})
        band = next_band
    return {"band": band, "changes": changes}


static func axis_can_have_band(axis: float, band: int) -> bool:
    if axis < MIN_AXIS or axis > MAX_AXIS:
        return false
    match band:
        Band.LOOSE:
            return axis < 1.20
        Band.STABLE:
            return axis > 0.80 and axis < 2.20
        Band.STRONG:
            return axis > 1.80 and axis < 3.20
        Band.LOCKED:
            return axis > 2.80
    return false


static func drift_rate(top_behavior: String, bottom_behavior: String) -> float:
    var top: String = "HOLD" if top_behavior == "CONSERVE" else top_behavior
    var bottom: String = "PROTECT" if bottom_behavior == "CONSERVE" else bottom_behavior
    match top + "|" + bottom:
        "PRESSURE|ESCAPE":
            return 0.10
        "PRESSURE|PROTECT":
            return 0.15
        "HOLD|ESCAPE":
            return -0.10
        "HOLD|PROTECT":
            return 0.0
    assert(false, "Unknown Mount behavior combination")
    return 0.0


static func positional_modifier(initiator: String, band: int) -> int:
    if initiator == "bottom" and (band == Band.STRONG or band == Band.LOCKED):
        return -1
    if initiator == "top" and band == Band.LOOSE:
        return -1
    return 0
