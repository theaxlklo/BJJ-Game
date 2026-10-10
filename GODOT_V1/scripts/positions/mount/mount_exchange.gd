class_name BjjMountExchange
extends RefCounted

# Exchange-only port of engine/match.py::MountMatch.attempt(). No clock advancement,
# recovery, Recognition, stalling, scoring, reset, or full-match aggregate.
# Context is supplied by an owning simulation; all admission checks precede mutation.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const FINISH: String = "mount.top.americana_submission_finish"
const STAGES: Array[String] = ["Threat", "Control", "Finish"]
const TIERS: Array[String] = ["None", "Partial", "Ready"]
const GRADE_NAMES: Array[String] = ["Strong Failure", "Failure", "Contested", "Success", "Strong Success"]

var rules: BjjExchangeRules = BjjExchangeRules.new()
var cost_policy: BjjStaminaCostPolicy = BjjStaminaCostPolicy.defaults()
var top: BjjStaminaPool = BjjStaminaPool.new()
var bottom: BjjStaminaPool = BjjStaminaPool.new()
var position: BjjMountPosition = BjjMountPosition.new()
var history: BjjExchangeHistory = BjjExchangeHistory.new()
var initiator: String = "top"
var initial_clock: int = BjjMountRules.DEFAULT_CLOCK_SECONDS
var clock_seconds: int = BjjMountRules.DEFAULT_CLOCK_SECONDS
var top_behavior: String = "PRESSURE"
var bottom_behavior: String = "ESCAPE"
var americana_tier: int = 0
var trap_tier: int = 0
var submission_stage: String = ""
var submission_tapped: bool = false
var exit_destination: String = ""
var exit_reason: String = ""

static func process(state: BjjMountExchange, request: BjjExchangeResult.Request) -> BjjExchangeResult:
    if state == null:
        var missing := BjjExchangeResult.new()
        missing.error = "missing_state"
        return missing
    return state.attempt(request)

func validate_context(allow_finished_advance: bool = false) -> String:
    if rules == null or cost_policy == null or position == null or history == null:
        return "missing_configuration_or_state"
    if top == null or bottom == null:
        return "missing_stamina_pool"
    if top == bottom:
        return "aliased_fighter_pools"
    for pool: BjjStaminaPool in [top, bottom]:
        if pool.maximum <= 0 or pool.maximum > BjjStaminaPool.MAXIMUM_EXACT or pool.current < 0 or pool.current > pool.maximum:
            return "invalid_stamina_state"
        if (pool.current <= pool.exhaustion_enter_threshold and pool.band != "Exhausted") or (
                pool.current >= pool.exhaustion_recover_threshold and pool.band == "Exhausted"):
            return "invalid_exhaustion_latch"
    if initiator != "top" and initiator != "bottom":
        return "invalid_initiator"
    if initial_clock <= 0 or initial_clock > BjjStaminaPool.MAXIMUM_EXACT or clock_seconds < 0 or clock_seconds > initial_clock:
        return "invalid_clock_context"
    # User-approved safety boundary differs from three Python terminal anomalies.
    if ((clock_seconds == 0 or submission_tapped) and not allow_finished_advance) or position.broken or not exit_destination.is_empty():
        return "terminal_exchange"
    if not is_finite(position.axis) or not BjjMountRules.axis_can_have_band(position.axis, position.band):
        return "invalid_mount_context"
    if not ["PRESSURE", "HOLD", "CONSERVE"].has(top_behavior) or not ["ESCAPE", "PROTECT", "CONSERVE"].has(bottom_behavior):
        return "invalid_behavior"
    if americana_tier < 0 or americana_tier > 2 or trap_tier < 0 or trap_tier > 2:
        return "invalid_setup_context"
    if not submission_stage.is_empty() and not STAGES.has(submission_stage):
        return "invalid_submission_stage"
    return ""

