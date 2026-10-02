# BJJ Mount v0 Prototype

A dependency-free implementation of the frozen **Mount v0** rules for the tactical BJJ roguelike.

Sources of truth included under `docs/`:

- `BJJ_Game_Concept_Current_Recap_v9_CODE_READY_FREEZE.md`
- `Mount_v0_Canonical_BJJ_Technique_Naming_Lock_REVISED.md`
- `Mount_v0_Final_Playtest_Tuning.md` — final evidence-driven Elbow-Knee branch override after logged playtesting

The implementation also includes the final coding cleanups agreed after the revised naming lock:

- `Tight-Elbow Arm Defense` keeps its name; its meaning is compact elbows that defend the High Mount climb and Americana isolation while leaving the head/shoulder line open to Crossface Pressure.
- `--enumerate` reports `NEVER-BEST (hedge response)` for `Turn-In Recovery` and `Wide Mount Base`; this is informational, not an error.
- name normalization replaces `+` and `&` as characters before separator normalization, and `Repummel` is accepted as an alias.

## What is implemented

- 12 canonical action/response entities with stable IDs and aliases
- corrected 18-entry deterministic BJJ matchup matrix
- result-grade ladder and initiator-relative axis direction
- behavior drift with 1-second ticks
- drift clamp to `+0.10..+4.00`
- `PRESSURE`, `HOLD`, `ESCAPE`, `PROTECT`
- HOLD and PROTECT behavior modifiers
- visible-band positional modifiers
- full hysteresis, including multi-band jumps
- Bridge special rule
- failure clamp
- Elbow-Knee Escape → band-constrained Half Guard/Open Guard Exit Map
- Trap-and-Roll Escape → Reversal Exit Map
- partial final intervals with real start/end clock values
- alternating Top/Bottom v0 initiative scaffold
- command-line hot-seat play
- full decision/drift logging and run summary
- `--enumerate` exhaustive checker
- perfect-response-lock diagnostic
- never-best hedge-response diagnostic
- automated branch-reachability and naming-invariant checks
- full Section 58 branch-range reporting by visible band and Top behavior
- Trap-and-Roll/HOLD reachability comparison
- persistent `--log PATH` text-session logging
- exact hot-seat input capture in text logs, including blank/invalid entries
- cancellation summaries on `Ctrl+C` / `Ctrl+D`, marked `CANCELLED`
- readable short-name histories in run summaries

## Run without installing

Primary OOP entry point:

```bash
PYTHONPATH=src python -m bjj_game --check
PYTHONPATH=src python -m bjj_game --enumerate
PYTHONPATH=src python -m bjj_game
PYTHONPATH=src python -m bjj_game --log logs/session-001.txt
```

Targeted run:

```bash
PYTHONPATH=src python -m bjj_game --axis 0.50 --clock 0:30 --interval 7 --log logs/session-001.txt
```

Blind hot-seat playtest mode:

```bash
PYTHONPATH=src python -m bjj_game --blind --log logs/blind-session.txt
```

Solo seeded blind playtest mode:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed 42 \
  --log logs/blind-seed-42.txt
```

For clean behavior experiments, either side can be fixed for the entire session:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed 42 \
  --top-behavior PRESSURE \
  --bottom-behavior ESCAPE \
  --log logs/pressure-vs-escape-seed-42.txt
```

Supported fixed values:

```text
--top-behavior PRESSURE|HOLD|CONSERVE
--bottom-behavior ESCAPE|PROTECT|CONSERVE
```

A fixed side is not re-prompted between windows. The other side stays interactive when only one behavior flag is supplied.

In `--blind`, the responder locks a response before the initiator chooses an action or RESET. Human mode hides the typed response with `getpass`. Random mode uses a deterministic seeded policy and reveals/logs the selected response only after the initiator commits, so one person can run genuinely blind sessions.

Current fixed random-response mixes:

```text
Bottom responding to Top:
Frame : Tight Elbows = 4 : 3
Turn-In = 0

Top responding to Bottom:
Wide Base : Hip Follow = 2 : 1
Post = 0
```

The seed and every random draw/response are written to the session log for replay. This changes input order only; resolution mechanics are unchanged. The legacy `mount_v0` path rejects blind-testing flags.

