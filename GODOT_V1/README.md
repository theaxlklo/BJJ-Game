# GODOT_V1 — Godot implementation workspace

This directory is the **isolated home of the Godot 4 / typed GDScript implementation** of BJJ Game. New Godot-related project files, scripts, scenes, 3D prototypes, UI, tests and assets belong under `GODOT_V1/`, not mixed into the existing Python engine directories.

## Design authority

Read [the Master Development Guide v10.4](../docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md) for accepted game rules and implementation priorities.

## Boundaries

- **Preserve the existing Python code** as the frozen behavioral reference while migrating. Do not delete or rewrite it as part of directory setup.
- Port Mount by **decomposing** shared match, stamina, resolution, timing and technique responsibilities from Mount-specific position rules; use **typed GDScript**.
- Keep the simulation deterministic and independent of Godot rendering, frame rate, animations and physics. Verify parity against Python reference traces and tests before replacing that reference.
- Start with a small playable **3D greybox** and position-aware cameras; do not require final animations for headless match logic.
- **No-Gi first**. Plan both IBJJF rules-based points and custom Submission-Only modes.
- New positions should reuse shared contracts and resolver behavior, not copy `MountMatch`.
- Do not implement career, Memory Constellation or multiplayer prematurely; retain design boundaries for them.

## Planned layout (not created yet)

```text
GODOT_V1/
  project.godot              # Godot project root
  scripts/
    core/                    # Deterministic match and fighter systems
    positions/mount/         # Mount-specific rules
    positions/                # Future positions and shared position contract
    techniques/              # Catalog and matchup rules
    progression/             # Later career/memory systems
    presentation/            # Camera/UI adapters, not match authority
  scenes/                    # 3D greybox and presentation
  tests/                     # Headless parity and deterministic regression tests
  assets/                    # Godot-only visuals and audio
```

Only this README exists at directory initialization. Add subdirectories and files when each migration slice genuinely needs them.

## First migration milestone

1. Pin the Godot version and establish reference Python Mount traces.
2. Port the smallest shared domain/resolution slice into typed GDScript.
3. Port the Mount-specific rules without changing their semantics.
4. Verify exact or explicitly justified parity for action results, clock, stamina, bands, positional exits and replay.
5. Validate reuse with a second position before expanding to the full position graph.
