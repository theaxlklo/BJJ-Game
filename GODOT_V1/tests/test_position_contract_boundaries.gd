extends SceneTree

# Negative-first contract tests. Every rejected command must leave the authoritative
# match (state, histories, pools, meters) exactly as it was. The positive sections
# prove the contract is a thin view over the unchanged Mount implementation.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const FINISH: String = "mount.top.americana_submission_finish"

var checks: int = 0
var failures: int = 0
var direct_requests: int = 0
var trajectory_operations: int = 0

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func same(label: String, actual: Variant, expected: Variant) -> void:
    # Full-precision structural comparison; both sides come from the same code path,
    # so integer/float typing must match as well.
    checks += 1
    if JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: structures differ" % label)

func modern_rules() -> Dictionary:
    var s := BjjProductionStaminaPolicy.settings()
    s["enable_v02_setup"] = true
    s["enable_v03_submissions"] = true
    s["enable_v04_commitment_semantics"] = true
    return s

func make_match(rules: Dictionary = {}, production: bool = false) -> BjjMountMatch:
    return BjjMountMatch.create({"rules": rules, "production": production}).match_state

func make_contract(state: BjjMountMatch) -> BjjMountContract:
    return BjjMountContract.create(state, TOP_ID, BOTTOM_ID).contract

func fighter_for(role: String) -> String:
    return TOP_ID if role == "top" else BOTTOM_ID

func command(action: String, response: String, commitment: String = "MEDIUM", response_commitment: String = "",
        fighter: String = TOP_ID, position: String = "mount") -> BjjPositionContract.Command:
    return BjjPositionContract.Command.new(position, fighter, action, response, commitment, response_commitment)

func views(contract: BjjMountContract) -> Dictionary:
    return {"state": contract.state_fields(), "history": contract.history_fields(),
        "setup": contract.setup_state(), "submission": contract.submission_state()}

func rejected(label: String, contract: BjjMountContract, state: BjjMountMatch, cmd: BjjPositionContract.Command, expected_error: String) -> void:
    var before := state.lifecycle_fields()
    var before_views := views(contract)
    var o := contract.submit(cmd)
    check(label + " rejected", o.ok(), false)
    check(label + " error", o.error, expected_error)
    check(label + " no exchange data", o.exchange.is_empty(), true)
    check(label + " no transition", o.transition.kind, "none")
    same(label + " authoritative state unchanged", state.lifecycle_fields(), before)
    same(label + " contract views unchanged", views(contract), before_views)

