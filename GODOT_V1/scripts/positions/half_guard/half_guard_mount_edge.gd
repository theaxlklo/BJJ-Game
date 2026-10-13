class_name BjjHalfGuardMountEdge
extends RefCounted

# Mount -> Half Guard edge adapter (B1c; HALF_GUARD_V0_PROPOSAL.md section 5.2). Pure and static: it takes a Mount carry-over
# segment (A3b) and a caller-supplied interval and returns a detached neutral entry request for BjjHalfGuardEntry. It reads
# no Mount object, builds no match and owns no state, so it cannot mutate its input or any position. Nothing here starts Half
# Guard: the graph transition is a later slice (B1d).
#
# The record's role-keyed fighter state is re-keyed by FIGHTER ID (POSITION_TOPOLOGY section 6.2): stamina and behavior
# remainder follow the fighter, never the role label. This edge declares the identity role map (D1): Mount Top -> Half Guard
# Top, Mount Bottom -> Half Guard Bottom. D3-B state is not carried (Half Guard v0 has no D3-B controller).
const SOURCE_POSITION_ID: String = BjjMountContract.POSITION_ID
const RAW_DESTINATION: String = "Half Guard"
const DESTINATION_POSITION_ID: String = BjjHalfGuardRules.POSITION_ID

const E_NOT_AN_EXIT: String = "mount_edge_not_an_exit"
const E_UNRESOLVED_EXIT: String = "mount_edge_unresolved_exit"
const E_WRONG_DESTINATION: String = "mount_edge_wrong_destination"
const E_TAPPED: String = "mount_edge_submission_tapped"

class Result extends RefCounted:
    var error: String = "incomplete_edge_request"
    var request: Dictionary = {}
    func ok() -> bool:
        return error.is_empty()

static func _failed(code: String) -> Result:
    var result := Result.new()
    result.error = code
    return result

# Stable error code and no request on any refusal. Record errors are BjjMountCarryover's own codes (the whole record is
# validated first, so a malformed record never reaches an edge decision); edge refusals use the codes above; interval and
# entry-level problems use BjjHalfGuardEntry's codes. The request is validated by BjjHalfGuardEntry before it is returned.
static func entry_from_record(record: Variant, interval_seconds: Variant) -> Result:
    var record_error := BjjMountCarryover.validate_segment(record)
    if not record_error.is_empty():
        return _failed(record_error)
    var segment: Dictionary = record
    # validate_segment guarantees: terminal.ended == (remaining == 0 or tapped or exited) and an exit leaves remaining >= 1,
    # so an exit record is always ended with time left and "not ended" / "zero clock" cannot reach the decisions below.
    var exit_block: Dictionary = segment.exit
    if exit_block.kind != "exit":
        return _failed(E_NOT_AN_EXIT)
    if not exit_block.resolved:
        return _failed(E_UNRESOLVED_EXIT)
    if exit_block.raw_destination != RAW_DESTINATION or exit_block.destination_position_id != DESTINATION_POSITION_ID:
        return _failed(E_WRONG_DESTINATION)
    if segment.terminal.submission_tapped:
        return _failed(E_TAPPED)
    var top_id: String = segment.fighter_by_role.top
    var bottom_id: String = segment.fighter_by_role.bottom
    var fighters: Dictionary = {}
    # Keyed by fighter id; each id is looked up through the record's own role mapping.
    for role: String in BjjMountCarryover.ROLES:
        var id: String = segment.fighter_by_role[role]
        var source: Dictionary = segment.fighters[role]
        fighters[id] = {"stamina_current": source.stamina_current, "stamina_maximum": source.stamina_maximum,
            "exhaustion_latched": source.exhaustion_latched, "behavior_remainder_units": source.behavior_remainder_units}
    var request := {
        "role_map": {"top": top_id, "bottom": bottom_id},
        "fighters": fighters,
        "clock": {"initial_seconds": segment.clock.initial_seconds, "remaining_seconds": segment.clock.remaining_seconds},
        "window": {"last_issued_id": segment.window.last_issued_id},
        "interval_seconds": interval_seconds,
    }
    var entry_error := BjjHalfGuardEntry.validate(request)
    if not entry_error.is_empty():
        return _failed(entry_error)
    var result := Result.new()
    result.error = ""
    result.request = request
    return result
