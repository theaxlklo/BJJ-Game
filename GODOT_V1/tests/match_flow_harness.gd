extends RefCounted

# Deterministic match-flow harness (B1e). It drives the REAL opt-in sealed graph (BjjPositionGraphMatch.create_with_sealed_half_guard) through
# its PUBLIC API only: open_window, submit, seal_intent, public_intent_view, respond, apply_response_timeout, plus the read views. It never
# fabricates a transition, never injects state and never bypasses the gateway; every legal choice comes from the graph's own menus, windows and
# initiative. It adds no game rule: the graph (B1i), Mount (A3/F-series) and Half Guard (B1b-B1h) rules are the baseline and are not retuned here.
#
# Policies are explicitly NAMED, scripted and seeded. A "seeded_legal" policy picks uniformly among LEGAL options with a fixed linear congruential
# generator: it is a reproducible random walk, not an intelligent or balanced player. Nothing here reads a clock or uses Godot's random numbers;
# the same spec always produces the same trace (the trace digest proves it). The measuring entry point and the CI-gated structural test share this
# file so that what is measured is exactly what is verified.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP: String = "fighter_alpha"
const BOTTOM: String = "fighter_bravo"
const CF: String = BjjHalfGuardCatalog.TOP_CROSSFACE
const FL: String = BjjHalfGuardCatalog.TOP_FLATTEN
const KS: String = BjjHalfGuardCatalog.TOP_KNEE_SLICE
const UH: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK
const RG: String = BjjHalfGuardCatalog.BOTTOM_RECOVER_GUARD
const HF: String = BjjHalfGuardCatalog.BOTTOM_HIP_FRAME
const UF: String = BjjHalfGuardCatalog.BOTTOM_UNDERHOOK_FIGHT
const HC: String = BjjHalfGuardCatalog.TOP_HEAD_CONTROL
const HP: String = BjjHalfGuardCatalog.TOP_HIP_PRESSURE
const MOUNT_FINISH: String = "mount.top.americana_submission_finish"
const COMMITMENT_ORDER: Array = ["LOW", "MEDIUM", "HIGH"]

const MOUNT_POLICIES: Array = ["pass_only", "top_direct", "top_finish", "bottom_escape", "bottom_trap_roll", "seeded_legal"]
const MOUNT_DEFENDERS: Array = ["first_available", "last_available", "seeded"]
const HG_ATTACKERS: Array = ["hg_pass", "hg_direct_cycle", "hg_feint_when_eligible", "hg_prep_oriented", "hg_seeded_legal"]
const HG_DEFENDERS: Array = ["bite", "call", "balanced", "fallback", "seeded"]

# Optional observer: Callable(event: String, graph: BjjPositionGraphMatch, info: Dictionary) -> void. It may read and may PROBE (issue commands that must be
# rejected); a rejected command changes nothing, so a run with an observer produces the identical trace.
var observer: Callable = Callable()
var plans: Array = []


class Lcg extends RefCounted:
    var x: int = 0

    func _init(seed: int) -> void:
        x = (seed * 6364136223846793005 + 1442695040888963407) & 0x7fffffffffffffff

    func below(n: int) -> int:
        x = (x * 6364136223846793005 + 1442695040888963407) & 0x7fffffffffffffff
        return (x >> 33) % n


# ---- Construction ------------------------------------------------------------------------------------------------------------------------

static func rules() -> Dictionary:
    var settings := BjjProductionStaminaPolicy.settings()
    settings["enable_v02_setup"] = true
    settings["enable_v03_submissions"] = true
    settings["enable_v04_commitment_semantics"] = true
    return settings


static func plain_rules() -> Dictionary:
    var settings := BjjProductionStaminaPolicy.settings()
    settings["enable_v02_setup"] = true
    settings["enable_v04_commitment_semantics"] = true
    return settings


static func new_graph(extra: Dictionary = {}) -> BjjPositionGraphMatch:
    var configuration := {"rules": rules()}
    configuration.merge(extra, true)
    return BjjPositionGraphMatch.create_with_sealed_half_guard(configuration, TOP, BOTTOM).graph


