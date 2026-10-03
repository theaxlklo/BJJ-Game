# Mount v0.3b — Directional Escalation and Time-Share Final Measurement

## Status

AUTHORITATIVE CURRENT v0.3b CLOSURE MEASUREMENT.

This measurement supersedes the Gate-A conclusion in:

- `MOUNT_V0_3B_POST_RESET_STEADY_STATE_MEASUREMENT.md`

while preserving that file as historical evidence of the decision-window sampling artifact.

## Mechanics / measurement head

```text
af2f6f59d2a4ff46b911d29cb2a718825cc3a7ee
```

## Verification

Python 3.11 push job:

```text
242 tests PASS
frozen digest PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen enumerate digest:

```text
expected=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
actual=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Directional escalation bug

The previous offense-3+ implementation always reset Mount control to:

```text
+1.50 Stable
```

That could help Bottom when Bottom was the offender.

It could also make Top's later consequence weaker than the ordinary one-band consequence from the same state.

The corrected rule is:

### Top offender

```text
target = min(+1.50, current one-band target)
```

when a numeric one-band target exists.

If the one-band consequence is the Loose boundary, Bottom receives free initiative instead.

### Bottom offender

The canonical +1.50 reset is never used.

Bottom offense 3+ uses the ordinary one-band consequence toward Top, or free initiative for Top at Locked.

The tracker rung remains `POSITION_RESET`; the actual applied effect is audited separately as:

- canonical Position Reset;
- one-band axis effect;
- free initiative.

Batch counters count the actual effect.

## Gate F — directional and monotonic escalation

Gate F sweeps both offender sides across every 0.1-axis state compatible with each persisted hysteresis band.

Measured:

```text
cases=98
backward effects=0
weaker later effects=0
boundary mismatches=0
Bottom-lowering cases=0
classic both-RESET Bottom-lowering=0
```

Therefore:

```text
v0.3b Gate F PASS
```

A later offense never moves control toward the offender and is never weaker than the offense-2 one-band consequence evaluated from the same starting state.

## Gate A — simulated-time occupancy

The 26-case timing sweep is unchanged:

```text
intervals:
  5s
  7s

match lengths:
  240, 245, 250, ..., 300s
```

The steady-state window still begins immediately after the first canonical Position Reset.

The threshold remains unchanged:

```text
post-reset Locked time share < 0.50
post-reset longest Locked dwell < 20s
```

Decision-window share is now diagnostic only.

### Result

```text
sweep cases=26
failing cases=0

max post-reset Locked time share=0.393
threshold=<0.50

max post-reset decision-window share=0.500
diagnostic only

max post-reset Locked dwell=11s
threshold=<20s
```

Whole-match diagnostics:

```text
max decision-window share=0.657
max time share=0.567
max Locked dwell=49s
Locked-at-timeout cases=10/26
```

Those whole-match values include the intentionally non-positional Warning / first-penalty grace period and do not feed Gate A.

Therefore:

```text
v0.3b Gate A PASS
```

## Why the previous exact 0.500 ties disappeared

The previous occupancy metric sampled the visible band only at decision windows.

At a 7-second interval those samples fall near Top's RESET opportunity, when PRESSURE drift is most likely to have rebuilt Locked.

The same gate already measured uninterrupted dwell in simulated seconds, and both stamina pacing and the 20-second stalling clock are time-based.

The corrected occupancy metric therefore measures:

```text
simulated seconds in Locked
/
post-first-reset simulated seconds
```

without changing the strict `<0.50` threshold.

The window-share diagnostic still reaches exactly:

```text
0.500
```

while the actual maximum time share is:

```text
0.393
```

This directly demonstrates the sampling artifact rather than hiding it.

## v0.2 Gate 2

The executable evidence now reports:

```text
v03b_sweep_cases=26
v03b_sweep_failing=0
v03b_max_post_reset_locked_time_share=0.393
v03b_max_post_reset_window_share=0.500
v03b_max_post_reset_locked_dwell=11s
v03b_locked_timeout_cases=10
```

Therefore:

```text
v0.2 Gate 2 PASS
```

Final timeout band remains diagnostic only.

## Other v0.3b gates

```text
A PASS
B PASS
C PASS
D PASS
E PASS
F PASS
```

Gate B still protects the informed Americana stalemate.

Gate C still proves both sides are subject to the stalling ladder.

Gate D still prevents a stalling consequence from crossing Neutral.

Gate E still keeps the v0.3a competent-defender deferral intact.

Gate F now proves direction and escalation strength.

## Normal-play guard

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

## Stall versus active Bottom

The non-gating observation remains:

```text
matches=100
timeouts=100
escapes=0
warnings=100
one-band penalties=100
Position Resets=800
```

This does not assign competitive meaning to `TIMEOUT — Mount retained`.

That belongs to the later scoring/ruleset layer.

## Final gate surface

```text
v0.2
1 PASS
2 PASS
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
A PASS
B PASS
C PASS
D PASS
E PASS
F PASS

V0.3b NORMAL-PLAY GUARD PASS
```

## Unchanged debts

This closure does not change:

- v0.2 Gate 7 commitment meaning;
- v0.3a Gate B competent-defender submission finish deferral;
- setup-policy debt;
- response commitment;
- Recognition/information;
- submission stamina asymmetry;
- scoring / points interpretation.
