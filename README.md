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

```bash
PYTHONPATH=src python -m mount_v0 --check
PYTHONPATH=src python -m mount_v0 --enumerate
PYTHONPATH=src python -m mount_v0
PYTHONPATH=src python -m mount_v0 --log logs/session-001.txt
```

Targeted run:

```bash
PYTHONPATH=src python -m mount_v0 --axis 0.50 --clock 0:30 --interval 7 --log logs/session-001.txt
```

## Install editable

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
mount-v0 --check
mount-v0 --enumerate
mount-v0
```

## Test

No third-party test runner is required:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Known v0 limitation

The responder sees the exact initiated action and has unrestricted access to every response. Every action therefore has a Failure-or-worse best counter. `--enumerate` reports:

```text
PERFECT-RESPONSE LOCK: PRESENT
Classification: KNOWN V0 SCAFFOLDING LIMITATION
```

The matrix is intentionally **not** distorted to fix this. v0.2 setup/Ready/initiative legality is the planned layer that can restrict which responses are actually available or tactically valid.

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

- `Competitor` owns grappler identity/state and is the extension point for v0.1 stamina, then later belt/style/injury/run state.
- `MountMatch` owns mutable match state: competitors, clock, current position, initiative, history and exit state.
- `MountPosition` owns the Mount positional state; future positions can implement the same `Position` abstraction.
- `MountAxis` owns the positional control value and visible hysteresis band.
- `MountRuleSet` owns frozen Mount thresholds, drift rates, behavior modifiers, positional modifiers and Exit Map policy.
- `TechniqueCatalog` owns canonical technique/response definitions and lookup indexes.
- `MatchupTable` owns the 18 hand-authored deterministic BJJ grades.
- `MountResolutionEngine` resolves drift and exchanges without owning mutable match state.
- `diagnostics` and `interfaces` are separated from the domain/engine so future UI layers do not need to rewrite grappling mechanics.

The design favors composition over deep inheritance. Techniques, belts, styles and future stamina/commitment are data/state attached to domain objects rather than subclass trees.

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

The OOP migration changed architecture only, not Mount v0 mechanics. The original 44 tests pass unchanged, six architecture tests were added, `--enumerate` is byte-identical to the pre-refactor build, and the Session 11/12 blunder replay logs are byte-identical apart from the absolute `LOG FILE` path line.


## Blunder playtests

Sessions 11 and 12 in `docs/playtest/` (also in `playtest_logs/blunders/`) show what happens when one player picks a bad move: a Bottom blunder that jumps Top from Stable to Locked, and a Top blunder that is clamped at Loose and then punished with Open Guard. `tests/test_blunder_replays.py` replays both. See the "Blunder sessions" section of `docs/PLAYTEST_REPORT.md`.

## Session logging and cancellation

Interactive `--log` sessions record both game output and the exact text entered at each prompt. This includes numeric menu choices, aliases, invalid entries, and blank Enter presses. The tee delegates terminal TTY/file-descriptor behavior to the real stdout so normal terminal input behavior is preserved.

If an interactive run is interrupted with `Ctrl+C` or reaches EOF (`Ctrl+D` on a terminal), Mount v0 prints and logs a partial run summary before exiting with status 130. The summary is explicitly marked:

```text
Run status: CANCELLED
Exit reason: CANCELLED
```

Elapsed simulated time, current axis/band, histories, initiation counts, clamps, and threshold state are preserved up to the interruption point.