func _validate(request: BjjExchangeResult.Request) -> String:
    if request == null:
        return "missing_request"
    var context_error := validate_context()
    if not context_error.is_empty():
        return context_error
    if not BjjCommitment.valid(request.commitment):
        return "invalid_commitment"
    # Frozen legacy path ignores the optional response commitment entirely.
    if rules.v04 and not request.response_commitment.is_empty() and not BjjCommitment.valid(request.response_commitment):
        return "invalid_response_commitment"
    # Typed integer exchange costs. Primitive bool compatibility stays separate;
    # Python bool-as-int spend serialization is outside this admission contract.
    for id: String in BjjCommitment.ORDER:
        var f := cost_policy.determine(id, top.maximum)
        if not f.ok() or f.fields().requested_cost is bool:
            return "unsupported_cost_policy"
    var action_id := request.action_id
    if action_id == FINISH:
        if not rules.submissions or not rules.setup or submission_stage.is_empty():
            return "inactive_submission"
        if initiator != "top":
            return "incorrect_finish_initiator"
    else:
        if not C.ENTITIES.has(action_id):
            return "unknown_action"
        var action: Dictionary = C.ENTITIES[action_id]
        if action.kind != "action" or action.side != initiator:
            return "incorrect_action_side_or_kind"
        if rules.setup and _is_target(action_id) and _tier(action_id) != 2:
            return "setup_not_ready"
    if not C.ENTITIES.has(request.response_id):
        return "unknown_response"
    var response: Dictionary = C.ENTITIES[request.response_id]
    if response.kind != "response" or response.side == initiator:
        return "incorrect_response_side_or_kind"
    if action_id == FINISH or (rules.setup and _is_target(action_id) and _tier(action_id) == 2):
        if action_id == C.BOTTOM_TRAP_AND_ROLL_ESCAPE:
            if not [C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL].has(request.response_id):
                return "incompatible_ready_response"
        elif not [C.BOTTOM_RESPONSE_FOREARM_FRAME, C.BOTTOM_RESPONSE_TURN_IN_RECOVERY].has(request.response_id):
            return "incompatible_ready_response"
    var proxy_id := C.TOP_AMERICANA_ARM_ISOLATION if action_id == FINISH else action_id
    if not C.RAW_GRADES.has(proxy_id + "|" + request.response_id):
        return "unsupported_matchup"
    return ""

func attempt(request: BjjExchangeResult.Request) -> BjjExchangeResult:
    var r := BjjExchangeResult.new()
    r.error = _validate(request)
    if not r.error.is_empty():
        return r
    # Capture all historical authority before initiative flips or either charge.
    r.initiator = initiator
    r.action_id = request.action_id
    var attacker := top if initiator == "top" else bottom
    var defender := bottom if initiator == "top" else top
    r.initiator_stamina_before = attacker.current
    r.responder_stamina_before = defender.current
    r.exhaustion = BjjExhaustionPolicy.exchange(attacker.band, defender.band)
    r.initiator_funding = cost_policy.determine(request.commitment, attacker.current)
    r.responder_funding = BjjStaminaCostPolicy.Funding.new()
    if rules.v04:
        var requested := BjjCommitment.MEDIUM if request.response_commitment.is_empty() else request.response_commitment
        r.responder_funding = cost_policy.determine(requested, defender.current)
    var ready := rules.setup and _is_target(request.action_id) and _tier(request.action_id) == 2
    var stage_before := submission_stage
    r.base_resolution = _resolve(request, 0, ready)
    r.resolution = r.base_resolution if r.exhaustion.modifier == 0 else _resolve(request, r.exhaustion.modifier, ready)
    if rules.v04:
        r.initiator_commitment_modifier = _magnitude(r.initiator_funding.effective, r.resolution.final_grade)
        r.response_undercommitment_modifier = 1 if _rank(r.responder_funding.effective) < _rank(r.initiator_funding.effective) else 0
        var magnitude_grade := BjjGrade.shift(r.resolution.final_grade, r.initiator_commitment_modifier)
        var final_grade := BjjGrade.shift(magnitude_grade, r.response_undercommitment_modifier)
        if r.initiator_commitment_modifier != 0 or r.response_undercommitment_modifier != 0:
            # Re-resolve using actual sequential target, not the sum of shifts.
            r.resolution = _resolve(request, final_grade - r.base_resolution.final_grade, ready)
    _apply_resolution(r.resolution)
    _apply_setup(request.action_id, r.resolution, ready)
    _apply_submission(r, ready, stage_before)
    # Reference order: initiator -> response commitment -> supplemental/legacy hold.
    r.stamina = attacker.spend_up_to(r.initiator_funding.effective_cost)
    if rules.v04:
        var response_cost := r.responder_funding.effective_cost
        if rules.rule1 and r.initiator_funding.effective.is_empty():
            r.response_stamina_waived = response_cost
            response_cost = 0
        r.response_stamina = defender.spend_up_to(response_cost)
    var hold := r.resolution.final_grade == BjjGrade.CONTESTED and (
        request.action_id == FINISH or (rules.submissions and request.action_id == C.TOP_AMERICANA_ARM_ISOLATION and ready))
    if hold:
        r.submission_hold_nominal_cost = cost_policy.determine(BjjCommitment.LOW, defender.maximum).requested_cost
        var hold_request := r.submission_hold_nominal_cost
        if rules.rule1 and r.initiator_funding.effective.is_empty():
            hold_request = 0
        elif rules.rule2 and not r.initiator_funding.effective.is_empty():
            var response_charged := r.response_stamina.charged if r.response_stamina != null else 0
            r.submission_hold_covered_by_response = mini(r.submission_hold_nominal_cost, response_charged)
            hold_request = maxi(0, r.submission_hold_nominal_cost - response_charged)
        r.submission_hold_stamina = defender.spend_up_to(hold_request)
    _record_settlement(r)
    r.outcome = snapshot()
    return r

