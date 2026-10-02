# v0.3a First Measurement — Gate B Failure

## Evidence point

Measured after the batch policy was corrected to recognize both:

- positive probability of entering the submission track from Ready Americana; and
- positive probability of advancing an already-active submission stage.

Evidence head:

```text
cbb1d46c2c212a9598dbc529d09b5e3f728bdb8a
```

GitHub Actions pull-request run:

```text
#357
```

Both Python 3.11 and 3.13 jobs passed the full test/check pipeline at that head.

Frozen enumerate digest remained:

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

Gate 2's DEFERRED -> OPEN transition is the planned v0.3a transition, not a regression.

## Gate B failure

The frozen Gate-B target is:

```text
0% < Tap match rate < 50%
```

Measured standard batch:

```text
Tap: 98/100 (98.0%)
Threat reached: 99
Control reached: 99
Finish reached: 99
submission-stage attempts: 626
```

The Gate-B threshold is unchanged. The implementation fails it.

## Gate C is not sufficient by itself

Gate C still passes:

```text
Threat: 12 reachable / 12 best-defense-stops / 0 guaranteed
Control: 12 reachable / 12 best-defense-stops / 0 guaranteed
Finish: 12 reachable / 12 best-defense-stops / 0 guaranteed
```

This proves the defender can stop **one** fresh exchange at every stage.

It does not prove that a successful defense creates durable submission relief.

The current implementation leaves the attacker at the same submission stage after a defended exchange. Against the positive-weight batch response mix, submission progress is therefore retried repeatedly. A stopped trial does not undo prior submission progress, so enough repeated trials make a tap nearly inevitable.

The existing -1.00 defended-stage axis penalty prevents the old +4.00 cap treadmill, but by itself it does not unwind the submission track.

## Prediction probe

The non-gating matched-seed probe measured:

```text
fresh-fixed:
  taps=98
  escapes=2
  timeouts=0
  submission-attempts=626

exhausted-fixed:
  taps=100
  escapes=0
  timeouts=0
  submission-attempts=626

exhausted-recover:
  taps=100
  escapes=0
  timeouts=0
  submission-attempts=619
```

The prediction that an exhausted Bottom is more vulnerable is directionally visible, but the current submission loop saturates the outcome so heavily that recovery cannot produce useful separation.

No gate is based on this probe.

## Next mechanics experiment

Keep every frozen v0.3a gate and threshold unchanged.

Strengthen the consequence of a defended submission exchange without adding new techniques or response weights:

```text
Threat defended  -> submission track breaks
Control defended -> regress to Threat
Finish defended  -> regress to Control
```

The already-frozen defenderward axis cost remains:

```text
defended stage -> axis -1.00
```

Rationale:

- defense should stop current advancement (Gate C);
- successful defense should also recover some submission position rather than merely delay the same stage;
- the change gives the three-stage track actual two-way state movement;
- it does not alter the frozen response mix, raw Americana matchup row, stamina values, Gate-B range, Gate-5 threshold, or commitment costs.

This is an implementation correction against the frozen DoD, not a threshold adjustment.
