class_name BjjExchangeResult
extends RefCounted

# Historical value data. Mutable result objects never alias authoritative state.
class Request extends RefCounted:
    var action_id: String
    var response_id: String
    var commitment: String
    var response_commitment: String
    # Initiator effort is required; only omitted responder effort has a default.
    func _init(action: String = "", response: String = "", requested: String = "", responder: String = "") -> void:
        action_id = action
        response_id = response
        commitment = requested
        response_commitment = responder
    func fields() -> Dictionary:
        return {"action_id":action_id, "response_id":response_id,
            "commitment":commitment, "response_commitment":response_commitment}

class BandChange extends RefCounted:
    var before: int
    var after: int
    func fields() -> Dictionary:
        return {"before":before, "after":after, "clock_seconds":null}

class Resolution extends RefCounted:
    var initiator: String = ""
    var action_id: String = ""
    var response_id: String = ""
    var raw_grade: int = 0
    var behavior_grade: int = 0
    var final_grade: int = 0
    var behavior_modifier: int = 0
    var positional_modifier: int = 0
    var external_grade_modifier: int = 0
    var grade_value: int = 0
    var axis_before: float = 0.0
    var axis_delta: float = 0.0
    var proposed_axis: float = 0.0
    var axis_after: float = 0.0
    var band_before: int = 0
    var band_after: int = 0
    var floor_clamp_used: bool = false
    var failure_clamp_used: bool = false
    var escape_threshold_reached: bool = false
    var exit_capable_action: bool = false
    var exit_destination: String = ""
    var band_changes: Array[BandChange] = []
    static func from_fields(data: Dictionary) -> Resolution:
        var r := Resolution.new()
        r.initiator = str(data["initiator"])
        r.action_id = str(data["action_id"])
        r.response_id = str(data["response_id"])
        r.raw_grade = int(data["raw_grade"])
        r.behavior_grade = int(data["behavior_grade"])
        r.final_grade = int(data["final_grade"])
        r.behavior_modifier = int(data["behavior_modifier"])
        r.positional_modifier = int(data["positional_modifier"])
        r.external_grade_modifier = int(data["external_grade_modifier"])
        r.grade_value = int(data["grade_value"])
        r.axis_before = float(data["axis_before"])
        r.axis_delta = float(data["axis_delta"])
        r.proposed_axis = float(data["proposed_axis"])
        r.axis_after = float(data["axis_after"])
        r.band_before = int(data["band_before"])
        r.band_after = int(data["band_after"])
        r.floor_clamp_used = bool(data["floor_clamp_used"])
        r.failure_clamp_used = bool(data["failure_clamp_used"])
        r.escape_threshold_reached = bool(data["escape_threshold_reached"])
        r.exit_capable_action = bool(data["exit_capable_action"])
        r.exit_destination = str(data["exit_destination"])
        for change: Dictionary in data.band_changes:
            var c := BandChange.new()
            c.before = int(change.before)
            c.after = int(change.after)
            r.band_changes.append(c)
        return r
    func fields() -> Dictionary:
        var changes: Array[Dictionary] = []
        for c: BandChange in band_changes:
            changes.append(c.fields())
        return {
            "initiator":initiator,
            "action_id":action_id,
            "response_id":response_id,
            "raw_grade":raw_grade,
            "behavior_grade":behavior_grade,
            "final_grade":final_grade,
            "behavior_modifier":behavior_modifier,
            "positional_modifier":positional_modifier,
            "external_grade_modifier":external_grade_modifier,
            "grade_value":grade_value,
            "axis_before":axis_before,
            "axis_delta":axis_delta,
            "proposed_axis":proposed_axis,
            "axis_after":axis_after,
            "band_before":band_before,
            "band_after":band_after,
            "floor_clamp_used":floor_clamp_used,
            "failure_clamp_used":failure_clamp_used,
            "escape_threshold_reached":escape_threshold_reached,
            "exit_capable_action":exit_capable_action,
            "exit_destination":exit_destination,
            "band_changes":changes}

