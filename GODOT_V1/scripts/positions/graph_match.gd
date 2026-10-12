class_name BjjPositionGraphMatch
extends RefCounted

# Position-graph coordinator. The graph owns the choice of the ACTIVE POSITION; each position owns its own combat
# mechanics. At every moment of an active match exactly one positional relationship is shared by both fighters and exactly
# one position simulation owner accepts commands (active_position_id()); a transition replaces that owner atomically, and
# the previous segment is retained as frozen history (never advanced, submitted to or exported again). A halt at an
# unsupported transition is an incomplete-engine boundary, not a state of a finished playable game.
#
# Slice A: a thin wrapper around exactly one BjjMatchWindowGateway (Mount, the default). B1d adds an OPT-IN second typed,
# nullable slot for Half Guard (create_with_receivers); `create` builds a graph with no receivers and behaves exactly as
# before. The wrapper owns NO gameplay state: stamina, meters, clock, D3-B, fighter identity, histories and window
# identity stay with the active segment's gateway; every view here is a detached read through it. The graph owns only
# its status, its global event log, the recorded blocked transition and (opt-in) the receiver table and cadence.
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
# B1d (opt-in Half Guard receiver)
const HALF_GUARD_ID: String = BjjHalfGuardRules.POSITION_ID
const RECEIVER_IDS: Array[String] = [HALF_GUARD_ID]
const ERROR_INVALID_RECEIVERS: String = "invalid_receivers"
const ERROR_UNSUPPORTED_EXPORT: String = "carryover_unsupported_position"
const REASON_ENTRY_INVALID: String = "transition_entry_invalid"

var _gateway: BjjMatchWindowGateway
# Typed, nullable second segment (HG-16). Null until a validated Mount -> Half Guard commit; while null Mount is the active position.
var _half_guard: BjjHalfGuardWindowGateway
# Opt-in receiver table {destination position id: Callable(record, interval_seconds) -> BjjHalfGuardWindowGateway.Creation}; empty by default.
var _receivers: Dictionary = {}
# Window cadence handed to a receiver (HG-25): the graph's own configured interval.
var _interval_seconds: int = BjjMountRules.DEFAULT_INTERVAL_SECONDS
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

# Opt-in construction (HG-22). `receivers` keys must be a subset of RECEIVER_IDS and values valid two-argument Callables;
# anything else builds no graph. An empty table is observably identical to `create`. The caller's table is copied.
static func create_with_receivers(configuration: Dictionary, top_fighter_id: String, bottom_fighter_id: String, receivers: Variant) -> Creation:
    if not _receivers_are_valid(receivers):
        var rejected := Creation.new()
        rejected.error = ERROR_INVALID_RECEIVERS
        return rejected
    var result := create(configuration, top_fighter_id, bottom_fighter_id)
    if not result.ok():
        return result
    var table: Dictionary = receivers
    result.graph._receivers = table.duplicate()
    result.graph._interval_seconds = int(configuration.get("interval", BjjMountRules.DEFAULT_INTERVAL_SECONDS))
    return result

# The Half Guard edge as a receiver table, for future callers and tests. No production caller exists yet (F1 uses `create`).
static func default_receivers() -> Dictionary:
    return {HALF_GUARD_ID: Callable(BjjPositionGraphMatch, "_half_guard_from_record")}

static func _half_guard_from_record(record: Dictionary, interval_seconds: int) -> BjjHalfGuardWindowGateway.Creation:
    var edge := BjjHalfGuardMountEdge.entry_from_record(record, interval_seconds)
    if not edge.ok():
        var failed := BjjHalfGuardWindowGateway.Creation.new()
        failed.error = edge.error
        return failed
    return BjjHalfGuardWindowGateway.create(edge.request)

static func _receivers_are_valid(receivers: Variant) -> bool:
    if typeof(receivers) != TYPE_DICTIONARY:
        return false
    var table: Dictionary = receivers
    for key: Variant in table:
        if typeof(key) != TYPE_STRING or not RECEIVER_IDS.has(key):
            return false
        var receiver: Variant = table[key]
        if typeof(receiver) != TYPE_CALLABLE:
            return false
        var callable: Callable = receiver
        if not callable.is_valid() or callable.get_argument_count() != 2:
            return false
    return true

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

# The one position whose simulation owner currently accepts commands: "mount" until a Half Guard commit, then "half_guard".
func active_position_id() -> String:
    return HALF_GUARD_ID if _half_guard != null else POSITION_ID

