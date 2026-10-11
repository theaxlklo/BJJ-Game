class_name BjjMountCarryover
extends RefCounted

# Detached, validated carry-over record of a Mount segment (A3b). Specification:
# GODOT_V1/docs/CARRYOVER_EXPORT.md. This class owns the SCHEMA and its validation only. It reads
# no live Mount object: the gateway builds the segment from state it already owns, the graph builds
# the envelope from graph state, and both finish with the validators below. Nothing here consumes
# the record, creates a receiving position or decides any rule.
#
# Validation never calls BjjMountExchange.validate_context(): that rejects every terminal context
# (exit, timeout, tap), and carry-over is exported exactly then.
const SEGMENT_SCHEMA: String = "mount_carryover"
const ENVELOPE_SCHEMA: String = "position_graph_carryover"
const VERSION: int = 1
# Graph status names, repeated as literals so the Mount layer does not depend on the graph class;
# test_carryover_export.gd pins them to the graph's own constants.
const STATUS_ACTIVE: String = "active"
const STATUS_ENDED: String = "ended"
const STATUS_HALTED: String = "halted_at_unsupported_transition"
const STATUSES: Array[String] = [STATUS_ACTIVE, STATUS_ENDED, STATUS_HALTED]
const ROLES: Array[String] = ["top", "bottom"]

const E_SHAPE: String = "invalid_carryover_shape"
const E_SCHEMA: String = "unsupported_carryover_schema"
const E_IDS: String = "invalid_fighter_ids"
const E_STAMINA: String = "invalid_stamina"
const E_LATCH: String = "invalid_exhaustion_latch"
const E_CLOCK: String = "invalid_clock"
const E_WINDOW: String = "invalid_window"
const E_D3B: String = "invalid_d3b_state"
const E_TERMINAL: String = "invalid_terminal_state"
const E_EXIT: String = "invalid_exit"
const E_GRAPH: String = "invalid_graph_block"
const E_CONSISTENCY: String = "inconsistent_graph_segment"

class Export extends RefCounted:
    var error: String = "incomplete_export"
    var record: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()

static func failed(code: String) -> Export:
    var result := Export.new()
    result.error = code
    return result

static func succeeded(record: Dictionary) -> Export:
    var result := Export.new()
    result.error = ""
    result.record = record
    return result

# --- Shape helpers ---------------------------------------------------------------------

static func _keys_are(value: Variant, keys: Array[String]) -> bool:
    if not value is Dictionary:
        return false
    var dictionary: Dictionary = value
    if dictionary.size() != keys.size():
        return false
    for key: String in keys:
        if not dictionary.has(key):
            return false
    return true

static func _is_int(value: Variant) -> bool:
    return typeof(value) == TYPE_INT

static func _is_bool(value: Variant) -> bool:
    return typeof(value) == TYPE_BOOL

static func _is_string(value: Variant) -> bool:
    return typeof(value) == TYPE_STRING

static func _fighter_shape_ok(value: Variant) -> bool:
    return _keys_are(value, ["stamina_current", "stamina_maximum", "exhaustion_latched", "behavior_remainder_units"]) \
        and _is_int(value.stamina_current) and _is_int(value.stamina_maximum) \
        and _is_bool(value.exhaustion_latched) and _is_int(value.behavior_remainder_units)

static func _exit_shape_ok(value: Variant) -> bool:
    return _keys_are(value, ["kind", "raw_destination", "destination_position_id", "resolved"]) \
        and _is_string(value.kind) and _is_string(value.raw_destination) \
        and _is_string(value.destination_position_id) and _is_bool(value.resolved)

static func _shape_ok(record: Variant) -> bool:
    if not _keys_are(record, ["schema", "version", "source_position_id", "fighter_by_role", "fighters", "clock", "window", "d3b", "terminal", "exit"]):
        return false
    if not (_is_string(record.schema) and _is_int(record.version) and _is_string(record.source_position_id)):
        return false
    if not (_keys_are(record.fighter_by_role, ROLES) and _is_string(record.fighter_by_role.top) and _is_string(record.fighter_by_role.bottom)):
        return false
    if not (_keys_are(record.fighters, ROLES) and _fighter_shape_ok(record.fighters.top) and _fighter_shape_ok(record.fighters.bottom)):
        return false
    if not (_keys_are(record.clock, ["initial_seconds", "remaining_seconds"]) and _is_int(record.clock.initial_seconds) and _is_int(record.clock.remaining_seconds)):
        return false
    if not (_keys_are(record.window, ["last_issued_id"]) and _is_int(record.window.last_issued_id)):
        return false
    if not (_keys_are(record.d3b, ["armed", "token_consumed", "previous_exhausted"]) and _is_bool(record.d3b.armed) \
            and _is_bool(record.d3b.token_consumed) and _is_bool(record.d3b.previous_exhausted)):
        return false
    if not (_keys_are(record.terminal, ["ended", "submission_tapped"]) and _is_bool(record.terminal.ended) and _is_bool(record.terminal.submission_tapped)):
        return false
    return _exit_shape_ok(record.exit)

# --- Segment validation ----------------------------------------------------------------