static func mount_views(gateway: BjjMatchWindowGateway) -> Dictionary:
    return {"state": gateway.state_fields(), "history": gateway.history_fields(), "controller": gateway.controller_fields(), "window": gateway.window_fields(),
        "behavior": gateway.behavior_fields(), "roles": gateway.roles().fields(), "terminal": gateway.is_terminal(), "segment": gateway.carryover_segment().record}


# Every authoritative surface of a graph (read-only; private reads are the test seam): the graph's own views and events, the retained Mount segment, the Half Guard
# gateway and the adopted protocol's executor state. Equality of two fingerprints is "the whole state is unchanged".
static func everything(g: BjjPositionGraphMatch) -> Dictionary:
    return {"status": g.status(), "events": g.events(), "blocked": g.blocked_transition(), "active": g.active_position_id(), "state": g.state_fields(),
        "history": g.history_fields(), "window": g.window_fields(), "roles": g.roles().fields(), "public_events": g.sealed_public_events(),
        "mount": mount_views(g._gateway), "half_guard": g._half_guard.snapshot() if g._half_guard != null else {},
        "protocol": g._sealed.executor_snapshot() if g._sealed != null else {}}


static func strip(report: BjjMatchWindowGateway.Report) -> Dictionary:
    var values := report.values.duplicate(true)
    values.erase("graph")
    return {"error": report.error, "values": values}


# ---- Real Mount entries into Half Guard (the B1d/B1i plan builder), used by the Half Guard populations ----------------------------------------------

func run_plan(g: BjjPositionGraphMatch, plan: Dictionary) -> bool:
    for index in range(int(plan.rounds)):
        var top_round := g.open_window_for(0)
        if not top_round.ok() or not g.submit(top_round.values.window_id, TOP).ok():
            return false
        var bottom_round := g.open_window_for(0)
        if not bottom_round.ok():
            return false
        var bottom_done := g.submit(bottom_round.values.window_id, BOTTOM)
        if not bottom_done.ok() or str(bottom_done.values.transition.raw_destination) != "":
            return false
    var opened := g.open_window_for(0)
    if not opened.ok() or not g.submit(opened.values.window_id, TOP).ok() or not g.open_window_for(0).ok():
        return false
    var tries := 0
    while plan.action == C.BOTTOM_TRAP_AND_ROLL_ESCAPE and not g.action_options(BOTTOM).available_ids().has(plan.action) and tries < 6:
        tries += 1
        var prep := g.submit(g.window_fields().window_id, BOTTOM, C.BOTTOM_BRIDGE, plan.response)
        if not prep.ok() or str(prep.values.transition.raw_destination) != "":
            return false
        var top_window := g.open_window_for(0)
        if not top_window.ok() or not g.submit(top_window.values.window_id, TOP).ok() or not g.open_window_for(0).ok():
            return false
    if not g.action_options(BOTTOM).available_ids().has(plan.action):
        return false
    var exit_report := g.submit(g.window_fields().window_id, BOTTOM, plan.action, plan.response)
    return exit_report.ok() and str(exit_report.values.transition.raw_destination) == plan.label


func plan_graph(plan: Dictionary) -> BjjPositionGraphMatch:
    var extra: Dictionary = (plan.config as Dictionary).duplicate()
    var configuration := {"rules": plain_rules() if plan.rule_set == "plain" else rules()}
    configuration.merge(extra, true)
    var g := BjjPositionGraphMatch.create_with_sealed_half_guard(configuration, TOP, BOTTOM).graph
    return g


