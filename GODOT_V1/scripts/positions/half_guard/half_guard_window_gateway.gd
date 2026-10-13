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
# B1i: at most one sealed-intent protocol may ever drive this gateway (it is the position graph's own gateway when adopted). The claim
# is one-way for the lifetime of the object and changes no simulation state.
var _protocol_claimed: bool = false

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

# --- Feints (B1h; the single authority is BjjHalfGuardMatch, these only expose it) ---------------------------------

# Pure: whether the initiator could feint `apparent_id` as `real_id` at `commitment` (empty = the selected commitment) in the current state.
# "" = admissible, otherwise the match's own refusal code. Nothing is reserved, charged or recorded.
func feint_error(apparent_id: String, real_id: String, commitment: String = "") -> String:
    return _match.feint_error(apparent_id, real_id, selected_commitment() if commitment.is_empty() else commitment)

# Pure: the real techniques `apparent_id` may conceal right now (pair table x public tier condition; ignores stamina and funding).
func eligible_real_ids(apparent_id: String) -> Array[String]:
    return BjjHalfGuardCatalog.eligible_real_ids(apparent_id, _match.top_base, _match.bottom_frame)

# One-shot, one-way claim by a sealed-intent protocol (BjjHalfGuardSealedProtocol.create / adopt). False when already claimed, so a second
# protocol can never be attached to the same simulation.
func claim_for_protocol() -> bool:
    if _protocol_claimed:
        return false
    _protocol_claimed = true
    return true

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

# One decision that is an explicit feint: `action_id` is the apparent technique (it never resolves), `real_action_id` settles through the
# same path as `submit`. Same window, report keys and atomicity; the settlement record carries one extra `feint` sub-record.
func submit_feint(window_id: int, fighter_id: String, action_id: String, real_action_id: String, response_id: String = "",
        commitment: String = "", response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    return _report(_match.decide(window_id, fighter_id, action_id, response_id, commitment, response_commitment, real_action_id))
