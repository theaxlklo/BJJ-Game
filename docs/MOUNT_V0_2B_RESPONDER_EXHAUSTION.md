# Mount v0.2b — Responder Exhaustion

## Status

Implemented on the v0.2 review branch.

This slice gives responder stamina a direct mechanical consequence without adding a new response cost.

The frozen Mount-v0 matchup matrix and enumerate digest remain unchanged.

## Rule

The existing initiator exhaustion rule remains:

```text
Exhausted initiator
→ initiated action -1 grade
```

v0.2b adds the mirror:

```text
Exhausted responder
→ initiated action +1 grade for the initiator
```

Therefore:

```text
fresh initiator / fresh responder       0
Exhausted initiator / fresh responder  -1
fresh initiator / Exhausted responder  +1
both Exhausted                          0
```

The same 25/35 hysteresis latch is used for both sides.

Both stamina bands are read before the initiator's action cost is paid.

Responding still has no direct stamina cost.

## Ready interaction

The responder modifier is applied through the same external-grade surface as initiator exhaustion.

Ready setup still establishes its fresh stalemate before exhaustion:

```text
fresh Ready stalemate
→ Contested
```

If the responder is Exhausted:

```text
Ready stalemate
→ +1 for initiator
→ Success
```

If both sides are Exhausted, the modifiers cancel and the fresh Ready result is preserved.

This keeps Gate 1's fresh Ready invariant intact while making stamina matter to defense.

## Batch-policy consistency

The scripted initiator policy reads both stamina bands and evaluates actions with the same net exhaustion modifier used by `MountMatch.attempt()`.

The policy therefore does not choose using fresh-responder expected values and then resolve against different exhausted-responder rules.

## Gate 3 — PASS

The isolated checker holds the initiator fresh and changes only responder stamina.

Current result:

```text
fresh-vs-Exhausted responder outcome differences = 258
```

Gate 3 therefore reports PASS.

## Gate 6 — ACCEPTED via path B

The original static reachability probe still reports:

```text
PRESSURE: 1
HOLD:     0
CONSERVE: 1
```

So a fresh HOLD Top can still completely deny an already-Exhausted Bottom's positive-weight static escape routes.

That lockout is deliberately retained.

The checker now also runs a fixed-behavior 100-match path-B probe:

```text
Bottom starts Exhausted at 25
Top starts fresh at 100
Bottom behavior = ESCAPE
v0.2 setup enabled
no recovery policy
seed 42
```

Measured escapes:

```text
PRESSURE: 0 / 100
HOLD:    76 / 100
CONSERVE:35 / 100
```

HOLD therefore has a real no-recovery route out of the static lockout as Top spends stamina on setup work, becomes Exhausted, and defends one grade worse.

Gate 6 reports ACCEPTED when every behavior with a static zero-route lockout has a measured dynamic escape route. If that route disappears later, the gate automatically returns to OPEN.

ACCEPTED is intentionally distinct from PASS:

- PASS means every Top behavior has a static positive-weight route;
- ACCEPTED means a documented path-B lockout remains, but the checker proves a measured way out during actual match evolution.

## Side effects observed in 1,000-match batches

The responder rule changes some match distributions:

- HOLD vs ESCAPE produces Open Guard in batch play for the first time (10.2% in the review run), because an Exhausted Top can no longer defend Elbow-Knee at full strength.
- CONSERVE vs ESCAPE Reversals fall from 15.7% to 2.1% in the reported comparison, because an Exhausted Bottom now defends Top attacks worse.
- PRESSURE conditions were materially unchanged in the reported comparison.
- Gate 5 moves only slightly on the cap-progress stack, from 0.630 to 0.610 meaningful follow-ups per match and remains OPEN.

These are consequences of stamina becoming two-sided rather than a retune of the frozen matchup table.

## Recovery fixture

The adaptive recovery regression now starts at axis +3.50 rather than +1.50.

At +1.50, responder exhaustion can let Bottom escape before Top completes the recover/return cycle. The fixture still tests the same behavior-policy contract:

```text
Exhausted
→ CONSERVE
→ recover through 35
→ return to baseline behavior
```

## Deliberate non-changes

v0.2b does not add:

- direct response stamina costs;
- response commitment;
- setup-speed changes from exhaustion;
- new behavior stamina rates;
- changes to 3/7/12 action costs;
- a forced escape route against a fresh HOLD Top;
- any frozen matchup-table changes.

A direct response cost remains a later design option if one-grade responder exhaustion proves insufficient.
