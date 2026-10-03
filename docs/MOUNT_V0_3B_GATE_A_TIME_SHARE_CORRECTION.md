# Mount v0.3b — Gate A Time-Share Measurement Correction

## Status

RECORDED AFTER THE WINDOW-SHARE SAMPLING ARTIFACT WAS IDENTIFIED, BEFORE CHECKER REVISION.

The strict Gate-A threshold remains unchanged.

## Problem

The post-reset Gate-A sweep currently mixes two time models:

```text
longest Locked dwell
-> measured in simulated seconds

Locked occupancy share
-> measured by counting decision windows
```

At non-5-second intervals, decision-window sampling is phase-sensitive.

At a 7-second interval the decision sample is taken near the moment Top is about to RESET, which over-represents Locked relative to the actual simulated time spent there.

That is inconsistent with the project rule established earlier for stamina and the stalling clock itself: pacing mechanics are measured in simulated game time, not number of windows.

## Exploratory evidence that triggered this correction

Review on head `684930510f4aa3d15b6eee03420917afb1298cd0` reported:

```text
interval 5s:
  maximum window share = 0.25
  maximum time share   = 0.15

interval 7s:
  maximum window share = 0.500
  maximum time share   = 0.393
```

The three strict-window-share failures:

```text
7s / 250s: window share 0.500
7s / 275s: window share 0.500
7s / 280s: window share 0.500
```

were measured by time as approximately:

```text
0.382
0.389
0.379
```

These values are recorded as the reason for revisiting the unit of measurement, not as thresholds.

The implementation must reproduce its own deterministic evidence before Gate A can close.

## Authoritative share metric

The Gate-A occupancy metric is now simulated-time share:

```text
post-reset Locked time share =
  simulated seconds persisted in Locked after first Position Reset
  /
  total simulated seconds after first Position Reset
```

The already-frozen threshold remains exactly:

```text
post-reset Locked time share < 0.50
```

Exactly 0.50 still fails.

## Dwell metric

The second Gate-A metric remains unchanged:

```text
post-reset longest uninterrupted Locked dwell < 20 simulated seconds
```

Both Gate-A state-occupancy metrics are therefore expressed in simulated seconds.

## Sweep remains unchanged

```text
intervals:
  5s
  7s

match lengths:
  240, 245, 250, ..., 300s

cases:
  26
```

Every case must pass.

The post-first-Position-Reset measurement window remains unchanged.

## Diagnostic window share

Decision-window share may remain visible as a diagnostic to demonstrate the sampling difference.

It does not feed Gate A.

## Why this is not threshold tuning

This correction does not change:

- the strict `<0.50` threshold;
- the `<20s` dwell threshold;
- the 26-case sweep;
- the 20-second stalling cadence;
- any stalling consequence.

It changes the occupancy unit from sampled windows to simulated seconds so it matches the dwell metric and the project's established time-based pacing model.

## Gate 2 dependency

v0.2 Gate 2 follows the corrected time-share Gate A.

If any case has:

```text
post-reset Locked time share >= 0.50
```

or:

```text
post-reset longest Locked dwell >= 20s
```

Gate A and Gate 2 remain OPEN.
