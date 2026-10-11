class_name BjjMountPracticeController
extends RefCounted

# F1 practice controller: input handling and presentation model for the 2D Mount practice scene,
# kept free of rendering so it is testable headlessly. It owns ONLY temporary UI state (the
# selected technique, response and commitment, the last command's outcome text and a practice-match
# serial) and a handle to the BjjPositionGraphMatch it drives.
#
# Every simulation command goes through that graph's public API (open_window, submit); every
# displayed fact is a detached read of the graph's public views and of the F0 snapshot adapter
# over the same graph. It never reaches the graph's private gateway, the Mount match, stamina
# pools, behaviors, initiative, grades or policy, and it never advances time on its own: only the
# player's Next Window command calls open_window() (never open_window_for()).
#
# Practice rules for F1 (presentation choices, not game rules): the human decides for the Top
# fighter and picks the opponent's response among the responses the existing API admits; when the
# Bottom fighter owns a window, the existing no-action Bottom decision is submitted as a
# deterministic, clearly labelled SCRIPTED practice behavior. This is a positional-training
# prototype, not a match from Standing and not a combat AI.
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const KIND_ACTIVE: String = "active"
const KIND_TERMINAL: String = "terminal"
const KIND_BLOCKED: String = "blocked"
const SCRIPTED_REASON: String = "scripted_practice_opponent"
const EVENT_TAIL: int = 40
# Match settings a caller may override (the engine still validates their values). Policy and rules are not among them.
const SETTINGS_ALLOW_LIST: Array[String] = ["clock", "interval", "axis", "top_stamina", "bottom_stamina"]
const GRADE_NAMES: Dictionary = {-2: "Strong Failure", -1: "Failure", 0: "Contested", 1: "Success", 2: "Strong Success"}

var match_serial: int = 0
var selected_action: String = ""
var selected_response: String = ""
var selected_commitment: String = ""

var _graph: BjjPositionGraphMatch
var _adapter: BjjFighterSnapshotAdapter
var _names: Dictionary = {}
var _last_report: Dictionary = {}
var _last_lines: Array[String] = []
var _last_message: String = ""


# The practice configuration: the production-qualified policy with the existing setup,
# submission and commitment features enabled (as the gateway suites run it). It adds no rule.
static func match_configuration() -> Dictionary:
    var rules := BjjProductionStaminaPolicy.settings()
    rules["enable_v02_setup"] = true
    rules["enable_v03_submissions"] = true
    rules["enable_v04_commitment_semantics"] = true
    return {"rules": rules}


# Starts an independent practice match. Fighter ids are supplied here (match identity); the
# definitions only supply names. `extra` may override only the SETTINGS_ALLOW_LIST keys (a shorter
# "clock", an "axis", the "interval" or starting stamina); anything else is refused, and the engine
# validates the values. A failed start leaves any current match untouched.
func start_new_match(top_definition: Variant, bottom_definition: Variant, extra: Dictionary = {}) -> Dictionary:
    for key: Variant in extra:
        if not key is String or not SETTINGS_ALLOW_LIST.has(key):
            return _refuse_command("unsupported_practice_setting")
    var configuration := match_configuration()
    configuration.merge(extra, true)
    var created := BjjPositionGraphMatch.create(configuration, TOP_ID, BOTTOM_ID)
    if not created.ok():
        return _refuse_command(created.error)
    var adapter := BjjFighterSnapshotAdapter.create(created.graph, {TOP_ID: top_definition, BOTTOM_ID: bottom_definition})
    if not adapter.ok():
        return _refuse_command(adapter.error)
    _graph = created.graph
    _adapter = adapter.adapter
    _names = {TOP_ID: String(top_definition.display_name), BOTTOM_ID: String(bottom_definition.display_name)}
    match_serial += 1
    selected_action = ""
    selected_response = ""
    selected_commitment = ""
    _last_report = {}
    _last_lines = []
    _last_message = "New independent practice match started."
    return {"ok": true, "error": ""}


func has_match() -> bool:
    return _graph != null


# --- Commands (each goes through the graph or is refused without touching it) -------------

func next_window() -> Dictionary:
    var gate := _next_window_gate()
    if not gate.is_empty():
        return _refuse_command(gate)
    var report := _graph.open_window()
    if not report.ok():
        return _refuse_command(report.error)
    selected_action = ""
    selected_response = ""
    selected_commitment = ""
    var window := _graph.window_fields()
    if window.open:
        _last_message = "Window %d opened for %s (%s)." % [window.window_id, _display(window.fighter_id), window.role]
    else:
        _last_message = "The match reached its end of time."
    return {"ok": true, "error": ""}


func select_action(action_id: String) -> Dictionary:
    var status_gate := _status_gate()
    if not status_gate.is_empty():
        return _refuse_command(status_gate)
    var window := _graph.window_fields()
    if not window.open or window.role != "top":
        return _refuse_command("not_selectable")
    for option: BjjPositionContract.Option in _graph.action_options(window.fighter_id).options:
        if option.id == action_id:
            if not option.available:
                return _refuse_command(option.reason)
            selected_action = action_id
            selected_response = ""
            return {"ok": true, "error": ""}
    return _refuse_command("unknown_action")