# Finds up to `count` distinct real Mount plans that exit to Half Guard (different stamina, interval and rule sets). Deterministic search order.
func find_plans(count: int) -> Array:
    var found: Array = []
    var seen: Dictionary = {}
    for rule_set: String in ["modern", "plain"]:
        for interval: int in [5, 7]:
            for axis: float in [0.2, 0.4, 0.8, 1.5, 3.0]:
                for top_stamina: int in [100, 60, 20]:
                    for bottom_stamina: int in [100, 60, 20]:
                        for action_id: String in [C.BOTTOM_ELBOW_KNEE_ESCAPE, C.BOTTOM_TRAP_AND_ROLL_ESCAPE]:
                            for response_id: String in [C.TOP_RESPONSE_POST_AND_BASE, C.TOP_RESPONSE_WIDE_MOUNT_BASE, C.TOP_RESPONSE_HIP_FOLLOW_REPUMMEL]:
                                for rounds: int in [0, 2]:
                                    if found.size() >= count:
                                        return found
                                    var plan := {"rule_set": rule_set, "config": {"axis": axis, "top_stamina": top_stamina, "bottom_stamina": bottom_stamina,
                                        "interval": interval}, "action": action_id, "response": response_id, "rounds": rounds, "label": "Half Guard"}
                                    var g := plan_graph(plan)
                                    if not run_plan(g, plan) or g.active_position_id() != "half_guard":
                                        continue
                                    var signature := JSON.stringify(g.state_fields()) + JSON.stringify(g.history_fields().initiated_action_history)
                                    if seen.has(signature):
                                        continue
                                    seen[signature] = true
                                    found.append(plan)
    return found


# Identity, resource and time continuity at the moment of a Mount -> Half Guard transition (private read-only seam: the retained Mount segment's record
# against the freshly entered Half Guard snapshot, before any Half Guard window opened). Returns the number of violated facts (0 = continuous).
func continuity_violations(g: BjjPositionGraphMatch) -> int:
    var record: Dictionary = g._gateway.carryover_segment().record
    var snapshot: Dictionary = g._half_guard.snapshot()
    var violations := 0
    if JSON.stringify(snapshot.role_map, "", true, true) != JSON.stringify({"top": TOP, "bottom": BOTTOM}, "", true, true):
        violations += 1
    for role: String in ["top", "bottom"]:
        var id := TOP if role == "top" else BOTTOM
        var carried: Dictionary = record.fighters[role]
        var entered: Dictionary = snapshot.fighters[id]
        if int(carried.stamina_current) != int(entered.stamina_current) or int(carried.stamina_maximum) != int(entered.stamina_maximum) \
                or bool(carried.exhaustion_latched) != bool(entered.exhaustion_latched) or int(carried.behavior_remainder_units) != int(entered.behavior_remainder_units):
            violations += 1
    if int(record.clock.remaining_seconds) != int(snapshot.clock_seconds) or int(record.clock.initial_seconds) != int(snapshot.initial_clock):
        violations += 1
    if int(record.window.last_issued_id) != int(snapshot.window_id) or bool(snapshot.window_open):
        violations += 1
    return violations


# ---- Public-table helpers for the Half Guard defenders (the catalog's published raw grades; nothing is computed by a private rule) -----------------

static func best_counter(side: String, technique: String) -> String:
    var responder := "bottom" if side == "top" else "top"
    var best := ""
    var best_value := 99
    for response: String in BjjHalfGuardCatalog.responses_of(responder):
        var value := int(BjjHalfGuardCatalog.RAW[side][technique][response])
        if value < best_value:
            best_value = value
            best = response
    return best


static func balanced_response(side: String, apparent: String, reals: Array) -> String:
    var responder := "bottom" if side == "top" else "top"
    var best := ""
    var best_worst := 99
    for response: String in BjjHalfGuardCatalog.responses_of(responder):
        var worst := int(BjjHalfGuardCatalog.RAW[side][apparent][response])
        for real: String in reals:
            worst = maxi(worst, int(BjjHalfGuardCatalog.RAW[side][real][response]))
        if worst < best_worst:
            best_worst = worst
            best = response
    return best


# ---- One game ---------------------------------------------------------------------------------------------------------------------------------

