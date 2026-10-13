class_name BjjFighterSnapshotAdapter
extends RefCounted

# Read-only, fighter-keyed views of a live Mount source (F0): a BjjMatchWindowGateway or, since F1,
# a BjjPositionGraphMatch. Both expose the same public read views (roles(), state_fields(),
# behavior_fields()); the adapter never reaches the gateway behind a graph. The Mount match stays
# the ONLY owner of stamina, exhaustion, behavior, roles, initiative and time; this adapter holds
# no second copy of any of it. It keeps the source reference and plain-string identity metadata
# copied from the definitions at creation (so later edits to a shared Resource cannot change
# an existing view), and builds a fresh, detached Dictionary per fighter on every call.
#
# It reads only public gateway views (roles(), state_fields(), behavior_fields()). It never
# touches private match/pool/controller state and never uses carryover_segment(), which
# correctly refuses an open window. Sourcing is Mount-specific (role-prefixed stamina fields);
# a later position supplies its own mapping instead of subclassing fighters per position.
const ROLES: Array[String] = ["top", "bottom"]

var _source: Variant
var _identity: Dictionary = {}
var _fighter_ids: Array[String] = []

class Creation extends RefCounted:
    var error: String = ""
    var adapter: BjjFighterSnapshotAdapter
    func ok() -> bool:
        return error.is_empty() and adapter != null


# `source` is a BjjMatchWindowGateway or a BjjPositionGraphMatch; anything else is refused with
# missing_gateway (the original F0 code). `definitions` maps each of the source's two stable
# fighter ids to a BjjFighterDefinition. The keys must equal the source's fighter ids exactly. The SAME definition may back both
# fighters. Validation runs before anything is stored; nothing here mutates the gateway.
# Codes, in order: missing_gateway, invalid_definitions, invalid_fighter_id_key,
# unknown_fighter_id, missing_fighter_definition, invalid_fighter_definition, then the
# definition's own validation_error().
static func create(source: Variant, definitions: Variant) -> Creation:
    var result := Creation.new()
    if not (source is BjjMatchWindowGateway or source is BjjPositionGraphMatch):
        result.error = "missing_gateway"
        return result
    if not definitions is Dictionary:
        result.error = "invalid_definitions"
        return result
    var gateway_ids: Array[String] = _source_ids(source)
    for key: Variant in definitions:
        if typeof(key) != TYPE_STRING:
            result.error = "invalid_fighter_id_key"
            return result
    for key: String in definitions:
        if not gateway_ids.has(key):
            result.error = "unknown_fighter_id"
            return result
    for fighter_id: String in gateway_ids:
        if not definitions.has(fighter_id):
            result.error = "missing_fighter_definition"
            return result
    var identity: Dictionary = {}
    for fighter_id: String in gateway_ids:
        var definition: Variant = definitions[fighter_id]
        if not definition is BjjFighterDefinition:
            result.error = "invalid_fighter_definition"
            return result
        var problem: String = definition.validation_error()
        if not problem.is_empty():
            result.error = problem
            return result
        identity[fighter_id] = {"definition_id": String(definition.definition_id), "display_name": String(definition.display_name)}
    var adapter := BjjFighterSnapshotAdapter.new()
    adapter._source = source
    adapter._identity = identity
    adapter._fighter_ids = gateway_ids
    result.adapter = adapter
    return result


# The two stable fighter ids, sorted: a deterministic order that never depends on roles.
func fighter_ids() -> Array[String]:
    return _fighter_ids.duplicate()


# A fresh, detached Dictionary keyed by fighter id on every call. Each value holds only plain
# data: fighter_id, definition_id, display_name, role, stamina_current, stamina_maximum,
# exhaustion_band, behavior. Safe before a window, while one is open and after a decision.
func snapshots() -> Dictionary:
    return _build(_source.roles(), _source.state_fields(), _source.behavior_fields(), _identity)


# Pure mapping, separate from the gateway so the identity rules are testable with synthetic
# roles. Roles resolve by fighter id through `roles.fighter_by_role`, never by array order or
# display name. Returns {} (refusal) if the roles do not name exactly the known fighters;
# a fighter named in both roles collapses to one entry, which the size check refuses.
static func _build(roles: BjjPositionContract.Roles, state: Dictionary, behaviors: Dictionary, identity: Dictionary) -> Dictionary:
    var result: Dictionary = {}
    for role: String in ROLES:
        var fighter_id: String = str(roles.fighter_by_role.get(role, ""))
        if fighter_id.is_empty() or not identity.has(fighter_id):
            return {}
        var who: Dictionary = identity[fighter_id]
        result[fighter_id] = {
            "fighter_id": fighter_id,
            "definition_id": who.definition_id,
            "display_name": who.display_name,
            "role": role,
            "stamina_current": state["%s_stamina" % role],
            "stamina_maximum": state["%s_maximum" % role],
            "exhaustion_band": state["%s_band" % role],
            "behavior": behaviors[role],
        }
    if result.size() != identity.size():
        return {}
    return result


static func _source_ids(source: Variant) -> Array[String]:
    var ids: Array[String] = []
    var mapping: Dictionary = source.roles().fighter_by_role
    for role: String in ROLES:
        ids.append(str(mapping.get(role, "")))
    ids.sort()
    return ids
