# Mount v0.3b — Gate A Steady-State Window Clarification

## Status

FROZEN BEFORE CHECKER REVISION.

This clarification follows the failed first sweep recorded in:

`MOUNT_V0_3B_STEADY_STATE_FIRST_MEASUREMENT.md`.

It does **not** move either Gate-A threshold and does **not** change stalling mechanics.

## Problem in the first measurement window

The first steady-state sweep measured Locked occupancy/dwell from match start.

That includes the intentional escalation grace:

```text
offense 1 -> persistent Warning
offense 2 -> first positional consequence
offense 3 -> first Position Reset
```

The Warning is intentionally non-positional.

Therefore a match starting in Locked may remain Locked for more than one 20-second advancement period before the repeating enforcement regime begins.

Using that initial grace period to define the "steady state" contradicts the frozen ladder.

## Authoritative steady-state start

For Gate A, the repeating steady-state measurement window begins:

```text
immediately after the first Position Reset is applied
```

The first Position Reset is the transition from initial escalation into the repeated-offense regime:

```text
offense 3+
-> Position Reset
-> Position Reset
-> Position Reset
...
```

This is the regime Gate A is intended to test for persistent Locked dominance.

## Frozen sweep remains unchanged

```text
interval_seconds:
  5
  7

match_length_seconds:
  240, 245, 250, ..., 300

cases:
  26
```

Every case must reach at least one Position Reset.

A case that never reaches Position Reset fails Gate A; it does not get an empty measurement window.

## Metric 1 — post-reset Locked share

Only decision windows occurring after the first Position Reset enter the steady-state occupancy denominator.

```text
post-reset Locked share =
  post-first-reset decision windows observed in Locked
  /
  all post-first-reset decision windows
```

Threshold remains exactly:

```text
post-reset Locked share < 0.50
```

Exactly 50% fails.

## Metric 2 — post-reset longest Locked dwell

The uninterrupted Locked-dwell metric is reset to zero when the first Position Reset occurs.

Only persisted Locked time after that first reset is eligible.

Threshold remains exactly:

```text
post-reset longest Locked dwell < 20 simulated seconds
```

Exactly 20 seconds fails.

The dwell remains measured in simulated seconds, not number of windows.

## Pre-reset evidence remains observable

The checker should continue reporting the initial escalation and may report whole-match Locked statistics for context.

Those pre-reset values are diagnostic only.

They do not feed the steady-state PASS formula.

This preserves visibility into the Warning/grace period without misclassifying it as recurring steady-state behavior.

## Gate A PASS formula

Every one of the same 26 cases must satisfy:

```text
Warning count >= 1
one-band penalty count >= 1
Position Reset count >= 1

post-reset Locked share < 0.50

post-reset longest Locked dwell < 20s
```

PASS remains all-cases, not an average.

## Gate 2

v0.2 Gate 2 depends on this revised Gate-A steady-state sweep.

Final timeout band remains diagnostic only.

A match may happen to end in Locked because of phase alignment and still pass if Locked cannot persist as the repeating steady state.

## Why this is not threshold tuning

The failed first measurement showed:

```text
max whole-match Locked share=0.657
max whole-match Locked dwell=49s
```

This clarification does not change:

```text
0.50 share threshold
20s dwell threshold
5s/7s interval sweep
240..300s match-length sweep
20s stalling cadence
Warning/penalty/Position Reset ladder
```

It changes only which phase is called "steady state."

That phase boundary is defined by the existing mechanics event that starts repeated escalation: the first Position Reset.

## Change-control rule

If the post-first-reset sweep still fails:

1. record the failed cases and metrics;
2. do not move either threshold;
3. do not exclude interval 7;
4. do not exclude inconvenient match lengths;
5. do not change stalling mechanics without a new design review.