func _notify(event: String, g: BjjPositionGraphMatch, info: Dictionary = {}) -> void:
    if observer.is_valid():
        observer.call(event, g, info)


func _rank(commitment: String) -> int:
    return COMMITMENT_ORDER.find(commitment) + 1


func _commit(spec: Dictionary, rng: Lcg) -> String:
    var mode := str(spec.get("commit", "MEDIUM"))
    return COMMITMENT_ORDER[rng.below(3)] if mode == "seeded" else mode


func _pick_response(ids: Array, defender: String, rng: Lcg) -> String:
    if ids.is_empty():
        return ""
    if defender == "last_available":
        return ids[ids.size() - 1]
    if defender == "seeded":
        return ids[rng.below(ids.size())]
    return ids[0]


func _new_record(spec: Dictionary) -> Dictionary:
    return {"windows": 0, "passes": 0, "pass_streak": 0, "longest_pass_streak": 0, "idle_streak": 0, "longest_idle_streak": 0, "mount_holds": 0, "bottom_decision_kinds": {}, "no_progress_streak": 0, "longest_no_progress": 0, "mount_windows": 0,
        "half_guard_windows": 0, "entered_half_guard": false, "entry_window": -1, "entry_clock": -1, "min_top": 100, "min_bottom": 100, "exhausted_top": 0, "exhausted_bottom": 0,
        "downgrades": 0, "axis_min": 99.0, "axis_max": -99.0, "axis_final": 0.0, "axis_samples": 0, "stamina_increases": 0, "stamina_increases_mount": 0, "stamina_increases_half_guard": 0, "exchanges": 0, "mount_exchanges": 0, "half_guard_exchanges": 0, "feint_attempts": 0, "feint_refused": {}, "feints_accepted": 0, "feints_bit": 0,
        "feints_not_bit": 0, "feints_effective": 0, "feints_neutral": 0, "feints_punished": 0, "feint_exits": 0, "feint_capped": 0, "timeouts": 0, "timeout_undercommit": 0,
        "timeout_expected_undercommit": 0, "timeout_other_modifiers": 0, "continuity_checks": 0, "continuity_violations": 0, "policy_errors": [], "trace": [], "stamina_samples": [], "outcome": "",
        "seconds": 0, "initial_clock": 0}


func _fingerprint(g: BjjPositionGraphMatch) -> String:
    var s := g.state_fields()
    if g.active_position_id() == "mount":
        return "m|%s|%s|%s|%s|%s" % [s.axis, s.band, s.americana_tier, s.trap_tier, s.submission_stage]
    return "h|%s|%s|%s|%s" % [s.axis_tenths, s.band, s.top_base, s.bottom_frame]


