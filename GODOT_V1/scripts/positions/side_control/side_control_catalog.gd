class_name BjjSideControlCatalog
extends RefCounted

# Side Control v0 catalog (SIDE_CONTROL_V0_RULES.md section 3): stable ids, the two 3x3 raw-grade matrices, the readiness tracks and the
# four exits. Provisional prototype constants, not balance. The ids side_control.top.kimura_route / .armbar_route are RESERVED and are
# deliberately absent: they are `unknown_action`.
const TOP_STABILIZE: String = "side_control.top.stabilize"
const TOP_ADVANCE_TO_MOUNT: String = "side_control.top.advance_to_mount"
const TOP_EXPOSE_BACK: String = "side_control.top.expose_back"
const BOTTOM_SHRIMP: String = "side_control.bottom.shrimp"
const BOTTOM_RECOVER_HALF_GUARD: String = "side_control.bottom.recover_half_guard"
const BOTTOM_TURN_TO_KNEES: String = "side_control.bottom.turn_to_knees"
const BOTTOM_FOREARM_FRAME: String = "side_control.bottom_response.forearm_frame"
const BOTTOM_HIP_ESCAPE: String = "side_control.bottom_response.hip_escape"
const BOTTOM_BRIDGE_DEFENSE: String = "side_control.bottom_response.bridge_defense"
const TOP_SHOULDER_PRESSURE: String = "side_control.top_response.shoulder_pressure"
const TOP_HIP_BLOCK: String = "side_control.top_response.hip_block"
const TOP_FOLLOW_THE_HIPS: String = "side_control.top_response.follow_the_hips"

const TOP_PIN: String = "top_pin"
const BOTTOM_SPACE: String = "bottom_space"

# id -> {side, kind, name, break_capable, track, exit}. `side` is the side that OWNS the entity (a response belongs to the responder's
# side). `track` is the readiness track a break-capable ACTION spends/reads, or the track a governed RESPONSE reads ("" = none).
# `exit` is the exit label of a break-capable action (its destination id is EXIT_DESTINATIONS[label]).
const ENTITIES: Dictionary = {
    TOP_STABILIZE: {"side": "top", "kind": "action", "name": "Stabilize", "break_capable": false, "track": "", "exit": ""},
    TOP_ADVANCE_TO_MOUNT: {"side": "top", "kind": "action", "name": "Advance to Mount", "break_capable": true, "track": TOP_PIN, "exit": "Mount"},
    TOP_EXPOSE_BACK: {"side": "top", "kind": "action", "name": "Expose Back", "break_capable": true, "track": TOP_PIN, "exit": "Back Control"},
    BOTTOM_SHRIMP: {"side": "bottom", "kind": "action", "name": "Shrimp", "break_capable": false, "track": "", "exit": ""},
    BOTTOM_RECOVER_HALF_GUARD: {"side": "bottom", "kind": "action", "name": "Recover Half Guard", "break_capable": true, "track": BOTTOM_SPACE, "exit": "Half Guard"},
    BOTTOM_TURN_TO_KNEES: {"side": "bottom", "kind": "action", "name": "Turn to Knees", "break_capable": true, "track": BOTTOM_SPACE, "exit": "Turtle"},
    BOTTOM_FOREARM_FRAME: {"side": "bottom", "kind": "response", "name": "Forearm Frame", "break_capable": false, "track": "", "exit": ""},
    BOTTOM_HIP_ESCAPE: {"side": "bottom", "kind": "response", "name": "Hip Escape", "break_capable": false, "track": BOTTOM_SPACE, "exit": ""},
    BOTTOM_BRIDGE_DEFENSE: {"side": "bottom", "kind": "response", "name": "Bridge Defense", "break_capable": false, "track": "", "exit": ""},
    TOP_SHOULDER_PRESSURE: {"side": "top", "kind": "response", "name": "Shoulder Pressure", "break_capable": false, "track": "", "exit": ""},
    TOP_HIP_BLOCK: {"side": "top", "kind": "response", "name": "Hip Block", "break_capable": false, "track": TOP_PIN, "exit": ""},
    TOP_FOLLOW_THE_HIPS: {"side": "top", "kind": "response", "name": "Follow the Hips", "break_capable": false, "track": "", "exit": ""},
}

# Raw grades from the INITIATOR's point of view (section 3.3): action -> response -> grade. All 18 cells exist.
const RAW: Dictionary = {
    TOP_STABILIZE: {BOTTOM_FOREARM_FRAME: -1, BOTTOM_HIP_ESCAPE: 1, BOTTOM_BRIDGE_DEFENSE: 0},
    TOP_ADVANCE_TO_MOUNT: {BOTTOM_FOREARM_FRAME: 1, BOTTOM_HIP_ESCAPE: -2, BOTTOM_BRIDGE_DEFENSE: 1},
    TOP_EXPOSE_BACK: {BOTTOM_FOREARM_FRAME: 1, BOTTOM_HIP_ESCAPE: 0, BOTTOM_BRIDGE_DEFENSE: -2},
    BOTTOM_SHRIMP: {TOP_SHOULDER_PRESSURE: -1, TOP_HIP_BLOCK: 1, TOP_FOLLOW_THE_HIPS: 0},
    BOTTOM_RECOVER_HALF_GUARD: {TOP_SHOULDER_PRESSURE: 2, TOP_HIP_BLOCK: -1, TOP_FOLLOW_THE_HIPS: 1},
    BOTTOM_TURN_TO_KNEES: {TOP_SHOULDER_PRESSURE: 0, TOP_HIP_BLOCK: 2, TOP_FOLLOW_THE_HIPS: -2},
}

# Exit label -> declared destination id. All four are declared but UNSUPPORTED in v0: no receiver exists (section 10).
const EXIT_DESTINATIONS: Dictionary = {"Mount": "mount", "Back Control": "back_control", "Half Guard": "half_guard", "Turtle": "turtle"}

static func is_action(id: String) -> bool:
    return ENTITIES.has(id) and str(ENTITIES[id].kind) == "action"

static func is_response(id: String) -> bool:
    return ENTITIES.has(id) and str(ENTITIES[id].kind) == "response"

static func is_break_capable(action_id: String) -> bool:
    return ENTITIES.has(action_id) and bool(ENTITIES[action_id].break_capable)

# {kind, raw_destination, destination_position_id, resolved}: `resolved` means "a declared position id", never "a receiver exists".
static func transition_fields(label: String) -> Dictionary:
    if label.is_empty():
        return {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}
    return {"kind": "exit", "raw_destination": label,
        "destination_position_id": str(EXIT_DESTINATIONS.get(label, "")), "resolved": EXIT_DESTINATIONS.has(label)}
