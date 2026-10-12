class_name BjjHalfGuardSealedProtocol
extends RefCounted

# Explicit, Half Guard-only two-phase decision protocol (B1g; TACTICAL_PREPARATION_AND_FEINTS.md section 7). It is a protocol
# slice, not a feint slice: the sealed technique is the direct technique and nothing here changes a grade, a cost, a readiness
# tier, the axis or an exit.
#   1. seal_intent: the initiator seals ONE direct technique and its commitment for the open window. The executor (this object)
#      stores it privately. Nothing in the simulation changes.
#   2. respond: the responder chooses a response and a response commitment from the closed-schema public_intent_view().
#   3. The same call hands the resolved command to the unchanged BjjHalfGuardWindowGateway.submit, which is the single authority
#      for grades, stamina, readiness, axis, initiative and exits. One window, one accepted exchange, one initiative advancement.
# This object owns its gateway (nothing outside can mutate it between seal and response), keeps only the sealed store, a serial
# counter and an event log of its own, and returns detached values. The existing one-call BjjHalfGuardWindowGateway.submit is
# untouched; `submit` here is a gated pass-through that is refused while an intent is pending.
# Information isolation (accurate scope): a controller that is handed ONLY the dictionaries returned by public_intent_view() /
# public_events() cannot reach the sealed store, because those are detached copies built from an allow-list. GDScript has no private
# members, so any in-process code that holds THIS object can read `_pending`; this is discipline plus tests, not a security boundary.
const POSITION_ID: String = BjjHalfGuardRules.POSITION_ID
# The allow-list of the closed public intent view. The sealed commitment is deliberately absent (owner decision GP-3 is open).
const PUBLIC_VIEW_KEYS: Array[String] = ["position_id", "window_id", "intent_serial", "initiator_id", "responder_id",
    "apparent_technique_id", "apparent_technique_name", "response_ids"]
const PUBLIC_SEALED_KEYS: Array[String] = ["event", "index", "window_id", "intent_serial", "initiator_id", "apparent_technique_id"]

var _gateway: BjjHalfGuardWindowGateway
var _pending: Dictionary = {}
var _serial: int = 0
var _events: Array = []
var _closed: bool = false

class Creation extends RefCounted:
    var error: String = ""
    var protocol: BjjHalfGuardSealedProtocol
    func ok() -> bool:
        return error.is_empty() and protocol != null

static func create(entry: Variant) -> Creation:
    var result := Creation.new()
    var built := BjjHalfGuardWindowGateway.create(entry)
    if not built.ok():
        result.error = built.error
        return result
    var protocol := BjjHalfGuardSealedProtocol.new()
    protocol._gateway = built.gateway
    result.protocol = protocol
    return result

static func _fail(code: String) -> BjjMatchWindowGateway.Report:
    var report := BjjMatchWindowGateway.Report.new()
    report.error = code
    return report

static func _done(values: Dictionary) -> BjjMatchWindowGateway.Report:
    var report := BjjMatchWindowGateway.Report.new()
    report.error = ""
    report.values = values.duplicate(true)
    return report

# --- Detached read-only views (no sealed content) ------------------------------------------------

func window_fields() -> Dictionary:
    return _gateway.window_fields()

func state_fields() -> Dictionary:
    return _gateway.state_fields()

func history_fields() -> Dictionary:
    return _gateway.history_fields()

func roles() -> BjjPositionContract.Roles:
    return _gateway.roles()

func is_terminal() -> bool:
    return _gateway.is_terminal()

func action_options(fighter_id: String) -> BjjPositionContract.OptionList:
    return _gateway.action_options(fighter_id)

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    return _gateway.response_options(action_id)

# The simulation snapshot only. The sealed store is not part of it (a seal is not a simulation event).
func snapshot() -> Dictionary:
    return _gateway.snapshot()

func has_pending_intent() -> bool:
    return not _pending.is_empty()

func is_closed() -> bool:
    return _closed

# The closed-schema view a responder may read: exactly PUBLIC_VIEW_KEYS, values built from the allow-list, never an alias.
func public_intent_view() -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    if _pending.is_empty():
        return _fail("no_sealed_intent")
    return _done(_public_view())

# What the initiator may read about its own seal (and nobody else).
func sealed_intent_view(fighter_id: String) -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    if _pending.is_empty():
        return _fail("no_sealed_intent")
    if fighter_id != str(_pending.fighter_id):
        return _fail("not_intent_owner")
    return _done({"window_id": _pending.window_id, "intent_serial": _pending.intent_serial, "action_id": _pending.action_id,
        "commitment_requested": _pending.commitment})

