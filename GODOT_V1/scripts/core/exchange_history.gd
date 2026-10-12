class_name BjjExchangeHistory
extends RefCounted

# Detached value histories, matching domain/model.py::RunHistory.
# Unsupported controllers never append to their reserved histories.
var top_behavior_history: Array[String] = []
var bottom_behavior_history: Array[String] = []
var initiated_action_history: Array[String] = []
var response_history: Array[String] = []
var raw_grade_history: Array[String] = []
var modified_grade_history: Array[String] = []
var commitment_history: Array[String] = []
var effective_commitment_history: Array[String] = []
var commitment_initiator_history: Array[String] = []
var stamina_requested_history: Array[int] = []
var stamina_charged_history: Array[int] = []
var stamina_shortfall_history: Array[int] = []
var stamina_funding_gap_history: Array[int] = []
var response_requested_commitment_history: Array[String] = []
var response_effective_commitment_history: Array[String] = []
var response_stamina_requested_history: Array[int] = []
var response_stamina_charged_history: Array[int] = []
var response_stamina_shortfall_history: Array[int] = []
var response_stamina_funding_gap_history: Array[int] = []
var response_stamina_waived_history: Array[int] = []
var initiator_commitment_modifier_history: Array[int] = []
var response_undercommitment_modifier_history: Array[int] = []
var recognition_history: Array[String] = []
var submission_feint_cap_history: Array[String] = []
var stamina_band_at_initiation_history: Array[String] = []
var responder_stamina_band_history: Array[String] = []
var initiator_exhaustion_modifier_history: Array[int] = []
var responder_exhaustion_modifier_history: Array[int] = []
var exhaustion_modifier_history: Array[int] = []
var top_behavior_stamina_history: Array[int] = []
var bottom_behavior_stamina_history: Array[int] = []
var reset_window_history: Array[String] = []
var stalling_progress_opportunity_history: Array[String] = []
var stalling_progress_engagement_history: Array[String] = []
var stalling_defensive_engagement_history: Array[String] = []
var stalling_reset_with_route_history: Array[String] = []
var stalling_warning_history: Array[String] = []
var stalling_penalty_history: Array[String] = []
var stalling_position_reset_history: Array[String] = []
var stalling_free_initiative_history: Array[String] = []
var stalling_clock_history: Array[String] = []
var stalling_boundary_history: Array[String] = []
var setup_change_history: Array[String] = []
var setup_consumption_history: Array[String] = []
var submission_attempt_history: Array[String] = []
var submission_change_history: Array[String] = []
var submission_defense_history: Array[String] = []
var submission_hold_responder_side_history: Array[String] = []
var submission_hold_nominal_stamina_history: Array[int] = []
var submission_hold_covered_by_response_history: Array[int] = []
var submission_hold_stamina_requested_history: Array[int] = []
var submission_hold_stamina_charged_history: Array[int] = []
var submission_hold_stamina_shortfall_history: Array[int] = []
var submission_tap_count: int = 0
var top_initiation_count: int = 0
var bottom_initiation_count: int = 0
var clamp_count: int = 0
var escape_threshold_reached: bool = false
var recovery_hold_history: Array[String] = []

func fields() -> Dictionary:
    return {
        "top_behavior_history": top_behavior_history.duplicate(),
        "bottom_behavior_history": bottom_behavior_history.duplicate(),
        "initiated_action_history": initiated_action_history.duplicate(),
        "response_history": response_history.duplicate(),
        "raw_grade_history": raw_grade_history.duplicate(),
        "modified_grade_history": modified_grade_history.duplicate(),
        "commitment_history": commitment_history.duplicate(),
        "effective_commitment_history": effective_commitment_history.duplicate(),
        "commitment_initiator_history": commitment_initiator_history.duplicate(),
        "stamina_requested_history": stamina_requested_history.duplicate(),
        "stamina_charged_history": stamina_charged_history.duplicate(),
        "stamina_shortfall_history": stamina_shortfall_history.duplicate(),
        "stamina_funding_gap_history": stamina_funding_gap_history.duplicate(),
        "response_requested_commitment_history": response_requested_commitment_history.duplicate(),
        "response_effective_commitment_history": response_effective_commitment_history.duplicate(),
        "response_stamina_requested_history": response_stamina_requested_history.duplicate(),
        "response_stamina_charged_history": response_stamina_charged_history.duplicate(),
        "response_stamina_shortfall_history": response_stamina_shortfall_history.duplicate(),
        "response_stamina_funding_gap_history": response_stamina_funding_gap_history.duplicate(),
        "response_stamina_waived_history": response_stamina_waived_history.duplicate(),
        "initiator_commitment_modifier_history": initiator_commitment_modifier_history.duplicate(),
        "response_undercommitment_modifier_history": response_undercommitment_modifier_history.duplicate(),
        "recognition_history": recognition_history.duplicate(),
        "submission_feint_cap_history": submission_feint_cap_history.duplicate(),
        "stamina_band_at_initiation_history": stamina_band_at_initiation_history.duplicate(),
        "responder_stamina_band_history": responder_stamina_band_history.duplicate(),
        "initiator_exhaustion_modifier_history": initiator_exhaustion_modifier_history.duplicate(),
        "responder_exhaustion_modifier_history": responder_exhaustion_modifier_history.duplicate(),
        "exhaustion_modifier_history": exhaustion_modifier_history.duplicate(),
        "top_behavior_stamina_history": top_behavior_stamina_history.duplicate(),
        "bottom_behavior_stamina_history": bottom_behavior_stamina_history.duplicate(),
        "reset_window_history": reset_window_history.duplicate(),
        "stalling_progress_opportunity_history": stalling_progress_opportunity_history.duplicate(),
        "stalling_progress_engagement_history": stalling_progress_engagement_history.duplicate(),
        "stalling_defensive_engagement_history": stalling_defensive_engagement_history.duplicate(),
        "stalling_reset_with_route_history": stalling_reset_with_route_history.duplicate(),
        "stalling_warning_history": stalling_warning_history.duplicate(),
        "stalling_penalty_history": stalling_penalty_history.duplicate(),
        "stalling_position_reset_history": stalling_position_reset_history.duplicate(),
        "stalling_free_initiative_history": stalling_free_initiative_history.duplicate(),
        "stalling_clock_history": stalling_clock_history.duplicate(),
        "stalling_boundary_history": stalling_boundary_history.duplicate(),
        "setup_change_history": setup_change_history.duplicate(),
        "setup_consumption_history": setup_consumption_history.duplicate(),
        "submission_attempt_history": submission_attempt_history.duplicate(),
        "submission_change_history": submission_change_history.duplicate(),
        "submission_defense_history": submission_defense_history.duplicate(),
        "submission_hold_responder_side_history": submission_hold_responder_side_history.duplicate(),
        "submission_hold_nominal_stamina_history": submission_hold_nominal_stamina_history.duplicate(),
        "submission_hold_covered_by_response_history": submission_hold_covered_by_response_history.duplicate(),
        "submission_hold_stamina_requested_history": submission_hold_stamina_requested_history.duplicate(),
        "submission_hold_stamina_charged_history": submission_hold_stamina_charged_history.duplicate(),
        "submission_hold_stamina_shortfall_history": submission_hold_stamina_shortfall_history.duplicate(),
        "submission_tap_count": submission_tap_count,
        "top_initiation_count": top_initiation_count,
        "bottom_initiation_count": bottom_initiation_count,
        "clamp_count": clamp_count,
        "escape_threshold_reached": escape_threshold_reached,
        "recovery_hold_history": recovery_hold_history.duplicate()
    }