func _initialize() -> void:
    # ---- 1. Fail-closed base contract ------------------------------------------------
    var bare := BjjPositionContract.new()
    check("base position id empty", bare.position_id(), "")
    check("base is terminal", bare.is_terminal(), true)
    check("base submit rejected", bare.submit(command("a", "b")).error, BjjPositionContract.UNIMPLEMENTED)
    check("base actions rejected", bare.action_options(TOP_ID).error, BjjPositionContract.UNIMPLEMENTED)
    check("base responses rejected", bare.response_options("a").error, BjjPositionContract.UNIMPLEMENTED)
    check("base transition rejected", bare.validate_transition("half_guard"), "undeclared_transition_destination")
    check("base no commitments", bare.commitment_options().size(), 0)

    # ---- 2. Missing position state / invalid fighter identity -------------------------
    check("null state rejected", BjjMountContract.create(null, TOP_ID, BOTTOM_ID).error, "missing_position_state")
    var detached := BjjMountContract.new()
    check("unwired adapter submit", detached.submit(command(C.TOP_HIGH_MOUNT_CLIMB, C.BOTTOM_RESPONSE_FOREARM_FRAME)).error, "missing_position_state")
    check("unwired adapter terminal", detached.is_terminal(), true)
    check("unwired adapter actions", detached.action_options(TOP_ID).error, "missing_position_state")
    for pair: Array in [["", BOTTOM_ID], [TOP_ID, ""], [TOP_ID, TOP_ID], [" padded", BOTTOM_ID], [TOP_ID, "bravo "]]:
        check("fighter ids %s rejected" % [pair], BjjMountContract.create(make_match(), pair[0], pair[1]).error, "invalid_fighter_id")
    check("valid ids accepted", BjjMountContract.create(make_match(), TOP_ID, BOTTOM_ID).ok(), true)

    # ---- 3. Command addressing: position, fighter, initiative -------------------------
    var m := make_match(modern_rules())
    var k := make_contract(m)
    var climb := C.TOP_HIGH_MOUNT_CLIMB
    var frame := C.BOTTOM_RESPONSE_FOREARM_FRAME
    check("null command", k.submit(null).error, "missing_command")
    rejected("missing position", k, m, command(climb, frame, "MEDIUM", "", TOP_ID, ""), "missing_position")
    rejected("unknown position", k, m, command(climb, frame, "MEDIUM", "", TOP_ID, "side_control"), "unknown_position")
    rejected("missing fighter", k, m, command(climb, frame, "MEDIUM", "", ""), "missing_fighter_id")
    rejected("unknown fighter", k, m, command(climb, frame, "MEDIUM", "", "ghost"), "unknown_fighter")
    # Initiator is Top: the physically-Bottom fighter does not hold initiative.
    rejected("bottom lacks initiative", k, m, command(C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE, "MEDIUM", "", BOTTOM_ID), "not_initiator")
    # Initiative is distinct from physical role: hand it to Bottom; Top is now rejected.
    m.initiator = "bottom"
    rejected("physical top lacks initiative", k, m, command(climb, frame, "MEDIUM", "", TOP_ID), "not_initiator")
    var bottom_roles := k.roles()
    check("initiative follows bottom", bottom_roles.initiative_id, BOTTOM_ID)
    check("control authority stays with top", bottom_roles.control_authority_id, TOP_ID)
    check("fighter roles", bottom_roles.fighter_by_role, {"top": TOP_ID, "bottom": BOTTOM_ID})
    check("role lookup", bottom_roles.role_of(BOTTOM_ID), "bottom")
    check("role lookup unknown", bottom_roles.role_of("ghost"), "")
    m.initiator = "top"

    # ---- 4. Unknown/illegal actions, invalid responses and commitments ---------------
    rejected("unknown action", k, m, command("mount.top.nonexistent", frame), "unknown_action")
    rejected("wrong-side action", k, m, command(C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE), "incorrect_action_side_or_kind")
    rejected("response as action", k, m, command(frame, frame), "incorrect_action_side_or_kind")
    rejected("unknown response", k, m, command(climb, "mount.bottom_response.nonexistent"), "unknown_response")
    rejected("same-side response", k, m, command(climb, C.TOP_RESPONSE_POST_AND_BASE), "incorrect_response_side_or_kind")
    rejected("action as response", k, m, command(climb, C.BOTTOM_BRIDGE), "incorrect_response_side_or_kind")
    rejected("empty response", k, m, command(climb, ""), "unknown_response")
    for bad: String in ["", "EXTREME", "low"]:
        rejected("invalid commitment '%s'" % bad, k, m, command(climb, frame, bad), "invalid_commitment")
    for bad: String in ["EXTREME", "high"]:
        rejected("invalid response commitment '%s'" % bad, k, m, command(climb, frame, "MEDIUM", bad), "invalid_response_commitment")

    # ---- 5. Missing setup / inactive submission --------------------------------------
    rejected("americana without setup", k, m, command(C.TOP_AMERICANA_ARM_ISOLATION, frame), "setup_not_ready")
    rejected("finish without submission", k, m, command(FINISH, frame), "inactive_submission")
    m.americana_tier = 2
    rejected("ready americana with incompatible response", k, m, command(C.TOP_AMERICANA_ARM_ISOLATION, C.BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE), "incompatible_ready_response")
    m.americana_tier = 0
    m.initiator = "bottom"
    rejected("trap-and-roll without setup", k, m, command(C.BOTTOM_TRAP_AND_ROLL_ESCAPE, C.TOP_RESPONSE_POST_AND_BASE, "MEDIUM", "", BOTTOM_ID), "setup_not_ready")
    m.initiator = "top"
    m.submission_stage = "Threat"
    m.initiator = "bottom"
    rejected("finish by bottom initiator", k, m, command(FINISH, frame, "MEDIUM", "", BOTTOM_ID), "incorrect_finish_initiator")
    m.initiator = "top"
    m.submission_stage = ""
    var raw := make_match()
    var raw_contract := make_contract(raw)
    rejected("finish with submissions disabled", raw_contract, raw, command(FINISH, frame), "inactive_submission")

    # ---- 6. Transition destinations ---------------------------------------------------
    same("declared destinations", k.transition_destinations(), ["half_guard", "open_guard"])
    check("destination accepted", k.validate_transition("half_guard"), "")
    check("destination accepted 2", k.validate_transition("open_guard"), "")
    check("missing destination", k.validate_transition(""), "missing_transition_destination")
    check("side control not declared", k.validate_transition("side_control"), "undeclared_transition_destination")
    check("raw label not a position id", k.validate_transition("Half Guard"), "undeclared_transition_destination")
    check("reversal is not a position", k.validate_transition("reversal"), "undeclared_transition_destination")

    # ---- 7. Terminal states -----------------------------------------------------------
    var ended := make_match(modern_rules())
    var ended_contract := make_contract(ended)
    ended.clock_seconds = 0
    check("timeout terminal", ended_contract.is_terminal(), true)
    rejected("timeout rejects", ended_contract, ended, command(climb, frame), "terminal_exchange")
    check("terminal options rejected", ended_contract.action_options(TOP_ID).error, "terminal_exchange")
    check("terminal responses rejected", ended_contract.response_options(climb).error, "terminal_exchange")
    var tapped := make_match(modern_rules())
    var tapped_contract := make_contract(tapped)
    tapped.submission_tapped = true
    check("tap terminal", tapped_contract.is_terminal(), true)
    rejected("tap rejects", tapped_contract, tapped, command(climb, frame), "terminal_exchange")
    var broken := make_match(modern_rules())
    var broken_contract := make_contract(broken)
    broken.position.break_mount(0.1)
    broken.exit_destination = "Open Guard"
    check("exit terminal", broken_contract.is_terminal(), true)
    rejected("exit rejects", broken_contract, broken, command(climb, frame), "terminal_exchange")
    var wrong_while_terminal := broken_contract.submit(command(climb, frame, "MEDIUM", "", "ghost"))
    check("terminal outranks fighter errors", wrong_while_terminal.error, "terminal_exchange")

    # ---- 8. Roles, options, detachment ------------------------------------------------
    var live := make_match(modern_rules())
    var lk := make_contract(live)
    check("position id", lk.position_id(), "mount")
    same("fighter ids", lk.fighter_ids(), [TOP_ID, BOTTOM_ID])
    same("commitments", lk.commitment_options(), ["LOW", "MEDIUM", "HIGH"])
    var roles := lk.roles()
    check("initial initiative", roles.initiative_id, TOP_ID)
    check("initial control", roles.control_authority_id, TOP_ID)
    check("roles position", roles.position_id, "mount")
    var top_options := lk.action_options(TOP_ID)
    check("top options ok", top_options.ok(), true)
    same("top available == legal_actions", top_options.available_ids(), live.legal_actions("top").ids)
    var reasons: Dictionary = {}
    for option: BjjPositionContract.Option in top_options.options:
        reasons[option.id] = option.reason
    check("americana reason", reasons[C.TOP_AMERICANA_ARM_ISOLATION], "setup_not_ready")
    check("finish reason", reasons[FINISH], "inactive_submission")
    check("climb available", reasons[C.TOP_HIGH_MOUNT_CLIMB], "")
    var bottom_options := lk.action_options(BOTTOM_ID)
    check("bottom options listed", bottom_options.options.size(), 3)
    check("bottom none available", bottom_options.available_ids().size(), 0)
    for option: BjjPositionContract.Option in bottom_options.options:
        check("bottom reason " + option.id, option.reason, "not_initiator")
    check("unknown fighter options", lk.action_options("ghost").error, "unknown_fighter")
    check("missing fighter options", lk.action_options("").error, "missing_fighter_id")
    var response_list := lk.response_options(climb)
    check("responses ok", response_list.ok(), true)
    same("available == legal_responses", response_list.available_ids(), live.legal_responses(climb).ids)
    check("responder-side responses only", response_list.options.size(), 3)
    check("illegal action responses", lk.response_options(C.TOP_AMERICANA_ARM_ISOLATION).error, "illegal_action")
    live.americana_tier = 2
    var ready_responses := lk.response_options(C.TOP_AMERICANA_ARM_ISOLATION)
    check("ready americana responses ok", ready_responses.ok(), true)
    var ready_reason: Dictionary = {}
    for option: BjjPositionContract.Option in ready_responses.options:
        ready_reason[option.id] = option.reason
    check("ready incompatible reason", ready_reason[C.BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE], "incompatible_ready_response")
    check("ready compatible", ready_reason[C.BOTTOM_RESPONSE_FOREARM_FRAME], "")
    check("setup state", lk.setup_state(), {C.TOP_AMERICANA_ARM_ISOLATION: "Ready", C.BOTTOM_TRAP_AND_ROLL_ESCAPE: "None"})
    check("no submission yet", lk.submission_state(), {"action_id": FINISH, "stage": "", "tapped": false})
    check("setup disabled hides tiers", make_contract(make_match()).setup_state(), {})
    check("submissions disabled hide stage", make_contract(make_match()).submission_state(), {})
    # Returned data is detached: mutating it can never reach authoritative state.
    var snapshot := lk.state_fields()
    snapshot["axis"] = 99.0
    snapshot["top_stamina"] = -5
    var history := lk.history_fields()
    history["initiated_action_history"].append("forged")
    check("state detached", lk.state_fields().axis, 1.5)
    check("history detached", lk.history_fields().initiated_action_history.size(), 0)
    var o := lk.submit(command(climb, frame, "HIGH", "LOW"))
    o.exchange["attempt"]["initiator"] = "forged"
    o.state["axis"] = 99.0
    check("outcome detached from match", live.history.initiated_action_history.size(), 1)
    check("axis not forged", live.position.axis != 99.0, true)

    # ---- 9. Same interaction through both entry points -------------------------------
    run_equivalence_sweep()
    # ---- 10. Exit semantics ----------------------------------------------------------
    run_exit_semantics()
    # ---- 11. Full trajectories, replayed ---------------------------------------------
    run_trajectories()

    print("Position contract native: %d assertions, %d failures; %d direct-vs-contract requests, %d trajectory operations" % [
        checks, failures, direct_requests, trajectory_operations])
    quit(0 if failures == 0 else 1)