# Match-level carry-over envelope (A3b): the gateway's segment record beside the graph's own
# status, global event count and recorded blocked transition. Read-only; a halt stays a halt.
func carryover_export() -> BjjMountCarryover.Export:
    # HG-20: no v2 envelope exists; a non-Mount source is refused rather than invented.
    if _half_guard != null:
        return BjjMountCarryover.failed(ERROR_UNSUPPORTED_EXPORT)
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
    return _half_guard.state_fields() if _half_guard != null else _gateway.state_fields()

func history_fields() -> Dictionary:
    return _half_guard.history_fields() if _half_guard != null else _gateway.history_fields()

func controller_fields() -> Dictionary:
    return _half_guard.controller_fields() if _half_guard != null else _gateway.controller_fields()

func window_fields() -> Dictionary:
    return _half_guard.window_fields() if _half_guard != null else _gateway.window_fields()

# Read-only pass-through of the gateway's held per-role behaviors (F0 accessor). Detached; it
# opens no window, moves no time and never exposes the gateway itself.
func behavior_fields() -> Dictionary:
    return _half_guard.behavior_fields() if _half_guard != null else _gateway.behavior_fields()

func roles() -> BjjPositionContract.Roles:
    return _half_guard.roles() if _half_guard != null else _gateway.roles()

func action_options(fighter_id: String) -> BjjPositionContract.OptionList:
    return _half_guard.action_options(fighter_id) if _half_guard != null else _gateway.action_options(fighter_id)

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    return _half_guard.response_options(action_id) if _half_guard != null else _gateway.response_options(action_id)

func selected_commitment() -> String:
    return _half_guard.selected_commitment() if _half_guard != null else _gateway.selected_commitment()

# --- Commands ------------------------------------------------------------------------------

func open_window() -> BjjMatchWindowGateway.Report:
    return open_window_for(null)

func open_window_for(duration: Variant) -> BjjMatchWindowGateway.Report:
    if _status == STATUS_HALTED:
        return _rejected(ERROR_HALTED)
    var report := _half_guard.open_window_for(duration) if _half_guard != null else _gateway.open_window_for(duration)
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
    var source := active_position_id()
    var report := _half_guard.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment) if _half_guard != null \
        else _gateway.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)
    if not report.ok():
        return report
    _append({"kind": "decision_accepted", "window_id": window_id, "fighter_id": fighter_id,
        "role": report.values.role, "decision": report.values.kind})
    var exit_label: String = str(report.values.transition.raw_destination)
    var verdict := _classify(source, exit_label)
    if verdict.kind == "transition":
        _commit_or_halt(exit_label, verdict.destination_position_id)
    elif verdict.kind == "blocked":
        _halt(source, exit_label, verdict.reason, verdict.destination_position_id)
    elif report.values.ended:
        _record_terminal()
    report.values["graph"] = _graph_fields()
    return report

# --- Internals -----------------------------------------------------------------------------

# One decision point for "what does this exit label mean for the active position". Default graphs (no receivers) return
# exactly the static answer. An opt-in Mount graph turns the static "destination not implemented" answer into a transition
# iff the destination is a registered receiver (HG-23); the static classifier itself is unchanged. Half Guard's own
# declared exits are classified by the same unchanged static function with Half Guard's declarations.
func _classify(source_position_id: String, label: String) -> Dictionary:
    if source_position_id == HALF_GUARD_ID:
        return classify_exit_from(HALF_GUARD_ID, label, {HALF_GUARD_ID: {"exits": BjjHalfGuardCatalog.EXIT_DESTINATIONS, "unresolved": []}})
    var verdict := classify_exit_from(source_position_id, label)
    if verdict.kind == "blocked" and verdict.reason == "destination_not_implemented" and _receivers.has(verdict.destination_position_id):
        return {"kind": "transition", "destination_position_id": verdict.destination_position_id}
    return verdict

func _halt(source_position_id: String, label: String, reason: String, destination_position_id: String) -> void:
    _blocked = {"from_position_id": source_position_id, "label": label, "reason": reason,
        "destination_position_id": destination_position_id}
    _append({"kind": "transition_blocked", "from_position_id": source_position_id, "label": label,
        "reason": reason, "destination_position_id": destination_position_id})
    _status = STATUS_HALTED

# The exchange that produced the exit is already accepted and settled, so a failure here cannot roll back (HG-18): the
# graph halts with `transition_entry_invalid` and no partial Half Guard activation. Success replaces the active segment
# in one step (set the slot, append one event); this step cannot fail. It opens no window and charges nothing.
func _commit_or_halt(label: String, destination_position_id: String) -> void:
    var built := _build_half_guard(label, destination_position_id)
    if built == null:
        _halt(POSITION_ID, label, REASON_ENTRY_INVALID, destination_position_id)
        return
    _half_guard = built
    _append({"kind": "transition_committed", "from_position_id": POSITION_ID, "to_position_id": destination_position_id, "label": label})

