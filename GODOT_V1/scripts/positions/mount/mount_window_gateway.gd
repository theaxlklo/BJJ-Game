class_name BjjMatchWindowGateway
extends RefCounted

# Match-level owner of production decision windows for the headless Mount.
#
# It composes the unchanged authorities and adds only window identity and admission:
#   * simulated time moves ONLY through BjjMountMatch.next_window() (open_window);
#   * Bottom decisions run ONLY through BjjMountMatch.bottom_decision(), so selected
#     commitment, D3-B TOKEN / LOCKOUT_HOLD and genuine RESET are never bypassed;
#   * Top decisions run through BjjMountContract.submit() (== attempt());
#   * a no-action decision is the existing reset_window().
# No grade, cost, recovery or token logic lives here. The gateway builds and owns its
# match so no outside reference can mutate it; every returned value is detached.
#
# Window lifecycle: open_window() advances time and opens at most one window; exactly one
# accepted decision closes it. A second open_window() before a decision, a replayed or
# stale decision, or any command after the match ends is rejected before any mutation.
const POSITION_ID: String = BjjMountContract.POSITION_ID

var _match: BjjMountMatch
var _contract: BjjMountContract
var _top_id: String = ""
var _bottom_id: String = ""
var _window_open: bool = false
var _window_id: int = 0
var _window_side: String = ""

class Creation extends RefCounted:
    var error: String = ""
    var gateway: BjjMatchWindowGateway
    func ok() -> bool:
        return error.is_empty() and gateway != null

class Report extends RefCounted:
    var error: String = "incomplete_report"
    var values: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()
    func fields() -> Dictionary:
        return values.duplicate(true) if ok() else {"error": error}

static func _fail(code: String) -> Report:
    var report := Report.new()
    report.error = code
    return report

static func create(configuration: Dictionary, top_fighter_id: String, bottom_fighter_id: String) -> Creation:
    var result := Creation.new()
    result.error = BjjPositionContract.fighter_ids_error(top_fighter_id, bottom_fighter_id)
    if not result.error.is_empty():
        return result
    # Production policy is the only supported mode; it cannot be opted out of here.
    if configuration.get("production", true) != true:
        result.error = "production_configuration_required"
        return result
    var settings := configuration.duplicate(true)
    settings["production"] = true
    var created := BjjMountMatch.create(settings)
    if not created.ok():
        result.error = created.error
        return result
    var contract := BjjMountContract.create(created.match_state, top_fighter_id, bottom_fighter_id)
    if not contract.ok():
        result.error = contract.error
        return result
    var gateway := BjjMatchWindowGateway.new()
    gateway._match = created.match_state
    gateway._contract = contract.contract
    gateway._top_id = top_fighter_id
    gateway._bottom_id = bottom_fighter_id
    result.gateway = gateway
    return result

# --- Detached views ------------------------------------------------------------------

func window_fields() -> Dictionary:
    return {"open": _window_open, "window_id": _window_id,
        "fighter_id": _fighter_for(_window_side) if _window_open else "",
        "role": _window_side if _window_open else ""}

func state_fields() -> Dictionary:
    return _contract.state_fields()

func history_fields() -> Dictionary:
    return _contract.history_fields()

func controller_fields() -> Dictionary:
    return _match.d3b.fields()

func roles() -> BjjPositionContract.Roles:
    return _contract.roles()

func is_terminal() -> bool:
    return _contract.is_terminal()

func action_options(fighter_id: String) -> BjjPositionContract.OptionList:
    return _contract.action_options(fighter_id)

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    return _contract.response_options(action_id)

func selected_commitment() -> String:
    return _match.selected_commitment()

func _fighter_for(role: String) -> String:
    return _top_id if role == "top" else _bottom_id if role == "bottom" else ""

func _role_of(fighter_id: String) -> String:
    if fighter_id.is_empty():
        return ""
    return "top" if fighter_id == _top_id else "bottom" if fighter_id == _bottom_id else ""

# --- Time: the only place simulated seconds advance -----------------------------------

# Production entry point: always the match's own interval. A session or UI cannot pick the
# cadence, so it cannot manufacture extra zero-time windows through this call.
func open_window() -> Report:
    return open_window_for(null)