func select_response(response_id: String) -> Dictionary:
    var status_gate := _status_gate()
    if not status_gate.is_empty():
        return _refuse_command(status_gate)
    if selected_action.is_empty():
        return _refuse_command("technique_required")
    for option: BjjPositionContract.Option in _graph.response_options(selected_action).options:
        if option.id == response_id:
            if not option.available:
                return _refuse_command(option.reason)
            selected_response = response_id
            return {"ok": true, "error": ""}
    return _refuse_command("unknown_response")


# Commitment is selectable only for the Top fighter's open window (Bottom's is policy-selected).
func select_commitment(commitment_id: String) -> Dictionary:
    var status_gate := _status_gate()
    if not status_gate.is_empty():
        return _refuse_command(status_gate)
    var window := _graph.window_fields()
    if not window.open or window.role != "top":
        return _refuse_command("commitment_is_policy_selected")
    if not BjjCommitment.valid(commitment_id):
        return _refuse_command("unknown_commitment")
    selected_commitment = commitment_id
    return {"ok": true, "error": ""}


func submit_decision() -> Dictionary:
    var gate := _submit_gate()
    if not gate.is_empty():
        return _refuse_command(gate)
    var window := _graph.window_fields()
    var before := _adapter.snapshots()
    var report: BjjMatchWindowGateway.Report
    var scripted: bool = window.role == "bottom"
    if scripted:
        # The existing, admitted no-action Bottom decision (Bottom never supplies a commitment).
        report = _graph.submit(window.window_id, window.fighter_id)
    else:
        report = _graph.submit(window.window_id, window.fighter_id, selected_action, selected_response, selected_commitment)
    if not report.ok():
        return _refuse_command(report.error)
    _last_report = report.fields()
    _last_lines = _decision_lines(window, scripted, before, _adapter.snapshots(), _last_report)
    _last_message = "Decision accepted."
    selected_action = ""
    selected_response = ""
    selected_commitment = ""
    return {"ok": true, "error": ""}


# --- Presentation model: a fresh, detached read; it never advances or changes anything -------

func view() -> Dictionary:
    if _graph == null:
        return {"has_match": false}
    var state := _graph.state_fields()
    var window := _graph.window_fields()
    var kind := _status_kind()
    var snapshots := _adapter.snapshots()
    var fighters: Array = []
    for id: String in [TOP_ID, BOTTOM_ID]:
        fighters.append(snapshots[id])
    return {
        "has_match": true, "match_serial": match_serial,
        "status": _graph.status(), "status_kind": kind, "banner": _banner(kind),
        "terminal_reason": _terminal_reason(), "blocked": _graph.blocked_transition(),
        "fighters": fighters,
        "clock_seconds": state.clock_seconds, "initial_clock": state.initial_clock,
        "axis": state.axis, "control_axis": state.control_axis, "band": state.band, "band_name": BjjMountRules.Band.keys()[int(state.band)],
        "window": {"open": window.open, "window_id": window.window_id, "fighter_id": window.fighter_id, "role": window.role,
            "owner_name": _display(window.fighter_id), "scripted": window.open and window.role == "bottom"},
        "actions": _action_rows(window), "responses": _response_rows(window),
        "commitment": _commitment_view(window),
        "commands": {"next_window": _command(_next_window_gate()), "submit": _command(_submit_gate()), "new_match": {"enabled": true, "reason": ""}},
        "last_lines": _last_lines.duplicate(), "last_message": _last_message,
        "events": _event_lines(),
    }


func last_report() -> Dictionary:
    return _last_report.duplicate(true)


# --- Internals -----------------------------------------------------------------------------

func _status_kind() -> String:
    if _graph == null:
        return KIND_TERMINAL
    match _graph.status():
        BjjPositionGraphMatch.STATUS_HALTED:
            return KIND_BLOCKED
        BjjPositionGraphMatch.STATUS_ENDED:
            return KIND_TERMINAL
    return KIND_ACTIVE


# Controller-level codes: no_match, match_ended, window_already_open, no_open_window, technique_required,
# response_required, not_selectable, unknown_action, unknown_response, unknown_commitment,
# unsupported_practice_setting. Everything else (the halt code, option reasons, admission errors) is the
# graph's or the engine's own code, passed through unchanged.
func _status_gate() -> String:
    if _graph == null:
        return "no_match"
    match _status_kind():
        KIND_BLOCKED:
            return BjjPositionGraphMatch.ERROR_HALTED
        KIND_TERMINAL:
            return "match_ended"
    return ""


func _next_window_gate() -> String:
    var status_gate := _status_gate()
    if not status_gate.is_empty():
        return status_gate
    if _graph.window_fields().open:
        return "window_already_open"
    return ""


func _submit_gate() -> String:
    var status_gate := _status_gate()
    if not status_gate.is_empty():
        return status_gate
    var window := _graph.window_fields()
    if not window.open:
        return "no_open_window"
    if window.role == "top":
        if selected_action.is_empty():
            return "technique_required"
        if selected_response.is_empty():
            return "response_required"
    return ""


