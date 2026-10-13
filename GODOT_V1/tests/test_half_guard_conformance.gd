extends SceneTree

# Conformance of the Half Guard window gateway to the established Mount window gateway: shared report shapes (keys and
# value types), shared view keys the graph and F0 read, identical results for the shared admission codes in equivalent
# situations, and identical simulated-time advancement under the same interval. Position-specific content (histories,
# detail payloads, technique vocabularies, report `kind` names) is deliberately NOT required to be equal and is asserted
# as the documented difference where it matters. The Mount gateway is only read through its public API; nothing in Mount changes.
const HG_TOP: String = "fighter_alpha"
const HG_BOTTOM: String = "fighter_bravo"
# Keys that BjjFighterSnapshotAdapter (F0) and the position graph read from a segment's state view.
const SHARED_STATE_KEYS: Array[String] = ["top_stamina", "bottom_stamina", "top_maximum", "bottom_maximum", "top_band", "bottom_band",
    "clock_seconds", "initial_clock", "initiator", "exit_destination", "exit_reason", "submission_tapped"]

var checks: int = 0
var failures: int = 0


func check(label: String, actual: Variant, expected: Variant) -> void:
    checks += 1
    if typeof(actual) != typeof(expected) or JSON.stringify(actual, "", true, true) != JSON.stringify(expected, "", true, true):
        failures += 1
        if failures <= 25:
            push_error("%s: got %s expected %s" % [label, JSON.stringify(actual), JSON.stringify(expected)])


func _initialize() -> void:
    _test_state_view_keys()
    _test_report_shapes()
    _test_shared_admission_codes()
    _test_same_time_advancement()
    _test_view_surface()
    if failures > 0:
        push_error("Half Guard conformance: %d / %d assertions failed" % [failures, checks])
        quit(1)
        return
    print("Half Guard conformance PASS: %d assertions" % checks)
    quit(0)


func rules() -> Dictionary:
    var settings := BjjProductionStaminaPolicy.settings()
    settings["enable_v02_setup"] = true
    settings["enable_v03_submissions"] = true
    settings["enable_v04_commitment_semantics"] = true
    return settings


func mount(extra: Dictionary = {}) -> BjjMatchWindowGateway:
    var configuration := {"rules": rules()}
    configuration.merge(extra, true)
    var created := BjjMatchWindowGateway.create(configuration, HG_TOP, HG_BOTTOM)
    check("Mount gateway builds (%s)" % extra, created.ok(), true)
    return created.gateway


func half_guard() -> BjjHalfGuardWindowGateway:
    var fighter := {"stamina_current": 100, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0}
    return BjjHalfGuardWindowGateway.create({"role_map": {"top": HG_TOP, "bottom": HG_BOTTOM},
        "fighters": {HG_TOP: fighter.duplicate(), HG_BOTTOM: fighter.duplicate()}, "clock": {"initial_seconds": 300, "remaining_seconds": 300},
        "window": {"last_issued_id": 0}, "interval_seconds": 5}).gateway


func key_types(values: Dictionary) -> Dictionary:
    var out := {}
    for key: Variant in values:
        out[str(key)] = typeof(values[key])
    return out


func sorted_keys(values: Dictionary) -> Array:
    var out: Array = []
    for key: Variant in values:
        out.append(str(key))
    out.sort()
    return out


func _test_state_view_keys() -> void:
    var m := mount().state_fields()
    var h := half_guard().state_fields()
    for key: String in SHARED_STATE_KEYS:
        check("both state views carry %s" % key, [m.has(key), h.has(key)], [true, true])
        check("%s has the same value type" % key, typeof(h[key]), typeof(m[key]))
    check("values agree at the start", [h.initial_clock, h.clock_seconds, h.top_maximum, h.bottom_maximum, h.top_stamina, h.bottom_stamina, h.top_band, h.exit_destination, h.submission_tapped],
        [m.initial_clock, m.clock_seconds, m.top_maximum, m.bottom_maximum, m.top_stamina, m.bottom_stamina, m.top_band, m.exit_destination, m.submission_tapped])
    check("initiator labels agree", h.initiator, m.initiator)
    check("the ended flag is a Mount view key too", [m.has("ended"), h.has("ended")], [true, true])


