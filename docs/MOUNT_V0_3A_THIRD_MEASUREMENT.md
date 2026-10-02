# v0.3a Third Measurement — Track Break Still Leaves Gate B Open

## Evidence point

After making any defended submission stage break the Americana track while retaining the frozen -1.00 defenderward axis cost, the exact PR head was:

```text
4b2dcd205f14195706b4d4fd1d3b96522354f892
```

GitHub Actions pull-request run:

```text
#377
```

Both Python 3.11 and Python 3.13 jobs passed:

```text
202 tests PASS
frozen enumerate digest unchanged
modern checker PASS
legacy checker PASS
```

Frozen digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Measured gates

```text
v0.2 Gate 1 PASS
v0.2 Gate 2 OPEN
v0.2 Gate 3 PASS
v0.2 Gate 4 PASS
v0.2 Gate 5 PASS
v0.2 Gate 6 ACCEPTED
v0.2 Gate 7 OPEN

v0.3a Gate A PASS
v0.3a Gate B OPEN
v0.3a Gate C PASS
v0.3a Gate D PASS
```

Gate 2 OPEN is the planned v0.3a transition.

## Gate B

The frozen target remains:

```text
0% < Tap match rate < 50%
```

Measured standard batch:

```text
Tap: 55/100 (55.0%)
Threat reached: 99
Control reached: 98
Finish reached: 78
submission-stage attempts: 902
```

The target is unchanged. Gate B still fails.

## Prediction probe

```text
fresh-fixed:
  taps=55
  escapes=2
  timeouts=43
  submission-attempts=902

exhausted-fixed:
  taps=56
  escapes=0
  timeouts=44
  submission-attempts=894

exhausted-recover:
  taps=58
  escapes=0
  timeouts=42
  submission-attempts=859
```

This remains observational only.

## Remaining structural inconsistency

v0.3a already requires Strong or Locked Mount to **enter** the Americana submission track.

However, once Threat is active, the current legality rule keeps the Americana submission action legal even if normal match evolution drops Mount to Stable or Loose. The checker also treats active submission states in those lower bands as reachable.

That means the submission can retain continuity after the dominant Mount condition that justified entry has been lost.

## Pre-implementation continuity rule

Before another mechanics run, freeze this rule:

> An active Americana submission track requires dominant Mount continuity. If Mount leaves Strong/Locked and becomes Stable/Loose before the next submission resolution, the active Americana track breaks.

Consequences:

- Strong/Locked remain the only bands with an active Threat/Control/Finish state.
- Losing positional dominance gives Bottom genuine submission relief without inventing new response weights or grades.
- The submission can be attempted again only by rebuilding the existing Americana setup and re-entering from Strong/Locked.
- Any defended stage still breaks the track and applies the existing -1.00 axis penalty.
- Gate B remains `0% < Tap < 50%`.
- Gate C remains "best fresh defense stops every **reachable** stage state."
- Gate D remains unchanged.
- Gate 5 remains observational with its unchanged >1.000 threshold.

No raw matchup grade, response weight, stamina value, commitment cost, or gate threshold changes.

If this structural continuity rule still leaves Gate B OPEN, v0.3a should remain OPEN for design review rather than continue tuning numbers to chase the threshold.