Legacy compatibility remains available during migration:

```bash
PYTHONPATH=src python -m mount_v0 --check
PYTHONPATH=src python -m mount_v0 --enumerate
PYTHONPATH=src python -m mount_v0
```

## Install editable

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
bjj-game --check
bjj-game --enumerate
bjj-game
```

`mount-v0` remains installed as a legacy alias.

## Test

No third-party test runner is required:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

CI runs the full suite and both semantic-check entry points on Python 3.11 and 3.13.

## Mount v0.1a — stamina telemetry

The first v0.1 slice is now present as **state only**. Every `Competitor` owns an independent `StaminaPool`; the CLI can start Top and Bottom at any value from 0–100 and reports the observational band.

```bash
PYTHONPATH=src python -m bjj_game \
  --top-stamina 75 \
  --bottom-stamina 25
```

Current bands are observational quartiles:

```text
76–100  Fresh
51–75   Working
26–50   Tired
0–25    Exhausted
```

**Stamina has no mechanical effect in v0.1a.** It does not change grades, drift, axis movement, clamps, exits, or action availability.

The exact frozen v0 `--enumerate` output is protected by SHA-256 regression test:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

See `docs/MOUNT_V0_1A_STAMINA.md`.

## Mount v0.1b — commitment + stamina costs

The primary `bjj_game` flow now wraps each initiated action in an `ActionAttempt` with explicit commitment:

```text
LOW       3 stamina requested
MEDIUM    7 stamina requested
HIGH     12 stamina requested
```

These are prototype cost values. Commitment changes stamina cost only in v0.1b; LOW/MEDIUM/HIGH do **not** change the frozen Mount grade or axis resolution yet.

`MountMatch.attempt()` charges the initiator and records `before / requested / charged / shortfall / after`. If the fighter cannot fully pay, the remaining stamina is charged, shortfall is logged, and the action still resolves normally. Recovery and exhaustion consequences come later.

The legacy `mount_v0` CLI keeps the old prompt sequence and calls cost-free `decide()`.

See `docs/MOUNT_V0_1B_COMMITMENT.md`.
## Mount v0.1c — behavior stamina + CONSERVE

The normal-speed behavior layer now has a stamina economy:

```text
PRESSURE   -1 / 5s
ESCAPE     -1 / 5s
HOLD        0 / 5s
PROTECT     0 / 5s
CONSERVE   +2 / 5s
```

`CONSERVE` projects onto HOLD/PROTECT for positional drift but does **not** inherit their special resolution modifier. Five 1-second windows equal one 5-second window through fixed-point carry.

Standard play defaults commitment to `MEDIUM` because LOW still strictly dominates while commitment has no outcome effect. Use `--commitment LOW|MEDIUM|HIGH` for targeted tests.

Underfunded commitment downgrades to the highest fully payable level; at zero stamina it becomes `UNFUNDED`, preventing future HIGH effects from being free.

See `docs/MOUNT_V0_1C_CONSERVE.md`.
## Mount v0.1e — exhaustion consequence

v0.1e was intentionally implemented before v0.1d so STABILIZE can be designed against a stamina system that already matters.

Minimal rule:

```text
Initiator starts the action Exhausted
→ final initiated-action grade -1
```

Exhaustion now has 25/35 hysteresis: enter at <=25, but once exhausted you must recover to >=35 before the penalty clears. The band is read before the action's commitment cost is paid. If the current action pushes the fighter into Exhausted, the penalty begins on their next initiation.

`bjj_game --check` now reports projected time to Exhausted and zero stamina for LOW/MEDIUM/HIGH under active PRESSURE/ESCAPE, plus exhausted escape reachability and the v0.2 responder-stamina debt. The current costs are intentionally left unchanged until playtests produce evidence.

Behavior-stamina logs always include fixed-point carry so partial recovery/spend across behavior changes is visible.

The modern v0.1 flow also offers **RESET / NO ACTION**. It yields the current attack window with no action cost or immediate axis change, allowing CONSERVE to recover from Exhausted instead of forcing another paid technique every 10 seconds. Repeated RESET is explicitly tracked as a future stalling-system debt.

`StaminaPool.current` is read-only; supported mutation routes all refresh the 25/35 exhaustion latch. Latched displays explain the recovery threshold, e.g. `30/100 (Exhausted — recovers at 35)`.

See `docs/MOUNT_V0_1E_EXHAUSTION.md`.
## Known v0 limitation

The responder sees the exact initiated action and has unrestricted access to every response. Every action therefore has a Failure-or-worse best counter. `--enumerate` reports:

```text
PERFECT-RESPONSE LOCK: PRESENT
Classification: KNOWN V0 SCAFFOLDING LIMITATION
```

The matrix is intentionally **not** distorted to fix this. v0.2 setup/Ready/initiative legality is the planned layer that can restrict which responses are actually available or tactically valid.

For v0.1 playtests, `bjj_game --blind` can remove the full-information response advantage without changing the matrix: the responder commits before the initiated action is shown. `--blind-responder random --seed N` makes that usable in solo sessions. This is a testing mode, not the final v0.2 information model.

Bridge remains a known v0 setup limitation: in the raw matrix Trap-and-Roll is at least as good against every response and has the stronger Hip Follow result plus an escape branch. Bridge is being left intact for v0.2 setup/Ready work rather than receiving an ad-hoc stamina discount.

## Batch behavior experiments

For repeatable statistics instead of one seed at a time:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 1000 \
  --initiator-policy escape-first \
  --seed 42 \
  --top-behavior HOLD \
  --bottom-behavior CONSERVE
```

