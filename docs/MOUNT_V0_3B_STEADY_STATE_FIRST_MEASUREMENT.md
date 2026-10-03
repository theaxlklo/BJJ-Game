# Mount v0.3b — First Steady-State Sweep Measurement

## Status

RECORDED BEFORE STEADY-STATE WINDOW CLARIFICATION.

This measurement tests the first Option-A formulation exactly as frozen in:

`MOUNT_V0_3B_GATE_A_STEADY_STATE_AMENDMENT.md`.

No thresholds are moved by this document.

## Evidence head

Checker implementation head:

```text
590848228689ca360c4c55b3d3d287f5dd5f8104
```

## Frozen sweep

```text
intervals:
  5s
  7s

match lengths:
  240, 245, 250, ..., 300s

cases:
  26
```

Frozen thresholds:

```text
Locked decision-window share < 0.50
longest uninterrupted Locked dwell < 20 simulated seconds
```

## Result

The first formulation fails:

```text
failing cases=26/26
max Locked share=0.657
max Locked dwell=49s
Locked timeout cases=10/26
```

Therefore:

```text
v0.3b Gate A OPEN
v0.2 Gate 2 OPEN
```

The thresholds are not changed.

## Why all cases fail the dwell criterion

The first formulation starts measuring uninterrupted Locked dwell from match start.

But the frozen stalling ladder intentionally begins:

```text
offense 1 -> Warning
offense 2 -> first positional consequence
offense 3+ -> Position Reset
```

Starting from Locked, the Warning is deliberately non-positional.

Therefore the initial grace/escalation phase can preserve Locked for longer than one 20-second offense period before the repeating Position Reset regime begins.

Demanding:

```text
longest Locked dwell < 20s
```

from time zero is incompatible with the persistent-Warning rung itself.

This is a measurement-window problem, not evidence that the 20-second threshold should be moved.

## Active-Bottom observation

The new non-gating probe reproduces the reported result exactly:

```text
matches=100
timeouts=100
escapes=0
warnings=100
one-band penalties=100
Position Resets=800
```

Top deliberately RESETs every Top initiation.

Bottom uses the normal escape-first policy with the normal random response mix.

The stalling system changes positional control repeatedly but does not produce a terminal escape in this probe.

This is observational only.

v0 does not yet define whether:

```text
TIMEOUT — Mount retained
```

is a win, draw, or loss.

That interpretation belongs to a later scoring/ruleset layer.

## Design conclusion

Gate A is intended to answer:

> After enforcement is active, can Locked remain the steady state under deliberate stalling?

The first sweep instead included the intentional pre-enforcement Warning/first-penalty escalation period inside the steady-state dwell metric.

The next design clarification must preserve both frozen thresholds and the full 26-case sweep while defining the steady-state measurement window around the repeating escalation regime.

No stalling mechanic is changed by this measurement.
