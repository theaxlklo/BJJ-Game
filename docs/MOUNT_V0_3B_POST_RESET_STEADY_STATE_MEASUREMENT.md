# Mount v0.3b — Post-Reset Steady-State Sweep Measurement

## Status

AUTHORITATIVE CURRENT GATE-A MEASUREMENT.

This measurement follows:

- `MOUNT_V0_3B_GATE_A_STEADY_STATE_AMENDMENT.md`
- `MOUNT_V0_3B_STEADY_STATE_FIRST_MEASUREMENT.md`
- `MOUNT_V0_3B_GATE_A_STEADY_STATE_WINDOW_CLARIFICATION.md`

No stalling mechanic or threshold was changed to obtain this result.

## Sweep

```text
intervals:
  5s
  7s

match lengths:
  240, 245, 250, ..., 300s

cases:
  26
```

The repeating steady-state window begins immediately after the first Position Reset.

Frozen thresholds remain:

```text
post-reset Locked share < 0.50
post-reset longest Locked dwell < 20s
```

Every case must pass both.

## Result

The dwell criterion passes comfortably:

```text
max post-reset Locked dwell = 7s
threshold = <20s
```

The occupancy criterion fails in exactly three cases:

```text
interval=7s, match=250s:
  post-reset Locked share=0.500
  post-reset longest Locked dwell=7s

interval=7s, match=275s:
  post-reset Locked share=0.500
  post-reset longest Locked dwell=7s

interval=7s, match=280s:
  post-reset Locked share=0.500
  post-reset longest Locked dwell=7s
```

Aggregate diagnostics:

```text
sweep cases=26
failing cases=3
max post-reset Locked share=0.500
max post-reset Locked dwell=7s

whole-match max Locked share=0.657
whole-match max Locked dwell=49s

Locked-at-timeout cases=10/26
```

Because the frozen share rule is strictly:

```text
Locked share < 0.50
```

exactly `0.500` does not pass.

Therefore:

```text
v0.3b Gate A OPEN
v0.2 Gate 2 OPEN
```

## Why the threshold is not moved

Changing:

```text
<0.50
```

to:

```text
<=0.50
```

after observing these three exact ties would be a post-hoc threshold change.

The project explicitly froze the strict threshold before this measurement and will not move it merely because the current result is close.

## What the result does show

The Position Reset escalation materially prevents long Locked holds.

After the first reset:

```text
longest continuous Locked dwell <= 7s
```

across the entire 26-case sweep.

The remaining failure is occupancy frequency at three discrete 7-second timing combinations, not a long uninterrupted Locked hold.

Final timeout band remains timing-sensitive and diagnostic only:

```text
Locked timeout cases=10/26
```

It does not feed Gate A directly.

## Normal-play guard

The stronger escalation still does not leak into standard engaged play:

```text
V0.3b NORMAL-PLAY GUARD [PASS]

random:
  warnings=0/0
  penalties=0/0
  Position Resets=0/0

informed:
  warnings=0/0
  penalties=0/0
  Position Resets=0/0
```

## Stall versus active Bottom observation

The requested non-gating probe is now executable in `--check`:

```text
Top:
  RESET every Top initiation

Bottom:
  normal escape-first policy

responses:
  normal random mix

matches=100

timeouts=100
escapes=0
warnings=100
one-band penalties=100
Position Resets=800
```

The stalling system repeatedly changes positional control but does not produce a terminal Bottom escape in this probe.

This remains observational.

v0 does not yet define whether:

```text
TIMEOUT — Mount retained
```

is a win, draw, or loss.

That interpretation belongs to the later scoring/ruleset layer, including Section-33 points consequences.

## Current gate surface

```text
v0.2
1 PASS
2 OPEN
3 PASS
4 PASS
5 PASS
6 ACCEPTED
7 OPEN

v0.3a
A PASS
B DEFERRED
C PASS
D PASS
E PASS

v0.3b
A OPEN
B PASS
C PASS
D PASS
E PASS

V0.3b NORMAL-PLAY GUARD PASS
```

## Change-control consequence

PR #4 is not ready to merge under the current strict Option-A definition.

The following are **not** authorized by this measurement alone:

- moving `<0.50` to `<=0.50`;
- dropping the three failing cases;
- dropping interval 7;
- weakening the all-cases rule;
- changing the 20-second cadence merely to force a pass.

Any closure from here requires an explicit design decision rather than silent tuning.
