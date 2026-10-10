class_name BjjMountContract
extends BjjPositionContract

# Thin adapter exposing the existing, parity-qualified Mount implementation through
# BjjPositionContract. It wraps a BjjMountMatch by composition: admission, resolution,
# stamina settlement, setup/submission progress, initiative and histories are all
# performed by the unchanged Mount code. This class only (1) maps stable fighter ids
# onto Mount's "top"/"bottom" roles, (2) adds addressing/initiative checks that run
# BEFORE the existing admission, and (3) re-presents results as detached data.
#
# Mount conventions preserved verbatim: the signed axis is positive toward Top control,
# bands are Mount-relative, and Mount's roles never swap while Mount exists. Control
# authority is therefore the Top fighter for the whole life of the position, while
# initiative alternates exactly as the existing match decides it.
#
# Out of scope here (owned by BjjMountMatch, unchanged): clock advancement, RECOVER,
# D3-B windows, RESET and free windows. Those are match orchestration, not position
# responsibilities.
const POSITION_ID: String = "mount"
const ROLE_TOP: String = "top"
const ROLE_BOTTOM: String = "bottom"
const FINISH: String = "mount.top.americana_submission_finish"
const TIER_NAMES: Array[String] = ["None", "Partial", "Ready"]
# Mount's own exit labels -> stable destination ids. These nodes do not exist yet.
const EXIT_DESTINATIONS: Dictionary = {"Half Guard": "half_guard", "Open Guard": "open_guard"}
# "Reversal" is an action overlay in guide v10.4 section 9, not a position node. The
# frozen catalog emits it for Trap-and-Roll; where it lands is an unspecified rule, so
# it is surfaced as an explicit unresolved exit instead of inventing a destination.
const UNRESOLVED_EXITS: Array[String] = ["Reversal"]

var _state: BjjMountMatch
var _top_id: String = ""
var _bottom_id: String = ""

class Creation extends RefCounted:
    var error: String = ""
    var contract: BjjMountContract

    func ok() -> bool:
        return error.is_empty() and contract != null

static func create(state: BjjMountMatch, top_fighter_id: String, bottom_fighter_id: String) -> Creation:
    var result := Creation.new()
    if state == null:
        result.error = "missing_position_state"
        return result
    result.error = BjjPositionContract.fighter_ids_error(top_fighter_id, bottom_fighter_id)
    if not result.error.is_empty():
        return result
    var contract := BjjMountContract.new()
    contract._state = state
    contract._top_id = top_fighter_id
    contract._bottom_id = bottom_fighter_id
    result.contract = contract
    return result

# --- Identity -------------------------------------------------------------------------

func position_id() -> String:
    return POSITION_ID

func fighter_ids() -> Array[String]:
    return [_top_id, _bottom_id]

func _fighter_for_role(role: String) -> String:
    if role == ROLE_TOP:
        return _top_id
    if role == ROLE_BOTTOM:
        return _bottom_id
    return ""

func _role_of_fighter(fighter_id: String) -> String:
    if fighter_id.is_empty():
        return ""
    if fighter_id == _top_id:
        return ROLE_TOP
    if fighter_id == _bottom_id:
        return ROLE_BOTTOM
    return ""

func roles() -> BjjPositionContract.Roles:
    var roles_value := BjjPositionContract.Roles.new()
    roles_value.position_id = POSITION_ID
    roles_value.fighter_by_role = {ROLE_TOP: _top_id, ROLE_BOTTOM: _bottom_id}
    roles_value.control_authority_id = _top_id
    roles_value.initiative_id = _fighter_for_role(_state.initiator) if _state != null else ""
    return roles_value

# --- State views (all detached) --------------------------------------------------------

func state_fields() -> Dictionary:
    return {} if _state == null else _state.snapshot().fields()

func history_fields() -> Dictionary:
    return {} if _state == null else _state.history.fields()

func setup_state() -> Dictionary:
    if _state == null or _state.rules == null or not _state.rules.setup:
        return {}
    return {BjjMountCatalog.TOP_AMERICANA_ARM_ISOLATION: _tier_name(_state.americana_tier),
        BjjMountCatalog.BOTTOM_TRAP_AND_ROLL_ESCAPE: _tier_name(_state.trap_tier)}

func submission_state() -> Dictionary:
    if _state == null or _state.rules == null or not _state.rules.submissions:
        return {}
    return {"action_id": FINISH, "stage": _state.submission_stage, "tapped": _state.submission_tapped}

func _tier_name(tier: int) -> String:
    return TIER_NAMES[tier] if tier >= 0 and tier < TIER_NAMES.size() else ""