func _command(gate: String) -> Dictionary:
    return {"enabled": gate.is_empty(), "reason": gate}


func _refuse_command(code: String) -> Dictionary:
    _last_message = "Rejected: %s" % code
    return {"ok": false, "error": code}


func _display(fighter_id: String) -> String:
    return String(_names.get(fighter_id, fighter_id))


func _banner(kind: String) -> String:
    match kind:
        KIND_BLOCKED:
            var blocked := _graph.blocked_transition()
            var destination: String = str(blocked.get("destination_position_id", ""))
            var landing := "declared destination %s is not implemented" % destination if not destination.is_empty() else "destination unresolved (no landing)"
            return "BLOCKED POSITION TRANSITION (not a victory or defeat): exit '%s'; %s [%s]. Mount play stops here." % [
                blocked.get("label", "?"), landing, blocked.get("reason", "?")]
        KIND_TERMINAL:
            return "TERMINAL OUTCOME: %s" % _terminal_reason()
    return "Active Mount practice match"


func _terminal_reason() -> String:
    for event: Dictionary in _graph.events():
        if event.kind == "terminal_outcome":
            return str(event.reason)
    return ""


func _option_name(id: String) -> String:
    var entity: Dictionary = BjjMountCatalog.ENTITIES.get(id, {})
    return String(entity.get("name", id))


func _action_rows(window: Dictionary) -> Array:
    var rows: Array = []
    if _status_kind() != KIND_ACTIVE or not window.open:
        return rows
    var scripted: bool = window.role == "bottom"
    for option: BjjPositionContract.Option in _graph.action_options(window.fighter_id).options:
        rows.append({"id": option.id, "name": _option_name(option.id), "available": option.available and not scripted,
            "reason": SCRIPTED_REASON if scripted and option.available else option.reason, "selected": option.id == selected_action})
    return rows


func _response_rows(window: Dictionary) -> Array:
    var rows: Array = []
    if _status_kind() != KIND_ACTIVE or not window.open or window.role != "top" or selected_action.is_empty():
        return rows
    for option: BjjPositionContract.Option in _graph.response_options(selected_action).options:
        rows.append({"id": option.id, "name": _option_name(option.id), "available": option.available, "reason": option.reason,
            "selected": option.id == selected_response})
    return rows


func _commitment_view(window: Dictionary) -> Dictionary:
    var selectable: bool = _status_kind() == KIND_ACTIVE and window.open and window.role == "top"
    var policy: String = _graph.selected_commitment()
    return {"selectable": selectable, "options": BjjCommitment.ORDER.duplicate(), "policy_selected": policy,
        "selected": selected_commitment if not selected_commitment.is_empty() else policy}


func _event_lines() -> Array:
    var lines: Array = []
    var events := _graph.events()
    for event: Dictionary in events.slice(maxi(0, events.size() - EVENT_TAIL)):
        var line := "#%d %s" % [event.index, event.kind]
        match event.kind:
            "window_opened":
                line += " - window %d, %s (%s)" % [event.window_id, _display(event.fighter_id), event.role]
            "decision_accepted":
                line += " - window %d, %s (%s), %s" % [event.window_id, _display(event.fighter_id), event.role, event.decision]
            "transition_blocked":
                line += " - %s, destination '%s', reason %s" % [event.label, event.destination_position_id, event.reason]
            "terminal_outcome":
                line += " - %s" % event.reason
        lines.append(line)
    return lines


func _decision_lines(window: Dictionary, scripted: bool, before: Dictionary, after: Dictionary, report: Dictionary) -> Array[String]:
    var lines: Array[String] = []
    var who := _display(window.fighter_id)
    if scripted:
        lines.append("%s (Bottom) - SCRIPTED practice behavior: the existing no-action Bottom decision (engine decision kind %s; production policy may run a recovery hold)." % [who, str(report.detail.decision.kind)])
    else:
        var resolution: Dictionary = report.detail.settlement.resolution
        lines.append("%s (Top): %s vs %s" % [who, _option_name(str(resolution.action_id)), _option_name(str(resolution.response_id))])
        lines.append("Grade: %s (raw %s, final %s)" % [GRADE_NAMES.get(int(resolution.final_grade), "?"), resolution.raw_grade, resolution.final_grade])
        lines.append("Axis %s -> %s; band %s -> %s" % [resolution.axis_before, resolution.axis_after,
            BjjMountRules.Band.keys()[int(resolution.band_before)], BjjMountRules.Band.keys()[int(resolution.band_after)]])
        if not str(report.transition.raw_destination).is_empty():
            lines.append("Exit: %s" % report.transition.raw_destination)
    for id: String in [TOP_ID, BOTTOM_ID]:
        lines.append("%s stamina %d -> %d (%s)" % [_display(id), before[id].stamina_current, after[id].stamina_current, after[id].exhaustion_band])
    lines.append("Clock %d s remaining; match status %s" % [report.state.clock_seconds, _graph.status()])
    return lines
