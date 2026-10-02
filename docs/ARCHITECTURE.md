# BJJ Game Architecture

## Status

Mount v0 mechanics are frozen. This document describes the object-oriented structure used to carry those mechanics into v0.1 and later positions without changing their results.

## Design goals

- Keep BJJ matchup and technique-specific interaction knowledge data-driven.
- Put player-specific mutable state on `Competitor`.
- Keep persisted position state legal at all times.
- Separate match state from resolution policy.
- Make resolution dependencies explicitly injectable.
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
    ├── mechanics.py
    └── other compatibility facades
```

There is deliberately no compatibility module under `bjj_game/positions/mount/`; compatibility imports only point **into** the new package, never back out of it.

## Core objects

### `Competitor`

Represents a grappler and owns player-specific changing state.

Mount v0.1c stores:

- side
- name
- current behavior
- an independent `StaminaPool`

The CLI updates behavior when the player chooses it. `MountMatch.drift()` and `decide()` then read behavior from the competitors. Optional behavior arguments still exist only to preserve the frozen v0 API and update the same competitor-owned state.

Stamina is attached to `Competitor` through composition. v0.1c adds time-based behavior upkeep/recovery through `MountMatch.advance()` while the frozen `MountResolutionEngine` still does not read stamina or commitment. Later belt/style/attribute/injury/run state follow the same composition rule rather than becoming more method parameters.

### `MountMatch`

The aggregate root for the current prototype. It owns top and bottom competitors, simulated clock, current `MountPosition`, scheduled initiator, history, and exit state.

It does not contain grade-resolution formulas; those live in the resolution engine and rule set.

`MountMatch` is intentionally Mount-specific in v0. A generic multi-position match coordinator should be introduced only when a second playable position exists.

### `Position` / `MountPosition`

`Position` is currently a deliberately minimal common abstraction. `MountPosition` owns Mount state and the transition between a valid Mount and a broken Mount.

A broken Mount stores the terminal crossing value separately from persisted Mount control. Future positions can then be introduced without storing out-of-domain values in another position's state.

### `MountAxis`

Owns persisted Mount control value and visible hysteresis band. It is the **only** path used to update persisted Mount control.

`MountAxis.apply()` rejects values outside `+0.10..+4.00` and impossible axis/band combinations. When an escape crosses below the Mount floor, that overshoot is event/transition data on `MountPosition.crossing_axis`; it is not persisted in `MountAxis`.

### `MountRuleSet`

Owns position-wide Mount-v0 policies: persisted range, initial bands, hysteresis thresholds, drift rates, positional modifiers, and Exit Map policy.

Technique-specific behavior sensitivities and special floor-clamp semantics are **catalog metadata**, not hard-coded action IDs in `MountRuleSet` or the engine.

### `TechniqueCatalog`

Indexes canonical technique and response definitions by stable ID. Mechanics reference stable IDs, never player-facing strings.

A `TechniqueEntity` can carry escape capability, Exit Map, band-specific exit overrides, behavior modifiers, and whether a non-escape action clamps at the Mount floor.

### `MatchupTable`

Contains the 18 hand-authored action/response grades. The BJJ judgments remain data rather than being hidden in technique subclasses.

### `MountResolutionEngine`

A stateless service that resolves drift and exchanges. Its dependencies are explicit constructor fields:

```python
MountResolutionEngine(
    rules=...,
    catalog=...,
    matchups=...,
)
```

`MountResolutionEngine.default()` wires the production Mount-v0 objects. Tests can inject a modified catalog, rule set, or even a one-entry matchup table without monkey-patching globals.

## Dependency direction

```text
interfaces / diagnostics
        ↓
      engine
        ↓
domain + positions

mount_v0 compatibility facade
        ↓
      bjj_game
```

The new `bjj_game` package never imports from `mount_v0`. The legacy package is a one-way adapter only.

## Compatibility policy

Existing `mount_v0` imports continue to work, but implementation lives in `bjj_game`.

Compatibility behavior parameters remain accepted by `MountMatch.drift()` and `decide()` so all frozen v0 tests/playtest tooling continue to work. New code sets behavior on the competitors and omits those parameters.

## v0.1 extension points

v0.1a now proves the player-owned stamina state can exist without reworking or changing the positional engine:

```text
Competitor
├── behavior
└── StaminaPool

ActionAttempt
├── Technique
└── Commitment

MountMatch
├── ActionAttempt
├── StaminaCostPolicy
└── invokes unchanged MountResolutionEngine
```

Planned objects:

- `StaminaPool` — implemented in v0.1a
- `StaminaBand` — implemented in v0.1a, observational only
- `Commitment` — implemented in v0.1b
- `ActionAttempt` — implemented in v0.1b
- `StaminaCostPolicy` — implemented in v0.1b and injected into `MountMatch`
- `BehaviorStaminaPolicy` — implemented in v0.1c with fixed-point interval carry
- `CONSERVE` — implemented in v0.1c as a recovery behavior layered around frozen drift

`CONSERVE` and `STABILIZE` are behaviors/policies, not competitor subclasses. v0.1b does not yet add either behavior.


### Commitment boundary

`MountMatch.decide()` remains the cost-free frozen-v0 path. `MountMatch.attempt()` is the v0.1b path:

```text
ActionAttempt
→ validate frozen resolution
→ charge initiator through StaminaCostPolicy
→ apply unchanged ResolutionResult
```

This keeps stamina economics outside the BJJ matchup table and resolution engine.
## Refactor proof

The architecture-hardening pass is behavior-preserving:

- frozen Mount-v0 tests: **44/44 pass unchanged**
- architecture tests: **13/13 pass**
- total: **57/57**
- `python -m bjj_game --check`: PASS
- `python -m mount_v0 --check`: PASS
- exhaustive `--enumerate`: byte-identical to the previous OOP build
- custom matchup-table injection is tested
- behavior ownership is tested
- catalog-driven HOLD/PROTECT/special-clamp metadata is tested
- an escape regression proves terminal negative overshoot is not persisted in `MountAxis`

No Mount-v0 mechanics changed during this pass.
