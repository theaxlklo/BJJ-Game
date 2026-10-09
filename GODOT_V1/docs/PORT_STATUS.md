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

- Complete `MountMatch` aggregate: clock advancement/recovery controllers, non-Mount transitions, scoring and full lifecycle
- Complete production recovery policy: Bottom RECOVER and D3-B (exchange settlement and explicit Rule 1/2 selection are ported below)
- Custom setup/submission policies, Recognition, stalling and penalties (default exchange setup/Americana transitions are ported below)
- Generic PositionContract, stable Fighter IDs, Standing, non-Mount positions
- Real decision window/session timer, scoring modes, IBJJF rules table
- Memory Constellation, career, rewards, persistence and netcode
- Complete Python↔Godot parity corpus (initial Godot headless slice has passed)

## Headless tests

From repository root, with Godot 4.7.2 on PATH:

```bash
godot --headless --path GODOT_V1 --script res://tests/test_mount_slice.gd
```

The tests assert published Python reference cases (not only self-consistency). **Verified on a GitHub Actions Ubuntu runner using Godot 4.7.2 on 2026-10-09:** project import PASS; **40/40 initial Mount-slice assertions PASS**; 3D greybox startup (headless smoke check) PASS. [Verified workflow run](https://github.com/theaxlklo/BJJ-Game/actions/runs/37970015682). This does **not** establish full Python engine parity or visually certify the 3D scene.

Next: run the Godot headless test and collect independently generated Python `MountResolutionEngine` fixtures (including all 18 matchups, band boundaries, drift/escape overshoots and injected modifiers). Then port the remaining MountMatch responsibilities incrementally, verifying parity each step; do not rename a successful partial slice "full parity."

## Hard rules

- No GDScript resolution depends on frame ticks, animation, physics, UI or random draw.
- Python reference source and tests are immutable during parity migration.
- Any numeric change or legacy policy mismatch is reported and reviewed, never silently "fixed" during a port.
- Structural reuse must be shown with a second position before generalized match-engine claims.

## CI setup

The GitHub Actions workflow `.github/workflows/godot-v1.yml` runs when files under `GODOT_V1/` change, on pull requests, and via manual dispatch. It installs pinned Godot 4.7.2, imports the project, runs the Mount-slice tests, and smoke-tests the default 3D scene. [First passing test run](https://github.com/theaxlklo/BJJ-Game/actions/runs/37970015682). The implementation stays inside `GODOT_V1`; GitHub requires workflow definitions under `.github/workflows`.

## Independent Python-to-GDScript fixture comparison (new)

`tests/generate_mount_reference.py` invokes the original, unchanged Python `MountResolutionEngine`. It records the 18 frozen action/response matchups across band-history overlap, starting control values, behaviors, grade modifiers, override grades, and drift durations. `tests/test_mount_reference.gd` checks the GDScript results against that output field by field. GitHub Actions generates the fixture and runs the comparison.

This is **Mount-v0 resolution/drift parity only**, not complete stamina, setup, submissions, stalling or `MountMatch` parity. If this workflow fails, its mismatch log is authoritative evidence for the next correction.

```bash
PYTHONPATH=src python GODOT_V1/tests/generate_mount_reference.py
godot --headless --path GODOT_V1 --script res://tests/test_mount_reference.gd
```

## Stamina and commitment primitive slice

Five typed core modules now cover the pool/latch/bands, commitment costs and
funding, signed behavior carry, and default exhaustion modifiers. See
[STAMINA_MIGRATION.md](STAMINA_MIGRATION.md) for APIs, exact scope, numeric/type
boundaries, Python findings, and focused settlement/RECOVER/D3-B follow-up tasks.
This does not claim full MountMatch or production stamina/recovery parity.

```bash
PYTHONPATH=src python GODOT_V1/tests/generate_stamina_reference.py
godot --headless --path GODOT_V1 --script res://tests/test_stamina_reference.gd
godot --headless --path GODOT_V1 --script res://tests/test_stamina_boundaries.gd
```

The existing GitHub Actions Godot workflow now generates both reference corpora
and runs stamina parity/native boundary checks in addition to unchanged Mount
tests, project import and greybox startup. The existing Python CI qualification
workflow remains unchanged, including historical and frozen digest checks.

## Phase 19 exchange settlement

`BjjMountExchange` now implements validated integer-cost exchange settlement,
historical exhaustion, frozen v0.4a sequential grade transforms, response waiver,
legacy/supplemental hold controls, and default Ready/Americana integration.
`BjjProductionStaminaPolicy` selects Rule 1 ON / Rule 2 OFF separately; raw defaults
remain OFF. See [EXCHANGE_SETTLEMENT.md](EXCHANGE_SETTLEMENT.md) for source/API
mapping, test evidence, three explicitly approved terminal rejection differences,
strict admission boundaries and remaining dependencies. This is not full
MountMatch or production recovery parity. Issue #20 is the next controller slice.
