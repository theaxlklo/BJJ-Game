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

## Design correction after BJJ review

The measured 55% Gate-B failure above remains valid evidence.

The proposed follow-up rule that an Americana track should automatically break when Mount falls below Strong/Locked is **rejected**. Americana is not Mount-exclusive and can remain mechanically relevant through transitions and from other positions. Encoding "lost dominant Mount = lost Americana" would make the current Mount slice easier to balance by asserting a false general BJJ rule.

Therefore this branch returns to the last mechanics state before that continuity experiment:

```text
any defended submission stage -> track breaks
defended stage -> axis -1.00
submission may otherwise continue according to its own control state
```

Gate B remains honestly OPEN at 55/100 until a BJJ-valid submission/defense model resolves it. No threshold, response weight, raw matchup grade, stamina value, or commitment cost is changed to chase the remaining five points.

The next design step should model submission control independently from position ownership so that future Americana continuations can survive legitimate transitions without pretending that every positional loss preserves the same control either.