func configure_context(state: BjjMountMatch, axis: float, initiator: String, americana: int, trap: int, stage: String, stamina: int) -> void:
    state.position.axis = axis
    state.position.band = BjjMountRules.initial_band(axis)
    state.initiator = initiator
    state.americana_tier = americana
    state.trap_tier = trap
    state.submission_stage = stage
    state.top.set_current(stamina)
    state.bottom.set_current(stamina)

func sweep_rule_sets() -> Array[Dictionary]:
    var sets: Array[Dictionary] = [{}, {"enable_v02_setup": true}, {"enable_v02_setup": true, "enable_v03_submissions": true}]
    var modern := modern_rules()
    sets.append(modern)
    return sets

func run_equivalence_sweep() -> void:
    var rule_sets := sweep_rule_sets()
    var configurations: Array[Array] = []
    for index in range(rule_sets.size()):
        configurations.append([rule_sets[index], false])
    configurations.append([modern_rules(), true])
    for configuration: Array in configurations:
        for axis: float in [0.2, 1.5, 3.5]:
            for initiator: String in ["top", "bottom"]:
                for tiers: Array in [[0, 0], [2, 2]]:
                    for stage: String in ["", "Control"]:
                        for stamina: int in [100, 30]:
                            sweep_context(configuration[0], configuration[1], axis, initiator, tiers, stage, stamina)

