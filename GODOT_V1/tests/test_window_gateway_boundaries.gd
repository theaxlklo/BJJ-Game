extends SceneTree

# Negative-first tests for BjjMatchWindowGateway. Every rejected call must leave match
# state, histories, the D3-B controller and the window record exactly as they were. The
# trajectory section drives the gateway in lockstep with a twin driven only through the
# unchanged BjjMountMatch entry points (next_window / bottom_decision / attempt /
# reset_window), which the Python oracle suites already qualify.
const C = preload("res://scripts/positions/mount/mount_catalog.gd")
const TOP_ID: String = "fighter_alpha"
const BOTTOM_ID: String = "fighter_bravo"
const FINISH: String = "mount.top.americana_submission_finish"

var checks: int = 0
var failures: int = 0
var trajectory_operations: int = 0
var tally: Dictionary = {}

func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if actual != expected:
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, actual, expected])

func same(label: String, actual: Variant, expected: Variant) -> void:
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

func config(extra: Dictionary = {}) -> Dictionary:
    var c := {"rules": modern_rules()}
    c.merge(extra, true)
    return c

func make(extra: Dictionary = {}) -> BjjMatchWindowGateway:
    return BjjMatchWindowGateway.create(config(extra), TOP_ID, BOTTOM_ID).gateway

func everything(g: BjjMatchWindowGateway) -> Dictionary:
    return {"state": g.state_fields(), "history": g.history_fields(), "controller": g.controller_fields(),
        "window": g.window_fields(), "lifecycle": g._match.lifecycle_fields()}

func rejected_submit(label: String, g: BjjMatchWindowGateway, expected_error: String, window_id: int, fighter: String,
        action: String = "", response: String = "", commitment: String = "", response_commitment: String = "") -> void:
    var before := everything(g)
    var r := g.submit(window_id, fighter, action, response, commitment, response_commitment)
    check(label + " rejected", r.ok(), false)
    check(label + " error", r.error, expected_error)
    check(label + " no values", r.values.is_empty(), true)
    same(label + " unchanged", everything(g), before)

func rejected_open(label: String, g: BjjMatchWindowGateway, expected_error: String, duration: Variant = null) -> void:
    var before := everything(g)
    var r := g.open_window_for(duration)
    check(label + " rejected", r.ok(), false)
    check(label + " error", r.error, expected_error)
    same(label + " unchanged", everything(g), before)

# Top window -> Top RESET -> Bottom window, all in zero simulated time.
func to_bottom_window(g: BjjMatchWindowGateway) -> Dictionary:
    var o := g.open_window_for(0)
    check("to_bottom open top", o.ok() and o.values.role == "top", true)
    var t := g.submit(o.values.window_id, TOP_ID)
    check("to_bottom top reset", t.ok() and t.values.kind == "reset", true)
    var b := g.open_window_for(0)
    check("to_bottom open bottom", b.ok() and b.values.role == "bottom", true)
    return b.values

