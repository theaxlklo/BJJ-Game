extends SceneTree

# B1e: deterministic, headless match-flow MEASUREMENT (evidence only). Three kinds of statement are kept apart in the report this prints:
#   STRUCTURAL  exact, CI-gated properties (see test_match_flow_invariants.gd);
#   POPULATION  what a NAMED, scripted, seeded policy does over a bounded number of games (this script);
#   DESIGN QUESTION  possible later owner decisions (never implemented here).
# Nothing here changes a rule, penalizes a no-progress sequence, scores a match or decides a winner: reaching an unsupported destination is an
# incomplete-engine boundary, not a result. Usage:
#   godot-bjj --headless --path GODOT_V1 --script res://tests/measure_match_flow.gd [-- seeds=30 hg_seeds=20]
# Everything printed before the line "== PERFORMANCE" is deterministic and byte-identical across runs; the performance section reads the wall clock
# and is excluded from every determinism claim.
const H = preload("res://tests/match_flow_harness.gd")
const MAX_WINDOWS: int = 80
const PLAN_COUNT: int = 5

var seeds: int = 30
var hg_seeds: int = 20
var harness: RefCounted
var plans: Array = []
var digests: Array = []


func _initialize() -> void:
    for argument: String in OS.get_cmdline_user_args():
        if argument.begins_with("seeds="):
            seeds = int(argument.substr(6))
        elif argument.begins_with("hg_seeds="):
            hg_seeds = int(argument.substr(9))
    harness = H.new()
    plans = harness.find_plans(PLAN_COUNT)
    var started := Time.get_ticks_usec()
    var out: Array[String] = []
    out.append("# Match-flow measurement (B1e) — evidence only, not a balance claim")
    out.append("")
    out.append("maximum windows per game: %d (the 300 s clock at a 5 s interval ends a game after at most 60 windows); seeds: %d (Mount/full-flow populations), %d (Half Guard populations);" % [MAX_WINDOWS, seeds, hg_seeds])
    out.append("real Mount entries into Half Guard used by population B: %d distinct plans" % plans.size())
    var populations: Array = [_population_a(), _population_b(), _population_c()]
    var performance: Array[String] = []
    var total_windows := 0
    var total_games := 0
    for population: Dictionary in populations:
        out.append("")
        out.append("## " + str(population.title))
        out.append(str(population.note))
        out.append_array(_summary(population, str(population.group)))
        out.append_array(_tables(population))
        total_windows += int(population.windows)
        total_games += int(population.games)
    # replay: the whole populations a second time; every game's trace digest must be identical
    var first_digest := "".join(digests).sha256_text()
    var first_count := digests.size()
    digests.clear()
    var replay_started := Time.get_ticks_usec()
    _population_a()
    _population_b()
    _population_c()
    var second_digest := "".join(digests).sha256_text()
    var replay_usec := Time.get_ticks_usec() - replay_started
    out.append("")
    out.append("## Determinism and replay (STRUCTURAL)")
    out.append("games: %d; windows driven: %d; population trace digest (first run) %s; (second run) %s; replay %s" % [first_count, total_windows, first_digest, second_digest,
        "IDENTICAL" if first_digest == second_digest and digests.size() == first_count else "DIFFERENT"])
    var policy_errors := 0
    for population: Dictionary in populations:
        for cell: Dictionary in population.cells:
            for game: Dictionary in cell.games:
                policy_errors += (game.policy_errors as Array).size()
    out.append("policy errors (a refused command the harness did not intend; any non-zero value is a harness defect): %d" % policy_errors)
    var totals := {"checked": 0, "violations": 0, "hg_rises": 0, "mount_rises": 0, "fallbacks": 0, "undercommit": 0, "expected": 0, "mismatches": 0, "holds": 0, "taps": 0, "clock_ends": 0, "halts": 0}
    for population: Dictionary in populations:
        for cell: Dictionary in population.cells:
            for game: Dictionary in cell.games:
                totals.checked += int(game.continuity_checks)
                totals.violations += int(game.continuity_violations)
                totals.hg_rises += int(game.stamina_increases_half_guard)
                totals.mount_rises += int(game.stamina_increases_mount)
                totals.fallbacks += int(game.timeouts)
                totals.undercommit += int(game.timeout_undercommit)
                totals.expected += int(game.timeout_expected_undercommit)
                totals.mismatches += int(game.timeout_other_modifiers)
                totals.holds += int(game.mount_holds)
                var outcome := str(game.outcome)
                totals.taps += 1 if outcome.begins_with("tap_") else 0
                totals.clock_ends += 1 if outcome.begins_with("timeout_") else 0
                totals.halts += 1 if outcome.begins_with("halt_") else 0
    out.append("")
    out.append("## Structural totals over every game above (STRUCTURAL; each must hold for the report to be valid)")
    out.append("Mount -> Half Guard transitions checked for identity, stamina, latch, meter, clock and window continuity: %d; violations: %d" % [totals.checked, totals.violations])
    out.append("Half Guard windows in which any stamina rose (Half Guard v0 has no recovery rule): %d" % totals.hg_rises)
    out.append("published-fallback exchanges: %d; undercommitment +1 applied: %d; expected from the funded commitments alone: %d; any other modifier difference: %d" % [totals.fallbacks, totals.undercommit, totals.expected, totals.mismatches])
    out.append("(measured, not an invariant) Mount windows where any stamina rose: %d; Mount D3-B HOLD windows: %d; games ended by a tap: %d, by a clock end: %d, halted at an unsupported exit: %d" % [totals.mount_rises, totals.holds, totals.taps, totals.clock_ends, totals.halts])
    for line: String in out:
        print(line)
    print("")
    print("== PERFORMANCE (wall clock; not part of the deterministic report)")
    print("first run: %d ms for %d games and %d windows (%.1f windows/s); replay: %d ms" % [(replay_started - started) / 1000, total_games, total_windows,
        float(total_windows) / maxf(0.001, float(replay_started - started) / 1000000.0), replay_usec / 1000])
    # a structural violation or a harness defect fails the run; no outcome frequency ever does
    quit(0 if policy_errors == 0 and first_digest == second_digest and totals.violations == 0 and totals.hg_rises == 0 and totals.mismatches == 0 else 1)