# Plays one game. `spec`: {mount, mount_defender, hg, defender, commit, seed, max_windows, config, plan (optional real Mount entry)}.
func play(spec: Dictionary) -> Dictionary:
    var rec := _new_record(spec)
    var rng := Lcg.new(int(spec.get("seed", 0)))
    var g: BjjPositionGraphMatch
    if spec.has("plan"):
        g = plan_graph(spec.plan)
        if not run_plan(g, spec.plan):
            rec.policy_errors.append("entry_failed")
            rec["outcome"] = "setup_failed"
            return rec
        rec["entered_half_guard"] = true
        rec["entry_window"] = 0
    else:
        g = new_graph(spec.get("config", {}))
    rec["graph"] = g
    var initial_clock := int(g.state_fields().get("initial_clock", 0))
    rec["initial_clock"] = initial_clock
    rec["entry_clock"] = int(g.state_fields().clock_seconds)
    var start_clock := int(g.state_fields().clock_seconds)
    var fingerprint := _fingerprint(g)
    var previous_position := g.active_position_id()
    var max_windows := int(spec.get("max_windows", 80))
    _notify("game_start", g, {"entered": spec.has("plan")})
    var index := 0
    while index < max_windows and g.status() == "active":
        var opened := g.open_window()
        rec.trace.append({"op": "open", "error": opened.error, "closed": opened.values.get("closed", false), "role": str(opened.values.get("role", "")),
            "window_id": int(opened.values.get("window_id", -1))})
        if not opened.ok():
            rec.policy_errors.append("open:" + opened.error)
            break
        if opened.values.get("closed", false):
            _notify("after_open", g, {"closed": true})
            break
        var wid := int(opened.values.window_id)
        var fighter_id := str(opened.values.fighter_id)
        var role := str(opened.values.role)
        var position := g.active_position_id()
        _notify("after_open", g, {"closed": false, "window_id": wid, "fighter_id": fighter_id, "role": role, "position": position})
        rec.windows += 1
        if position == "mount":
            rec.mount_windows += 1
        else:
            rec.half_guard_windows += 1
        var state := g.state_fields()
        if str(state.get("top_band", "")) == "Exhausted" or bool(state.get("top_latched", false)):
            rec.exhausted_top += 1
        if str(state.get("bottom_band", "")) == "Exhausted" or bool(state.get("bottom_latched", false)):
            rec.exhausted_bottom += 1
        var ok := _decide(g, rec, spec, rng, position, wid, fighter_id, role, index)
        if not ok:
            break
        _notify("after_decision", g, {"window_id": wid, "position": position})
        var after := g.state_fields()
        rec.min_top = mini(rec.min_top, int(after.get("top_stamina", 100)))
        rec.min_bottom = mini(rec.min_bottom, int(after.get("bottom_stamina", 100)))
        # the phase of a sample is the position that was active when the window was decided (a rise inside one position's own rules)
        if not rec.stamina_samples.is_empty():
            var previous: Array = rec.stamina_samples[rec.stamina_samples.size() - 1]
            if int(after.get("top_stamina", 0)) > int(previous[0]) or int(after.get("bottom_stamina", 0)) > int(previous[1]):
                rec.stamina_increases += 1
                if str(previous[2]) == position:
                    rec["stamina_increases_" + position] += 1
        rec.stamina_samples.append([int(after.get("top_stamina", 0)), int(after.get("bottom_stamina", 0)), position])
        # one comparable axis (positive = Top advantage in both positions): Mount `axis`, Half Guard `axis_tenths / 10`
        var axis_now := float(after.axis_tenths) / 10.0 if after.has("axis_tenths") else float(after.axis)
        rec.axis_min = minf(rec.axis_min, axis_now)
        rec.axis_max = maxf(rec.axis_max, axis_now)
        rec.axis_final = axis_now
        rec.axis_samples += 1
        var now_fingerprint := _fingerprint(g)
        if now_fingerprint == fingerprint and g.active_position_id() == previous_position:
            rec.no_progress_streak += 1
        else:
            rec.no_progress_streak = 0
        rec.longest_no_progress = maxi(rec.longest_no_progress, rec.no_progress_streak)
        fingerprint = now_fingerprint
        if g.active_position_id() != previous_position:
            if previous_position == "mount":
                rec["entered_half_guard"] = true
                rec["entry_window"] = rec.windows
                rec["entry_clock"] = int(after.clock_seconds)
                rec.continuity_checks += 1
                rec.continuity_violations += continuity_violations(g)
            previous_position = g.active_position_id()
        index += 1
    # classify the end
    var status := g.status()
    var position_end := g.active_position_id()
    if status == "ended":
        rec["outcome"] = "%s_%s" % [str(g.events().back().reason), position_end]
    elif status == "halted_at_unsupported_transition":
        var blocked := g.blocked_transition()
        rec["outcome"] = "halt_%s:%s" % [str(blocked.from_position_id), str(blocked.label)] + ("" if str(blocked.reason) == "destination_not_implemented" else "(" + str(blocked.reason) + ")")
    else:
        rec["outcome"] = "max_windows_%s" % position_end
    var clock_end := int(g.state_fields().clock_seconds)
    rec["seconds"] = start_clock - clock_end
    rec["position_end"] = position_end
    rec["status"] = status
    rec["clock_end"] = clock_end
    _notify("game_end", g, {"outcome": rec.outcome})
    rec["digest"] = JSON.stringify(rec.trace, "", true, true).sha256_text()
    return rec