static func _rank(commitment: String) -> int:
    return BjjCommitment.ORDER.find(commitment) + 1

static func _magnitude(commitment: String, grade: int) -> int:
    if commitment == BjjCommitment.HIGH:
        if grade == BjjGrade.SUCCESS:
            return 1
        if grade == BjjGrade.FAILURE:
            return -1
    if commitment == BjjCommitment.LOW or commitment.is_empty():
        if grade == BjjGrade.STRONG_SUCCESS:
            return -1
        if grade == BjjGrade.STRONG_FAILURE:
            return 1
    return 0

func _resolve(request: BjjExchangeResult.Request, modifier: int, ready: bool) -> BjjExchangeResult.Resolution:
    var finish := request.action_id == FINISH
    var proxy := C.TOP_AMERICANA_ARM_ISOLATION if finish else request.action_id
    var override_grade := 99
    if ready and ((proxy == C.TOP_AMERICANA_ARM_ISOLATION and request.response_id == C.BOTTOM_RESPONSE_TURN_IN_RECOVERY) or (
            proxy == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and request.response_id == C.TOP_RESPONSE_WIDE_MOUNT_BASE)):
        override_grade = BjjGrade.CONTESTED
    var data := BjjMountResolver.resolve_action(position.axis, position.band, initiator, proxy, request.response_id,
        top_behavior, bottom_behavior, modifier, 99 if finish else override_grade)
    var r := BjjExchangeResult.Resolution.from_fields(data)
    if finish:
        r.action_id = FINISH
        r.proposed_axis = BjjMountRules.round_ten(position.reported_axis() - 1.0) if BjjGrade.failed(r.final_grade) else position.reported_axis()
        r.axis_after = BjjMountRules.clamp_axis(r.proposed_axis)
        r.axis_delta = BjjMountRules.round_ten(r.axis_after - position.reported_axis())
        var update := BjjMountRules.update_band(r.axis_after, position.band)
        r.band_after = int(update.band)
        r.band_changes.clear()
        for change: Dictionary in update.changes:
            var c := BjjExchangeResult.BandChange.new()
            c.before = int(change.before)
            c.after = int(change.after)
            r.band_changes.append(c)
        r.floor_clamp_used = false
        r.failure_clamp_used = false
        r.escape_threshold_reached = false
        r.exit_capable_action = false
        r.exit_destination = ""
    return r

static func _is_target(action: String) -> bool:
    return action == C.TOP_AMERICANA_ARM_ISOLATION or action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE

func _tier(action: String) -> int:
    if action == C.TOP_AMERICANA_ARM_ISOLATION:
        return americana_tier
    if action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE:
        return trap_tier
    return -1 # Not a setup target. Never interpret another action as Trap-and-Roll.

func _apply_resolution(r: BjjExchangeResult.Resolution) -> void:
    history.initiated_action_history.append(r.action_id)
    history.response_history.append(r.response_id)
    history.raw_grade_history.append(_grade_name(r.raw_grade))
    history.modified_grade_history.append(_grade_name(r.final_grade))
    if r.initiator == "top":
        history.top_initiation_count += 1
    else:
        history.bottom_initiation_count += 1
    history.clamp_count += int(r.failure_clamp_used) + int(r.floor_clamp_used)
    history.escape_threshold_reached = history.escape_threshold_reached or r.escape_threshold_reached
    if not r.exit_destination.is_empty():
        position.break_mount(r.axis_after)
        exit_destination = r.exit_destination
        exit_reason = "%s reached the escape threshold with final grade %s" % [C.ENTITIES[r.action_id].name, _grade_name(r.final_grade)]
    else:
        position.apply_control(r.axis_after, r.band_after)
        initiator = "bottom" if r.initiator == "top" else "top"

func _apply_setup(action: String, r: BjjExchangeResult.Resolution, ready: bool) -> void:
    if not rules.setup:
        return
    var absorbed := r.proposed_axis > r.axis_after + 0.000000000001 and absf(r.axis_after-r.axis_before) <= 0.000000000001
    var target := ""
    if action == C.TOP_HIGH_MOUNT_CLIMB:
        target = C.TOP_AMERICANA_ARM_ISOLATION
    elif action == C.BOTTOM_BRIDGE:
        target = C.BOTTOM_TRAP_AND_ROLL_ESCAPE
    if not target.is_empty() and not absorbed and _tier(target) < 2:
        var before := _tier(target)
        if target == C.TOP_AMERICANA_ARM_ISOLATION:
            americana_tier += 1
        else:
            trap_tier += 1
        history.setup_change_history.append("%s->%s:%s->%s" % [action,target,TIERS[before],TIERS[before+1]])
    if ready:
        if action == C.TOP_AMERICANA_ARM_ISOLATION:
            americana_tier = 0
        else:
            trap_tier = 0
        history.setup_consumption_history.append(action + ":Ready->None")

func _apply_submission(r: BjjExchangeResult, ready: bool, stage_before: String) -> void:
    if not rules.submissions:
        return
    var resolution := r.resolution
    if r.action_id == C.TOP_AMERICANA_ARM_ISOLATION and ready and resolution.initiator == "top" and (
            resolution.band_before == BjjMountRules.Band.STRONG or resolution.band_before == BjjMountRules.Band.LOCKED) and BjjGrade.successful(resolution.final_grade):
        var before_label := "None" if submission_stage.is_empty() else "SubmissionStage." + submission_stage.to_upper()
        submission_stage = "Threat"
        history.submission_change_history.append("entry:" + before_label + "->Threat")
        return
    if r.action_id != FINISH:
        return
    history.submission_attempt_history.append(stage_before)
    if BjjGrade.successful(resolution.final_grade) and rules.v04 and r.initiator_funding.requested == BjjCommitment.LOW:
        history.submission_change_history.append("%s->%s:feint-capped" % [stage_before,stage_before])
        var effective := r.initiator_funding.effective if not r.initiator_funding.effective.is_empty() else "UNFUNDED"
        history.submission_feint_cap_history.append("%s@%ds:requested=LOW:effective=%s" % [stage_before,initial_clock-clock_seconds,effective])
        return
    if BjjGrade.successful(resolution.final_grade):
        var index := STAGES.find(stage_before)
        if index == 2:
            submission_tapped = true
            exit_reason = "TAP — Americana"
            history.submission_tap_count += 1
            history.submission_change_history.append(stage_before + "->Tap")
        else:
            submission_stage = STAGES[index+1]
            history.submission_change_history.append(stage_before + "->" + submission_stage)
    elif BjjGrade.failed(resolution.final_grade):
        submission_stage = ""
        history.submission_change_history.append(stage_before + "->None:defended")
        history.submission_defense_history.append("%s->None:%s:%s->%s" % [stage_before,_grade_name(resolution.final_grade),
            _signed_axis(resolution.axis_before),_signed_axis(resolution.axis_after)])
    elif resolution.final_grade == BjjGrade.CONTESTED:
        history.submission_change_history.append("%s->%s:held" % [stage_before,stage_before])

