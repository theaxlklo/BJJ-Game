class_name BjjHalfGuardCatalog
extends RefCounted

# Half Guard v0 catalog: stable ids, the 15 raw grades (C1) and the small rule tables that are keyed by technique
# (HALF_GUARD_V0_RULES.md section 3 and 5). Names are the Guide section 11.4 technique names; response names are new content.
const TOP_CROSSFACE: String = "half_guard.top.crossface"
const TOP_FLATTEN: String = "half_guard.top.flatten"
const TOP_KNEE_SLICE: String = "half_guard.top.knee_slice"
const BOTTOM_UNDERHOOK: String = "half_guard.bottom.underhook"
const BOTTOM_RECOVER_GUARD: String = "half_guard.bottom.recover_guard"
const BOTTOM_HIP_FRAME: String = "half_guard.bottom_response.hip_frame"
const BOTTOM_UNDERHOOK_FIGHT: String = "half_guard.bottom_response.underhook_fight"
const BOTTOM_KNEE_SHIELD: String = "half_guard.bottom_response.knee_shield"
const TOP_HEAD_CONTROL: String = "half_guard.top_response.head_control"
const TOP_HIP_PRESSURE: String = "half_guard.top_response.hip_pressure"
const TOP_KNEE_PIN: String = "half_guard.top_response.knee_pin"

const TOP_BASE: String = "top_base"
const BOTTOM_FRAME: String = "bottom_frame"

# id -> {side, kind, name, break_capable}. `side` is the side that OWNS the entity (a response belongs to the responder's side).
const ENTITIES: Dictionary = {
    TOP_CROSSFACE: {"side": "top", "kind": "action", "name": "Crossface", "break_capable": false},
    TOP_FLATTEN: {"side": "top", "kind": "action", "name": "Flatten", "break_capable": false},
    TOP_KNEE_SLICE: {"side": "top", "kind": "action", "name": "Knee Slice", "break_capable": true},
    BOTTOM_UNDERHOOK: {"side": "bottom", "kind": "action", "name": "Underhook", "break_capable": false},
    BOTTOM_RECOVER_GUARD: {"side": "bottom", "kind": "action", "name": "Recover Guard", "break_capable": true},
    BOTTOM_HIP_FRAME: {"side": "bottom", "kind": "response", "name": "Hip Frame", "break_capable": false},
    BOTTOM_UNDERHOOK_FIGHT: {"side": "bottom", "kind": "response", "name": "Underhook Fight", "break_capable": false},
    BOTTOM_KNEE_SHIELD: {"side": "bottom", "kind": "response", "name": "Knee Shield", "break_capable": false},
    TOP_HEAD_CONTROL: {"side": "top", "kind": "response", "name": "Head Control", "break_capable": false},
    TOP_HIP_PRESSURE: {"side": "top", "kind": "response", "name": "Hip Pressure", "break_capable": false},
    TOP_KNEE_PIN: {"side": "top", "kind": "response", "name": "Knee Pin", "break_capable": false},
}

const TOP_ACTIONS: Array[String] = [TOP_CROSSFACE, TOP_FLATTEN, TOP_KNEE_SLICE]
const BOTTOM_ACTIONS: Array[String] = [BOTTOM_UNDERHOOK, BOTTOM_RECOVER_GUARD]
const TOP_RESPONSES: Array[String] = [TOP_HEAD_CONTROL, TOP_HIP_PRESSURE, TOP_KNEE_PIN]
const BOTTOM_RESPONSES: Array[String] = [BOTTOM_HIP_FRAME, BOTTOM_UNDERHOOK_FIGHT, BOTTOM_KNEE_SHIELD]

# C1 raw grades from the initiator's point of view: initiator side -> action -> response -> grade.
const RAW: Dictionary = {
    "top": {
        TOP_CROSSFACE: {BOTTOM_HIP_FRAME: 1, BOTTOM_UNDERHOOK_FIGHT: -1, BOTTOM_KNEE_SHIELD: 0},
        TOP_FLATTEN: {BOTTOM_HIP_FRAME: -1, BOTTOM_UNDERHOOK_FIGHT: 1, BOTTOM_KNEE_SHIELD: 1},
        TOP_KNEE_SLICE: {BOTTOM_HIP_FRAME: 1, BOTTOM_UNDERHOOK_FIGHT: 2, BOTTOM_KNEE_SHIELD: -2},
    },
    "bottom": {
        BOTTOM_UNDERHOOK: {TOP_HEAD_CONTROL: -1, TOP_HIP_PRESSURE: 0, TOP_KNEE_PIN: 1},
        BOTTOM_RECOVER_GUARD: {TOP_HEAD_CONTROL: 2, TOP_HIP_PRESSURE: 1, TOP_KNEE_PIN: -2},
    },
}