func is_terminal() -> bool:
    return _state == null or _state.ended

func commitment_options() -> Array[String]:
    var options: Array[String] = []
    for id: String in BjjCommitment.ORDER:
        options.append(id)
    return options

func transition_destinations() -> Array[String]:
    var destinations: Array[String] = []
    for label: String in EXIT_DESTINATIONS:
        destinations.append(str(EXIT_DESTINATIONS[label]))
    return destinations

# --- Menus -----------------------------------------------------------------------------

func _menu_error() -> String:
    if _state == null:
        return "missing_position_state"
    return _state.validate_context()

func action_options(fighter_id: String) -> BjjPositionContract.OptionList:
    var list := BjjPositionContract.OptionList.new()
    list.error = _menu_error()
    if not list.error.is_empty():
        return list
    if fighter_id.is_empty():
        list.error = "missing_fighter_id"
        return list
    var side := _role_of_fighter(fighter_id)
    if side.is_empty():
        list.error = "unknown_fighter"
        return list
    var has_initiative := side == _state.initiator
    var legal := _state.legal_actions(side).ids
    for id: String in BjjMountCatalog.ENTITIES:
        var entity: Dictionary = BjjMountCatalog.ENTITIES[id]
        if entity.kind == "action" and entity.side == side:
            list.options.append(_action_option(id, has_initiative, legal))
    if side == ROLE_TOP and _state.rules.submissions and _state.rules.setup:
        list.options.append(_action_option(FINISH, has_initiative, legal))
    return list

func _action_option(id: String, has_initiative: bool, legal: Array[String]) -> BjjPositionContract.Option:
    if legal.has(id) and has_initiative:
        return BjjPositionContract.Option.new(id, true, "")
    if not has_initiative:
        return BjjPositionContract.Option.new(id, false, "not_initiator")
    if id == FINISH:
        return BjjPositionContract.Option.new(id, false, "inactive_submission")
    return BjjPositionContract.Option.new(id, false, "setup_not_ready")

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    var list := BjjPositionContract.OptionList.new()
    list.error = _menu_error()
    if not list.error.is_empty():
        return list
    if not _state.legal_actions().ids.has(action_id):
        list.error = "illegal_action"
        return list
    for id: String in BjjMountCatalog.ENTITIES:
        var entity: Dictionary = BjjMountCatalog.ENTITIES[id]
        if entity.kind != "response" or entity.side == _state.initiator:
            continue
        var why := _state.admission_error(BjjExchangeResult.Request.new(action_id, id, BjjCommitment.MEDIUM))
        list.options.append(BjjPositionContract.Option.new(id, why.is_empty(), why))
    return list

# --- Command execution -----------------------------------------------------------------

# Everything here runs before the existing admission and mutates nothing.
func _command_error(command: BjjPositionContract.Command) -> String:
    if command == null:
        return "missing_command"
    if command.position_id.is_empty():
        return "missing_position"
    if command.position_id != POSITION_ID:
        return "unknown_position"
    if _state == null:
        return "missing_position_state"
    var context_error := _state.validate_context()
    if not context_error.is_empty():
        return context_error
    if command.fighter_id.is_empty():
        return "missing_fighter_id"
    if _role_of_fighter(command.fighter_id).is_empty():
        return "unknown_fighter"
    if _fighter_for_role(_state.initiator) != command.fighter_id:
        return "not_initiator"
    return ""

func submit(command: BjjPositionContract.Command) -> BjjPositionContract.Outcome:
    var outcome := BjjPositionContract.Outcome.new()
    outcome.position_id = POSITION_ID
    outcome.error = _command_error(command)
    if not outcome.error.is_empty():
        return outcome
    var request := BjjExchangeResult.Request.new(command.action_id, command.response_id,
        command.commitment, command.response_commitment)
    var result := _state.attempt(request)
    if not result.ok():
        # The existing admission rejects before any authoritative mutation.
        outcome.error = result.error if not result.error.is_empty() else "incomplete_exchange_result"
        return outcome
    outcome.exchange = result.fields()
    outcome.transition = _transition_after(result)
    outcome.state = state_fields()
    return outcome

func _transition_after(result: BjjExchangeResult) -> BjjPositionContract.Transition:
    var transition := BjjPositionContract.Transition.new()
    var raw := result.resolution.exit_destination
    if raw.is_empty():
        return transition
    transition.kind = "exit"
    transition.raw_destination = raw
    if EXIT_DESTINATIONS.has(raw):
        transition.destination_position_id = str(EXIT_DESTINATIONS[raw])
        transition.resolved = true
    return transition