class Snapshot extends RefCounted:
    var axis: float = 0.0
    var control_axis: float = 0.0
    var band: int = 0
    var broken: bool = false
    var initiator: String = ""
    var initial_clock: int = 0
    var clock_seconds: int = 0
    var top_stamina: int = 0
    var bottom_stamina: int = 0
    var top_maximum: int = 0
    var bottom_maximum: int = 0
    var top_band: String = ""
    var bottom_band: String = ""
    var americana_tier: int = 0
    var trap_tier: int = 0
    var submission_stage: String = ""
    var submission_tapped: bool = false
    var exit_destination: String = ""
    var exit_reason: String = ""
    var ended: bool = false
    var crossing_axis: float = 0.0
    func fields() -> Dictionary:
        return {
            "axis":axis,
            "control_axis":control_axis,
            "band":band,
            "broken":broken,
            "initiator":initiator,
            "initial_clock":initial_clock,
            "clock_seconds":clock_seconds,
            "top_stamina":top_stamina,
            "bottom_stamina":bottom_stamina,
            "top_maximum":top_maximum,
            "bottom_maximum":bottom_maximum,
            "top_band":top_band,
            "bottom_band":bottom_band,
            "americana_tier":americana_tier,
            "trap_tier":trap_tier,
            "submission_stage":submission_stage,
            "submission_tapped":submission_tapped,
            "exit_destination":exit_destination,
            "exit_reason":exit_reason,
            "ended":ended,
            "crossing_axis":crossing_axis if broken else null}

var error: String = ""
var initiator: String = ""
var action_id: String = ""
var initiator_funding: BjjStaminaCostPolicy.Funding
var responder_funding: BjjStaminaCostPolicy.Funding
var exhaustion: BjjExhaustionPolicy.Exchange
var initiator_stamina_before: int = 0
var responder_stamina_before: int = 0
var initiator_commitment_modifier: int = 0
var response_undercommitment_modifier: int = 0
var base_resolution: Resolution
var resolution: Resolution
var stamina: BjjStaminaPool.Change
var response_stamina: BjjStaminaPool.Change
var response_stamina_waived: int = 0
var submission_hold_nominal_cost: int = 0
var submission_hold_covered_by_response: int = 0
var submission_hold_stamina: BjjStaminaPool.Change
var outcome: Snapshot

func ok() -> bool:
    return error.is_empty()

func fields() -> Dictionary:
    if not ok():
        return {"error":error}
    return {"attempt":{"initiator":initiator, "action_id":action_id,
            "requested_commitment":initiator_funding.requested, "effective_commitment":initiator_funding.effective},
        "requested_cost":initiator_funding.requested_cost, "effective_cost":initiator_funding.effective_cost,
        "funding_gap":initiator_funding.funding_gap,
        "response_requested_commitment":responder_funding.requested,
        "response_effective_commitment":responder_funding.effective,
        "response_requested_cost":responder_funding.requested_cost,
        "response_effective_cost":responder_funding.effective_cost,
        "response_funding_gap":responder_funding.funding_gap,
        "stamina":stamina.spend_fields(),
        "response_stamina":response_stamina.spend_fields() if response_stamina != null else null,
        "response_stamina_waived":response_stamina_waived,
        "submission_hold_nominal_cost":submission_hold_nominal_cost,
        "submission_hold_covered_by_response":submission_hold_covered_by_response,
        "submission_hold_stamina":submission_hold_stamina.spend_fields() if submission_hold_stamina != null else null,
        "stamina_band_before_action":exhaustion.initiator,
        "responder_stamina_band_before_action":exhaustion.responder,
        "initiator_exhaustion_modifier":exhaustion.initiator_modifier,
        "responder_exhaustion_modifier":exhaustion.responder_modifier,
        "exhaustion_modifier":exhaustion.modifier,
        "initiator_commitment_modifier":initiator_commitment_modifier,
        "response_undercommitment_modifier":response_undercommitment_modifier,
        "base_resolution":base_resolution.fields(), "resolution":resolution.fields(),
        "initiator_stamina_before":initiator_stamina_before, "responder_stamina_before":responder_stamina_before,
        "outcome":outcome.fields()}