# Receiver construction is a trust boundary. Everything is built and checked in isolation from detached values; nothing
# is committed here. Returns null on any failure.
func _build_half_guard(label: String, destination_position_id: String) -> BjjHalfGuardWindowGateway:
    var before := _mount_fingerprint()
    var segment := _gateway.carryover_segment()
    if not segment.ok():
        return null
    var record: Dictionary = segment.record
    if record.exit.raw_destination != label or record.exit.destination_position_id != destination_position_id or not record.exit.resolved:
        return null
    # The graph computes its OWN expected request and fresh reference state; the receiver's answer is only compared with them.
    var expected := BjjHalfGuardMountEdge.entry_from_record(record.duplicate(true), _interval_seconds)
    if not expected.ok():
        return null
    var reference := BjjHalfGuardMatch.from_entry(expected.request)
    if not reference.ok():
        return null
    var receiver: Callable = _receivers[destination_position_id]
    var answer: Variant = receiver.call(record.duplicate(true), _interval_seconds)
    if typeof(answer) != TYPE_OBJECT or not answer is BjjHalfGuardWindowGateway.Creation:
        return null
    var creation: BjjHalfGuardWindowGateway.Creation = answer
    if not creation.ok():
        return null
    if not _receiver_matches(creation.gateway, expected.request, reference.match_state.snapshot()):
        return null
    # A faulty receiver may not have touched the retained Mount segment.
    if not _same(_mount_fingerprint(), before):
        return null
    return creation.gateway

# Every entry invariant, checked on detached views of the receiver's gateway against the validated request, then the whole
# fresh snapshot against the one the graph built itself.
func _receiver_matches(gateway: BjjHalfGuardWindowGateway, request: Dictionary, fresh: Dictionary) -> bool:
    var roles_view := gateway.roles().fields()
    if roles_view.position_id != HALF_GUARD_ID or not _same(roles_view.fighter_by_role, request.role_map):
        return false
    var snapshot := gateway.snapshot()
    if snapshot.position_id != HALF_GUARD_ID or not _same(snapshot.role_map, request.role_map):
        return false
    if not _same(snapshot.fighters, request.fighters):
        return false
    if snapshot.initial_clock != request.clock.initial_seconds or snapshot.clock_seconds != request.clock.remaining_seconds \
            or snapshot.interval_seconds != request.interval_seconds or snapshot.window_id != request.window.last_issued_id:
        return false
    if snapshot.window_open or snapshot.window_side != "" or snapshot.exit_destination != "" or snapshot.exit_reason != "":
        return false
    if snapshot.axis_tenths != BjjHalfGuardRules.ENTRY_AXIS or snapshot.band != BjjHalfGuardRules.ENTRY_BAND \
            or snapshot.top_base != BjjHalfGuardRules.ENTRY_TIER or snapshot.bottom_frame != BjjHalfGuardRules.ENTRY_TIER \
            or snapshot.initiator != "top":
        return false
    if not _same(snapshot.history, BjjHalfGuardMatch.empty_history()) or not _same(gateway.history_fields(), BjjHalfGuardMatch.empty_history()):
        return false
    var window_view := gateway.window_fields()
    if not _same(window_view, {"open": false, "window_id": request.window.last_issued_id, "fighter_id": "", "role": ""}):
        return false
    if gateway.state_fields().ended or gateway.is_terminal():
        return false
    return _same(snapshot, fresh)

# Public read views of the retained Mount segment (plus its export, which includes the private meters), used to prove a
# receiver did not touch it.
func _mount_fingerprint() -> Dictionary:
    return {"state": _gateway.state_fields(), "history": _gateway.history_fields(), "controller": _gateway.controller_fields(),
        "window": _gateway.window_fields(), "behavior": _gateway.behavior_fields(), "roles": _gateway.roles().fields(),
        "segment": _gateway.carryover_segment().record}

static func _same(left: Variant, right: Variant) -> bool:
    return typeof(left) == typeof(right) and JSON.stringify(left, "", true, true) == JSON.stringify(right, "", true, true)

func _rejected(code: String) -> BjjMatchWindowGateway.Report:
    var report := BjjMatchWindowGateway.Report.new()
    report.error = code
    return report

func _append(event: Dictionary) -> void:
    var entry := event.duplicate(true)
    entry["index"] = _events.size() + 1
    _events.append(entry)

func _record_terminal() -> void:
    var reason := terminal_reason(state_fields())
    _terminal_reason = reason if not reason.is_empty() else "unclassified_terminal"
    _append({"kind": "terminal_outcome", "reason": _terminal_reason})
    _status = STATUS_ENDED

func _graph_fields() -> Dictionary:
    return {"status": _status, "event_count": _events.size()}