func _test_report_shapes() -> void:
    var m := mount()
    var h := half_guard()
    var open_m := m.open_window()
    var open_h := h.open_window()
    check("open report keys", sorted_keys(open_h.values), sorted_keys(open_m.values))
    for key: String in ["closed", "window_open", "free", "window_id", "fighter_id", "role", "commitment"]:
        check("open report %s type" % key, typeof(open_h.values[key]), typeof(open_m.values[key]))
    check("open report values", [open_h.values.closed, open_h.values.window_open, open_h.values.free, open_h.values.window_id, open_h.values.fighter_id,
        open_h.values.role, open_h.values.commitment], [open_m.values.closed, open_m.values.window_open, open_m.values.free, open_m.values.window_id,
        open_m.values.fighter_id, open_m.values.role, open_m.values.commitment])
    check("open report advance is a dictionary in both", [typeof(open_h.values.advance), typeof(open_m.values.advance)], [TYPE_DICTIONARY, TYPE_DICTIONARY])
    check("window views agree", h.window_fields(), m.window_fields())
    var pass_m := m.submit(1, HG_TOP)
    var pass_h := h.submit(1, HG_TOP)
    check("submit report keys", sorted_keys(pass_h.values), sorted_keys(pass_m.values))
    for key: String in ["window_id", "fighter_id", "role", "kind", "ended"]:
        check("submit report %s type" % key, typeof(pass_h.values[key]), typeof(pass_m.values[key]))
    check("pass kind is the shared reset kind", [pass_h.values.kind, pass_m.values.kind], ["reset", "reset"])
    check("transition shape", sorted_keys(pass_h.values.transition), sorted_keys(pass_m.values.transition))
    check("transition value for a pass", pass_h.values.transition, pass_m.values.transition)
    check("ended flag", pass_h.values.ended, pass_m.values.ended)
    # the documented difference: an exchange kind is `exchange` in Half Guard and `top_exchange` in Mount
    var exchange_h := h.open_window()
    check("second window", exchange_h.values.role, "bottom")
    var done := h.submit(2, HG_BOTTOM, BjjHalfGuardCatalog.BOTTOM_UNDERHOOK, BjjHalfGuardCatalog.TOP_HEAD_CONTROL)
    check("Half Guard exchange kind", done.values.kind, "exchange")
    check("Half Guard detail payload", sorted_keys(done.values.detail), ["settlement"])
    check("Half Guard reports are the shared report type", [done is BjjMatchWindowGateway.Report, pass_h is BjjMatchWindowGateway.Report], [true, true])
    check("report fields() is a detached copy", done.fields() == done.values and not is_same(done.fields(), done.values), true)
    var failed := h.submit(99, HG_TOP)
    check("a failed report carries only its error", [failed.ok(), failed.fields()], [false, {"error": "no_open_window"}])


# Equivalent situations on fresh gateways: the same stable code from both.
func _test_shared_admission_codes() -> void:
    var cases: Array = [
        ["no_open_window", func(g: Variant) -> String: return g.submit(1, HG_TOP, "x", "y").error],
        ["stale_window", func(g: Variant) -> String:
            g.open_window()
            return g.submit(9, HG_TOP, "x", "y").error],
        ["missing_fighter_id", func(g: Variant) -> String:
            g.open_window()
            return g.submit(1, "", "x", "y").error],
        ["unknown_fighter", func(g: Variant) -> String:
            g.open_window()
            return g.submit(1, "ghost", "x", "y").error],
        ["not_initiator", func(g: Variant) -> String:
            g.open_window()
            return g.submit(1, HG_BOTTOM, "x", "y").error],
        ["response_without_action", func(g: Variant) -> String:
            g.open_window()
            return g.submit(1, HG_TOP, "", "y").error],
        ["commitment_without_action", func(g: Variant) -> String:
            g.open_window()
            return g.submit(1, HG_TOP, "", "", "LOW").error],
        ["window_already_open", func(g: Variant) -> String:
            g.open_window()
            return g.open_window().error],
        ["invalid_duration", func(g: Variant) -> String: return g.open_window_for("5").error],
        ["invalid_duration (float)", func(g: Variant) -> String: return g.open_window_for(2.5).error],
        ["invalid_duration (bool)", func(g: Variant) -> String: return g.open_window_for(true).error],
        ["invalid_window_request", func(g: Variant) -> String: return g.open_window_for(-1).error],
    ]
    for c: Array in cases:
        var expected: String = str(c[0]).split(" ")[0]
        check("Mount %s" % c[0], (c[1] as Callable).call(mount()), expected)
        check("Half Guard %s" % c[0], (c[1] as Callable).call(half_guard()), expected)


