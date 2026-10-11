class_name BjjPositionGraphMatch
extends RefCounted

# Slice A position-graph coordinator: a thin wrapper around exactly one BjjMatchWindowGateway.
#
# Mount is the only implemented position. The wrapper owns NO gameplay state: stamina, meters,
# clock, D3-B, fighter identity, histories and window identity stay with the gateway (and the
# BjjMountMatch it owns); every view here is a detached read through it. The graph owns only
# its status, its global event log and the recorded blocked transition.
#
# An accepted exchange that exits Mount stays accepted and settled. Because no destination
# position exists yet (Half Guard / Open Guard unimplemented, Reversal unresolved), the graph
# records one `transition_blocked` event and halts. A halt is not a match outcome: no winner,
# score or terminal result is produced, and later commands are rejected before reaching the
# gateway. Timeout and tap are reported as `terminal_outcome`, never as positional exits.
const POSITION_ID: String = BjjMountContract.POSITION_ID
const STATUS_ACTIVE: String = "active"
const STATUS_ENDED: String = "ended"
const STATUS_HALTED: String = "halted_at_unsupported_transition"
const ERROR_HALTED: String = "halted_unsupported_transition"
const REASON_UNKNOWN_SOURCE: String = "unknown_source_position"
const REASON_MALFORMED_DECLARATION: String = "malformed_declaration"

var _gateway: BjjMatchWindowGateway
var _status: String = STATUS_ACTIVE
var _events: Array[Dictionary] = []
var _blocked: Dictionary = {}
var _terminal_reason: String = ""

class Creation extends RefCounted:
    var error: String = ""
    var graph: BjjPositionGraphMatch
    func ok() -> bool:
        return error.is_empty() and graph != null

static func create(configuration: Dictionary, top_fighter_id: String, bottom_fighter_id: String) -> Creation:
    var result := Creation.new()
    var created := BjjMatchWindowGateway.create(configuration, top_fighter_id, bottom_fighter_id)
    if not created.ok():
        result.error = created.error
        return result
    var graph := BjjPositionGraphMatch.new()
    graph._gateway = created.gateway
    result.graph = graph
    return result

# --- Pure classification ----------------------------------------------------------------

# Maps one raw Mount exit label to a graph decision (the Slice A public entry point). Equivalent to
# classify_exit_from(POSITION_ID, raw_label).
static func classify_exit(raw_label: String) -> Dictionary:
    return classify_exit_from(POSITION_ID, raw_label)

# Position-aware, pure and read-only classification. Fail closed: only the active source
# position's own declared exits are understood, and an arbitrary label is never treated as a
# destination. Mount is read from BjjMountContract (its mapping is not copied here).
# `declarations` is an optional {source_position_id: {"exits": {label: destination_id},
# "unresolved": [label, ...]}} used by tests for synthetic positions; production passes none, so
# no other position is registered. It may never redefine Mount. A result is either
# {"kind": "none"} or {"kind": "blocked", reason, destination_position_id}; no result is a
# transition, because no destination commit exists yet.
static func classify_exit_from(source_position_id: String, raw_label: String, declarations: Dictionary = {}) -> Dictionary:
    if declarations.has(POSITION_ID):
        return _blocked_decision(REASON_MALFORMED_DECLARATION)
    if source_position_id == POSITION_ID:
        return _classify_mount_exit(raw_label)
    if source_position_id.is_empty() or not declarations.has(source_position_id):
        return _blocked_decision(REASON_UNKNOWN_SOURCE)
    var declaration: Variant = declarations[source_position_id]
    if not _declaration_is_valid(source_position_id, declaration):
        return _blocked_decision(REASON_MALFORMED_DECLARATION)
    if raw_label.is_empty():
        return {"kind": "none"}
    if (declaration.unresolved as Array).has(raw_label):
        return _blocked_decision("unresolved_destination")
    if (declaration.exits as Dictionary).has(raw_label):
        return _blocked_decision("destination_not_implemented", str(declaration.exits[raw_label]))
    return _blocked_decision("undeclared_exit_label")

static func _classify_mount_exit(raw_label: String) -> Dictionary:
    if raw_label.is_empty():
        return {"kind": "none"}
    var transition := BjjMountContract.transition_for(raw_label)
    if BjjMountContract.UNRESOLVED_EXITS.has(raw_label):
        return _blocked_decision("unresolved_destination")
    if transition.resolved:
        # Declared by Mount, but no receiving position is implemented yet.
        return _blocked_decision("destination_not_implemented", transition.destination_position_id)
    return _blocked_decision("undeclared_exit_label")

static func _blocked_decision(reason: String, destination_position_id: String = "") -> Dictionary:
    return {"kind": "blocked", "reason": reason, "destination_position_id": destination_position_id}