# The redacted public event stream: the same events minus the sealed commitment, which is revealed only by exchange_revealed.
func public_events() -> Array:
    var redacted: Array = []
    for event: Dictionary in _events:
        if str(event.event) == "intent_sealed":
            var kept := {}
            for key: String in PUBLIC_SEALED_KEYS:
                kept[key] = event[key]
            redacted.append(kept)
        else:
            redacted.append(event.duplicate(true))
    return redacted

# Executor / diagnostic surface (replay, parity tests). Never hand this to a controller.
func protocol_events() -> Array:
    return _events.duplicate(true)

func executor_snapshot() -> Dictionary:
    return {"gateway": _gateway.snapshot(), "pending": _pending.duplicate(true), "serial": _serial, "events": _events.duplicate(true),
        "closed": _closed}

func _public_view() -> Dictionary:
    var roles_value := _gateway.roles()
    var initiator_id := str(_pending.fighter_id)
    var responder_id := ""
    for role: Variant in roles_value.fighter_by_role:
        if str(roles_value.fighter_by_role[role]) != initiator_id:
            responder_id = str(roles_value.fighter_by_role[role])
    var response_ids: Array = []
    for option in _gateway.response_options(str(_pending.action_id)).options:
        if option.available:
            response_ids.append(option.id)
    return {"position_id": POSITION_ID, "window_id": int(_pending.window_id), "intent_serial": int(_pending.intent_serial),
        "initiator_id": initiator_id, "responder_id": responder_id, "apparent_technique_id": str(_pending.action_id),
        "apparent_technique_name": BjjHalfGuardCatalog.technique_name(str(_pending.action_id)), "response_ids": response_ids}

# --- Time (unchanged gateway behavior; a window can never open while another is open, so a seal can never be overtaken) ---

func open_window() -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    return _gateway.open_window()

func open_window_for(duration: Variant) -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    return _gateway.open_window_for(duration)

# Existing one-call decision (an exchange or a pass), unchanged semantics, refused while a seal is pending so the sealed intent can
# never be bypassed, cancelled or overtaken.
func submit(window_id: int, fighter_id: String, action_id: String = "", response_id: String = "", commitment: String = "",
        response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    if not _pending.is_empty():
        return _fail("intent_pending")
    return _gateway.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)

# --- Phase 1: seal -----------------------------------------------------------------------------------

# Order: closed session, window state, window identity, gateway context/addressing, initiator, duplicate seal, technique, commitment.
# A refusal depends only on public state and the caller's own command; it changes nothing.
func _seal_error(window_id: int, fighter_id: String, action_id: String, commitment: String) -> String:
    if _closed:
        return "session_closed"
    var window := _gateway.window_fields()
    if not bool(window.open):
        return "no_open_window"
    if window_id != int(window.window_id):
        return "stale_window"
    var menu := _gateway.action_options(fighter_id)
    if not menu.error.is_empty():
        return menu.error
    if fighter_id != str(window.fighter_id):
        return "not_initiator"
    if not _pending.is_empty():
        return "intent_already_sealed"
    var known := false
    for option in menu.options:
        if option.id == action_id:
            known = option.available
    if not known:
        return "unknown_action"
    if not commitment.is_empty() and not BjjCommitment.valid(commitment):
        return "invalid_commitment"
    return ""

# Seals one direct technique with its commitment (empty = the gateway's selected commitment). The report carries the PUBLIC view,
# so the sealing call itself cannot leak anything the responder does not already see.
func seal_intent(window_id: int, fighter_id: String, action_id: String, commitment: String = "") -> BjjMatchWindowGateway.Report:
    var error := _seal_error(window_id, fighter_id, action_id, commitment)
    if not error.is_empty():
        return _fail(error)
    _serial += 1
    _pending = {"window_id": window_id, "intent_serial": _serial, "fighter_id": fighter_id, "action_id": action_id,
        "commitment": _gateway.selected_commitment() if commitment.is_empty() else commitment}
    _events.append({"event": "intent_sealed", "index": _events.size() + 1, "window_id": window_id, "intent_serial": _serial,
        "initiator_id": fighter_id, "apparent_technique_id": action_id, "commitment_requested": str(_pending.commitment)})
    return _done(_public_view())

# --- Phase 2: respond / timeout -------------------------------------------------------------------------

# Shared by respond and the timeout. Order: closed session, window state, window identity, seal, serial. The responder identity
# (respond only; a timeout is applied by the session on behalf of the responder) is checked before the response content, so an
# unauthorized fighter learns nothing about the response menu.
func _pending_error(window_id: int, intent_serial: int) -> String:
    if _closed:
        return "session_closed"
    var window := _gateway.window_fields()
    if not bool(window.open):
        return "no_open_window"
    if window_id != int(window.window_id):
        return "stale_window"
    if _pending.is_empty():
        return "no_sealed_intent"
    if intent_serial != int(_pending.intent_serial) or window_id != int(_pending.window_id):
        return "intent_serial_mismatch"
    return ""