func _initialize() -> void:
    # ---- 1. Construction ---------------------------------------------------------------
    for pair: Array in [["", BOTTOM_ID], [TOP_ID, ""], [TOP_ID, TOP_ID], [" a", BOTTOM_ID]]:
        check("fighter ids %s" % [pair], BjjMatchWindowGateway.create(config(), pair[0], pair[1]).error, "invalid_fighter_id")
    check("production cannot be disabled", BjjMatchWindowGateway.create(config({"production": false}), TOP_ID, BOTTOM_ID).error, "production_configuration_required")
    check("raw rules are not production", BjjMatchWindowGateway.create({}, TOP_ID, BOTTOM_ID).ok(), false)
    check("unknown configuration", BjjMatchWindowGateway.create(config({"bogus": 1}), TOP_ID, BOTTOM_ID).ok(), false)
    check("valid creation", BjjMatchWindowGateway.create(config(), TOP_ID, BOTTOM_ID).ok(), true)
    var caller_config := config()
    BjjMatchWindowGateway.create(caller_config, TOP_ID, BOTTOM_ID)
    check("caller configuration not mutated", caller_config.has("production"), false)

    # ---- 2. No window yet: nothing may be submitted --------------------------------------
    var g := make()
    check("fresh window closed", g.window_fields().open, false)
    check("D3-B selected", g._match.d3b != null, true)
    rejected_submit("no window", g, "no_open_window", 0, TOP_ID, C.TOP_HIGH_MOUNT_CLIMB, C.BOTTOM_RESPONSE_FOREARM_FRAME)
    rejected_submit("no window id 1", g, "no_open_window", 1, TOP_ID)

    # ---- 3. Opening: time admission -------------------------------------------------------
    rejected_open("negative duration", g, "invalid_window_request", -1)
    rejected_open("float duration", g, "invalid_duration", 1.5)
    rejected_open("string duration", g, "invalid_duration", "5")
    var opened := g.open_window()
    check("open default interval", opened.ok(), true)
    check("window opened for top", opened.values.fighter_id, TOP_ID)
    check("window id 1", opened.values.window_id, 1)
    check("default interval advanced clock", g.state_fields().clock_seconds, 295)
    check("selected commitment reported", opened.values.commitment, "MEDIUM")
    # A second open before a decision would grant an extra window and extra time.
    rejected_open("double open", g, "window_already_open", 5)
    rejected_open("double open zero", g, "window_already_open", 0)
    rejected_submit("top no-action with commitment", g, "commitment_without_action", 1, TOP_ID, "", "", "HIGH")
    rejected_submit("top no-action with response commitment", g, "commitment_without_action", 1, TOP_ID, "", "", "", "LOW")
    check("clock unchanged by double open", g.state_fields().clock_seconds, 295)

    # ---- 4. Submission admission (all before any mutation) --------------------------------
    var climb := C.TOP_HIGH_MOUNT_CLIMB
    var frame := C.BOTTOM_RESPONSE_FOREARM_FRAME
    rejected_submit("stale low id", g, "stale_window", 0, TOP_ID, climb, frame)
    rejected_submit("stale future id", g, "stale_window", 2, TOP_ID, climb, frame)
    rejected_submit("stale negative id", g, "stale_window", -1, TOP_ID, climb, frame)
    rejected_submit("missing fighter", g, "missing_fighter_id", 1, "", climb, frame)
    rejected_submit("unknown fighter", g, "unknown_fighter", 1, "ghost", climb, frame)
    rejected_submit("wrong fighter bottom at top window", g, "not_initiator", 1, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    rejected_submit("response without action", g, "response_without_action", 1, TOP_ID, "", frame)
    rejected_submit("unknown action", g, "unknown_action", 1, TOP_ID, "nope", frame)
    rejected_submit("wrong side action", g, "incorrect_action_side_or_kind", 1, TOP_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    rejected_submit("unknown response", g, "unknown_response", 1, TOP_ID, climb, "nope")
    rejected_submit("missing response", g, "unknown_response", 1, TOP_ID, climb, "")
    rejected_submit("wrong side response", g, "incorrect_response_side_or_kind", 1, TOP_ID, climb, C.TOP_RESPONSE_POST_AND_BASE)
    rejected_submit("invalid commitment", g, "invalid_commitment", 1, TOP_ID, climb, frame, "EXTREME")
    rejected_submit("invalid response commitment", g, "invalid_response_commitment", 1, TOP_ID, climb, frame, "", "EXTREME")
    rejected_submit("setup not ready", g, "setup_not_ready", 1, TOP_ID, C.TOP_AMERICANA_ARM_ISOLATION, frame)
    rejected_submit("inactive finish", g, "inactive_submission", 1, TOP_ID, FINISH, C.BOTTOM_RESPONSE_TURN_IN_RECOVERY)
    # Corrupted match context is caught before the owners are called.
    g._match.initiator = "bottom"
    rejected_submit("window initiator changed externally", g, "window_initiator_changed", 1, TOP_ID, climb, frame)
    g._match.initiator = "top"
    g._match.top_behavior = "ESCAPE"
    rejected_submit("invalid behavior context", g, "invalid_behavior", 1, TOP_ID, climb, frame)
    g._match.top_behavior = "PRESSURE"

    # ---- 5. Accept once; replay, duplicate and stale are rejected -------------------------
    var before_accept := everything(g)
    var accepted := g.submit(1, TOP_ID, climb, frame)
    check("top exchange accepted", accepted.ok(), true)
    check("top exchange kind", accepted.values.kind, "top_exchange")
    check("window closed after decision", g.window_fields().open, false)
    check("initiative moved to bottom", g.roles().initiative_id, BOTTOM_ID)
    check("control authority stays top", g.roles().control_authority_id, TOP_ID)
    check("history grew once", g.history_fields().initiated_action_history.size(), 1)
    check("top commitment defaulted to selected", g.history_fields().commitment_history, ["MEDIUM"])
    check("before was a different state", everything(g) != before_accept, true)
    var after_accept := everything(g)
    rejected_submit("duplicate replay", g, "no_open_window", 1, TOP_ID, climb, frame)
    rejected_submit("stale replay by other fighter", g, "no_open_window", 1, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    same("replays left accepted state intact", everything(g), after_accept)

    # ---- 6. Detached results ---------------------------------------------------------------
    var report_state: Dictionary = accepted.values.state
    report_state["clock_seconds"] = -999
    var view := g.state_fields()
    view["clock_seconds"] = -999
    var hist := g.history_fields()
    hist["initiated_action_history"].append("poison")
    var fields := accepted.fields()
    fields.detail.settlement.clear()
    same("detached views leave authority intact", everything(g), after_accept)
    check("fighters stable", g.roles().fighter_by_role, {"top": TOP_ID, "bottom": BOTTOM_ID})

    # ---- 7. Bottom window: wrong fighter, commitment bypass, no mutation ------------------
    var bottom_open := g.open_window_for(0)
    check("bottom window opens", bottom_open.ok() and bottom_open.values.fighter_id == BOTTOM_ID, true)
    rejected_submit("top at bottom window", g, "not_initiator", 2, TOP_ID, climb, frame)
    rejected_submit("bottom crafting commitment", g, "commitment_is_policy_selected", 2, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE, "HIGH")
    rejected_submit("bottom crafting LOW commitment", g, "commitment_is_policy_selected", 2, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE, "LOW")
    rejected_submit("bottom response without action", g, "response_without_action", 2, BOTTOM_ID, "", C.TOP_RESPONSE_POST_AND_BASE)
    rejected_submit("bottom invalid pair", g, "unknown_action", 2, BOTTOM_ID, "INVALID", "INVALID")
    rejected_submit("bottom wrong side action", g, "incorrect_action_side_or_kind", 2, BOTTOM_ID, climb, frame)
    var token_before := g.controller_fields()
    rejected_submit("bottom stale", g, "stale_window", 1, BOTTOM_ID)
    same("D3-B untouched by rejections", g.controller_fields(), token_before)
    var bottom_done := g.submit(2, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    check("bottom decision accepted", bottom_done.ok(), true)
    check("bottom decision kind", bottom_done.values.kind, "bottom_decision")
    check("unarmed decision reported", bottom_done.values.detail.decision.kind, "UNARMED")
    check("bottom baseline MEDIUM", g.history_fields().commitment_history.back(), "MEDIUM")

    # ---- 8. D3-B through the gateway: clear -> TOKEN -> HOLD -> clear -> TOKEN ------------
    var d := make({"bottom_stamina": 25})
    check("initial exhaustion observed", d.controller_fields().previous_exhausted, true)
    d._match.bottom.set_current(35)
    to_bottom_window(d)  # zero-time observation of the clear arms the token
    check("clear armed token", d.controller_fields().armed, true)
    # Bottom window with the latch cleared: baseline MEDIUM, ARMED_NORMAL.
    var normal := d.submit(d.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    check("armed normal", normal.values.detail.decision.kind, "ARMED_NORMAL")
    check("armed normal MEDIUM", d.history_fields().commitment_history.back(), "MEDIUM")
    d._match.bottom.set_current(25)
    var w := to_bottom_window(d)
    check("exhausted commitment LOW", w.commitment, "LOW")
    var clock_before_token: int = d.state_fields().clock_seconds
    var token := d.submit(w.window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    check("token accepted", token.values.detail.decision.kind, "TOKEN")
    check("token LOW commitment", d.history_fields().commitment_history.back(), "LOW")
    check("token consumed", d.controller_fields().token_consumed, true)
    check("token attempt took no time", d.state_fields().clock_seconds, clock_before_token)
    d._match.bottom.set_current(25)
    w = to_bottom_window(d)
    var held_before := d.state_fields()
    var hist_before := d.history_fields()
    var hold := d.submit(w.window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    check("hold accepted", hold.ok(), true)
    check("second exhausted window locks out", hold.values.detail.decision.kind, "LOCKOUT_HOLD")
    var held_after := d.state_fields()
    check("hold spends no stamina", held_after.bottom_stamina, held_before.bottom_stamina)
    check("hold advances no time", held_after.clock_seconds, held_before.clock_seconds)
    check("hold takes no exchange", d.history_fields().initiated_action_history.size(), hist_before.initiated_action_history.size())
    check("hold recorded", d.history_fields().recovery_hold_history.size(), hist_before.recovery_hold_history.size() + 1)
    check("hold is not a reset", d.history_fields().reset_window_history.size(), hist_before.reset_window_history.size())
    check("hold hands initiative to top", d.roles().initiative_id, TOP_ID)
    # Rejections while armed + Exhausted must not consume the token or hold (D3-B is after validation).
    var armed := make({"bottom_stamina": 25})
    armed._match.bottom.set_current(35)
    to_bottom_window(armed)
    armed._match.bottom.set_current(25)
    var armed_id: int = armed.window_fields().window_id
    for stage in range(2):
        rejected_submit("armed bad action %d" % stage, armed, "unknown_action", armed_id, BOTTOM_ID, "bad", C.TOP_RESPONSE_POST_AND_BASE)
        rejected_submit("armed bad response %d" % stage, armed, "unknown_response", armed_id, BOTTOM_ID, C.BOTTOM_BRIDGE, "bad")
        rejected_submit("armed bad response commitment %d" % stage, armed, "invalid_response_commitment", armed_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE, "", "EXTREME")
        rejected_submit("armed crafted commitment %d" % stage, armed, "commitment_is_policy_selected", armed_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE, "HIGH")
        rejected_submit("armed junk no-action commitment %d" % stage, armed, "commitment_without_action", armed_id, BOTTOM_ID, "", "", "", "EXTREME")
        rejected_submit("armed stale %d" % stage, armed, "stale_window", armed_id + 1, BOTTOM_ID)
        check("token still unconsumed %d" % stage, armed.controller_fields().token_consumed, stage == 1)
        if stage == 0:
            check("token taken once", armed.submit(armed_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE).values.detail.decision.kind, "TOKEN")
            armed._match.bottom.set_current(25)
            armed_id = to_bottom_window(armed).window_id
    check("hold state window not spent by rejections", armed.window_fields().open, true)
    check("hold still next", armed.submit(armed_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE).values.detail.decision.kind, "LOCKOUT_HOLD")
    # No-action Bottom while exhausted and re-armed: a genuine RESET, still via D3-B.
    d._match.bottom.set_current(35)
    to_bottom_window(d)  # re-arm (clear observed)
    var reset_target: int = d.window_fields().window_id
    d._match.bottom.set_current(25)
    var no_action := d.submit(reset_target, BOTTOM_ID)
    check("new episode no-action accepted", no_action.ok(), true)
    check("new episode TOKEN", no_action.values.detail.decision.kind, "TOKEN")
    check("no-action is a genuine RESET", d.history_fields().reset_window_history.back(), "bottom")
    check("RESET moved initiative", d.roles().initiative_id, TOP_ID)

    # ---- 9. Free-window ownership: no time, no extra exchange ------------------------------
    var f := make()
    f._match.free_initiative_pending = true
    f._match.free_initiative_beneficiary = "bottom"
    rejected_open("free beneficiary mismatch", f, "invalid_window_request", 5)
    f._match.free_initiative_beneficiary = "top"
    rejected_open("free pending negative duration", f, "invalid_window_request", -1)
    rejected_open("free pending string duration", f, "invalid_duration", "5")
    check("free flag survives rejections", f._match.free_initiative_pending, true)
    var free_before_clock: int = f.state_fields().clock_seconds
    var free_window := f.open_window_for(5)
    check("free window opens", free_window.ok() and free_window.values.free, true)
    check("free window no time", f.state_fields().clock_seconds, free_before_clock)
    check("free flag consumed", f._match.free_initiative_pending, false)
    check("free window decision accepted", f.submit(1, TOP_ID).ok(), true)
    var normal_open := f.open_window_for(5)
    check("next window is not free", normal_open.values.free, false)

    # ---- 10. Terminal: timeout and exit --------------------------------------------------------
    var t := make({"clock": 5, "interval": 5})
    var last := t.open_window_for(5)
    check("timeout open succeeds", last.ok(), true)
    check("timeout closes match", last.values.closed, true)
    check("no window at timeout", t.window_fields().open, false)
    check("timeout state terminal", t.is_terminal(), true)
    rejected_submit("terminal submit", t, "no_open_window", 0, TOP_ID, climb, frame)
    rejected_submit("terminal submit id 1", t, "no_open_window", 1, TOP_ID)
    rejected_open("terminal open", t, "terminal_exchange", 5)
    rejected_open("terminal open zero", t, "terminal_exchange", 0)
    # Exit through a Bottom escape; Mount is then terminal and nothing further is accepted.
    var e := make({"axis": 0.4, "bottom_stamina": 100})
    to_bottom_window(e)
    var exit_attempt := e.submit(e.window_fields().window_id, BOTTOM_ID, C.BOTTOM_ELBOW_KNEE_ESCAPE, C.TOP_RESPONSE_POST_AND_BASE)
    check("escape accepted", exit_attempt.ok(), true)
    check("exit ends match", exit_attempt.values.ended, true)
    check("exit reports transition", exit_attempt.values.transition.kind, "exit")
    check("exit destination declared", exit_attempt.values.transition.resolved, true)
    check("exit is terminal", e.is_terminal(), true)
    rejected_submit("after exit", e, "no_open_window", e.window_fields().window_id, BOTTOM_ID, C.BOTTOM_BRIDGE, C.TOP_RESPONSE_POST_AND_BASE)
    rejected_open("open after exit", e, "terminal_exchange", 0)
    # Terminal reached externally while a window is open: still atomic.
    var x := make()
    x.open_window_for(0)
    x._match.clock_seconds = 0
    rejected_submit("terminal while open", x, "terminal_exchange", 1, TOP_ID, climb, frame)

    # ---- 11. Lockstep trajectories against the unchanged entry points ------------------------
    run_trajectories()

    print("Window gateway native: %d assertions, %d failures; %d lockstep trajectory operations" % [checks, failures, trajectory_operations])
    quit(0 if failures == 0 else 1)

# --- Lockstep -------------------------------------------------------------------------------

func lcg(state: int) -> int:
    return (state * 1103515245 + 12345) & 0x7fffffff

func twin_pick(twin: BjjMountMatch, side: String, seed_value: int) -> Array:
    var actions := twin.legal_actions(side).ids
    var action: String = actions[seed_value % actions.size()]
    var responses := twin.legal_responses(action).ids
    return [action, responses[(seed_value / 7) % responses.size()]]

func run_trajectories() -> void:
    var signatures: Array[String] = []
    for replay_pass in range(2):
        var run_signature := ""
        for bottom_start: int in [100, 40, 25, 0]:
            for axis: float in [0.5, 1.5, 3.0]:
                for seed_base in range(1, 4):
                    run_signature += trajectory(bottom_start, axis, seed_base, replay_pass)
        signatures.append(run_signature.sha256_text())
    check("two replays identical", signatures[0], signatures[1])
    for key: String in ["UNARMED", "ARMED_NORMAL", "TOKEN", "LOCKOUT_HOLD", "free", "terminal"]:
        check("lockstep visited " + key, int(tally.get(key, 0)) > 0, true)
    print("lockstep coverage: ", tally)

func trajectory(bottom_start: int, axis: float, seed_base: int, replay_pass: int) -> String:
    var label := "traj %d/%s/%d/p%d" % [bottom_start, axis, seed_base, replay_pass]
    var settings := config({"bottom_stamina": bottom_start, "axis": axis, "clock": 120})
    var g := BjjMatchWindowGateway.create(settings, TOP_ID, BOTTOM_ID).gateway
    var twin := BjjMountMatch.create(settings.merged({"production": true})).match_state
    var durations: Array[int] = [0, 1, 5, 7, 30, 5]
    var rng := seed_base * 977
    var log := ""
    for step in range(160):
        rng = lcg(rng)
        var duration: int = durations[rng % durations.size()]
        # Arrangement applied to both sides identically (re-exhaust / clear cycles).
        if step % 11 == 5:
            var value: int = [25, 35, 0, 40][(rng / 5) % 4]
            g._match.bottom.set_current(value)
            twin.bottom.set_current(value)
        if step % 13 == 7:
            g._match.free_initiative_pending = true
            g._match.free_initiative_beneficiary = g._match.initiator
            twin.free_initiative_pending = true
            twin.free_initiative_beneficiary = twin.initiator
        var opened := g.open_window_for(duration)
        var expected := twin.next_window(duration)
        if expected.ok() and expected.values.free:
            tally["free"] = int(tally.get("free", 0)) + 1
        check(label + " open ok parity", opened.ok(), expected.ok())
        if not expected.ok():
            check(label + " open error parity", opened.error, expected.error)
            break
        same(label + " advance parity", opened.values.advance, expected.values.advance)
        same(label + " lifecycle after open", g._match.lifecycle_fields(), twin.lifecycle_fields())
        same(label + " d3b after open", g.controller_fields(), twin.d3b.fields())
        trajectory_operations += 1
        if twin.ended:
            check(label + " closed together", opened.values.closed, true)
            tally["terminal"] = int(tally.get("terminal", 0)) + 1
            break
        var side := twin.initiator
        var fighter := TOP_ID if side == "top" else BOTTOM_ID
        var window_id: int = opened.values.window_id
        check(label + " window side", opened.values.role, side)
        check(label + " window commitment", opened.values.commitment, twin.selected_commitment())
        rng = lcg(rng)
        var choose_reset := rng % 5 == 0
        var pick := twin_pick(twin, side, rng) if not choose_reset else ["", ""]
        var report: BjjMatchWindowGateway.Report
        if side == "bottom":
            report = g.submit(window_id, fighter, pick[0], pick[1])
            var baseline := twin.bottom_decision(pick[0], pick[1])
            check(label + " bottom ok parity", report.ok(), baseline.ok())
            if baseline.ok():
                same(label + " bottom detail parity", report.values.detail, baseline.fields())
                var kind_key: String = str(baseline.values.decision.kind) + ("/reset" if pick[0] == "" else "")
                tally[kind_key] = int(tally.get(kind_key, 0)) + 1

        else:
            var requested: String = ["LOW", "MEDIUM", "HIGH"][(rng / 3) % 3]
            report = g.submit(window_id, fighter, pick[0], pick[1], "" if choose_reset else requested)
            if choose_reset:
                var reset := twin.reset_window()
                check(label + " reset ok parity", report.ok() and reset.ok(), true)
                same(label + " reset detail parity", report.values.detail.settlement, reset.fields())
            else:
                var baseline_exchange := twin.attempt(BjjExchangeResult.Request.new(pick[0], pick[1], requested))
                check(label + " top ok parity", report.ok(), baseline_exchange.ok())
                if baseline_exchange.ok():
                    same(label + " top detail parity", report.values.detail.settlement, baseline_exchange.fields())
        check(label + " submit accepted", report.ok(), true)
        same(label + " lifecycle after decision", g._match.lifecycle_fields(), twin.lifecycle_fields())
        same(label + " d3b after decision", g.controller_fields(), twin.d3b.fields())
        same(label + " histories parity", g.history_fields(), twin.history.fields())
        check(label + " window closed", g.window_fields().open, false)
        trajectory_operations += 2
        log += "%s|%s|%s;" % [side, pick[0], twin.clock_seconds]
        if twin.ended:
            break
    log += JSON.stringify(g.state_fields(), "", true, true) + JSON.stringify(g.history_fields(), "", true, true)
    return log