func sweep_context(rules: Dictionary, production: bool, axis: float, initiator: String, tiers: Array, stage: String, stamina: int) -> void:
    var actions: Array[String] = []
    for id: String in C.ENTITIES:
        if C.ENTITIES[id].kind == "action":
            actions.append(id)
    actions.append(FINISH)
    var responses: Array[String] = []
    for id: String in C.ENTITIES:
        if C.ENTITIES[id].kind == "response":
            responses.append(id)
    var prefix := "sweep rules=%d production=%s axis=%s %s tiers=%s stage=%s stamina=%d" % [rules.size(), production, axis, initiator, tiers, stage, stamina]
    for action: String in actions:
        for response: String in responses:
            for commitment: String in ["MEDIUM", "HIGH"]:
                for response_commitment: String in ["", "LOW"]:
                    var direct := make_match(rules, production)
                    var wrapped := make_match(rules, production)
                    for state: BjjMountMatch in [direct, wrapped]:
                        configure_context(state, axis, initiator, int(tiers[0]), int(tiers[1]), stage, stamina)
                    var k := make_contract(wrapped)
                    var before := wrapped.lifecycle_fields()
                    var result := direct.attempt(BjjExchangeResult.Request.new(action, response, commitment, response_commitment))
                    var outcome := k.submit(command(action, response, commitment, response_commitment, fighter_for(initiator)))
                    direct_requests += 1
                    var label := "%s %s|%s|%s|%s" % [prefix, action, response, commitment, response_commitment]
                    check(label + " admission", outcome.ok(), result.ok())
                    if result.ok():
                        same(label + " exchange fields", outcome.exchange, result.fields())
                        same(label + " outcome state", outcome.state, direct.snapshot().fields())
                        check(label + " transition", outcome.transition.raw_destination, result.resolution.exit_destination)
                    else:
                        check(label + " same rejection", outcome.error, result.error)
                        same(label + " rejection leaves state", wrapped.lifecycle_fields(), before)
                    same(label + " lifecycle", wrapped.lifecycle_fields(), direct.lifecycle_fields())

