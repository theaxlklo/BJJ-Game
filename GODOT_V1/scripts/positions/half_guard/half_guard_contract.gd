class_name BjjHalfGuardContract
extends BjjPositionContract

# Thin position-contract adapter over the single Half Guard match owner (compare BjjMountContract). It maps the stable fighter ids
# onto the "top"/"bottom" role labels, runs addressing and initiative checks BEFORE the match's own admission, and re-presents
# results as detached data. Windows and the clock are the gateway's concern; `submit` is the low-level exchange (the match's
# `attempt`) and needs an explicit, valid commitment, exactly as the Mount contract does.
const POSITION_ID: String = BjjHalfGuardRules.POSITION_ID
const ROLE_TOP: String = "top"
const ROLE_BOTTOM: String = "bottom"

var _state: BjjHalfGuardMatch

class Creation extends RefCounted:
    var error: String = ""
    var contract: BjjHalfGuardContract
    func ok() -> bool:
        return error.is_empty() and contract != null

static func create(state: BjjHalfGuardMatch) -> Creation:
    var result := Creation.new()
    if state == null:
        result.error = "missing_position_state"
        return result
    result.error = BjjPositionContract.fighter_ids_error(state.top_id, state.bottom_id)
    if not result.error.is_empty():
        return result
    var contract := BjjHalfGuardContract.new()
    contract._state = state
    result.contract = contract
    return result

# --- Identity ---------------------------------------------------------------------------------

func position_id() -> String:
    return POSITION_ID

func fighter_ids() -> Array[String]:
    return [_state.top_id, _state.bottom_id]

func roles() -> BjjPositionContract.Roles:
    var roles_value := BjjPositionContract.Roles.new()
    roles_value.position_id = POSITION_ID
    roles_value.fighter_by_role = {ROLE_TOP: _state.top_id, ROLE_BOTTOM: _state.bottom_id}
    roles_value.control_authority_id = _state.authority_id()
    roles_value.initiative_id = _state.top_id if _state.initiator == ROLE_TOP else _state.bottom_id if _state.initiator == ROLE_BOTTOM else ""
    return roles_value

func state_fields() -> Dictionary:
    return {} if _state == null else _state.state_fields()

func history_fields() -> Dictionary:
    return {} if _state == null else _state.history_fields()

func is_terminal() -> bool:
    return _state == null or _state.is_ended()

func commitment_options() -> Array[String]:
    var options: Array[String] = []
    for id: String in BjjCommitment.ORDER:
        options.append(id)
    return options

func transition_destinations() -> Array[String]:
    var destinations: Array[String] = []
    for label: String in BjjHalfGuardCatalog.EXIT_DESTINATIONS:
        destinations.append(str(BjjHalfGuardCatalog.EXIT_DESTINATIONS[label]))
    return destinations

# --- Menus --------------------------------------------------------------------------------------

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
    var side := _state.role_of(fighter_id)
    if side.is_empty():
        list.error = "unknown_fighter"
        return list
    for id: String in BjjHalfGuardCatalog.actions_of(side):
        # Every technique is always legal in v0: there are no setup or submission gates, only initiative.
        list.options.append(BjjPositionContract.Option.new(id, side == _state.initiator, "" if side == _state.initiator else "not_initiator"))
    return list

func response_options(action_id: String) -> BjjPositionContract.OptionList:
    var list := BjjPositionContract.OptionList.new()
    list.error = _menu_error()
    if not list.error.is_empty():
        return list
    if not BjjHalfGuardCatalog.actions_of(_state.initiator).has(action_id):
        list.error = "illegal_action"
        return list
    var responder := "bottom" if _state.initiator == ROLE_TOP else ROLE_TOP
    for id: String in BjjHalfGuardCatalog.responses_of(responder):
        list.options.append(BjjPositionContract.Option.new(id, true, ""))
    return list

# --- Command execution ------------------------------------------------------------------------

# Everything here runs before the match's own admission and mutates nothing.
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
    if _state.role_of(command.fighter_id).is_empty():
        return "unknown_fighter"
    if _state.role_of(command.fighter_id) != _state.initiator:
        return "not_initiator"
    return ""

func submit(command: BjjPositionContract.Command) -> BjjPositionContract.Outcome:
    var outcome := BjjPositionContract.Outcome.new()
    outcome.position_id = POSITION_ID
    outcome.error = _command_error(command)
    if not outcome.error.is_empty():
        return outcome
    var attempted := _state.attempt(command.action_id, command.response_id, command.commitment, command.response_commitment)
    if not attempted.ok():
        outcome.error = attempted.error
        return outcome
    outcome.exchange = attempted.values.duplicate(true)
    outcome.transition = transition_for(_state.exit_destination)
    outcome.state = state_fields()
    return outcome

# Single mapping from a Half Guard exit label to the contract's Transition (shared with the gateway through the catalog).
static func transition_for(raw: String) -> BjjPositionContract.Transition:
    var fields := BjjHalfGuardCatalog.transition_fields(raw)
    var transition := BjjPositionContract.Transition.new()
    transition.kind = str(fields.kind)
    transition.raw_destination = str(fields.raw_destination)
    transition.destination_position_id = str(fields.destination_position_id)
    transition.resolved = bool(fields.resolved)
    return transition
