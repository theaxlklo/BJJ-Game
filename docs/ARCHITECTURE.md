# BJJ Game Architecture

## Status

Mount v0 mechanics are frozen. This document describes the object-oriented structure used to carry those mechanics into v0.1 and later positions without changing their results.

## Design goals

- Keep BJJ matchup knowledge data-driven.
- Put mutable state on domain objects instead of global variables.
- Separate match state from resolution policy.
- Keep position-specific rules local to the position.
- Make later positions composable rather than adding `if position == ...` branches throughout the engine.
- Preserve the original `mount_v0` API while migration is in progress.
- Prefer composition over deep inheritance.

## Package layout

```text
src/
├── bjj_game/
│   ├── domain/
│   │   ├── catalog.py
│   │   ├── competitor.py
│   │   ├── matchup.py
│   │   ├── model.py
│   │   └── names.py
│   ├── engine/
│   │   ├── match.py
│   │   └── mount_engine.py
│   ├── positions/
│   │   ├── base.py
│   │   └── mount/
│   │       ├── axis.py
│   │       ├── catalog.py
│   │       ├── compat.py
│   │       ├── matchups.py
│   │       ├── names.py
│   │       ├── position.py
│   │       └── rules.py
│   ├── diagnostics/
│   │   └── checker.py
│   └── interfaces/
│       ├── cli.py
│       └── formatting.py
└── mount_v0/
    └── compatibility facade
```

## Core objects

### `Competitor`

Represents a grappler. v0 stores identity and side only. v0.1 stamina and later belt/style/attribute/injury/run state belong here or in composed objects owned by the competitor.

### `MountMatch`

The aggregate root for the current prototype. It owns:

- top and bottom competitors
- simulated clock
- current `MountPosition`
- scheduled initiator
- history
- exit state

It does not contain the grade-resolution formulas; those live in the resolution engine and rule set.

### `Position` / `MountPosition`

`Position` is the common positional abstraction. `MountPosition` contains Mount-specific state today. Future `HalfGuardPosition`, `ClosedGuardPosition`, `SideControlPosition`, `BackControlPosition`, `TurtlePosition`, `StandingPosition`, etc. can be introduced without converting the engine into a large position switch statement.

### `MountAxis`

Owns the numeric Mount control state and its visible hysteresis band. Mount-specific threshold policy remains centralized in `MountRuleSet`.

### `MountRuleSet`

Owns the frozen v0 rules:

- `+0.10..+4.00` persisted Mount range
- initial bands
- hysteresis thresholds
- drift rates
- HOLD/PROTECT behavior modifiers
- positional modifiers
- exit-destination policy, including the final Elbow-Knee playtest tune

### `TechniqueCatalog`

Indexes canonical technique and response definitions by stable ID. Mechanics reference stable IDs, never player-facing strings.

### `MatchupTable`

Contains the 18 hand-authored action/response grades. The BJJ judgments remain data rather than being hidden in technique subclasses.

### `MountResolutionEngine`

A stateless/injectable service that resolves:

- drift
- raw matchup grade
- behavior modifier
- positional modifier
- grade clamp
- axis delta
- Bridge/failure clamp
- escape threshold
- Exit Map

It receives state and returns immutable result objects. `MountMatch` applies those results to mutable match state.

## Compatibility policy

The `mount_v0` package is intentionally retained as a facade. Existing imports such as:

```python
from mount_v0.engine import MountRun
from mount_v0.mechanics import resolve_action
```

continue to work, but the implementation lives in `bjj_game`.

This gives us a migration path without discarding the regression suite or breaking playtest tooling.

## v0.1 extension points

Stamina should be added without reworking the positional engine:

```text
Competitor
└── Stamina

ActionAttempt
├── Technique
└── Commitment

MountResolutionEngine
└── consumes stamina/commitment policy as an additional modifier source
```

Recommended new objects:

- `StaminaPool`
- `StaminaBand`
- `Commitment`
- `ActionAttempt`

`CONSERVE` and `STABILIZE` should be behaviors/policies, not competitor subclasses.

## Refactor proof

The OOP migration is behavior-preserving:

- original v0 tests: 44/44 pass unchanged
- architecture tests: 6/6 pass
- total: 50/50
- `python -m mount_v0 --check`: PASS
- `python -m bjj_game --check`: PASS
- exhaustive `--enumerate`: byte-identical to the pre-refactor build
- Session 11 blunder replay output: byte-identical except absolute log path
- Session 12 blunder replay output: byte-identical except absolute log path

No Mount v0 mechanics were changed during the refactor.