func _decide(g: BjjPositionGraphMatch, rec: Dictionary, spec: Dictionary, rng: Lcg, position: String, wid: int, fighter_id: String, role: String, index: int) -> bool:
    if position == "mount":
        return _decide_mount(g, rec, spec, rng, wid, fighter_id, role, index)
    return _decide_half_guard(g, rec, spec, rng, wid, fighter_id, role, index)


func _count_pass(rec: Dictionary) -> void:
    rec.passes += 1
    rec.pass_streak += 1
    rec.longest_pass_streak = maxi(rec.longest_pass_streak, rec.pass_streak)
    rec.idle_streak += 1
    rec.longest_idle_streak = maxi(rec.longest_idle_streak, rec.idle_streak)


# A Mount Bottom decision the production policy resolved as a HOLD (D3-B lockout): accepted, no exchange, no history entry, and the Bottom recovers.
func _count_hold(rec: Dictionary) -> void:
    rec.mount_holds += 1
    rec.pass_streak = 0
    rec.idle_streak += 1
    rec.longest_idle_streak = maxi(rec.longest_idle_streak, rec.idle_streak)


func _count_action(rec: Dictionary) -> void:
    rec.pass_streak = 0
    rec.idle_streak = 0


func _decide_mount(g: BjjPositionGraphMatch, rec: Dictionary, spec: Dictionary, rng: Lcg, wid: int, fighter_id: String, role: String, index: int) -> bool:
    var policy := str(spec.get("mount", "pass_only"))
    var ids: Array = g.action_options(fighter_id).available_ids()
    var action := ""
    var acts := false
    match policy:
        "pass_only":
            acts = false
        "top_direct":
            if role == "top":
                var pool := ids.filter(func(id: String) -> bool: return not id.contains("finish"))
                if not pool.is_empty():
                    action = pool[index % pool.size()]
        "top_finish":
            if role == "top" and not ids.is_empty():
                action = MOUNT_FINISH if ids.has(MOUNT_FINISH) else (C.TOP_AMERICANA_ARM_ISOLATION if ids.has(C.TOP_AMERICANA_ARM_ISOLATION) else ids[0])
        "bottom_escape":
            if role == "bottom" and not ids.is_empty():
                action = C.BOTTOM_ELBOW_KNEE_ESCAPE if ids.has(C.BOTTOM_ELBOW_KNEE_ESCAPE) else (C.BOTTOM_BRIDGE if ids.has(C.BOTTOM_BRIDGE) else ids[0])
        "bottom_trap_roll":
            if role == "bottom" and not ids.is_empty():
                action = C.BOTTOM_TRAP_AND_ROLL_ESCAPE if ids.has(C.BOTTOM_TRAP_AND_ROLL_ESCAPE) else (C.BOTTOM_BRIDGE if ids.has(C.BOTTOM_BRIDGE) else ids[0])
        "seeded_legal":
            var choice := rng.below(ids.size() + 1)
            action = "" if choice == ids.size() else ids[choice]
    var report: BjjMatchWindowGateway.Report
    if action.is_empty():
        report = g.submit(wid, fighter_id)
        _count_pass(rec)
        rec.trace.append({"op": "pass", "position": "mount", "role": role, "error": report.error})
    else:
        var responses: Array = g.response_options(action).available_ids()
        var response := _pick_response(responses, str(spec.get("mount_defender", "first_available")), rng)
        # Mount's production policy selects the Bottom's commitment itself (`commitment_is_policy_selected`); only the Top may request one
        var commitment := _commit(spec, rng) if role == "top" else ""
        report = g.submit(wid, fighter_id, action, response, commitment, "")
        rec.trace.append({"op": "mount_exchange", "role": role, "action": action, "response": response, "commitment": commitment, "error": report.error})
    if not report.ok():
        rec.policy_errors.append("mount_submit:" + report.error)
        return false
    if not action.is_empty():
        # What actually happened is read from the report: a Bottom decision may be a HOLD (no `attempt` in the settlement), never silently an exchange
        if (report.values.detail as Dictionary).has("decision"):
            var decision_kind := str(report.values.detail.decision.kind)
            rec.bottom_decision_kinds[decision_kind] = int(rec.bottom_decision_kinds.get(decision_kind, 0)) + 1
        if (report.values.detail.settlement as Dictionary).has("attempt"):
            _count_action(rec)
            rec.exchanges += 1
            rec.mount_exchanges += 1
            # a commitment is "downgraded" when the funded effective commitment ranks below the requested one (unfunded counts as the lowest rank)
            var settlement: Dictionary = report.values.detail.settlement
            if _rank(str(settlement.attempt.requested_commitment)) > _rank(str(settlement.attempt.effective_commitment)):
                rec.downgrades += 1
            if _rank(str(settlement.get("response_requested_commitment", ""))) > _rank(str(settlement.get("response_effective_commitment", ""))):
                rec.downgrades += 1
        else:
            _count_hold(rec)
    _notify("after_command", g, {"op": "submit", "position": "mount", "report": report})
    return true


