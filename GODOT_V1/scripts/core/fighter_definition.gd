class_name BjjFighterDefinition
extends Resource

# Reusable, Inspector-editable fighter CONTENT (F0). Not a match participant: it carries no
# stamina, exhaustion, behavior, role, position, initiative or window state, and no gameplay
# statistics. The match owner supplies the actual stable fighter ids, so one definition can
# back any number of participants without them sharing runtime state.
#
# Two fields only, each with a concrete consumer (tests now, the practice UI next):
#   definition_id - stable content/template id, never a match fighter id;
#   display_name  - human-readable label.
# Anything else (art, power, belt, techniques) needs its own authorized slice.
const MAX_LENGTH: int = 64
const INVALID_DEFINITION_ID: String = "invalid_definition_id"
const INVALID_DISPLAY_NAME: String = "invalid_display_name"

@export var definition_id: String = ""
@export var display_name: String = ""


# "" when valid, otherwise a stable code. A freshly created definition is invalid on purpose:
# content must be filled in before it can back a match participant.
func validation_error() -> String:
    if not _is_definition_id(definition_id):
        return INVALID_DEFINITION_ID
    if not _is_display_name(display_name):
        return INVALID_DISPLAY_NAME
    return ""


# Lowercase snake case: starts with a letter, then a-z, 0-9 and "_". Never normalized.
static func _is_definition_id(text: String) -> bool:
    if text.is_empty() or text.length() > MAX_LENGTH:
        return false
    for index: int in text.length():
        var code: int = text.unicode_at(index)
        var is_lower: bool = code >= 97 and code <= 122
        var is_digit: bool = code >= 48 and code <= 57
        if not (is_lower or (index > 0 and (is_digit or code == 95))):
            return false
    return true


# Non-empty, no leading/trailing whitespace, no control characters; other Unicode is allowed.
static func _is_display_name(text: String) -> bool:
    if text.is_empty() or text.length() > MAX_LENGTH or text != text.strip_edges():
        return false
    for index: int in text.length():
        var code: int = text.unicode_at(index)
        if code < 32 or (code >= 127 and code <= 159):
            return false
    return true