func run_exit_semantics() -> void:
    # Closure: every raw exit token the frozen catalog can produce is explicitly
    # declared by the adapter (resolved) or explicitly unresolved (Reversal).
    var tokens: Dictionary = {}
    for action: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE, C.BOTTOM_BRIDGE, C.TOP_HIGH_MOUNT_CLIMB]:
        for grade in range(-2, 3):
            for band in range(4):
                var token := BjjMountCatalog.exit_destination(action, grade, band)
                if not token.is_empty():
                    tokens[token] = true
    var expected := ["Half Guard", "Open Guard", "Reversal"]
    var found := tokens.keys()
    found.sort()
    check("catalog exit tokens", found, expected)
    for token: String in found:
        check("token declared: " + token, BjjMountContract.EXIT_DESTINATIONS.has(token) or BjjMountContract.UNRESOLVED_EXITS.has(token), true)
    # Observation: drive real exchanges to each destination through the contract.
    var observed: Dictionary = {}
    for axis in range(1, 16):
        for top_behavior: String in ["PRESSURE", "HOLD"]:
            for bottom_behavior: String in ["ESCAPE", "PROTECT"]:
                for action: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                    for response: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                        for commitment: String in ["LOW", "MEDIUM", "HIGH"]:
                            var state := make_match()
                            configure_context(state, float(axis) / 10.0, "bottom", 0, 0, "", 100)
                            state.top_behavior = top_behavior
                            state.bottom_behavior = bottom_behavior
                            var k := make_contract(state)
                            var outcome := k.submit(command(action, response, commitment, "", BOTTOM_ID))
                            if not outcome.ok() or outcome.transition.kind != "exit":
                                continue
                            var t := outcome.transition
                            observed[t.raw_destination] = true
                            check("exit is terminal", k.is_terminal(), true)
                            check("exit state ended", outcome.state.ended, true)
                            if BjjMountContract.EXIT_DESTINATIONS.has(t.raw_destination):
                                check("resolved " + t.raw_destination, t.resolved, true)
                                check("declared id " + t.raw_destination, k.validate_transition(t.destination_position_id), "")
                            else:
                                check("unresolved " + t.raw_destination, [t.resolved, t.destination_position_id], [false, ""])
                            var again := k.submit(command(action, response, commitment, "", BOTTOM_ID))
                            check("post-exit rejected", again.error, "terminal_exchange")
    var seen := observed.keys()
    seen.sort()
    check("every exit destination observed through the contract", seen, expected)

