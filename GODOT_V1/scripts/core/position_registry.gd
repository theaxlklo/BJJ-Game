class_name BjjPositionRegistry
extends RefCounted

# Canonical position-family identity (POSITION_TOPOLOGY.md section 18, P-1 to P-4).
#
# Identity only. This answers one question: "is this string a declared position
# family?" It deliberately holds no roles, authority, techniques, grades, exits,
# stamina, implementation status or UI names, and it does not decide whether a
# position can be started or entered. Declaring an id never implies that the
# position exists as an engine.
#
# The string is the persisted and replayed value; it is never renumbered. The
# list is append-only: an id is never reused or silently remapped, and changing
# it is a deliberate, owner-approved amendment (the exact list is pinned by
# test_position_registry.gd). Everything is pure and static: no state, no
# autoload, no scanning. Returned arrays are detached copies.
const BACK_CONTROL: String = "back_control"
const CLOSED_GUARD: String = "closed_guard"
const FRONT_HEADLOCK: String = "front_headlock"
const HALF_GUARD: String = "half_guard"
const LEG_ENTANGLEMENT: String = "leg_entanglement"
const MOUNT: String = "mount"
const OPEN_GUARD: String = "open_guard"
const SIDE_CONTROL: String = "side_control"
const STANDING: String = "standing"
const TURTLE: String = "turtle"

# Kept in sorted order so enumeration never depends on declaration history; a new
# id is inserted in sorted position (the string, not its position, is the persisted value).
const DECLARED: Array[String] = [
    BACK_CONTROL, CLOSED_GUARD, FRONT_HEADLOCK, HALF_GUARD, LEG_ENTANGLEMENT,
    MOUNT, OPEN_GUARD, SIDE_CONTROL, STANDING, TURTLE,
]

# Registry codes. Existing addressing codes (missing_position, unknown_position,
# unknown_source_position) keep their own meaning and are not used here.
const INVALID_POSITION_ID: String = "invalid_position_id"
const UNKNOWN_POSITION_ID: String = "unknown_position_id"


# "" when `position_id` is a declared family. Otherwise a stable code:
#   invalid_position_id - not a String, or not lowercase snake case
#                         (^[a-z][a-z0-9]*(_[a-z0-9]+)*$); casing and whitespace
#                         are never normalized;
#   unknown_position_id - well formed but not declared (for example "reversal",
#                         which is an unresolved outcome label, not a position).
static func error_for(position_id: Variant) -> String:
    if typeof(position_id) != TYPE_STRING:
        return INVALID_POSITION_ID
    var text: String = position_id
    if not _is_snake_case(text):
        return INVALID_POSITION_ID
    if not DECLARED.has(text):
        return UNKNOWN_POSITION_ID
    return ""


static func is_declared(position_id: Variant) -> bool:
    return error_for(position_id).is_empty()


# A new sorted copy on every call; mutating it never reaches the registry.
static func declared_ids() -> Array[String]:
    var ids: Array[String] = []
    ids.assign(DECLARED)
    return ids


# Hand-rolled instead of RegEx: PCRE "$" also matches before a trailing newline,
# and this keeps non-ASCII, whitespace and control characters unambiguously invalid.
static func _is_snake_case(text: String) -> bool:
    if text.is_empty():
        return false
    var previous_was_underscore: bool = true  # forbids a leading "_" and the "__" form
    for index: int in text.length():
        var code: int = text.unicode_at(index)
        var is_lower: bool = code >= 97 and code <= 122
        var is_digit: bool = code >= 48 and code <= 57
        if code == 95:
            if previous_was_underscore:
                return false
            previous_was_underscore = true
            continue
        if not (is_lower or is_digit):
            return false
        if index == 0 and is_digit:
            return false
        previous_was_underscore = false
    return not previous_was_underscore