# Under the same interval both gateways advance the same simulated seconds per window and end on the same boundary.
func _test_same_time_advancement() -> void:
    var m := mount()
    var h := half_guard()
    var durations: Array = [null, 0, 7, 99, 99, 99, 99]
    for step in range(durations.size()):
        var rm := m.open_window_for(durations[step])
        var rh := h.open_window_for(durations[step])
        check("step %d: both opened or both closed" % step, [rh.ok(), rh.values.closed, rh.values.window_open], [rm.ok(), rm.values.closed, rm.values.window_open])
        check("step %d: same clock" % step, h.state_fields().clock_seconds, m.state_fields().clock_seconds)
        check("step %d: same window id" % step, [h.window_fields().window_id, h.window_fields().open], [m.window_fields().window_id, m.window_fields().open])
        if rm.values.closed:
            break
        var side: String = rm.values.role
        check("step %d: same window owner" % step, rh.values.role, side)
        var fighter := HG_TOP if side == "top" else HG_BOTTOM
        check("step %d: Mount pass" % step, m.submit(rm.values.window_id, fighter).ok(), true)
        check("step %d: Half Guard pass" % step, h.submit(rh.values.window_id, fighter).ok(), true)
    check("both ended at the same boundary", [h.state_fields().ended, h.state_fields().clock_seconds], [m.state_fields().ended, 0])
    check("both refuse another window with the same code", [h.open_window().error, m.open_window().error], ["terminal_exchange", "terminal_exchange"])
    # a custom interval is honored by the Half Guard entry exactly as Mount's `interval` is
    var m7 := mount({"interval": 7})
    var fighter_record := {"stamina_current": 100, "stamina_maximum": 100, "exhaustion_latched": false, "behavior_remainder_units": 0}
    var h7 := BjjHalfGuardWindowGateway.create({"role_map": {"top": HG_TOP, "bottom": HG_BOTTOM}, "fighters": {HG_TOP: fighter_record.duplicate(), HG_BOTTOM: fighter_record.duplicate()},
        "clock": {"initial_seconds": 300, "remaining_seconds": 300}, "window": {"last_issued_id": 0}, "interval_seconds": 7}).gateway
    m7.open_window()
    h7.open_window()
    check("interval 7 advances the same", h7.state_fields().clock_seconds, m7.state_fields().clock_seconds)


func _test_view_surface() -> void:
    var m := mount()
    var h := half_guard()
    for method: String in ["window_fields", "state_fields", "history_fields", "controller_fields", "behavior_fields", "roles", "is_terminal", "action_options",
            "response_options", "selected_commitment", "open_window", "open_window_for", "submit"]:
        check("Half Guard gateway has %s like Mount" % method, [m.has_method(method), h.has_method(method)], [true, true])
    check("selected commitment agrees", h.selected_commitment(), m.selected_commitment())
    check("window view keys agree", sorted_keys(h.window_fields()), sorted_keys(m.window_fields()))
    check("role view keys agree", sorted_keys(h.roles().fields()), sorted_keys(m.roles().fields()))
    check("terminal flag type", typeof(h.is_terminal()), typeof(m.is_terminal()))
    check("Half Guard has no carry-over export yet", [h.has_method("carryover_segment"), m.has_method("carryover_segment")], [false, true])
    check("option list shape", sorted_keys(h.action_options(HG_TOP).fields()), sorted_keys(m.action_options(HG_TOP).fields()))
    check("option entry shape", sorted_keys(h.action_options(HG_TOP).fields().options[0]), sorted_keys(m.action_options(HG_TOP).fields().options[0]))