# "" when valid, otherwise a stable error code. Never mutates `record`.
static func validate_segment(record: Variant) -> String:
    if not _shape_ok(record):
        return E_SHAPE
    var segment: Dictionary = record
    if segment.schema != SEGMENT_SCHEMA or segment.version != VERSION or segment.source_position_id != BjjMountContract.POSITION_ID:
        return E_SCHEMA
    if not BjjPositionContract.fighter_ids_error(segment.fighter_by_role.top, segment.fighter_by_role.bottom).is_empty():
        return E_IDS
    for role: String in ROLES:
        var fighter: Dictionary = segment.fighters[role]
        var maximum: int = fighter.stamina_maximum
        var current: int = fighter.stamina_current
        if maximum < 1 or maximum > BjjStaminaPool.MAXIMUM_EXACT or current < 0 or current > maximum:
            return E_STAMINA
        if absi(fighter.behavior_remainder_units) > BjjStaminaPool.MAXIMUM_EXACT:
            return E_STAMINA
    for role: String in ROLES:
        # Thresholds come from the pool itself so the arithmetic cannot drift.
        var fighter: Dictionary = segment.fighters[role]
        var pool := BjjStaminaPool.create(fighter.stamina_current, fighter.stamina_maximum).pool
        if fighter.stamina_current <= pool.exhaustion_enter_threshold and not fighter.exhaustion_latched:
            return E_LATCH
        if fighter.stamina_current >= pool.exhaustion_recover_threshold and fighter.exhaustion_latched:
            return E_LATCH
    var initial: int = segment.clock.initial_seconds
    var remaining: int = segment.clock.remaining_seconds
    if initial < 1 or initial > BjjStaminaPool.MAXIMUM_EXACT or remaining < 0 or remaining > initial:
        return E_CLOCK
    if segment.window.last_issued_id < 0:
        return E_WINDOW
    # The controller consumes its token only while armed, and never un-arms.
    # previous_exhausted is deliberately NOT tied to the current latch: stamina can change after
    # the last D3-B observation.
    if segment.d3b.token_consumed and not segment.d3b.armed:
        return E_D3B
    var exited: bool = segment.exit.kind == "exit"
    if segment.terminal.ended != (remaining == 0 or segment.terminal.submission_tapped or exited):
        return E_TERMINAL
    if exited and remaining < 1:
        return E_TERMINAL
    return _exit_error(segment.exit)

static func _exit_error(exit_block: Dictionary) -> String:
    if exit_block.kind == "none":
        if exit_block.raw_destination.is_empty() and exit_block.destination_position_id.is_empty() and not exit_block.resolved:
            return ""
        return E_EXIT
    if exit_block.kind != "exit":
        return E_EXIT
    var label: String = exit_block.raw_destination
    if not BjjMountContract.EXIT_DESTINATIONS.has(label) and not BjjMountContract.UNRESOLVED_EXITS.has(label):
        return E_EXIT
    # Mount stays authoritative: the declared mapping is never re-implemented here.
    var declared := BjjMountContract.transition_for(label).fields()
    for key: String in declared:
        if exit_block[key] != declared[key]:
            return E_EXIT
    return ""

# --- Envelope validation ---------------------------------------------------------------

static func _blocked_shape_ok(blocked: Variant) -> bool:
    if not blocked is Dictionary:
        return false
    if (blocked as Dictionary).is_empty():
        return true
    return _keys_are(blocked, ["from_position_id", "label", "reason", "destination_position_id"]) \
        and _is_string(blocked.from_position_id) and _is_string(blocked.label) \
        and _is_string(blocked.reason) and _is_string(blocked.destination_position_id)

static func validate_envelope(record: Variant) -> String:
    if not _keys_are(record, ["schema", "version", "segment", "graph"]):
        return E_SHAPE
    var envelope: Dictionary = record
    if not (_is_string(envelope.schema) and _is_int(envelope.version) and envelope.segment is Dictionary and envelope.graph is Dictionary):
        return E_SHAPE
    if envelope.schema != ENVELOPE_SCHEMA or envelope.version != VERSION:
        return E_SCHEMA
    var graph_block: Dictionary = envelope.graph
    if not _keys_are(graph_block, ["status", "event_count", "blocked_transition"]):
        return E_GRAPH
    if not (_is_string(graph_block.status) and STATUSES.has(graph_block.status) and _is_int(graph_block.event_count) \
            and graph_block.event_count >= 0 and _blocked_shape_ok(graph_block.blocked_transition)):
        return E_GRAPH
    var segment_error := validate_segment(envelope.segment)
    if not segment_error.is_empty():
        return segment_error
    var segment: Dictionary = envelope.segment
    var blocked: Dictionary = graph_block.blocked_transition
    var exited: bool = segment.exit.kind == "exit"
    var halted: bool = graph_block.status == STATUS_HALTED
    if halted != exited or halted != not blocked.is_empty():
        return E_CONSISTENCY
    if halted:
        if blocked.from_position_id != segment.source_position_id or blocked.label != segment.exit.raw_destination \
                or blocked.destination_position_id != segment.exit.destination_position_id:
            return E_CONSISTENCY
    elif (graph_block.status == STATUS_ENDED) != segment.terminal.ended:
        return E_CONSISTENCY
    return ""
