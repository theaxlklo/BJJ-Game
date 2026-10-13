class_name BjjPositionContract
extends RefCounted

# Position-independent contract (guide v10.4 section 7), deliberately narrow.
#
# Four concepts stay separate and are never inferred from one another:
#   * fighter identity  - a stable fighter id chosen by the owning match;
#   * physical role     - a position-local label (Mount: "top", "bottom");
#   * control authority - which fighter owns the positive/control side of the
#                         position's signed axis;
#   * initiative        - which fighter holds the current decision window.
# Initiative moving is NOT a reversal, a position change or a score.
#
# This base class is an interface, not an engine. Every virtual fails closed, so a
# position that forgets to implement one cannot silently accept a command. Positions
# own their resolvers, stamina policies and controllers; the contract only exposes
# them. All returned data is detached: mutating it never reaches authoritative state.
const UNIMPLEMENTED: String = "unimplemented_position_contract"

# --- Value types ---------------------------------------------------------------------

class Roles extends RefCounted:
    var position_id: String = ""
    var fighter_by_role: Dictionary = {}
    var control_authority_id: String = ""
    var initiative_id: String = ""

    func role_of(fighter_id: String) -> String:
        for role: Variant in fighter_by_role:
            if fighter_by_role[role] == fighter_id:
                return str(role)
        return ""

    func fields() -> Dictionary:
        return {"position_id": position_id, "fighter_by_role": fighter_by_role.duplicate(),
            "control_authority_id": control_authority_id, "initiative_id": initiative_id}

# One entry of a legal-action or legal-response menu. `id` is a stable technique id.
# `reason` is a stable machine-readable code and is empty when the option is available.
class Option extends RefCounted:
    var id: String = ""
    var available: bool = false
    var reason: String = ""

    func _init(option_id: String = "", is_available: bool = false, why: String = "") -> void:
        id = option_id
        available = is_available
        reason = why

    func fields() -> Dictionary:
        return {"id": id, "available": available, "reason": reason}

class OptionList extends RefCounted:
    var error: String = ""
    var options: Array[Option] = []

    func ok() -> bool:
        return error.is_empty()

    func available_ids() -> Array[String]:
        var ids: Array[String] = []
        for option: Option in options:
            if option.available:
                ids.append(option.id)
        return ids

    func fields() -> Dictionary:
        if not ok():
            return {"error": error}
        var rows: Array[Dictionary] = []
        for option: Option in options:
            rows.append(option.fields())
        return {"options": rows}

# One decision. `position_id` addresses the contract; `fighter_id` is the submitting
# fighter and must currently hold initiative. The other fighter is the responder.
class Command extends RefCounted:
    var position_id: String
    var fighter_id: String
    var action_id: String
    var response_id: String
    var commitment: String
    var response_commitment: String

    func _init(position: String = "", fighter: String = "", action: String = "", response: String = "",
            requested: String = "", responder: String = "") -> void:
        position_id = position
        fighter_id = fighter
        action_id = action
        response_id = response
        commitment = requested
        response_commitment = responder

    func fields() -> Dictionary:
        return {"position_id": position_id, "fighter_id": fighter_id, "action_id": action_id,
            "response_id": response_id, "commitment": commitment, "response_commitment": response_commitment}

# What an accepted command did to the position graph. kind is "none" or "exit".
# `raw_destination` is the position's own label. `destination_position_id` is set only
# when that label maps to a declared, stable destination; otherwise `resolved` is false
# and the owner of the position graph must decide (see POSITION_CONTRACT.md).
class Transition extends RefCounted:
    var kind: String = "none"
    var raw_destination: String = ""
    var destination_position_id: String = ""
    var resolved: bool = false

    func fields() -> Dictionary:
        return {"kind": kind, "raw_destination": raw_destination,
            "destination_position_id": destination_position_id, "resolved": resolved}

class Outcome extends RefCounted:
    var error: String = ""
    var position_id: String = ""
    var exchange: Dictionary = {}
    var transition: Transition = Transition.new()
    var state: Dictionary = {}

    func ok() -> bool:
        return error.is_empty()

    func fields() -> Dictionary:
        if not ok():
            return {"error": error}
        return {"position_id": position_id, "exchange": exchange.duplicate(true),
            "transition": transition.fields(), "state": state.duplicate(true)}

# --- Shared validation ---------------------------------------------------------------

# Stable fighter ids: two distinct, non-empty ids without surrounding whitespace.
static func fighter_ids_error(first: String, second: String) -> String:
    for id: String in [first, second]:
        if id.is_empty() or id.strip_edges() != id:
            return "invalid_fighter_id"
    if first == second:
        return "invalid_fighter_id"
    return ""

# --- Virtual interface (fail closed) --------------------------------------------------

func position_id() -> String:
    return ""

func fighter_ids() -> Array[String]:
    return []

func roles() -> Roles:
    return Roles.new()

# Detached, position-local state (axis, bands, stamina, clock, setup, submission, exit).
func state_fields() -> Dictionary:
    return {}

# Detached append-only histories of every exchange accepted so far.
func history_fields() -> Dictionary:
    return {}

# Detached setup tiers keyed by stable technique id. Empty when the position has none.
func setup_state() -> Dictionary:
    return {}

# Detached submission progress. Empty when the position has no submission route.
func submission_state() -> Dictionary:
    return {}

func is_terminal() -> bool:
    return true

# Menu for a fighter: unavailable options carry a reason instead of disappearing.
func action_options(_fighter_id: String) -> OptionList:
    var list := OptionList.new()
    list.error = UNIMPLEMENTED
    return list

func response_options(_action_id: String) -> OptionList:
    var list := OptionList.new()
    list.error = UNIMPLEMENTED
    return list

func commitment_options() -> Array[String]:
    return []

# Stable position ids this position may hand control to.
func transition_destinations() -> Array[String]:
    return []

# Validates a destination against the declared set. Used by whatever owns the graph.
func validate_transition(destination_position_id: String) -> String:
    if destination_position_id.is_empty():
        return "missing_transition_destination"
    if not transition_destinations().has(destination_position_id):
        return "undeclared_transition_destination"
    return ""

# Executes one decision atomically: either it is rejected with no mutation at all, or
# it is accepted exactly as the position's existing entry point would accept it.
func submit(_command: Command) -> Outcome:
    var outcome := Outcome.new()
    outcome.error = UNIMPLEMENTED
    return outcome