# Half Guard attacker policies: returns {apparent, real, commit} or {} for a pass.
func _hg_attack(g: BjjPositionGraphMatch, spec: Dictionary, rng: Lcg, role: String, index: int) -> Dictionary:
    var actions: Array = BjjHalfGuardCatalog.actions_of(role)
    var apparent_feint := CF if role == "top" else UH
    var commit := _commit(spec, rng)
    var state := g.state_fields()
    match str(spec.get("hg", "hg_pass")):
        "hg_pass":
            return {}
        "hg_direct_cycle":
            return {"apparent": actions[index % actions.size()], "real": "", "commit": commit}
        "hg_feint_when_eligible":
            return {"apparent": apparent_feint, "real": str(BjjHalfGuardCatalog.FEINT_PAIRS[apparent_feint].real), "commit": commit, "wants_feint": true}
        "hg_prep_oriented":
            if role == "top":
                return {"apparent": FL if int(state.top_base) < 2 else KS, "real": "", "commit": commit}
            return {"apparent": UH if int(state.bottom_frame) < 2 else RG, "real": "", "commit": commit}
        "hg_seeded_legal":
            var choice := rng.below(actions.size() + 1)
            if choice == actions.size():
                return {}
            var apparent: String = actions[choice]
            var want_feint := apparent == apparent_feint and rng.below(3) == 0
            return {"apparent": apparent, "real": str(BjjHalfGuardCatalog.FEINT_PAIRS[apparent].real) if want_feint else "", "commit": commit, "wants_feint": want_feint}
    return {}


func _hg_defend(spec: Dictionary, rng: Lcg, role: String, view: Dictionary) -> Dictionary:
    var apparent := str(view.apparent_technique_id)
    var reals: Array = view.eligible_real_ids
    var responder_role := "bottom" if role == "top" else "top"
    var ids: Array = view.response_ids
    match str(spec.get("defender", "bite")):
        "bite":
            return {"response": best_counter(role, apparent), "commit": "MEDIUM"}
        "call":
            return {"response": best_counter(role, str(reals[0])) if not reals.is_empty() else best_counter(role, apparent), "commit": "MEDIUM"}
        "balanced":
            return {"response": balanced_response(role, apparent, reals), "commit": "MEDIUM"}
        "fallback":
            return {"fallback": true, "response": str(BjjHalfGuardCatalog.timeout_fallback(responder_role).response_id),
                "commit": str(BjjHalfGuardCatalog.timeout_fallback(responder_role).commitment)}
        "seeded":
            return {"response": ids[rng.below(ids.size())], "commit": COMMITMENT_ORDER[rng.below(3)]}
    return {"response": ids[0], "commit": "MEDIUM"}


