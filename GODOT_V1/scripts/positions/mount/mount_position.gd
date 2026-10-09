class_name BjjMountPosition
extends RefCounted

# Persisted Mount position. Escape overshoot is NOT stored as active Mount axis.
# Follows src/bjj_game/positions/mount/{axis,position}.py.

var axis: float
var band: int
var broken: bool = false
var crossing_axis: float = 0.0


func _init(start_axis: float = BjjMountRules.DEFAULT_AXIS) -> void:
    axis = start_axis
    band = BjjMountRules.initial_band(start_axis)


func apply_control(value: float, new_band: int) -> void:
    assert(not broken, "Cannot apply Mount control after leaving Mount")
    assert(BjjMountRules.axis_can_have_band(value, new_band))
    axis = BjjMountRules.round_ten(value)
    band = new_band


func break_mount(terminal_crossing_axis: float) -> void:
    assert(not broken)
    broken = true
    crossing_axis = terminal_crossing_axis


func reported_axis() -> float:
    return crossing_axis if broken else axis
