class_name BjjMountCatalog
extends RefCounted

# Frozen Mount-v0: twelve actions/responses and exactly eighteen matchups.
# Mirrors src/bjj_game/positions/mount/catalog.py and matchups.py.
# Modern Americana finish is deliberately NOT part of this v0 catalog.

const TOP_HIGH_MOUNT_CLIMB = "mount.top.high_mount_climb"
const TOP_CROSSFACE_PRESSURE = "mount.top.crossface_pressure"
const TOP_AMERICANA_ARM_ISOLATION = "mount.top.americana_arm_isolation"
const BOTTOM_BRIDGE = "mount.bottom.bridge"
const BOTTOM_ELBOW_KNEE_ESCAPE = "mount.bottom.elbow_knee_escape"
const BOTTOM_TRAP_AND_ROLL_ESCAPE = "mount.bottom.trap_and_roll_escape"

const TOP_RESPONSE_POST_AND_BASE = "mount.top_response.post_and_base"
const TOP_RESPONSE_WIDE_MOUNT_BASE = "mount.top_response.wide_mount_base"
const TOP_RESPONSE_HIP_FOLLOW_REPUMMEL = "mount.top_response.hip_follow_repummel"
const BOTTOM_RESPONSE_FOREARM_FRAME = "mount.bottom_response.forearm_frame"
const BOTTOM_RESPONSE_TURN_IN_RECOVERY = "mount.bottom_response.turn_in_recovery"
const BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE = "mount.bottom_response.tight_elbow_arm_defense"

const ENTITIES = {
    TOP_HIGH_MOUNT_CLIMB: {"side": "top", "kind": "action", "name": "High Mount Climb"},
    TOP_CROSSFACE_PRESSURE: {"side": "top", "kind": "action", "name": "Crossface Pressure"},
    TOP_AMERICANA_ARM_ISOLATION: {
        "side": "top", "kind": "action", "name": "Americana Arm Isolation",
        "behavior_modifiers": {"PROTECT": -1}
    },
    BOTTOM_BRIDGE: {
        "side": "bottom", "kind": "action", "name": "Bridge",
        "behavior_modifiers": {"HOLD": -1}, "clamp_at_mount_floor": true
    },
    BOTTOM_ELBOW_KNEE_ESCAPE: {
        "side": "bottom", "kind": "action", "name": "Elbow-Knee Escape",
        "escape_capable": true
    },
    BOTTOM_TRAP_AND_ROLL_ESCAPE: {
        "side": "bottom", "kind": "action", "name": "Trap-and-Roll Escape",
        "behavior_modifiers": {"HOLD": -1}, "escape_capable": true
    },
    TOP_RESPONSE_POST_AND_BASE: {
        "side": "top", "kind": "response", "name": "Hand Post and Base"
    },
    TOP_RESPONSE_WIDE_MOUNT_BASE: {
        "side": "top", "kind": "response", "name": "Wide Mount Base"
    },
    TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: {
        "side": "top", "kind": "response", "name": "Hip Follow and Knee Re-Pummel"
    },
    BOTTOM_RESPONSE_FOREARM_FRAME: {
        "side": "bottom", "kind": "response", "name": "Forearm Frame"
    },
    BOTTOM_RESPONSE_TURN_IN_RECOVERY: {
        "side": "bottom", "kind": "response", "name": "Turn-In Recovery"
    },
    BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE: {
        "side": "bottom", "kind": "response", "name": "Tight-Elbow Arm Defense"
    }
}

# These are int grades, not probabilistic weights.
const RAW_GRADES = {
    TOP_HIGH_MOUNT_CLIMB + "|" + BOTTOM_RESPONSE_FOREARM_FRAME: 1,
    TOP_HIGH_MOUNT_CLIMB + "|" + BOTTOM_RESPONSE_TURN_IN_RECOVERY: 0,
    TOP_HIGH_MOUNT_CLIMB + "|" + BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE: -1,
    TOP_CROSSFACE_PRESSURE + "|" + BOTTOM_RESPONSE_FOREARM_FRAME: -1,
    TOP_CROSSFACE_PRESSURE + "|" + BOTTOM_RESPONSE_TURN_IN_RECOVERY: 1,
    TOP_CROSSFACE_PRESSURE + "|" + BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE: 2,
    TOP_AMERICANA_ARM_ISOLATION + "|" + BOTTOM_RESPONSE_FOREARM_FRAME: 2,
    TOP_AMERICANA_ARM_ISOLATION + "|" + BOTTOM_RESPONSE_TURN_IN_RECOVERY: 0,
    TOP_AMERICANA_ARM_ISOLATION + "|" + BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE: -2,
    BOTTOM_BRIDGE + "|" + TOP_RESPONSE_POST_AND_BASE: -2,
    BOTTOM_BRIDGE + "|" + TOP_RESPONSE_WIDE_MOUNT_BASE: -1,
    BOTTOM_BRIDGE + "|" + TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: 1,
    BOTTOM_ELBOW_KNEE_ESCAPE + "|" + TOP_RESPONSE_POST_AND_BASE: 2,
    BOTTOM_ELBOW_KNEE_ESCAPE + "|" + TOP_RESPONSE_WIDE_MOUNT_BASE: 1,
    BOTTOM_ELBOW_KNEE_ESCAPE + "|" + TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: -2,
    BOTTOM_TRAP_AND_ROLL_ESCAPE + "|" + TOP_RESPONSE_POST_AND_BASE: -2,
    BOTTOM_TRAP_AND_ROLL_ESCAPE + "|" + TOP_RESPONSE_WIDE_MOUNT_BASE: -1,
    BOTTOM_TRAP_AND_ROLL_ESCAPE + "|" + TOP_RESPONSE_HIP_FOLLOW_REPUMMEL: 2
}


static func get_entity(id: String) -> Dictionary:
    assert(ENTITIES.has(id), "Unknown Mount entity: " + id)
    return ENTITIES.get(id, {}) as Dictionary


static func raw_grade(action_id: String, response_id: String) -> int:
    var key: String = action_id + "|" + response_id
    assert(RAW_GRADES.has(key), "Unknown frozen Mount matchup: " + key)
    return int(RAW_GRADES.get(key, 0))


static func behavior_modifier(action_id: String, opposing_behavior: String) -> int:
    var action: Dictionary = get_entity(action_id)
    var modifiers: Dictionary = action.get("behavior_modifiers", {}) as Dictionary
    return int(modifiers.get(opposing_behavior, 0))


static func exit_destination(action_id: String, final_grade: int, band_before: int) -> String:
    # Mirrors Python: band override wins over grade default.
    if action_id == BOTTOM_ELBOW_KNEE_ESCAPE:
        if final_grade == BjjGrade.SUCCESS:
            return "Half Guard"
        if final_grade == BjjGrade.STRONG_SUCCESS:
            if band_before == BjjMountRules.Band.STABLE:
                return "Half Guard"
            return "Open Guard"
    if action_id == BOTTOM_TRAP_AND_ROLL_ESCAPE and final_grade >= BjjGrade.SUCCESS:
        return "Reversal"
    return ""
