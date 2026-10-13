# Integrated match-flow diagnostics (B1e)

**Status: evidence, not a rule change.** B1e measures the deterministic behavior of the connected Mount + Half Guard engine **exactly as qualified in B1i**; it changes no combat number, no stamina rule, no default and adds no mechanic (no scoring, no positional-stalling penalty, no free-initiative priority, no new position, no return route). The default graph is unchanged and F1 is not enabled for the new graph. Nothing here is a balance qualification, a winner, a score or a claim that any outcome is good or bad.

Three kinds of statement are kept apart on purpose:

* **STRUCTURAL** — exact, deterministic properties; CI-gated by `GODOT_V1/tests/test_match_flow_invariants.gd` (pinned count).
* **POPULATION** — what a *named, scripted, seeded* policy does over a bounded number of games (`GODOT_V1/tests/measure_match_flow.gd`). Never gated. A `seeded_legal` or `seeded` policy is a reproducible random walk over legal options: it is **not** intelligent, strategic or balanced.
* **DESIGN QUESTION** — a possible later owner decision. Nothing in this slice implements one.

Reaching an unsupported destination (a Mount `Open Guard` / `Reversal` exit, or any Half Guard exit) is an **incomplete-engine boundary, not a win or a loss**. A clock expiry is reported as the existing `terminal_outcome` (`timeout`) with no adjudication.

## 1. Reproduce it

```
godot-bjj --headless --path GODOT_V1 --import                               # once per checkout
godot-bjj --headless --path GODOT_V1 --script res://tests/measure_match_flow.gd [-- seeds=30 hg_seeds=20]
godot-bjj --headless --path GODOT_V1 --script res://tests/test_match_flow_invariants.gd     # the CI-gated structural suite
```