func _seed_count(spec: Dictionary, fields: Array, count: int) -> int:
    for field: String in fields:
        var value := str(spec.get(field, ""))
        if value.contains("seeded"):
            return count
    return 1


func _run_cells(cells: Array, seed_fields: Array, count: int) -> Dictionary:
    var population := {"cells": [], "games": 0, "windows": 0}
    for cell: Dictionary in cells:
        var spec: Dictionary = cell.spec
        var cell_seeds := _seed_count(spec, seed_fields, count)
        if str(spec.get("commit", "")) == "seeded":
            cell_seeds = count
        var games: Array = []
        for seed_value in range(cell_seeds):
            var run := spec.duplicate()
            run["seed"] = seed_value
            run["max_windows"] = MAX_WINDOWS
            var record: Dictionary = harness.play(run)
            digests.append(str(record.get("digest", "")))
            games.append(record)
            population.windows += int(record.windows)
        population.games += games.size()
        population.cells.append({"name": cell.name, "spec": spec, "games": games})
    return population


func _population_a() -> Dictionary:
    var cells: Array = []
    for policy: String in H.MOUNT_POLICIES:
        for defender: String in ["first_available", "seeded"]:
            for commit: String in ["MEDIUM", "HIGH"]:
                if policy == "pass_only" and defender == "seeded":
                    continue
                cells.append({"name": "%s / %s / %s" % [policy, defender, commit], "spec": {"mount": policy, "mount_defender": defender, "commit": commit, "hg": "hg_pass", "defender": "bite"}})
    var population := _run_cells(cells, ["mount", "mount_defender"], seeds)
    population["group"] = "mount"
    population["title"] = "Population A — Mount-only policies (an entered Half Guard is then played with passes only)"
    population["note"] = "POPULATION. Rows are named scripted policies; `seeded_legal` and `seeded` are reproducible uniform random walks over LEGAL options, not intelligent or balanced players. Deterministic cells use one game."
    return population


func _population_b() -> Dictionary:
    var cells: Array = []
    var index := 0
    for plan: Dictionary in plans:
        for attacker: String in H.HG_ATTACKERS:
            for defender: String in H.HG_DEFENDERS:
                for commit: String in ["MEDIUM", "HIGH"]:
                    cells.append({"name": "entry %d / %s / %s / %s" % [index, attacker.trim_prefix("hg_"), defender, commit],
                        "spec": {"plan": plan, "hg": attacker, "defender": defender, "commit": commit}})
        index += 1
    var population := _run_cells(cells, ["hg", "defender"], hg_seeds)
    population["group"] = "hg"
    population["title"] = "Population B — Half Guard from real Mount entries (%d entries x attackers x defenders x commitments)" % plans.size()
    population["note"] = "POPULATION. Each entry is a REAL Mount escape taken through the graph (different stamina, interval and rule set); the Half Guard play starts at that real entry."
    return population


