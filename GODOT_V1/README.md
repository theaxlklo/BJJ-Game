# GODOT_V1 — Isolated Godot implementation

The complete new Godot implementation stays inside this folder. Python code in `../src/` is the frozen behavioral reference, not a required runtime dependency of the shipped game.

## What is here now

- **Godot 4.7.2-stable**, standard typed GDScript project (`project.godot`).
- Minimal **3D Mount greybox** (`scenes/mount_debug.tscn`) with camera presets **1**, **2**, **3**.
- First parity-oriented decomposition: grade arithmetic, Mount rules, Mount action/response catalog, 18 matchup entries, action resolver, drift and position state.
- An initial Godot **headless test script**: `tests/test_mount_slice.gd`.
- [Port status, limitations, and parity contract](docs/PORT_STATUS.md).

## Open the project

1. Download and install [Godot 4.7.2-stable](https://godotengine.org/download/archive/4.7.2-stable/) (standard build).
2. In Godot's Project Manager, choose **Import** and select `GODOT_V1/project.godot`.
3. Press **F6** or **F5** to run the project; press **1/2/3** for alternate cameras.
4. The scene is a **visual placeholder**, not yet an interactive grappling match.

## Run headless Mount tests

From the repository root:

```bash
godot --headless --path GODOT_V1 --script res://tests/test_mount_slice.gd
```

Or from inside the `GODOT_V1` folder:

```bash
godot --headless --path . --script res://tests/test_mount_slice.gd
```

If Godot is not on PATH, use its executable's full path. Test results must be verified on a machine with Godot before marking the migration parity-pass.

## Source of truth

[Master Development Guide v10.4](../docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md).

**Boundaries:** No-Gi first, 3D greybox presentation, typed GDScript, deterministic simulation independent of physics/rendering, Python Mount behavior retained through measured parity. No scoring, careers, multiplayer or memory economy implemented in this slice.

## Next milestone

1. Run the current Godot headless tests and fix parser/runtime errors, if any.
2. Generate and compare actual frozen Python Mount fixtures.
3. Port stamina/commitment/Match orchestration **piece by piece**, not a 65KB monolith.
4. Extract a generic position contract and prove it with Side Control before moving to all ten positions.

Do not claim that complete MountMatch, full-game parity or playable BJJ are implemented yet.
