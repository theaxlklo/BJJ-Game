class_name BjjHalfGuardWindowGateway
extends RefCounted

# Production-facing facade for one Half Guard v0 segment. Like the Mount gateway it adds only window identity, admission and
# reports: simulated time moves only through open_window(), exactly one accepted decision closes a window, and no grade, cost
# or readiness logic lives here (BjjHalfGuardMatch is the single owner of state). It builds and owns its match, so no outside
# reference can mutate it, and every returned value is detached. Reports use the shared BjjMatchWindowGateway.Report type with
# the same keys the Mount gateway's reports carry that the position graph reads. No carry-over export exists for this position yet.
const POSITION_ID: String = BjjHalfGuardRules.POSITION_ID

var _match: BjjHalfGuardMatch
var _contract: BjjHalfGuardContract

class Creation extends RefCounted:
    var error: String = ""
    var gateway: BjjHalfGuardWindowGateway
    func ok() -> bool:
        return error.is_empty() and gateway != null

static func create(entry: Variant) -> Creation:
    var result := Creation.new()
    var built := BjjHalfGuardMatch.from_entry(entry)
    if not built.ok():
        result.error = built.error
        return result
    var contract := BjjHalfGuardContract.create(built.match_state)
    if not contract.ok():
        result.error = contract.error
        return result
    var gateway := BjjHalfGuardWindowGateway.new()
    gateway._match = built.match_state
    gateway._contract = contract.contract
    result.gateway = gateway
    return result

static func _report(source: BjjHalfGuardMatch.Result) -> BjjMatchWindowGateway.Report:
    var report := BjjMatchWindowGateway.Report.new()
    report.error = source.error
    if source.ok():
        report.values = source.values.duplicate(true)
    return report

# --- Detached views --------------------------------------------------------------------------

func window_fields() -> Dictionary:
    var role := _match.window_side if _match.window_open else ""
    return {"open": _match.window_open, "window_id": _match.window_id,
        "fighter_id": (_match.top_id if role == "top" else _match.bottom_id) if _match.window_open else "", "role": role}

func state_fields() -> Dictionary:
    return _contract.state_fields()

func history_fields() -> Dictionary:
    return _contract.history_fields()

# Half Guard has no D3-B controller and no behaviors in v0; both views are explicit and constant.
func controller_fields() -> Dictionary:
    return {}

func behavior_fields() -> Dictionary:
    return {"top": "", "bottom": ""}

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

# Canonical detached snapshot of the whole segment (for parity tests and diagnostics).
func snapshot() -> Dictionary:
    return _match.snapshot()

# --- Time and decisions -------------------------------------------------------------------------

func open_window() -> BjjMatchWindowGateway.Report:
    return open_window_for(null)

# Explicit session-owner seam (tests, replays): `duration` is trusted simulated seconds, never wall-clock or frames.
func open_window_for(duration: Variant) -> BjjMatchWindowGateway.Report:
    return _report(_match.open_window_for(duration))

# One decision for the open window. An empty action_id is a pass (no stamina, no clock). Either side may pass.
func submit(window_id: int, fighter_id: String, action_id: String = "", response_id: String = "",
        commitment: String = "", response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    return _report(_match.decide(window_id, fighter_id, action_id, response_id, commitment, response_commitment))