* The measurement needs no fixtures (it drives the real engine only). Defaults: `seeds=30` (Mount and full-flow populations), `hg_seeds=20` (Half Guard populations), at most **80 windows** per game; the default 300 s clock at a 5 s interval ends every game at **59 windows** or earlier, so the cap is never what stops a game (no game was "still active after the maximum windows").
* Run time on the development machine: about 50 s for the 2534 games / 74490 windows, plus the same again for the built-in second replay (wall clock, **not** part of the deterministic report; ~1,450 windows/s).
* Determinism: the whole deterministic report (everything before `== PERFORMANCE`) is byte-identical across runs and across separate processes. The SHA-256 of the committed body (that report with trailing blank lines removed) is **`6f11aae39bddbf8ce865c824cba56077d120301c1f35b73cd8b96eb0bebe421a`**; the population trace digest (every game's trace, in order) is **`15c3e0493ca264d7bca2f402e174a462112bc956bd02ece8c939db82f18e74e9`**; the script replays all populations a second time and fails on any difference. The full report is committed as [MATCH_FLOW_MEASUREMENTS.md](MATCH_FLOW_MEASUREMENTS.md).
* CI only smoke-runs the script with `seeds=1 hg_seeds=1` and checks the exit code, the replay, `policy errors: 0` and `violations: 0`; **no measured frequency is gated**.

### Populations and policies (all scripted and seeded; fixed seeds `0 … N-1`)

| population | what varies | games |
| --- | --- | --- |
| **A** Mount-only | Mount policy × Mount defender × Top commitment; an entered Half Guard is then played with passes only | 22 cells |
| **B** Half Guard from **real** Mount entries | 5 distinct real Elbow-Knee exits (different stamina, interval, rule set) × 5 attackers × 5 defenders × commitment (MEDIUM, HIGH) | 250 cells |
| **C** bounded full flow | 5 Mount policies × 2 Half Guard attackers × 3 defenders, MEDIUM commitments | 30 cells |

Mount policies: `pass_only` (both fighters pass every window), `top_direct` (the Top cycles its non-finishing techniques, the Bottom passes), `top_finish` (the Top chases the Americana tap chain), `bottom_escape` (Elbow-Knee Escape when available, otherwise Bridge), `bottom_trap_roll` (Trap and Roll when available, otherwise Bridge), `seeded_legal` (uniform over the legal menu plus a pass). Mount defender: `first_available`, `last_available` (not used in the reports) or `seeded`. Half Guard attackers: `hg_pass`, `hg_direct_cycle`, `hg_feint_when_eligible` (seals the pair's feint; a refused feint is recorded and the apparent technique is played directly), `hg_prep_oriented` (Flatten / Underhook until the own track is Ready, then Knee Slice / Recover Guard), `hg_seeded_legal`. Half Guard defenders: `bite` (the best counter to the apparent technique), `call` (the best counter to the real technique the public view says may be concealed, otherwise to the apparent one), `balanced` (minimizes the attacker's worst case over the apparent and every eligible real technique), `fallback` (the published LOW timeout through `apply_response_timeout`), `seeded`. The counters are computed only from the published raw-grade table.

Every legal choice comes from the graph's own menus, windows and initiative; the harness never fabricates a transition and never touches a gateway directly. Two properties of the **existing** rules surfaced while building it and are modeled, not changed: Mount's production policy selects the **Bottom's commitment itself** (`commitment_is_policy_selected`), and a Mount Bottom decision can resolve as a **D3-B HOLD** (an accepted window with no exchange and no history entry, during which the Bottom recovers stamina).

## 2. The exact existing rules used (source links)

| rule | where |
| --- | --- |
| The graph coordinates outcomes; one settlement path (`_settle_accepted`) for direct, sealed and timeout resolutions; exits transition only through `_classify` / `_commit_or_halt`; admission order halted → ended → not enabled → wrong position | `GODOT_V1/scripts/positions/graph_match.gd`; `GODOT_V1/docs/POSITION_GRAPH.md` §15; `HALF_GUARD_V0_ENGINE.md` (B1i section) |
| 300 s clock, 5 s interval, capacity 100, axis 1.5 defaults | `GODOT_V1/scripts/positions/mount/mount_match.gd` (`configuration.get(...)`) |
| Windows, Bottom commitment selected by policy, `bottom_decision` kinds (UNARMED / ARMED_NORMAL / LOCKOUT_HOLD) | `mount/mount_window_gateway.gd`, `scripts/core/d3b_controller.gd`; `WINDOW_GATEWAY.md`, `MOUNT_LIFECYCLE.md` |
| Mount behavior stamina (a pass costs stamina each window), commitment funding and downgrade, exhaustion latch | `scripts/core/behavior_stamina_policy.gd`, `stamina_cost_policy.gd`, `commitment.gd`, `exhaustion_policy.gd`; `STAMINA_MIGRATION.md`, `EXCHANGE_SETTLEMENT.md` |
| Mount submission chain to a tap, exits and their destinations | `mount/mount_exchange.gd` (stage chain), `mount/mount_contract.gd` (`transition_for`), `POSITION_CONTRACT.md` |
| Half Guard grades, readiness, exits, **no recovery rule**, one clock step per window | `half_guard/half_guard_resolver.gd`, `half_guard_match.gd`, `HALF_GUARD_V0_RULES.md` §§3–7, 11 |
| Feint pairs, +3 surcharge, bite ±1, LOW-effective exit cap, published LOW fallback, public view | `half_guard/half_guard_catalog.gd`, `half_guard_match.gd`, `half_guard_sealed_protocol.gd`, `HALF_GUARD_V0_RULES.md` §13 |

## 3. STRUCTURAL verification (CI-gated)

`test_match_flow_invariants.gd` drives a fixed set of **real** games through the shared harness: 107 games, 3,198 observed windows, **16,973 rejected-command probes**, 13 real Mount → Half Guard transitions, 65 unsupported-exit halts, 42 ended matches (2 real taps), 1,173 Half Guard exchanges, 79 accepted feints, 314 published-fallback timeouts, and 23 Mount phases (982 windows) replayed on a bare Mount gateway. An observer checks every property live; a second run without the observer must give the identical trace and final state (so observing and probing change nothing). 14 disposable mutations of the graph and protocol were each detected.

| invariant | how it is checked |
| --- | --- |
| exactly one active positional owner | after every window and decision: the slots, the protocol's gateway identity and claim, and the frozen Mount segment (terminal, no window) |
| no forced positional transition | a decision with no exit label changes no position and appends no `transition_*` event; an exit produces exactly one outcome event; the position changes only through `transition_committed` |
| no duplicate stamina settlement | every Half Guard exchange: each fighter's stamina equals its value before minus the settlement's charge, surcharge included, once; every Mount phase equals a bare Mount gateway given the same commands |
| no clock advance from sealing | the Half Guard snapshot, the clock, the graph events and the window are unchanged by a seal; exactly one protocol event is added |
| no additional window from a feint | the window id and the clock do not move after a resolution; the number of `window_opened` events equals the windows opened |
| nothing accepted after a terminal outcome or a halt | after every ended or halted game: open, timed open, direct submit, pass, seal, feint seal, both views, response and timeout are all refused with their documented code and the whole state is unchanged |
| frozen previous-position state | after a transition the retained Mount views are compared at every later window |
| fighter identity and legal roles | `roles().fighter_by_role` equals the two ids at every step; continuity of identity, stamina, latch, meters, clock and window counter at every transition |
| whole-state equality for rejected commands | stale and foreign fighters, wrong position, no seal, duplicate seal, bypassing legacy submit, wrong serial, wrong responder, wrong fallback, a second window: refused with the exact code and `everything(g)` unchanged |
| deterministic replay | the digest and the final authoritative state are identical with and without the observer |
| Half Guard v0 has no recovery | its stamina never rose in any game (a window that opens in Half Guard also charges nothing) |
| one history entry per exchange; the published fallback's only consequence is the existing undercommitment step | history length equals the resolved exchanges of the active segment (Mount D3-B holds are accepted decisions with no exchange); the fallback's modifier equals what the funded commitments alone give, in every exchange |

## 4. Findings by question

Numbers are from the committed report; the pooled tables are in the appendix, every cell in [MATCH_FLOW_MEASUREMENTS.md](MATCH_FLOW_MEASUREMENTS.md).

**1. Can Mount sustain long sequences without an arbitrary forced transition? — STRUCTURAL + POPULATION. Yes.** `pass_only` runs all 59 windows (0 exchanges), `top_direct` runs 59 windows with 30 exchanges, and `bottom_trap_roll` runs 59 windows with 26 exchanges, with no transition. In the 107 games of the structural suite every transition followed a real accepted exit (the suite fails on any transition without one), and none of the 2,534 measured games ended by a forced change of position.

**2. How often do supported Mount outcomes occur? — POPULATION (policy-specific).** From Population A (pooled in the appendix): `pass_only` and `top_direct` end 100% by the clock; `top_finish` taps in 51 of 62 games (82%) and otherwise ends by the clock; `bottom_escape` enters Half Guard in 14 of 62 (23%); `bottom_trap_roll` never exits in 62 games; the legal random walk (`seeded_legal`, 120 games) taps in 36 (30%), enters Half Guard in 18 (15%), halts at a Mount `Open Guard` exit in 2 (2%) and otherwise ends by the clock. These are properties of those scripted policies only.

**3. How do stamina, exhaustion and commitment downgrades evolve? — POPULATION.** In Mount a pass costs stamina every window (both fighters 100 → 41 after 59 passes) and stamina can also rise in Mount (a rise in 9,763 windows over all games, 930 of the games' windows being D3-B HOLD windows; the source of each rise is not attributed here). A direct Top exhausts itself: `top_direct` ends with the Top at 0 and the Bottom at 14 (MEDIUM) / 25 (HIGH), with about 19 / 23 commitment downgrades per game (a requested commitment funded lower), and the Top is exhausted for most of the game (63 exhausted fighter-windows on average over 59 windows). Half Guard has **no recovery rule**: no Half Guard window ever raised stamina (0 windows), and a pass is free.

**4. Can Half Guard become stuck in repetitive exchanges without positional progress? — POPULATION; the cause is STRUCTURAL.** Yes. Two real mechanisms: (a) **pass-only** play never changes the state (Population B `pass`: every game ends by the clock after 59 windows with a no-progress streak of 59); (b) **exhaustion without recovery**: both fighters spend their stamina on exchanges that no longer change the axis or tiers. In the exchanging cells (200 cells, 1,720 games) 105 games (6%) contain a streak of 10 or more windows without any change of axis, band or readiness; the longest is **53 windows** (`entry 1 / feint_when_eligible / fallback / HIGH`; the previously stated 788 belonged to a different table's feint-attempt count, not to no-progress windows). It is concentrated in `feint_when_eligible` against `call`, `balanced` and `fallback` defenders (70% of those games). One examined game (entry 0, `feint_when_eligible` vs `call`): the Top's called feint wears the Bottom's frame to None, so the Bottom's own feint becomes ineligible (`feint_not_eligible` refusals, then direct play), both fighters fall to about 2 stamina by window 14, and a no-progress streak of 38 windows follows until the clock ends. Nothing penalizes this in B1e, by instruction.

**5. Do different defensive policies produce materially different trajectories? — POPULATION. Yes, strongly.** Against the same attacker (`feint_when_eligible`, Population B): `bite` halts 60% of games (Closed Guard 5, Open Guard 1) in 27.2 windows on average, while `call` and `balanced` halt only 30% (all Side Control) and end 70% by the clock in 43.0 windows. `prep_oriented` vs `call` halts every game (Open Guard 6, Closed Guard 4) in 8.2 windows; vs `bite`, 80% in 17.6 windows. The pooled tables list the final and extreme axis values per policy.

**6. How often are feints selected, accepted, effective or punished? — POPULATION.** Against `bite`: 34 feints accepted, 100% bit, 100% effective (grade ≥ Success). Against `call`: 39 accepted, 0% bit, 15% effective, 72% punished (grade ≤ Failure); `balanced`: 39 accepted, 18% effective, 72% punished. Against the published `fallback`: 26 accepted, 0% bit, 92% effective, 0% punished. Against the random walk defender: 707 accepted, 29% bit, 54% effective, 28% punished. Refusals are real: in the examined `call` game (entry 0) feints were refused 53 times (29 `feint_not_eligible` because a frame was worn, 24 `feint_requires_funding`) against 6 accepted; per-cell refusal codes are in the report.

**7. Does the LOW timeout fallback create only the approved disadvantage? — STRUCTURAL (verified) + POPULATION.** Over 3041 published-fallback exchanges the undercommitment +1 was applied in 1693 and was expected from the funded commitments alone in 1693; **any other modifier difference: 0**. Within the structural suite the same check runs in every fallback exchange (314). The defender's disadvantage is exactly the existing undercommitment step; no timeout-specific modifier, window, clock step or initiative exists.

**8. Are there reachable states where both fighters repeatedly pass or act ineffectively until the clock ends? — STRUCTURAL (reachable) + POPULATION.** Yes: both fighters passing in Mount for the whole clock (59 windows; the Mount positional fingerprint is unchanged for the last 54 of them, while stamina keeps falling by the per-window Mount cost), and in Half Guard for the whole clock at **zero** cost (Population B `pass`, 240 games). Exhausted fighters repeating ineffective exchanges is the second route (finding 4). There is no penalty because stalling is a separate, unimplemented rule family (Guide §§41–42).

**9. Does every completed transition preserve identities, stamina and match time? — STRUCTURAL. Yes.** Across the 68 Mount → Half Guard transitions in the populations: **0 violations** of identity, stamina, latch, meter, clock or window continuity; the structural suite checks the same at 13 more transitions and at every window.

**10. Determinism, state ownership, performance? — STRUCTURAL.** No determinism, ownership or performance problem was found: identical digests across runs and processes; the invariants held over every observed window; the harness sustained ~1,450 windows/s headless.

## 5. Observed design risks (not a to-do list)

**Demonstrated defects.** None found in the engine: every structural invariant held, including under mutation-sensitivity checks of the graph and the protocol. (Two **harness** defects of my own were found and fixed while building it — an explicit Bottom commitment the gateway correctly refused, and counting a D3-B hold as an exchange; both are why `policy errors` and the history check are hard failures.)

**Demonstrated properties of the current rules that may be design problems** (each is a deterministic consequence of rules as qualified):

1. A match can be played to the clock with both fighters passing, with no consequence (Mount: stamina falls 1 per window; Half Guard: free).
2. Half Guard has no stamina recovery, so after both fighters are depleted the position becomes a frozen no-progress state until the clock ends; there is no hold, reset or recovery analogue as in Mount.
3. Feint readiness is coupled to the opponent's governed defense: a called FP-1 feint wears the Bottom's frame, which can make the Bottom's FP-2 feint ineligible for the rest of the game.
4. 1,438 of 2534 measured games end at an unsupported exit (the positions behind Half Guard's three exits and Mount's `Open Guard` / `Reversal` do not exist yet), and 907 end by the clock with no result because scoring does not exist; the engine cannot yet finish a game.

**Possible balance concerns (evidence is policy-specific):**

5. The published fallback makes FP-1 feints "effective" in 92% of those games (a non-bite response is −1, the undercommitment +1 restores it): a timeout favors a feinting attacker.
6. Feint profitability swings from 100% effective (vs `bite`) to 15% effective and 72% punished (vs `call`): the intended rock-paper-scissors shape, but a defender that always calls never loses to a feint.
7. `bottom_trap_roll` never exits in 62 Mount games and `bottom_escape` exits in 23%: whether Mount escape pacing is acceptable is a design judgment.

## 6. Owner decisions to consider next (none is started here)

* Half Guard economy and recovery (a hold / recovery rule, or a pass cost), now with measured evidence of the depleted-stalemate state.
* The positional-stalling and priority rule family (Guide §§41–42), now with evidence that pass-only and depleted play can run to the clock.
* The next destination positions (Side Control, Closed Guard, Open Guard) and the unresolved Mount `Reversal`, since 57% of measured games halt at an unsupported exit.
* Scoring and adjudication for a clock end (907 of the 2,534 measured games).
* Whether the published fallback should keep a feint effective (finding 5).

## 7. Limits of this evidence

Policies are scripted or random walks, not players; Populations A and C use the default start (axis 1.5, 100 stamina), Population B uses five real entries; commitments are MEDIUM and HIGH; the default clock bounds every game at 59 windows; nothing was tuned, so no number here is a target.

## Appendix: pooled tables (the full per-cell tables are in the measurements file)

### Population A — Mount-only policies (pooled)

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only | 2 | 0 (0%) | 2 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 2 (100%) | +4.00 | +2.00 / +4.00 | - |
| top_direct | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 3 (5%) | +3.68 | +2.24 / +4.00 | - |
| top_finish | 62 | 51 (82%) | 11 (18%) | 0 (0%) | 0 (0%) | 0 | 26.4 | 13.7 | 0 | - | - | - | 0 | 4 (6%) | +3.97 | +2.26 / +4.00 | - |
| bottom_escape | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 14 (23%) | 0 | 59.0 | 25.1 | 0 | - | - | - | 0 | 24 (39%) | +2.37 | +0.97 / +3.98 | - |
| bottom_trap_roll | 62 | 0 (0%) | 62 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 14 (23%) | +2.82 | +1.50 / +4.00 | - |
| seeded_legal | 120 | 36 (30%) | 82 (68%) | 2 (2%) | 18 (15%) | 0 | 53.3 | 31.1 | 0 | - | - | - | 0 | 27 (22%) | +2.89 | +1.03 / +3.81 | mount:Open Guard 2 |

### Population A — time, entry and position time

**Time, entry and position time** (means over the cell's games; seconds are simulated clock seconds)
| cell | windows mean (min-max) | seconds mean | entered Half Guard | mean entry window | Mount windows mean | Half Guard windows mean | exchanges mean | passes mean | D3-B holds mean | longest pass streak max | longest idle streak max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| pass_only / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 0.0 | 59.0 | 0.0 | 59 | 59 |
| top_direct / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_direct / seeded / HIGH | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 30.0 | 29.0 | 0.0 | 1 | 1 |
| top_finish / first_available / MEDIUM | 41.0 (41-41) | 205.0 | 0/1 | - | 41.0 | 0.0 | 21.0 | 20.0 | 0.0 | 1 | 1 |
| top_finish / first_available / HIGH | 23.0 (23-23) | 115.0 | 0/1 | - | 23.0 | 0.0 | 12.0 | 11.0 | 0.0 | 1 | 1 |
| top_finish / seeded / MEDIUM | 23.5 (11-59) | 117.7 | 0/30 | - | 23.5 | 0.0 | 12.2 | 11.2 | 0.0 | 1 | 1 |
| top_finish / seeded / HIGH | 29.0 (11-59) | 146.5 | 0/30 | - | 29.0 | 0.0 | 15.0 | 14.0 | 0.0 | 1 | 1 |
| bottom_escape / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 16.0 | 43.0 | 0.0 | 27 | 27 |
| bottom_escape / first_available / HIGH | 59.0 (59-59) | 300.0 | 1/1 | 32.0 | 32.0 | 27.0 | 16.0 | 43.0 | 0.0 | 27 | 27 |
| bottom_escape / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 6/30 | 46.3 | 56.5 | 2.5 | 25.4 | 31.2 | 2.4 | 15 | 15 |
| bottom_escape / seeded / HIGH | 59.0 (59-59) | 300.0 | 6/30 | 46.3 | 56.5 | 2.5 | 25.4 | 31.2 | 2.4 | 15 | 15 |
| bottom_trap_roll / first_available / MEDIUM | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / first_available / HIGH | 59.0 (59-59) | 300.0 | 0/1 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / seeded / MEDIUM | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| bottom_trap_roll / seeded / HIGH | 59.0 (59-59) | 300.0 | 0/30 | - | 59.0 | 0.0 | 26.0 | 30.0 | 3.0 | 1 | 7 |
| seeded_legal / first_available / MEDIUM | 50.3 (27-59) | 253.8 | 5/30 | 8.8 | 42.0 | 8.4 | 28.2 | 20.7 | 1.4 | 57 | 57 |
| seeded_legal / first_available / HIGH | 48.3 (12-59) | 243.8 | 7/30 | 12.9 | 37.5 | 10.8 | 24.3 | 21.8 | 2.2 | 57 | 57 |
| seeded_legal / seeded / MEDIUM | 57.1 (37-59) | 290.2 | 2/30 | 46.0 | 56.3 | 0.9 | 37.0 | 17.5 | 2.7 | 15 | 15 |
| seeded_legal / seeded / HIGH | 57.4 (23-59) | 291.5 | 4/30 | 46.0 | 55.7 | 1.7 | 35.1 | 17.8 | 4.5 | 23 | 23 |

### Population A — stamina, exhaustion and commitment downgrades

**Stamina, exhaustion and commitment downgrades** (means; `downgrades` counts exchanges whose requested commitment was funded lower, either fighter)
| cell | min stamina top (mean) | min stamina bottom (mean) | games with an exhausted fighter | exhausted windows top+bottom (mean) | downgrades (mean) | windows where any stamina rose: Mount / Half Guard (total) |
|---|---|---|---|---|---|---|
| pass_only / first_available / MEDIUM | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| pass_only / first_available / HIGH | 41.0 | 41.0 | 0/1 | 0.0 | 0.0 | 0 / 0 |
| top_direct / first_available / MEDIUM | 0.0 | 14.0 | 1/1 | 63.0 | 19.0 | 19 / 0 |
| top_direct / first_available / HIGH | 0.0 | 25.0 | 1/1 | 62.0 | 23.0 | 13 / 0 |
| top_direct / seeded / MEDIUM | 0.0 | 13.2 | 30/30 | 64.6 | 19.0 | 582 / 0 |
| top_direct / seeded / HIGH | 0.0 | 25.0 | 30/30 | 62.0 | 23.0 | 390 / 0 |
| top_finish / first_available / MEDIUM | 0.0 | 14.0 | 1/1 | 38.0 | 10.0 | 13 / 0 |
| top_finish / first_available / HIGH | 0.0 | 28.0 | 1/1 | 12.0 | 5.0 | 0 / 0 |
| top_finish / seeded / MEDIUM | 14.0 | 18.3 | 21/30 | 14.5 | 2.7 | 146 / 0 |
| top_finish / seeded / HIGH | 8.1 | 36.1 | 16/30 | 22.8 | 8.5 | 132 / 0 |
| bottom_escape / first_available / MEDIUM | 0.0 | 19.0 | 1/1 | 82.0 | 5.0 | 7 / 0 |
| bottom_escape / first_available / HIGH | 0.0 | 19.0 | 1/1 | 82.0 | 5.0 | 7 / 0 |
| bottom_escape / seeded / MEDIUM | 0.0 | 19.0 | 30/30 | 75.7 | 14.4 | 609 / 0 |
| bottom_escape / seeded / HIGH | 0.0 | 19.0 | 30/30 | 75.7 | 14.4 | 609 / 0 |
| bottom_trap_roll / first_available / MEDIUM | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll / first_available / HIGH | 0.0 | 19.0 | 1/1 | 76.0 | 15.0 | 22 / 0 |
| bottom_trap_roll / seeded / MEDIUM | 0.0 | 19.0 | 30/30 | 76.0 | 15.0 | 660 / 0 |
| bottom_trap_roll / seeded / HIGH | 0.0 | 19.0 | 30/30 | 76.0 | 15.0 | 660 / 0 |
| seeded_legal / first_available / MEDIUM | 10.9 | 24.2 | 26/30 | 56.1 | 18.2 | 517 / 0 |
| seeded_legal / first_available / HIGH | 10.2 | 28.2 | 26/30 | 52.8 | 16.6 | 448 / 0 |
| seeded_legal / seeded / MEDIUM | 0.0 | 15.3 | 30/30 | 79.0 | 25.7 | 743 / 0 |
| seeded_legal / seeded / HIGH | 0.0 | 19.4 | 30/30 | 79.3 | 26.6 | 774 / 0 |

### Population B — Half Guard from real Mount entries (pooled by attacker and defender)

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass vs bite | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs call | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs balanced | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs fallback | 10 | 0 (0%) | 10 (100%) | 0 (0%) | 10 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 10 (100%) | +0.50 | +0.50 / +0.50 | - |
| pass vs seeded | 200 | 0 (0%) | 200 (100%) | 0 (0%) | 200 (100%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 200 (100%) | +0.50 | +0.50 / +0.50 | - |
| direct_cycle vs bite | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 16.6 | 16.6 | 0 | - | - | - | 0 | 2 (20%) | -0.80 | -2.30 / +2.10 | half_guard:Closed Guard 1, half_guard:Open Guard 3, half_guard:Side Control 4 |
| direct_cycle vs call | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 15.3 | 15.3 | 0 | - | - | - | 0 | 2 (20%) | +1.40 | -0.15 / +3.35 | half_guard:Closed Guard 1, half_guard:Side Control 7 |
| direct_cycle vs balanced | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 15.3 | 15.3 | 0 | - | - | - | 0 | 2 (20%) | +1.40 | -0.15 / +3.35 | half_guard:Closed Guard 1, half_guard:Side Control 7 |
| direct_cycle vs fallback | 10 | 0 (0%) | 4 (40%) | 6 (60%) | 10 (100%) | 0 | 28.2 | 28.2 | 0 | - | - | - | 282 | 0 (0%) | +0.60 | -0.30 / +3.10 | half_guard:Closed Guard 2, half_guard:Side Control 4 |
| direct_cycle vs seeded | 200 | 0 (0%) | 0 (0%) | 200 (100%) | 200 (100%) | 0 | 8.7 | 8.7 | 0 | - | - | - | 0 | 0 (0%) | +1.26 | -0.92 / +2.82 | half_guard:Closed Guard 40, half_guard:Open Guard 29, half_guard:Side Control 131 |
| feint_when_eligible vs bite | 10 | 0 (0%) | 4 (40%) | 6 (60%) | 10 (100%) | 0 | 27.2 | 27.2 | 34 | 34 (100%) | 34 (100%) | 0 (0%) | 0 | 1 (10%) | -1.80 | -2.65 / +2.95 | half_guard:Closed Guard 5, half_guard:Open Guard 1 |
| feint_when_eligible vs call | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 43.0 | 43.0 | 39 | 0 (0%) | 6 (15%) | 28 (72%) | 0 | 7 (70%) | +4.00 | -2.00 / +4.00 | half_guard:Side Control 3 |
| feint_when_eligible vs balanced | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 43.0 | 43.0 | 39 | 0 (0%) | 7 (18%) | 28 (72%) | 0 | 7 (70%) | +3.20 | -2.25 / +3.65 | half_guard:Side Control 3 |
| feint_when_eligible vs fallback | 10 | 0 (0%) | 7 (70%) | 3 (30%) | 10 (100%) | 0 | 42.9 | 42.9 | 26 | 0 (0%) | 24 (92%) | 0 (0%) | 429 | 7 (70%) | +3.20 | +0.35 / +3.85 | half_guard:Closed Guard 1, half_guard:Side Control 2 |
| feint_when_eligible vs seeded | 200 | 0 (0%) | 65 (32%) | 135 (68%) | 200 (100%) | 0 | 22.2 | 22.2 | 707 | 202 (29%) | 384 (54%) | 201 (28%) | 0 | 7 (4%) | +0.89 | -0.98 / +2.83 | half_guard:Closed Guard 52, half_guard:Open Guard 7, half_guard:Side Control 76 |
| prep_oriented vs bite | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 17.6 | 17.6 | 0 | - | - | - | 0 | 0 (0%) | -0.10 | -1.60 / +1.90 | half_guard:Closed Guard 4, half_guard:Side Control 4 |
| prep_oriented vs call | 10 | 0 (0%) | 0 (0%) | 10 (100%) | 10 (100%) | 0 | 8.2 | 8.2 | 0 | - | - | - | 0 | 0 (0%) | -3.70 | -3.70 / +0.40 | half_guard:Closed Guard 4, half_guard:Open Guard 6 |
| prep_oriented vs balanced | 10 | 0 (0%) | 2 (20%) | 8 (80%) | 10 (100%) | 0 | 17.0 | 17.0 | 0 | - | - | - | 0 | 2 (20%) | -0.75 | -2.50 / +1.25 | half_guard:Closed Guard 2, half_guard:Open Guard 2, half_guard:Side Control 4 |
| prep_oriented vs fallback | 10 | 0 (0%) | 0 (0%) | 10 (100%) | 10 (100%) | 0 | 5.4 | 5.4 | 0 | - | - | - | 54 | 0 (0%) | -2.45 | -2.90 / +0.75 | half_guard:Closed Guard 8, half_guard:Side Control 2 |
| prep_oriented vs seeded | 200 | 0 (0%) | 0 (0%) | 200 (100%) | 200 (100%) | 0 | 6.8 | 6.8 | 0 | - | - | - | 0 | 0 (0%) | +1.89 | -0.14 / +3.12 | half_guard:Closed Guard 42, half_guard:Open Guard 9, half_guard:Side Control 149 |
| seeded_legal vs bite | 200 | 0 (0%) | 58 (29%) | 142 (71%) | 200 (100%) | 0 | 25.4 | 17.0 | 94 | 94 (100%) | 94 (100%) | 0 (0%) | 0 | 16 (8%) | +0.20 | -1.97 / +2.58 | half_guard:Closed Guard 30, half_guard:Open Guard 20, half_guard:Side Control 92 |
| seeded_legal vs call | 200 | 0 (0%) | 56 (28%) | 144 (72%) | 200 (100%) | 0 | 25.2 | 16.8 | 71 | 0 (0%) | 14 (20%) | 54 (76%) | 0 | 21 (10%) | -0.14 | -2.05 / +2.28 | half_guard:Closed Guard 30, half_guard:Open Guard 33, half_guard:Side Control 81 |
| seeded_legal vs balanced | 200 | 0 (0%) | 65 (32%) | 135 (68%) | 200 (100%) | 0 | 27.0 | 18.1 | 80 | 0 (0%) | 20 (25%) | 48 (60%) | 0 | 22 (11%) | +0.09 | -1.98 / +2.40 | half_guard:Closed Guard 34, half_guard:Open Guard 17, half_guard:Side Control 84 |
| seeded_legal vs fallback | 200 | 0 (0%) | 14 (7%) | 186 (93%) | 200 (100%) | 0 | 15.2 | 9.8 | 97 | 0 (0%) | 90 (93%) | 3 (3%) | 1958 | 9 (4%) | +0.64 | -1.14 / +2.84 | half_guard:Closed Guard 63, half_guard:Open Guard 18, half_guard:Side Control 105 |
| seeded_legal vs seeded | 200 | 0 (0%) | 5 (2%) | 195 (98%) | 200 (100%) | 0 | 12.8 | 8.6 | 148 | 42 (28%) | 82 (55%) | 46 (31%) | 0 | 0 (0%) | +2.17 | -0.27 / +3.40 | half_guard:Closed Guard 33, half_guard:Open Guard 10, half_guard:Side Control 152 |

### Population C — bounded combinations (a Mount policy, then a Half Guard attacker against a named defender)

**Summary by policy** (all cells with the same policy pooled; percentages are of games)
| policy | games | ended by a tap | ended by the clock | halted at an unsupported exit | entered Half Guard | still active after the maximum windows | windows mean | exchanges mean | feints accepted | feints that bit | feints effective (grade >= Success) | feints punished (grade <= Failure) | fallbacks | games with a 10+ window no-progress streak | final axis mean | lowest / highest axis mean | unsupported-exit destinations (games) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pass_only -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| pass_only -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 0.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +2.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| top_direct -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 30.0 | 0 | - | - | - | 0 | 1 (100%) | +4.00 | +3.00 / +4.00 | - |
| bottom_escape -> feint_when_eligible vs bite | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 2 | 2 (100%) | 2 (100%) | 0 (0%) | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_escape -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 2 | 0 (0%) | 0 (0%) | 0 (0%) | 0 | 1 (100%) | +4.00 | +0.50 / +4.00 | - |
| bottom_escape -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 0 | - | - | - | 27 | 1 (100%) | +4.00 | +0.50 / +4.00 | - |
| bottom_escape -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 1 (100%) | 0 | 59.0 | 43.0 | 0 | - | - | - | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | - |
| bottom_escape -> prep_oriented vs call | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 0 | - | - | - | 0 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_escape -> prep_oriented vs fallback | 1 | 0 (0%) | 0 (0%) | 1 (100%) | 1 (100%) | 0 | 36.0 | 20.0 | 0 | - | - | - | 4 | 0 (0%) | -4.00 | -4.00 / +3.25 | half_guard:Closed Guard 1 |
| bottom_trap_roll -> feint_when_eligible vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> feint_when_eligible vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> feint_when_eligible vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs bite | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs call | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| bottom_trap_roll -> prep_oriented vs fallback | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 (0%) | 0 | 59.0 | 26.0 | 0 | - | - | - | 0 | 1 (100%) | +3.75 | +2.00 / +4.00 | - |
| seeded_legal -> feint_when_eligible vs bite | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 42.9 | 29.1 | 18 | 18 (100%) | 18 (100%) | 0 (0%) | 0 | 1 (3%) | +2.29 | +0.21 / +3.80 | half_guard:Closed Guard 5 |
| seeded_legal -> feint_when_eligible vs call | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 22 | 0 (0%) | 0 (0%) | 20 (91%) | 0 | 6 (20%) | +3.62 | +0.42 / +4.00 | - |
| seeded_legal -> feint_when_eligible vs fallback | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 8 | 0 (0%) | 8 (100%) | 0 (0%) | 251 | 6 (20%) | +3.62 | +0.96 / +4.00 | - |
| seeded_legal -> prep_oriented vs bite | 30 | 17 (57%) | 13 (43%) | 0 (0%) | 5 (17%) | 0 | 50.3 | 36.5 | 0 | - | - | - | 0 | 1 (3%) | +2.76 | +0.68 / +3.62 | - |
| seeded_legal -> prep_oriented vs call | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 42.6 | 28.8 | 0 | - | - | - | 0 | 1 (3%) | +2.36 | +0.28 / +3.62 | half_guard:Closed Guard 1, half_guard:Open Guard 4 |
| seeded_legal -> prep_oriented vs fallback | 30 | 17 (57%) | 8 (27%) | 5 (17%) | 5 (17%) | 0 | 43.2 | 29.4 | 0 | - | - | - | 36 | 1 (3%) | +2.29 | +0.21 / +3.62 | half_guard:Closed Guard 5 |
