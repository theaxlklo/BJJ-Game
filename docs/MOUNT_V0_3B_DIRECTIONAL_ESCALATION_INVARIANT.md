# Mount v0.3b — Directional Escalation Invariant Amendment

## Status

FROZEN BEFORE MECHANICS REVISION.

This amendment follows review of head `684930510f4aa3d15b6eee03420917afb1298cd0`.

It corrects a mechanics bug in the offense-3+ Position Reset rung.

## Bug

The original Position Reset always assigned the canonical Mount start:

```text
axis = +1.50
band = Stable
```

regardless of which player committed the offense.

That violates the already-frozen directional rule:

> every stalling consequence must benefit the non-stalling player.

Example from the two-sided RESET probe:

```text
Bottom offense:
+4.00 Locked -> +1.50 Stable
```

That is a large improvement for Bottom, the offender.

The same bug can also make escalation weaker than the offense-2 one-band consequence from the same pre-offense state.

## Authoritative offense-3+ rule

The tracker may still classify offense 3+ as the `POSITION_RESET` rung.

The mechanical effect is chosen from the current state.

### Top offender

Top's non-stalling beneficiary is Bottom, so the axis must move downward.

First compute the ordinary one-band Top-offense consequence for the current persisted band.

If that consequence is a boundary free-initiative consequence, use it.

Otherwise compare:

```text
canonical Position Reset target = +1.50
current one-band target
```

The offense-3+ target is:

```text
min(+1.50, current one-band target)
```

provided it moves the axis toward Bottom.

This guarantees that offense 3+ is never weaker than the current one-band consequence.

Examples:

```text
Top stalls at Locked:
one-band target +2.80
Position Reset target +1.50
-> use +1.50

Top stalls at Strong:
one-band target +1.80
Position Reset target +1.50
-> use +1.50

Top stalls at Stable:
one-band target +0.80
canonical +1.50 would be weaker / potentially backward
-> use +0.80

Top stalls at Loose:
one-band rule reaches Neutral-side boundary
-> free initiative for Bottom
```

### Bottom offender

Bottom's non-stalling beneficiary is Top, so the axis must move upward.

The canonical +1.50 reset is not used for Bottom offense 3+ because it can improve Bottom's position.

Instead offense 3+ uses the ordinary one-band Bottom-offense consequence from the current band:

```text
Loose -> Stable target
Stable -> Strong target
Strong -> Locked target
Locked -> free initiative for Top
```

No Bottom offense may reduce the axis.

## Effect observability

`stalling_consequence` continues to record the tracker rung:

```text
WARNING
PENALTY
POSITION_RESET
```

Actual mechanical effect is audited separately:

- one-band axis penalty fields/history;
- canonical Position Reset fields/history;
- free-initiative fields/history.

Counters must count the **actual applied effect**, not assume that every offense-3+ tracker rung performed a canonical Position Reset.

## New Gate F — directional and monotonic escalation

Gate F is an invariant gate.

For both offender sides, across every persisted Mount band/state used by the invariant probe:

1. every axis-moving stalling consequence moves strictly toward the non-stalling player;
2. a consequence that cannot move safely in that direction grants the non-stalling player a free initiative window instead;
3. the offense-3+ mechanical effect is never weaker than the offense-2 one-band effect evaluated from the same pre-offense state.

For numeric axis effects, severity is the absolute movement toward the beneficiary from the same starting axis.

For a boundary free-initiative consequence, the invariant is satisfied by the explicit non-staller initiative benefit rather than by an axis delta.

Any backward effect is an automatic Gate-F failure.

## Non-goals

This amendment does not:

- change the 20-second cadence;
- change the Warning rung;
- move Gate-A thresholds;
- change submission mechanics;
- tie Americana to Mount;
- add points/scoring;
- alter stamina;
- alter response commitment or Recognition.

## Regression requirement

The classic both-sides RESET trace must contain:

```text
Bottom offenses that lower the axis = 0
```

after this fix.
