# Mount v0.3b — Cadence Timing Clarification

## Status

FROZEN BEFORE MECHANICS IMPLEMENTATION.

The 20-second advancement threshold remains unchanged.

This clarification reconciles the v0.3b cadence with the existing Mount simulation's discrete decision windows.

## Threshold versus adjudication window

The stalling threshold is:

```text
20 simulated seconds
```

A stalling offense can only be adjudicated when that player actually receives an initiation opportunity and chooses RESET while a progress-capable route exists.

Therefore:

```text
clock < 20 at RESET
-> no offense

clock >= 20 at RESET
-> offense
```

The clock is never converted into a count of RESETs/windows.

## Non-divisible intervals

If `--interval` does not divide the 20-second threshold into an eligible initiation window, the offense is processed at the **first eligible RESET window at or after 20 seconds**.

Example:

```text
threshold = 20s
eligible RESET arrives at 21s
-> offense is processed at 21s
-> the threshold is still 20s
```

The engine must never:

- issue the offense before the player's clock reaches 20s;
- round the threshold down to a window count;
- change the threshold based on `--interval`.

## Interval-invariance regression

For intervals 2, 5, and 7, tests must prove:

1. the configured threshold is always exactly 20 simulated seconds;
2. no offense occurs on an eligible RESET with clock <20;
3. the first eligible RESET with clock >=20 produces the offense;
4. engagement resets the same simulated-seconds clock to 0 independent of interval.

Observed adjudication timestamps may differ by the unavoidable discrete-window overshoot.

This clarification supersedes any informal example that implies the second RESET is universally the offense. That statement is true only for a window schedule whose second eligible RESET occurs at or after the 20-second threshold.