Batch mode is non-interactive. It automatically uses the fixed seeded random-response mix; do not combine it with `--blind`.

Each match uses:

```text
match 0 → seed 42
match 1 → seed 43
match 2 → seed 44
...
```

Using the same base seed and match count across two behavior conditions therefore pairs comparable response streams.

The official `escape-first` initiator policy is deliberately lexicographic:

```text
at the exact current axis/band/stamina state
→ if any action can escape, choose the highest exact escape probability
→ otherwise require BOTH raw attacker-axis > 0 and realized attacker-axis > 0
→ among those positional attacks, choose the highest realized expectation
→ otherwise RESET
```

It includes current behavior, positional, exhaustion, floor, and cap effects. Escape is a lexicographic priority rather than a numeric bonus, so there is no hidden terminal-value conversion. Positional attacks must stay favorable both before and after clamping, which filters cap-only/floor-only gains. The policy does **not** assign a numeric value to Half Guard, Open Guard, Reversal, stamina, or time; it is a reproducible test rule, not an optimal-opponent model.

Batch output reports outcome frequencies, mean/median final stamina, mean final axis, RESET counts, and action counts by side.

Open Guard is unreachable under the fixed batch response mix because Hand Post and Base has zero response weight. `bjj_game --check` derives and reports unreachable Exit Map destinations automatically rather than hiding that limitation.

Fixed-behavior batches measure extreme conditions such as HOLD-vs-CONSERVE or HOLD-vs-PROTECT. They do not answer whether short bursts of CONSERVE are useful; adaptive human sessions are still required for that question.

### Per-band blind-mix diagnostics

`bjj_game --check` reports every action against the fixed random-response mix by visible band using two separate signals:

- **raw attacker-axis** — expected grade-derived axis delta from the initiator's perspective after behavior and positional grade modifiers, before floor/cap handling.
- **realized-axis** — min..max expected actual attacker-favorable axis movement across the legal 0.01 axis grid after floor/cap handling; escape crossings use the resolver's crossing axis.
- **escape** — the min..max escape probability across the same legal axis grid.

MEDIUM's 7-stamina action cost is printed separately. The checker never converts stamina or an escape into axis points and never emits a combined utility score.

The baseline for these lines is Top PRESSURE / Bottom ESCAPE with no exhaustion penalty. The realized range matters at the edges. For example, Top's raw Loose values are negative, but the Mount-floor clamp limits failures, so Americana can have positive realized-axis expectation within Loose. At Locked, the reverse can happen: upside is capped at +4.00 while failures still lose position, making realized expectation worse than the raw grade average.

## Final Elbow-Knee playtest tune

