# Mount v0.2b — Responder Exhaustion

## Status

Implemented on the review branch.

This slice closes the responder-stamina asymmetry without adding response stamina costs or changing the frozen Mount-v0 matchup matrix.

## Rule

Exhaustion now applies symmetrically to an initiated exchange:

```text
Exhausted initiator
→ action grade -1

Exhausted responder
→ action grade +1 to the initiator

Both Exhausted
→ -1 +1 = 0
```

Both stamina bands are read before the initiator pays the current action cost.

Responding still has no direct stamina cost.

The same 25/35 exhaustion latch is used for both sides.

## Ready interaction

Ready's fresh-defense invariant remains unchanged:

```text
fresh Ready stalemate response
→ Contested
```

Responder exhaustion applies after the Ready stalemate override:

```text
Ready stalemate
→ Contested
→ responder Exhausted +1
→ Success for the initiator
```

If both fighters are Exhausted, the initiator and responder modifiers cancel.

Gate 1 therefore remains a fresh-state Ready invariant rather than an exhaustion invariant.

## Gate 3

The checker compares otherwise-identical isolated exchanges with:

```text
initiator stamina = 100
responder stamina = 100 vs 25
```

Current result:

```text
fresh-vs-exhausted responder outcome differences = 258
```

Gate 3 is PASS.

## Gate 6 — accepted path B

Static Exhausted-Bottom reachability still contains a HOLD lockout:

```text
PRESSURE: 1 route
HOLD:     0 routes
CONSERVE: 1 route
```

The definition of done allows path B when that lockout is deliberately retained but a real match-state route prevents a dead state.

The checker now measures a fixed-behavior, no-recovery 100-match probe:

```text
Top starts 100 stamina
Bottom starts 25 stamina
Bottom behavior = ESCAPE
v0.2 setup enabled
seed = 42
```

Current dynamic escapes per 100 matches:

```text
PRESSURE: 0
HOLD:     76
CONSERVE: 35
```

HOLD is therefore ACCEPTED rather than PASS: a fresh patient Top can still completely suppress an Exhausted Bottom in the isolated state, but actual setup work can exhaust Top and remove that lock without Bottom using CONSERVE.

If that measured HOLD route disappears later, Gate 6 automatically returns to OPEN.

## Recovery side effect

The old adaptive-recovery fixture at +1.50 could end before Top completed its recovery cycle once responder exhaustion existed.

The fixture now starts at +3.50 so it still tests the intended behavior:

```text
Exhausted
→ CONSERVE
→ recover through 35
→ return to baseline behavior
```

This is a fixture-state change, not a rule change.

## Batch policy consistency

The scripted batch policy uses the same net exhaustion modifier as `MountMatch.attempt()`.

That prevents the AI from choosing actions using fresh-responder expected values and resolving them under exhausted-responder rules.

## Deferred

This slice does not add:

- response stamina costs;
- setup disruption;
- commitment effects;
- submission finishes;
- stalling penalties;
- any change to the frozen 18-entry matrix.

The direct response-cost idea remains available later if the mirrored grade modifier proves insufficient.
