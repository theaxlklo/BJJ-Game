# Half Guard v0 typed GDScript engine (B1b)

**Status: provisional v0 prototype baseline, not final game balance.** Implements [HALF_GUARD_V0_RULES.md](HALF_GUARD_V0_RULES.md) (C1 grades, decisions N-1 … N-11) in typed GDScript and is compared, cell for cell, with the independent Python oracle ([HALF_GUARD_V0_ORACLE.md](HALF_GUARD_V0_ORACLE.md)).
It is a headless, deterministic position implementation. It changes **no** Mount, graph, F0 or F1 behavior and is **not connected to any of them**: nothing starts, enters, exports or renders Half Guard yet (the Mount edge adapter and graph integration are later slices).

## Files (`GODOT_V1/scripts/positions/half_guard/`)

| Class | Role |
| --- | --- |
| `BjjHalfGuardRules` | Constants and pure axis/band rules (integer tenths, hysteresis, legal pairs, authority, shift tables) |
| `BjjHalfGuardCatalog` | Stable ids, the 15 C1 raw grades, governed responses, builders, exit destinations, the transition dictionary |
| `BjjHalfGuardResolver` | Pure grade pipeline, exit decision and readiness updates (no state) |
| `BjjHalfGuardEntry` | Pure fighter-id-keyed entry validation (first failing code) |
| `BjjHalfGuardMatch` | **The single mutable owner of simulation state**: axis, band, initiative, both stamina pools, both readiness integers, clock, window record, histories; `attempt`, `open_window_for`, `decide` |
| `BjjHalfGuardContract` | `BjjPositionContract` adapter (roles, authority, initiative, options, low-level `submit`, `Transition`) |
| `BjjHalfGuardWindowGateway` | Production-facing facade: reports (`BjjMatchWindowGateway.Report`), detached views, `snapshot()` |

Shared stamina and commitment primitives are reused **unchanged** (`BjjStaminaPool`, `BjjStaminaCostPolicy`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade`, the `Meter` type). There is no generic tactical framework and no shared preparation type: the two readiness tiers are two integers in the match.

## API

```gdscript
var created := BjjHalfGuardWindowGateway.create(entry)      # entry: the neutral fighter-id-keyed request (rules sheet section 4)
var gateway := created.gateway                               # created.error is a stable code; nothing is built on error
var opened := gateway.open_window()                          # BjjMatchWindowGateway.Report; open_window_for(duration) is the session-owner seam
var report := gateway.submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)   # empty action = pass
gateway.state_fields(); gateway.history_fields(); gateway.roles(); gateway.window_fields(); gateway.snapshot()
gateway.action_options(fighter_id); gateway.response_options(action_id); gateway.selected_commitment()
gateway.controller_fields()    # {}  (no D3-B)           gateway.behavior_fields()   # {"top": "", "bottom": ""} (no behaviors)
```

A successful submit report carries `kind` (`exchange` | `reset`), `detail.settlement`, `transition` (`BjjPositionContract.Transition.fields()` semantics: `none`, or `exit` with a resolved `side_control` / `open_guard` / `closed_guard`), `ended` and a detached `state`.
Every refusal is a stable code with no mutation of any kind. There is no `carryover_segment()` (the export envelope is a later schema decision).

## Qualification evidence

| Suite | Pin | What it proves |
| --- | --- | --- |
| `test_half_guard_boundaries.gd` | 4,006 assertions | Negative-first: entry refusals and precedence, Godot-measured fighter-id edges, latch restoration against a literal hysteresis model, context corruption, command refusal precedence, windows and timeouts, pipeline and readiness literals, Rule 1 / paid effort, exits and transitions, contract addressing, detached views, determinism, scope and hygiene scans |
| `test_half_guard_reference.gd` | 49,609 assertions | Replays the oracle fixture (16,858 rows: bands, entries, 13,365 exchange-grid and 2,916 break-grid rows rebuilt from full snapshots, 10 window trajectories replayed twice) with 0 mismatches |
| `test_half_guard_conformance.gd` | 151 assertions | Report shapes, shared view keys and shared admission codes agree with the Mount window gateway; time advances identically |

The counts are measured by the suites and pinned in `.github/workflows/godot-v1.yml` and `tools/ci/test_validate_mount_slice_log.py`; they change only with a reviewed change to the suite or the oracle. A development-time mutation control (disposable edits, not committed) confirmed that ten engine mutations — the C0 grade, the defense shift, paid-effort preservation, the Rule 1 waiver, latch restoration, initiative on an exit, the pass line, a hysteresis threshold, LOW-defense strength and readiness consumption — are each detected by these suites.

## Known limitations

* Not connected to the graph, F0 or F1; no Mount edge adapter, no receiver, no carry-over export, no UI.
* No feints, sealed intent, behaviors, drift, recovery or D3-B (all explicitly later work). Direct techniques only.
* Stamina-state corruption (an out-of-range pool value) is not representable (the pool refuses it); context corruption is exercised through plain field assignment on the match.
* `BjjHalfGuardMatch.new()` is not a supported construction path; a match is built only from an entry request.
* The oracle fixture is large (tens of megabytes) and generated at test time; it is git-ignored.