func _population_c() -> Dictionary:
    var cells: Array = []
    for mount: String in ["pass_only", "top_direct", "bottom_escape", "bottom_trap_roll", "seeded_legal"]:
        for attacker: String in ["hg_feint_when_eligible", "hg_prep_oriented"]:
            for defender: String in ["bite", "call", "fallback"]:
                cells.append({"name": "%s -> %s / %s" % [mount, attacker.trim_prefix("hg_"), defender],
                    "spec": {"mount": mount, "mount_defender": "first_available", "commit": "MEDIUM", "hg": attacker, "defender": defender}})
    var population := _run_cells(cells, ["mount"], seeds)
    population["group"] = "full"
    population["title"] = "Population C — bounded combinations: a Mount policy, then a Half Guard attacker against a named defender (MEDIUM commitments)"
    population["note"] = "POPULATION. The Half Guard phase only occurs for games whose Mount policy really reaches a Half Guard exit."
    return population


# Grouped summary: the per-cell tables below are exact; this groups cells by the policy of interest (all entries, commitments and seeds pooled).
func _group_name(cell: Dictionary, mode: String) -> String:
    var spec: Dictionary = cell.spec
    match mode:
        "mount":
            return str(spec.mount)
        "hg":
            return "%s vs %s" % [str(spec.hg).trim_prefix("hg_"), spec.defender]
    return "%s -> %s vs %s" % [spec.mount, str(spec.hg).trim_prefix("hg_"), spec.defender]