static func _signed_axis(value: float) -> String:
    return ("+" if value >= 0.0 else "") + ("%.2f" % value)

static func _grade_name(grade: int) -> String:
    return GRADE_NAMES[grade+2]

func _record_settlement(r: BjjExchangeResult) -> void:
    var a := r.initiator_funding
    history.commitment_history.append(a.requested)
    history.effective_commitment_history.append(a.effective if not a.effective.is_empty() else "UNFUNDED")
    history.commitment_initiator_history.append(r.initiator)
    history.stamina_requested_history.append(a.requested_cost)
    history.stamina_charged_history.append(r.stamina.charged)
    history.stamina_shortfall_history.append(r.stamina.shortfall)
    history.stamina_funding_gap_history.append(a.funding_gap)
    if rules.v04:
        var b := r.responder_funding
        history.response_requested_commitment_history.append(b.requested)
        history.response_effective_commitment_history.append(b.effective if not b.effective.is_empty() else "UNFUNDED")
        history.response_stamina_requested_history.append(b.requested_cost)
        history.response_stamina_charged_history.append(r.response_stamina.charged)
        history.response_stamina_shortfall_history.append(r.response_stamina.shortfall)
        history.response_stamina_funding_gap_history.append(b.funding_gap)
        history.response_stamina_waived_history.append(r.response_stamina_waived)
        history.initiator_commitment_modifier_history.append(r.initiator_commitment_modifier)
        history.response_undercommitment_modifier_history.append(r.response_undercommitment_modifier)
    history.stamina_band_at_initiation_history.append(r.exhaustion.initiator)
    history.responder_stamina_band_history.append(r.exhaustion.responder)
    history.initiator_exhaustion_modifier_history.append(r.exhaustion.initiator_modifier)
    history.responder_exhaustion_modifier_history.append(r.exhaustion.responder_modifier)
    history.exhaustion_modifier_history.append(r.exhaustion.modifier)
    if r.submission_hold_stamina != null:
        history.submission_hold_responder_side_history.append("bottom" if r.initiator == "top" else "top")
        history.submission_hold_nominal_stamina_history.append(r.submission_hold_nominal_cost)
        history.submission_hold_covered_by_response_history.append(r.submission_hold_covered_by_response)
        history.submission_hold_stamina_requested_history.append(r.submission_hold_stamina.requested)
        history.submission_hold_stamina_charged_history.append(r.submission_hold_stamina.charged)
        history.submission_hold_stamina_shortfall_history.append(r.submission_hold_stamina.shortfall)

func snapshot() -> BjjExchangeResult.Snapshot:
    var s := BjjExchangeResult.Snapshot.new()
    if position != null:
        s.axis = position.reported_axis()
        s.control_axis = position.axis
        s.band = position.band
        s.broken = position.broken
        s.crossing_axis = position.crossing_axis
    s.initiator = initiator
    s.initial_clock = initial_clock
    s.clock_seconds = clock_seconds
    if top != null:
        s.top_stamina = top.current
        s.top_maximum = top.maximum
        s.top_band = top.band
    if bottom != null:
        s.bottom_stamina = bottom.current
        s.bottom_maximum = bottom.maximum
        s.bottom_band = bottom.band
    s.americana_tier = americana_tier
    s.trap_tier = trap_tier
    s.submission_stage = submission_stage
    s.submission_tapped = submission_tapped
    s.exit_destination = exit_destination
    s.exit_reason = exit_reason
    s.ended = clock_seconds <= 0 or s.broken or submission_tapped
    return s