# Option M (N-2): only these responses are readiness-governed; value = the responder's track they read.
const GOVERNED: Dictionary = {BOTTOM_KNEE_SHIELD: BOTTOM_FRAME, TOP_KNEE_PIN: TOP_BASE}
# N-5: on final >= Success, action -> [track changed, delta]. Knee Slice builds nothing.
const BUILD: Dictionary = {
    TOP_CROSSFACE: [BOTTOM_FRAME, -1], TOP_FLATTEN: [TOP_BASE, 1],
    BOTTOM_UNDERHOOK: [BOTTOM_FRAME, 1], BOTTOM_RECOVER_GUARD: [TOP_BASE, -1],
}
# Exit label -> declared destination id. These nodes are declared but not implemented.
const EXIT_DESTINATIONS: Dictionary = {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"}

# B1h (HALF_GUARD_V0_RULES.md section 13.1): the only feint pairs, listed and never derived. apparent -> {id, real, track, minimum_tier, bite}.
# `bite` is the best counter to the APPARENT technique; `minimum_tier` is the public condition on the acting side's own track.
const FEINT_PAIRS: Dictionary = {
    TOP_CROSSFACE: {"id": "FP-1", "real": TOP_KNEE_SLICE, "track": TOP_BASE, "minimum_tier": 1, "bite": BOTTOM_UNDERHOOK_FIGHT},
    BOTTOM_UNDERHOOK: {"id": "FP-2", "real": BOTTOM_RECOVER_GUARD, "track": BOTTOM_FRAME, "minimum_tier": 1, "bite": TOP_HEAD_CONTROL},
}
# Section 13.8: the published ordinary-decision fallback, by the DEFENDER's role. The session layer supplies it; the engine never reads a clock.
const TIMEOUT_FALLBACK: Dictionary = {
    "bottom": {"response_id": BOTTOM_HIP_FRAME, "commitment": BjjCommitment.LOW},
    "top": {"response_id": TOP_HIP_PRESSURE, "commitment": BjjCommitment.LOW},
}

# The real techniques `apparent_id` may conceal in a PUBLIC state (the pair table crossed with the acting side's own track tier). A pure
# function of its three arguments: it ignores stamina, funding and anything an attacker sealed.
static func eligible_real_ids(apparent_id: String, top_base: int, bottom_frame: int) -> Array[String]:
    var eligible: Array[String] = []
    if FEINT_PAIRS.has(apparent_id):
        var pair: Dictionary = FEINT_PAIRS[apparent_id]
        var tier := top_base if str(pair.track) == TOP_BASE else bottom_frame
        if tier >= int(pair.minimum_tier):
            eligible.append(str(pair.real))
    return eligible

static func timeout_fallback(defender_role: String) -> Dictionary:
    return TIMEOUT_FALLBACK[defender_role].duplicate() if TIMEOUT_FALLBACK.has(defender_role) else {}

static func actions_of(side: String) -> Array[String]:
    return TOP_ACTIONS if side == "top" else BOTTOM_ACTIONS if side == "bottom" else []

# Responses OWNED by `side` (a Bottom action is answered with TOP responses, so the responder side owns them).
static func responses_of(side: String) -> Array[String]:
    return TOP_RESPONSES if side == "top" else BOTTOM_RESPONSES if side == "bottom" else []

static func is_break_capable(action_id: String) -> bool:
    return ENTITIES.has(action_id) and bool(ENTITIES[action_id].break_capable)

static func own_track(side: String) -> String:
    return TOP_BASE if side == "top" else BOTTOM_FRAME

static func short_name(entity_id: String) -> String:
    return entity_id.rsplit(".", false, 1)[1] if entity_id.contains(".") else entity_id

static func technique_name(action_id: String) -> String:
    return str(ENTITIES[action_id].name) if ENTITIES.has(action_id) else ""

# {kind, raw_destination, destination_position_id, resolved}: BjjPositionContract.Transition.fields() semantics.
static func transition_fields(label: String) -> Dictionary:
    if label.is_empty():
        return {"kind": "none", "raw_destination": "", "destination_position_id": "", "resolved": false}
    return {"kind": "exit", "raw_destination": label,
        "destination_position_id": str(EXIT_DESTINATIONS.get(label, "")), "resolved": EXIT_DESTINATIONS.has(label)}
