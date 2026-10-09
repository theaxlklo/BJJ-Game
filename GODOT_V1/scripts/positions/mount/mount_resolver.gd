class_name BjjMountResolver
extends RefCounted

# Frozen Mount-v0 action/response resolution.
# Returns result data; does NOT own the five-minute match, scoring,
# commitment, stamina, submission system or Godot visual objects.
# Port of src/bjj_game/engine/mount_engine.py::resolve_action.

static func resolve_action(
    axis: float,
    band: int,
    initiator: String,
    action_id: String,
    response_id: String,
    top_behavior: String = "PRESSURE",
    bottom_behavior: String = "ESCAPE",
    external_grade_modifier: int = 0,
    post_positional_grade_override: int = 99
) -> Dictionary:
    assert(initiator == "top" or initiator == "bottom")
    assert(BjjMountRules.axis_can_have_band(axis, band), "Invalid Mount axis/band pair")
    var action: Dictionary = BjjMountCatalog.get_entity(action_id)
    var response: Dictionary = BjjMountCatalog.get_entity(response_id)
    var opposing_side: String = "bottom" if initiator == "top" else "top"
    assert(action.get("kind") == "action", "Not an initiating action")
    assert(response.get("kind") == "response", "Not a response")
    assert(action.get("side") == initiator, "Action belongs to another side")
    assert(response.get("side") == opposing_side, "Response belongs to another side")

    var raw: int = BjjMountCatalog.raw_grade(action_id, response_id)
    var opposing_behavior: String = bottom_behavior if initiator == "top" else top_behavior
    var behavior_modifier: int = BjjMountCatalog.behavior_modifier(action_id, opposing_behavior)
    var behavior_grade: int = BjjGrade.shift(raw, behavior_modifier)
    var positional_modifier: int = BjjMountRules.positional_modifier(initiator, band)
    var positional_grade: int = BjjGrade.shift(behavior_grade, positional_modifier)
    var pre_external: int = positional_grade
    if post_positional_grade_override != 99:
        pre_external = post_positional_grade_override
    var final_grade: int = BjjGrade.shift(pre_external, external_grade_modifier)

    var axis_delta: float = float(final_grade if initiator == "top" else -final_grade)
    var proposed_axis: float = BjjMountRules.round_ten(axis + axis_delta)
    var floor_clamp_used: bool = false
    var failure_clamp_used: bool = false
    var escape_threshold_reached: bool = false
    var destination: String = ""
    var axis_after: float = proposed_axis

    # Branch order is important for exact parity. Only a successful,
    # escape-capable action may persist a terminal axis below the Mount floor.
    if bool(action.get("clamp_at_mount_floor", false)) and proposed_axis <= BjjMountRules.MIN_AXIS:
        floor_clamp_used = true
        axis_after = BjjMountRules.MIN_AXIS
    elif BjjGrade.failed(final_grade) and proposed_axis <= BjjMountRules.MIN_AXIS:
        failure_clamp_used = true
        axis_after = BjjMountRules.MIN_AXIS
    else:
        escape_threshold_reached = (
            bool(action.get("escape_capable", false))
            and BjjGrade.successful(final_grade)
            and proposed_axis <= BjjMountRules.MIN_AXIS
        )
        if escape_threshold_reached:
            destination = BjjMountCatalog.exit_destination(action_id, final_grade, band)
            assert(destination != "", "Missing exit-map destination for escape")
        else:
            axis_after = BjjMountRules.clamp_axis(proposed_axis)

    var band_after: int = band
    var changes: Array[Dictionary] = []
    if destination == "":
        var updated: Dictionary = BjjMountRules.update_band(axis_after, band)
        band_after = int(updated["band"])
        changes = updated["changes"] as Array[Dictionary]

    return {
        "initiator": initiator,
        "action_id": action_id,
        "response_id": response_id,
        "raw_grade": raw,
        "behavior_grade": behavior_grade,
        "final_grade": final_grade,
        "behavior_modifier": behavior_modifier,
        "positional_modifier": positional_modifier,
        "external_grade_modifier": external_grade_modifier,
        "grade_value": final_grade,
        "axis_before": axis,
        "axis_delta": axis_delta,
        "proposed_axis": proposed_axis,
        "axis_after": axis_after,
        "band_before": band,
        "band_after": band_after,
        "band_changes": changes,
        "floor_clamp_used": floor_clamp_used,
        "failure_clamp_used": failure_clamp_used,
        "escape_threshold_reached": escape_threshold_reached,
        "exit_capable_action": bool(action.get("escape_capable", false)),
        "exit_destination": destination
    }