func _decide_half_guard(g: BjjPositionGraphMatch, rec: Dictionary, spec: Dictionary, rng: Lcg, wid: int, fighter_id: String, role: String, index: int) -> bool:
    var attack := _hg_attack(g, spec, rng, role, index)
    if attack.is_empty():
        var passed := g.submit(wid, fighter_id)
        _count_pass(rec)
        rec.trace.append({"op": "pass", "position": "half_guard", "role": role, "error": passed.error})
        if not passed.ok():
            rec.policy_errors.append("hg_pass:" + passed.error)
            return false
        _notify("after_command", g, {"op": "submit", "position": "half_guard", "report": passed})
        return true
    var real := str(attack.real)
    var seal := g.seal_intent(wid, fighter_id, str(attack.apparent), str(attack.commit), real)
    if bool(attack.get("wants_feint", false)):
        rec.feint_attempts += 1
    if not seal.ok() and not real.is_empty():
        # a refused feint is a legal outcome of the policy: record why, then play the apparent technique directly
        rec.feint_refused[seal.error] = int(rec.feint_refused.get(seal.error, 0)) + 1
        rec.trace.append({"op": "feint_refused", "role": role, "code": seal.error})
        real = ""
        seal = g.seal_intent(wid, fighter_id, str(attack.apparent), str(attack.commit), "")
    if not seal.ok():
        rec.policy_errors.append("seal:" + seal.error)
        return false
    _notify("after_seal", g, {"window_id": wid, "fighter_id": fighter_id})
    var view: Dictionary = g.public_intent_view().values
    var defence := _hg_defend(spec, rng, role, view)
    var responder_id := BOTTOM if fighter_id == TOP else TOP
    var serial := int(seal.values.intent_serial)
    var done: BjjMatchWindowGateway.Report
    if bool(defence.get("fallback", false)):
        done = g.apply_response_timeout(wid, serial, str(defence.response), str(defence.commit))
    else:
        done = g.respond(wid, responder_id, serial, str(defence.response), str(defence.commit))
    _count_action(rec)
    rec.exchanges += 1
    rec.half_guard_exchanges += 1
    rec.trace.append({"op": "hg_exchange", "role": role, "apparent": str(attack.apparent), "real": real, "commit": str(attack.commit), "response": str(defence.response),
        "response_commit": str(defence.commit), "fallback": bool(defence.get("fallback", false)), "error": done.error})
    if not done.ok():
        rec.policy_errors.append("respond:" + done.error)
        return false
    _notify("after_command", g, {"op": "respond", "position": "half_guard", "report": done})
    var s: Dictionary = done.values.detail.settlement
    if _rank(str(s.commitment_requested)) > _rank(str(s.initiator_effective)):
        rec.downgrades += 1
    if _rank(str(s.response_commitment_requested)) > _rank(str(s.responder_effective)):
        rec.downgrades += 1
    if s.has("feint"):
        rec.feints_accepted += 1
        if bool(s.feint.bit):
            rec.feints_bit += 1
        else:
            rec.feints_not_bit += 1
        var final_grade := int(s.final_grade)
        if final_grade >= 1:
            rec.feints_effective += 1
        elif final_grade == 0:
            rec.feints_neutral += 1
        else:
            rec.feints_punished += 1
        if str(s.exit_destination) != "":
            rec.feint_exits += 1
        if bool(s.feint.exit_capped):
            rec.feint_capped += 1
    if bool(defence.get("fallback", false)):
        rec.timeouts += 1
        # the approved consequence is ONLY the existing undercommitment step: +1 exactly when the attacker's funded commitment outranks the defender's
        var expected := 1 if _rank(str(s.initiator_effective)) > _rank(str(s.responder_effective)) else 0
        rec.timeout_expected_undercommit += expected
        rec.timeout_undercommit += int(s.undercommitment_modifier)
        if int(s.undercommitment_modifier) != expected:
            rec.timeout_other_modifiers += 1
    return true