func _summary(population: Dictionary, mode: String) -> Array[String]:
    var order: Array = []
    var groups := {}
    for cell: Dictionary in population.cells:
        var name := _group_name(cell, mode)
        if not groups.has(name):
            groups[name] = []
            order.append(name)
        (groups[name] as Array).append_array(cell.games)
    var lines: Array[String] = ["", "**Summary by policy** (all cells with the same policy pooled; percentages are of games)",
        "| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name: String in order:
        var games: Array = groups[name]
        var n := games.size()
        var taps := 0
        var clock_ends := 0
        var ended := 0
        var halted := 0
        var entered := 0
        var active := 0
        var windows := 0
        var exchanges := 0
        var accepted := 0
        var bit := 0
        var effective := 0
        var punished := 0
        var fallbacks := 0
        var stuck := 0
        var axis_final := 0.0
        var axis_low := 0.0
        var axis_high := 0.0
        var destinations := {}
        for game: Dictionary in games:
            var outcome := str(game.outcome)
            axis_final += float(game.axis_final)
            axis_low += float(game.axis_min) if int(game.axis_samples) > 0 else 0.0
            axis_high += float(game.axis_max) if int(game.axis_samples) > 0 else 0.0
            if outcome.begins_with("halt_"):
                var destination := outcome.trim_prefix("halt_")
                destinations[destination] = int(destinations.get(destination, 0)) + 1
                halted += 1
            elif outcome.begins_with("max_windows"):
                active += 1
            else:
                ended += 1
                taps += 1 if outcome.begins_with("tap_") else 0
                clock_ends += 1 if outcome.begins_with("timeout_") else 0
            entered += 1 if bool(game.entered_half_guard) else 0
            windows += int(game.windows)
            exchanges += int(game.exchanges)
            accepted += int(game.feints_accepted)
            bit += int(game.feints_bit)
            effective += int(game.feints_effective)
            punished += int(game.feints_punished)
            fallbacks += int(game.timeouts)
            stuck += 1 if int(game.longest_no_progress) >= 10 else 0
        var destination_names := destinations.keys()
        destination_names.sort()
        var destination_text := ", ".join(destination_names.map(func(d: String) -> String: return "%s %d" % [d, destinations[d]])) if not destination_names.is_empty() else "-"
        lines.append("| %s | %d | %d (%.0f%%) | %d (%.0f%%) | %d (%.0f%%) | %d (%.0f%%) | %d | %.1f | %.1f | %d | %s | %s | %s | %d | %d (%.0f%%) | %+.2f | %+.2f / %+.2f | %s |" % [name, n, taps, 100.0 * taps / n, clock_ends, 100.0 * clock_ends / n, halted, 100.0 * halted / n,
            entered, 100.0 * entered / n, active, float(windows) / n, float(exchanges) / n, accepted, "%d (%.0f%%)" % [bit, 100.0 * bit / accepted] if accepted > 0 else "-",
            "%d (%.0f%%)" % [effective, 100.0 * effective / accepted] if accepted > 0 else "-", "%d (%.0f%%)" % [punished, 100.0 * punished / accepted] if accepted > 0 else "-",
            fallbacks, stuck, 100.0 * stuck / n, axis_final / n, axis_low / n, axis_high / n, destination_text])
    return lines


# ---- Aggregation and tables ---------------------------------------------------------------------------------------------------------------------

func _tables(population: Dictionary) -> Array[String]:
    var lines: Array[String] = []
    var outcome_names: Array = []
    for cell: Dictionary in population.cells:
        for game: Dictionary in cell.games:
            if not outcome_names.has(game.outcome):
                outcome_names.append(game.outcome)
    outcome_names.sort()
    lines.append("")
    lines.append("**Outcomes (games per terminal class)** — `halt_*` is an unsupported-destination boundary, not a result")
    var header := "| cell | games | " + " | ".join(outcome_names) + " |"
    lines.append(header)
    lines.append("|" + "---|".repeat(outcome_names.size() + 2))
    for cell: Dictionary in population.cells:
        var counts := {}
        for game: Dictionary in cell.games:
            counts[game.outcome] = int(counts.get(game.outcome, 0)) + 1
        var cells: Array[String] = [str(cell.name), str((cell.games as Array).size())]
        for name: String in outcome_names:
            cells.append(str(counts.get(name, 0)))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("**Time, entry and position time** (means over the cell's games; seconds are simulated clock seconds)")
    lines.append("| cell | windows mean (min-max) | seconds mean | entered Half Guard | mean entry window | Mount windows mean | Half Guard windows mean | exchanges mean | passes mean | D3-B holds mean | longest pass streak max | longest idle streak max |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cell: Dictionary in population.cells:
        var games: Array = cell.games
        var n := games.size()
        var w := 0
        var wmin := 9999
        var wmax := 0
        var sec := 0
        var entered := 0
        var entry_sum := 0
        var mw := 0
        var hw := 0
        var ex := 0
        var ps := 0
        var holds := 0
        var streak := 0
        var idle := 0
        for game: Dictionary in games:
            w += int(game.windows)
            wmin = mini(wmin, int(game.windows))
            wmax = maxi(wmax, int(game.windows))
            sec += int(game.seconds)
            mw += int(game.mount_windows)
            hw += int(game.half_guard_windows)
            ex += int(game.exchanges)
            ps += int(game.passes)
            holds += int(game.mount_holds)
            streak = maxi(streak, int(game.longest_pass_streak))
            idle = maxi(idle, int(game.longest_idle_streak))
            if bool(game.entered_half_guard):
                entered += 1
                entry_sum += int(game.entry_window)
        lines.append("| %s | %.1f (%d-%d) | %.1f | %d/%d | %s | %.1f | %.1f | %.1f | %.1f | %.1f | %d | %d |" % [cell.name, float(w) / n, wmin, wmax, float(sec) / n, entered, n,
            "%.1f" % (float(entry_sum) / entered) if entered > 0 else "-", float(mw) / n, float(hw) / n, float(ex) / n, float(ps) / n, float(holds) / n, streak, idle])
    lines.append("")
    lines.append("**Stamina, exhaustion and commitment downgrades** (means; `downgrades` counts exchanges whose requested commitment was funded lower, either fighter)")
    lines.append("| cell | min stamina top (mean) | min stamina bottom (mean) | games with an exhausted fighter | exhausted windows top+bottom (mean) | downgrades (mean) | windows where any stamina rose: Mount / Half Guard (total) |")
    lines.append("|---|---|---|---|---|---|---|")
    for cell: Dictionary in population.cells:
        var games2: Array = cell.games
        var n2 := games2.size()
        var mt := 0
        var mb := 0
        var any_exhausted := 0
        var exhausted := 0
        var down := 0
        var rises_mount := 0
        var rises_hg := 0
        for game: Dictionary in games2:
            rises_mount += int(game.stamina_increases_mount)
            rises_hg += int(game.stamina_increases_half_guard)
            mt += int(game.min_top)
            mb += int(game.min_bottom)
            exhausted += int(game.exhausted_top) + int(game.exhausted_bottom)
            down += int(game.downgrades)
            if int(game.exhausted_top) + int(game.exhausted_bottom) > 0:
                any_exhausted += 1
        lines.append("| %s | %.1f | %.1f | %d/%d | %.1f | %.1f | %d / %d |" % [cell.name, float(mt) / n2, float(mb) / n2, any_exhausted, n2, float(exhausted) / n2, float(down) / n2,
            rises_mount, rises_hg])
    lines.append("")
    lines.append("**Feints and the published LOW fallback** (totals over the cell's games; `effective` = final grade >= Success, `punished` = final grade <= Failure)")
    lines.append("| cell | feint attempts | refused (by code) | accepted | bit | not bit | effective | neutral | punished | exits by a feint | exits capped (LOW) | fallbacks | undercommitment +1 | fallback modifier mismatches |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    var any_feint := false
    for cell: Dictionary in population.cells:
        var t := {"feint_attempts": 0, "feints_accepted": 0, "feints_bit": 0, "feints_not_bit": 0, "feints_effective": 0, "feints_neutral": 0, "feints_punished": 0, "feint_exits": 0,
            "feint_capped": 0, "timeouts": 0, "timeout_undercommit": 0, "timeout_other_modifiers": 0}
        var refused := {}
        for game: Dictionary in cell.games:
            for key: String in t:
                t[key] += int(game[key])
            for code: String in game.feint_refused:
                refused[code] = int(refused.get(code, 0)) + int(game.feint_refused[code])
        if int(t.feint_attempts) + int(t.timeouts) + int(t.feints_accepted) == 0:
            continue
        any_feint = true
        var refused_text := ", ".join(refused.keys().map(func(code: String) -> String: return "%s:%d" % [code, refused[code]])) if not refused.is_empty() else "-"
        lines.append("| %s | %d | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % [cell.name, t.feint_attempts, refused_text, t.feints_accepted, t.feints_bit, t.feints_not_bit,
            t.feints_effective, t.feints_neutral, t.feints_punished, t.feint_exits, t.feint_capped, t.timeouts, t.timeout_undercommit, t.timeout_other_modifiers])
    if not any_feint:
        lines.append("| (no feint or fallback in this population) | | | | | | | | | | | | | |")
    lines.append("")
    lines.append("**Positional trajectory** (one comparable axis, positive = Top advantage: Mount `axis`, Half Guard `axis_tenths / 10`; means over games)")
    lines.append("| cell | final axis (mean) | lowest axis reached (mean) | highest axis reached (mean) |")
    lines.append("|---|---|---|---|")
    for cell: Dictionary in population.cells:
        var n4 := (cell.games as Array).size()
        var final_sum := 0.0
        var low_sum := 0.0
        var high_sum := 0.0
        for game: Dictionary in cell.games:
            final_sum += float(game.axis_final)
            low_sum += float(game.axis_min) if int(game.axis_samples) > 0 else 0.0
            high_sum += float(game.axis_max) if int(game.axis_samples) > 0 else 0.0
        lines.append("| %s | %+.2f | %+.2f | %+.2f |" % [cell.name, final_sum / n4, low_sum / n4, high_sum / n4])
    lines.append("")
    lines.append("**No-progress sequences** (a window that leaves the positional fingerprint unchanged: Mount axis, band, setup tiers and submission stage; Half Guard axis, band and both readiness tiers)")
    lines.append("| cell | longest no-progress streak (max) | mean | games with a streak of 10+ windows | policy errors | transitions checked | continuity violations |")
    lines.append("|---|---|---|---|---|---|---|")
    for cell: Dictionary in population.cells:
        var games3: Array = cell.games
        var n3 := games3.size()
        var longest := 0
        var total := 0
        var stuck := 0
        var errors := 0
        var checked := 0
        var violations := 0
        for game: Dictionary in games3:
            longest = maxi(longest, int(game.longest_no_progress))
            total += int(game.longest_no_progress)
            stuck += 1 if int(game.longest_no_progress) >= 10 else 0
            errors += (game.policy_errors as Array).size()
            checked += int(game.continuity_checks)
            violations += int(game.continuity_violations)
        lines.append("| %s | %d | %.1f | %d/%d | %d | %d | %d |" % [cell.name, longest, float(total) / n3, stuck, n3, errors, checked, violations])
    return lines