# Explicit session-owner seam (tests, replays). `duration` is trusted simulated seconds
# (null = the match interval), never wall-clock or frames. Do not expose it to a human UI.
func open_window_for(duration: Variant) -> Report:
    if _window_open:
        return _fail("window_already_open")
    var context := _match.validate_context()
    if not context.is_empty():
        return _fail(context)
    if duration != null and not duration is int:
        return _fail("invalid_duration")
    var seconds: int = _match.interval_seconds if duration == null else duration
    var window := _match.next_window(seconds)
    if not window.ok():
        return _fail(window.error)
    var report := Report.new()
    report.error = ""
    report.values = {"closed": _match.ended, "window_open": false}
    report.values.merge({"free": window.values.free, "advance": window.values.advance})
    if _match.ended:
        report.values.window_id = _window_id
        report.values.state = _contract.state_fields()
        return report
    _window_id += 1
    _window_open = true
    _window_side = _match.initiator
    report.values.window_open = true
    report.values.window_id = _window_id
    report.values.fighter_id = _fighter_for(_window_side)
    report.values.role = _window_side
    report.values.commitment = _match.selected_commitment()
    report.values.state = _contract.state_fields()
    return report

# --- Decisions -------------------------------------------------------------------------

# One decision for the open window. An empty action_id is the existing RESET (Bottom: via
# bottom_decision, so D3-B classification still applies). Bottom never supplies its own
# commitment; Top may request one, defaulting to the selected baseline.
func submit(window_id: int, fighter_id: String, action_id: String = "", response_id: String = "",
        commitment: String = "", response_commitment: String = "") -> Report:
    var error := _admission_error(window_id, fighter_id, action_id, response_id, commitment, response_commitment)
    if not error.is_empty():
        return _fail(error)
    var role := _window_side
    var kind := ""
    var detail: Dictionary = {}
    if role == "bottom":
        var decision := _match.bottom_decision(action_id, response_id, response_commitment)
        if not decision.ok():
            return _fail(decision.error)
        kind = "bottom_decision"
        detail = decision.fields()
    elif action_id.is_empty():
        var reset := _match.reset_window()
        if not reset.ok():
            return _fail(reset.error)
        kind = "reset"
        detail = {"settlement": reset.fields()}
    else:
        var requested := _match.selected_commitment() if commitment.is_empty() else commitment
        var outcome := _contract.submit(BjjPositionContract.Command.new(
            POSITION_ID, fighter_id, action_id, response_id, requested, response_commitment))
        if not outcome.ok():
            return _fail(outcome.error)
        kind = "top_exchange"
        detail = {"settlement": outcome.exchange}
    # Defensive: an owner reporting a nested settlement error must not close the window.
    if detail.get("settlement", {}).has("error"):
        return _fail(str(detail.settlement.error))
    _window_open = false
    var report := Report.new()
    report.error = ""
    report.values = {"window_id": window_id, "fighter_id": fighter_id, "role": role, "kind": kind,
        "detail": detail, "transition": _transition().fields(), "state": _contract.state_fields(),
        "ended": _match.ended}
    return report

# Everything here precedes any mutation. Order: window existence, identity, context,
# addressing, initiative, then command shape. Match-level admission follows in the owners.
func _admission_error(window_id: int, fighter_id: String, action_id: String, response_id: String, commitment: String, response_commitment: String) -> String:
    if not _window_open:
        return "no_open_window"
    if window_id != _window_id:
        return "stale_window"
    var context := _match.validate_context()
    if not context.is_empty():
        return context
    if _match.initiator != _window_side:
        return "window_initiator_changed"
    if fighter_id.is_empty():
        return "missing_fighter_id"
    var role := _role_of(fighter_id)
    if role.is_empty():
        return "unknown_fighter"
    if role != _window_side:
        return "not_initiator"
    if action_id.is_empty() and not response_id.is_empty():
        return "response_without_action"
    if _window_side == "bottom" and not commitment.is_empty():
        return "commitment_is_policy_selected"
    if action_id.is_empty() and not (commitment.is_empty() and response_commitment.is_empty()):
        return "commitment_without_action"
    return ""

func _transition() -> BjjPositionContract.Transition:
    return BjjMountContract.transition_for(_match.exit_destination)
