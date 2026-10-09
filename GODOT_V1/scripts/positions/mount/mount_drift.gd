class_name BjjMountDrift
extends RefCounted

# Exact one-simulated-second drift ticks from Python's MountResolutionEngine.
# Real-world decision countdown never affects this simulated clock.

static func simulate(
    axis: float,
    band: int,
    clock_seconds: int,
    duration_seconds: int,
    top_behavior: String,
    bottom_behavior: String
) -> Dictionary:
    assert(clock_seconds >= 0, "Clock must be nonnegative")
    assert(duration_seconds >= 0, "Duration must be nonnegative")
    assert(BjjMountRules.axis_can_have_band(axis, band), "Invalid Mount axis/band pair")
    var actual: int = mini(clock_seconds, duration_seconds)
    var start_axis: float = axis
    var start_band: int = band
    var changes: Array[Dictionary] = []
    var rate: float = BjjMountRules.drift_rate(top_behavior, bottom_behavior)

    for elapsed in range(1, actual + 1):
        axis = BjjMountRules.clamp_axis(axis + rate)
        var update: Dictionary = BjjMountRules.update_band(axis, band)
        for change in update["changes"]:
            changes.append({
                "before": int(change["before"]),
                "after": int(change["after"]),
                "clock_seconds": clock_seconds - elapsed
            })
        band = int(update["band"])

    return {
        "start_axis": start_axis,
        "end_axis": axis,
        "total_drift": BjjMountRules.round_ten(axis - start_axis),
        "start_clock": clock_seconds,
        "end_clock": clock_seconds - actual,
        "start_band": start_band,
        "end_band": band,
        "band_changes": changes
    }