func _responder_error(fighter_id: String) -> String:
    if fighter_id.is_empty():
        return "missing_fighter_id"
    if _gateway.roles().role_of(fighter_id).is_empty():
        return "unknown_fighter"
    if fighter_id == str(_pending.fighter_id):
        return "not_responder"
    return ""

func _content_error(response_id: String, response_commitment: String) -> String:
    var known := false
    var menu := _gateway.response_options(str(_pending.action_id))
    if not menu.error.is_empty():
        return menu.error
    for option in menu.options:
        if option.id == response_id:
            known = option.available
    if not known:
        return "unknown_response"
    if not response_commitment.is_empty() and not BjjCommitment.valid(response_commitment):
        return "invalid_response_commitment"
    return ""

# The responder's committed response. Everything is checked before any mutation; a refusal keeps the seal and the window, so a
# valid retry is possible.
func respond(window_id: int, fighter_id: String, intent_serial: int, response_id: String, response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    var error := _pending_error(window_id, intent_serial)
    if error.is_empty():
        error = _responder_error(fighter_id)
    if error.is_empty():
        error = _content_error(response_id, response_commitment)
    if not error.is_empty():
        return _fail(error)
    return _resolve(fighter_id, response_id, response_commitment, false)

# Session-layer timeout for the responder (Guide 5.2a): the SESSION supplies the published fallback response; this seam only checks
# that it is a legal response for the sealed technique and resolves it exactly like respond, flagged `defaulted`. The protocol
# invents no fallback table (the Half Guard published fallback, GP-5, is an open owner decision) and the clock never decides.
func apply_response_timeout(window_id: int, intent_serial: int, fallback_response_id: String, fallback_response_commitment: String = "") -> BjjMatchWindowGateway.Report:
    var error := _pending_error(window_id, intent_serial)
    if error.is_empty():
        error = _content_error(fallback_response_id, fallback_response_commitment)
    if not error.is_empty():
        return _fail(error)
    var roles_value := _gateway.roles()
    var responder_id := ""
    for role: Variant in roles_value.fighter_by_role:
        if str(roles_value.fighter_by_role[role]) != str(_pending.fighter_id):
            responder_id = str(roles_value.fighter_by_role[role])
    return _resolve(responder_id, fallback_response_id, fallback_response_commitment, true)

# The one resolution path. The unchanged gateway validates once more and applies the single exchange atomically; only after it
# accepted does this object clear the seal and append events. A gateway refusal leaves everything (seal, events, serial) as it was.
func _resolve(responder_id: String, response_id: String, response_commitment: String, defaulted: bool) -> BjjMatchWindowGateway.Report:
    var sealed := _pending.duplicate(true)
    var report := _gateway.submit(int(sealed.window_id), str(sealed.fighter_id), str(sealed.action_id), response_id,
        str(sealed.commitment), response_commitment)
    if not report.ok():
        return _fail(report.error)
    var requested_response := _gateway.selected_commitment() if response_commitment.is_empty() else response_commitment
    _pending = {}
    _events.append({"event": "response_committed", "index": _events.size() + 1, "window_id": int(sealed.window_id),
        "intent_serial": int(sealed.intent_serial), "responder_id": responder_id, "response_id": response_id,
        "response_commitment_requested": requested_response, "defaulted": defaulted})
    _events.append({"event": "exchange_revealed", "index": _events.size() + 1, "window_id": int(sealed.window_id),
        "intent_serial": int(sealed.intent_serial), "initiator_id": str(sealed.fighter_id), "responder_id": responder_id,
        "action_id": str(sealed.action_id), "response_id": response_id, "commitment_requested": str(sealed.commitment),
        "response_commitment_requested": requested_response, "defaulted": defaulted, "kind": str(report.values.kind),
        "settlement": (report.values.detail as Dictionary).settlement.duplicate(true),
        "transition": (report.values.transition as Dictionary).duplicate(true), "ended": bool(report.values.ended)})
    return report

# --- Session end ------------------------------------------------------------------------------------------

# Ends the session. An unresolved seal is DISCARDED, never resolved: no exchange, no charge, no history entry and no clock change.
# After this call every command is refused, so nothing half-committed can reach a later window; the underlying window is
# unreachable because this object owns its gateway. (A seal is irrevocable while the session lives; ending it is not a cancel
# the attacker can use to probe, because nobody can act afterwards.)
func end_session() -> BjjMatchWindowGateway.Report:
    if _closed:
        return _fail("session_closed")
    var discarded := 0 if _pending.is_empty() else int(_pending.intent_serial)
    _pending = {}
    _closed = true
    _events.append({"event": "session_closed", "index": _events.size() + 1, "discarded_intent_serial": discarded})
    return _done({"discarded_intent_serial": discarded})