func lcg(seed_value: int) -> int:
    return (seed_value * 1103515245 + 12345) & 0x7fffffff

func run_trajectories() -> void:
    var configurations: Array[Array] = [[{}, false], [modern_rules(), false], [modern_rules(), true]]
    for configuration: Array in configurations:
        for top_behavior: String in ["PRESSURE", "HOLD", "CONSERVE"]:
            for bottom_behavior: String in ["ESCAPE", "PROTECT", "CONSERVE"]:
                for seed_value in [1, 7, 42, 2026]:
                    var first := play_trajectory(configuration[0], configuration[1], top_behavior, bottom_behavior, seed_value)
                    var second := play_trajectory(configuration[0], configuration[1], top_behavior, bottom_behavior, seed_value)
                    same("replay %s/%s/%d" % [top_behavior, bottom_behavior, seed_value], first, second)

func play_trajectory(rules: Dictionary, production: bool, top_behavior: String, bottom_behavior: String, seed_value: int) -> Dictionary:
    var direct := make_match(rules, production)
    var wrapped := make_match(rules, production)
    for state: BjjMountMatch in [direct, wrapped]:
        state.top_behavior = top_behavior
        state.bottom_behavior = bottom_behavior
    var k := make_contract(wrapped)
    var exchanges: Array[Dictionary] = []
    var rng := seed_value
    for step in range(400):
        # Lifecycle (clock, drift, RECOVER) stays on the match; both twins use it identically.
        var wa := direct.next_window()
        var wb := wrapped.next_window()
        same("trajectory window %d" % step, wb.fields(), wa.fields())
        if not wa.ok() or direct.ended:
            break
        var side := direct.initiator
        var menu := k.action_options(fighter_for(side))
        same("trajectory actions %d" % step, menu.available_ids(), direct.legal_actions().ids)
        var ids := direct.legal_actions().ids
        if ids.is_empty():
            break
        rng = lcg(rng)
        var action: String = ids[rng % ids.size()]
        var legal := direct.legal_responses(action).ids
        same("trajectory responses %d" % step, k.response_options(action).available_ids(), legal)
        if legal.is_empty():
            break
        rng = lcg(rng)
        var response: String = legal[rng % legal.size()]
        rng = lcg(rng)
        var commitment: String = BjjCommitment.ORDER[rng % 3]
        rng = lcg(rng)
        var response_commitment: String = ["", "LOW", "MEDIUM", "HIGH"][rng % 4]
        var result := direct.attempt(BjjExchangeResult.Request.new(action, response, commitment, response_commitment))
        var outcome := k.submit(command(action, response, commitment, response_commitment, fighter_for(side)))
        trajectory_operations += 1
        check("trajectory admission %d" % step, outcome.ok(), result.ok())
        if result.ok():
            same("trajectory exchange %d" % step, outcome.exchange, result.fields())
            exchanges.append(outcome.exchange)
        same("trajectory lifecycle %d" % step, wrapped.lifecycle_fields(), direct.lifecycle_fields())
        if direct.ended:
            break
    same("trajectory final history", k.history_fields(), direct.history.fields())
    return {"exchanges": exchanges, "final": wrapped.lifecycle_fields()}