Eight logged pre-tune sessions plus two post-tune regression replays resolved the final Section 58 question. Mount v0 now uses the visible band as a branch constraint after the escape threshold is reached:

```text
Success → Half Guard
Strong Success from Loose → Open Guard
Strong Success from Stable → Half Guard
```

`--enumerate` reports the resulting ranges:

```text
Elbow-Knee Escape → Half Guard: +0.10..+2.10
Elbow-Knee Escape → Open Guard: +0.10..+1.19 (Loose only)
Trap-and-Roll → Reversal with PRESSURE: +0.10..+2.10
Trap-and-Roll → Reversal with HOLD: +0.10..+1.10
```

The numerical overshoot still does not choose the branch; the final grade plus the already-visible band does. See `docs/Mount_v0_Final_Playtest_Tuning.md` and `docs/PLAYTEST_REPORT.md`.

## Object-oriented architecture

The frozen Mount v0 mechanics now run through the `bjj_game` object model. The historical `mount_v0` package remains as a compatibility facade so the original v0 regression suite and command line continue to work unchanged.

Core responsibilities are separated deliberately:

- `Competitor` owns grappler identity and current behavior now; v0.1 stamina/commitment and later belt/style/injury/run state attach here through composition.
- `MountMatch` owns mutable match state: competitors, clock, current position, initiative, history and exit state.
- `MountPosition` owns the Mount positional state; future positions can implement the same `Position` abstraction.
- `MountAxis` is the only persisted Mount-control state writer. It always stays inside `+0.10..+4.00`; escape overshoot is stored separately on `MountPosition`.
- `MountRuleSet` owns frozen Mount thresholds, drift rates, positional modifiers and Exit Map policy. Technique-specific behavior sensitivities and special-clamp metadata live in the catalog.
- `TechniqueCatalog` owns canonical technique/response definitions and lookup indexes.
- `MatchupTable` owns the 18 hand-authored deterministic BJJ grades.
- `MountResolutionEngine` resolves drift and exchanges without owning mutable match state. Its rule set, catalog and matchup table are explicit constructor-injected dataclass fields; `default()` wires production v0 dependencies.
- `diagnostics` and `interfaces` are separated from the domain/engine so future UI layers do not need to rewrite grappling mechanics.

The design favors composition over deep inheritance. Techniques, behaviors, belts, styles and future stamina/commitment are data/state attached to domain objects rather than subclass trees. The CLI uses competitor-owned behavior; method behavior arguments remain only for frozen v0 API compatibility.

Primary entry point:

```bash
PYTHONPATH=src python -m bjj_game --check
PYTHONPATH=src python -m bjj_game --enumerate
PYTHONPATH=src python -m bjj_game
```

The legacy commands remain supported:

```bash
PYTHONPATH=src python -m mount_v0 --check
```

### Refactor safety gate

The architecture-hardening pass changed architecture only, not Mount v0 mechanics. The original 44 tests still pass unchanged, 13 architecture tests now cover real dependency injection, data-driven special rules, competitor-owned behavior, and legal persisted-axis state; `--enumerate` remains byte-identical to the pre-hardening build.

## Blunder playtests

Sessions 11 and 12 in `docs/playtest/` show what happens when one player picks a bad move: a Bottom blunder that jumps Top from Stable to Locked, and a Top blunder that is clamped at Loose and then punished with Open Guard. `tests/test_blunder_replays.py` replays both. See the "Blunder sessions" section of `docs/PLAYTEST_REPORT.md`.

## Session logging and cancellation

Interactive `--log` sessions record both game output and the exact text entered at each prompt. This includes numeric menu choices, aliases, invalid entries, and blank Enter presses. The tee delegates terminal TTY/file-descriptor behavior to the real stdout so normal terminal input behavior is preserved.

If an interactive run is interrupted with `Ctrl+C` or reaches EOF (`Ctrl+D` on a terminal), Mount v0 prints and logs a partial run summary before exiting with status 130. The summary is explicitly marked:

```text
Run status: CANCELLED
Exit reason: CANCELLED
```

Elapsed simulated time, current axis/band, histories, initiation counts, clamps, and threshold state are preserved up to the interruption point.