static func _declaration_is_valid(source_position_id: String, declaration: Variant) -> bool:
    if not declaration is Dictionary:
        return false
    var shape: Dictionary = declaration
    if shape.size() != 2 or not shape.has("exits") or not shape.has("unresolved"):
        return false
    if not shape.exits is Dictionary or not shape.unresolved is Array:
        return false
    for label: Variant in shape.exits:
        var destination: Variant = shape.exits[label]
        if not label is String or (label as String).is_empty():
            return false
        if not destination is String or (destination as String).is_empty() or destination == source_position_id:
            return false
    var seen: Dictionary = {}
    for label: Variant in shape.unresolved:
        if not label is String or (label as String).is_empty() or seen.has(label) or shape.exits.has(label):
            return false
        seen[label] = true
    return true

# "timeout", "tap", or "" when the state is not a normal terminal outcome.
static func terminal_reason(state: Dictionary) -> String:
    if bool(state.get("submission_tapped", false)):
        return "tap"
    if int(state.get("clock_seconds", 1)) <= 0:
        return "timeout"
    return ""

# --- Detached views -----------------------------------------------------------------------

func status() -> String:
    return _status

func events() -> Array[Dictionary]:
    var copy: Array[Dictionary] = []
    for event: Dictionary in _events:
        copy.append(event.duplicate(true))
    return copy

func blocked_transition() -> Dictionary:
    return _blocked.duplicate(true)

# Match-level carry-over envelope (A3b): the gateway's segment record beside the graph's own
# status, global event count and recorded blocked transition. Read-only; a halt stays a halt.
func carryover_export() -> BjjMountCarryover.Export:
    var segment := _gateway.carryover_segment()
    if not segment.ok():
        return segment
    var envelope := {"schema": BjjMountCarryover.ENVELOPE_SCHEMA, "version": BjjMountCarryover.VERSION,
        "segment": segment.record,
        "graph": {"status": _status, "event_count": _events.size(), "blocked_transition": _blocked.duplicate(true)}}
    var error := BjjMountCarryover.validate_envelope(envelope)
    if not error.is_empty():
        return BjjMountCarryover.failed(error)
    return BjjMountCarryover.succeeded(envelope)

func state_fields() -> Dictionary:
    return _gateway.state_fields()

func history_fields() -> Dictionary:
    return _gateway.history_fields()

func controller_fields() -> Dictionary:
    return _gateway.controller_fields()

func window_fields() -> Dictionary:
    return _gateway.window_fields()

func roles() -> BjjPositionContract.Roles:
    return _gateway.roles()

func action_options(fighter_id: String) -> BjjPositionContract.OptionList:
    return _gateway.action_options(fighter_id)

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    return _gateway.response_options(action_id)

func selected_commitment() -> String:
    return _gateway.selected_commitment()

# --- Commands ------------------------------------------------------------------------------

func open_window() -> BjjMatchWindowGateway.Report:
    return open_window_for(null)

func open_window_for(duration: Variant) -> BjjMatchWindowGateway.Report:
    if _status == STATUS_HALTED:
        return _rejected(ERROR_HALTED)
    var report := _gateway.open_window_for(duration)
    if not report.ok():
        return report
    if report.values.get("closed", false):
        _record_terminal()
    else:
        _append({"kind": "window_opened", "window_id": report.values.window_id,
            "fighter_id": report.values.fighter_id, "role": report.values.role})
    report.values["graph"] = _graph_fields()
    return report

func submit(window_id: int, fighter_id: String, action_id: String = "", response_id: String = "",
        commitment: String = "", response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    if _status == STATUS_HALTED:
        return _rejected(ERROR_HALTED)
    var report := _gateway.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)
    if not report.ok():
        return report
    _append({"kind": "decision_accepted", "window_id": window_id, "fighter_id": fighter_id,
        "role": report.values.role, "decision": report.values.kind})
    var exit_label: String = str(report.values.transition.raw_destination)
    var verdict := classify_exit_from(POSITION_ID, exit_label)
    if verdict.kind == "blocked":
        _blocked = {"from_position_id": POSITION_ID, "label": exit_label, "reason": verdict.reason,
            "destination_position_id": verdict.destination_position_id}
        _append({"kind": "transition_blocked", "from_position_id": POSITION_ID, "label": exit_label,
            "reason": verdict.reason, "destination_position_id": verdict.destination_position_id})
        _status = STATUS_HALTED
    elif report.values.ended:
        _record_terminal()
    report.values["graph"] = _graph_fields()
    return report

# --- Internals -----------------------------------------------------------------------------

func _rejected(code: String) -> BjjMatchWindowGateway.Report:
    var report := BjjMatchWindowGateway.Report.new()
    report.error = code
    return report

func _append(event: Dictionary) -> void:
    var entry := event.duplicate(true)
    entry["index"] = _events.size() + 1
    _events.append(entry)

func _record_terminal() -> void:
    var reason := terminal_reason(_gateway.state_fields())
    _terminal_reason = reason if not reason.is_empty() else "unclassified_terminal"
    _append({"kind": "terminal_outcome", "reason": _terminal_reason})
    _status = STATUS_ENDED

func _graph_fields() -> Dictionary:
    return {"status": _status, "event_count": _events.size()}
