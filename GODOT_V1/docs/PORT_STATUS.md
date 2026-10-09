# GODOT_V1 — Migration status and parity contract

## Version / scope

- Godot **4.7.2-stable** (standard GDScript release) is the initial pinned target.
- Python reference sources remain in `../src/bjj_game/`, untouched.
- This is a **migration slice**, not a playable complete match and not a verified full-engine rewrite.
- The 3D scene is a greybox preview; it is NOT wired into the authoritative state resolver.

## Initial modules

| Godot code | Python reference | Port status |
|---|---|---|
| `scripts/core/grade.gd` | `domain/model.py::Grade` | Implemented slice |
| `scripts/positions/mount/mount_rules.gd` | `positions/mount/rules.py` | Axis, band, drift rates and modifiers |
| `scripts/positions/mount/mount_catalog.gd` | `positions/mount/catalog.py`, `matchups.py` | Frozen v0 12-entity / 18-lookup table; no modern finish |
| `scripts/positions/mount/mount_resolver.gd` | `engine/mount_engine.py::resolve_action` | Core deterministic exchange, no match orchestration |
| `scripts/positions/mount/mount_drift.gd` | `engine/mount_engine.py::simulate_drift` | Per-second drift, clock, band-change events |
| `scripts/positions/mount/mount_position.gd` | `positions/mount/{axis,position}.py` | Persisted control / terminal crossing split |
| `scenes/mount_debug.tscn` | New | Visual placeholder with 3 camera presets |

## Still NOT ported

- `MountMatch` aggregate: initiative, five-minute clock lifecycle, transitions between positions, histories
- Commitment/stamina/exhaustion and production stamina policy
- Setup, Americana Threat/Control/Finish, Recognition, stalling and penalties
- Generic PositionContract, stable Fighter IDs, Standing, non-Mount positions
- Real decision window/session timer, scoring modes, IBJJF rules table
- Memory Constellation, career, rewards, persistence and netcode
- Complete parity corpus / verified Godot headless runs

## Headless tests

From repository root, with Godot 4.7.2 on PATH:

```bash
godot --headless --path GODOT_V1 --script res://tests/test_mount_slice.gd
```

The tests assert published Python reference cases (not only self-consistency). They do not establish full parity. **Godot CLI has not been run in this environment**, so parser/runtime execution needs verification before calling this phase passed.

Next: run the Godot headless test and collect independently generated Python `MountResolutionEngine` fixtures (including all 18 matchups, band boundaries, drift/escape overshoots and injected modifiers). Then port the remaining MountMatch responsibilities incrementally, verifying parity each step; do not rename a successful partial slice "full parity."

## Hard rules

- No GDScript resolution depends on frame ticks, animation, physics, UI or random draw.
- Python reference source and tests are immutable during parity migration.
- Any numeric change or legacy policy mismatch is reported and reviewed, never silently "fixed" during a port.
- Structural reuse must be shown with a second position before generalized match-engine claims.
