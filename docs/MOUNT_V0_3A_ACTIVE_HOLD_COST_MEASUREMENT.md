# v0.3a Hold-Stamina Measurement — Active-Stage Cost Does Not Reach Informed Gate B

## Evidence head

Mechanics/informed-Gate-B head:

```text
c4dca142d9de7ae7b0d8130ae0a5415e612ce24c
```

GitHub Actions push run:

```text
#451
```

Both Python 3.11 and 3.13 passed:

```text
214 tests PASS
frozen digest unchanged
modern checker PASS
legacy checker PASS
```

Frozen digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Implemented experiment

The responder pays the existing LOW cost:

```text
3 stamina
```

only when an **active Americana submission stage** resolves Contested.

Timing is post-resolution, so the cost changes only later exchanges.

Direct tests prove:

- Contested active-stage hold charges 3;
- a responder at 26 resolves the current exchange non-Exhausted, then falls to 23 and is Exhausted next exchange;
- Failure that breaks the track does not pay the hold cost.

## Result

Gate B remains OPEN:

```text
informed Tap=0/100
Threat=0
Control=0
Finish=0
stage-attempts=738

random contrast Tap=98/100
```

The active-stage hold cost therefore has **zero opportunity to affect the gating match**.

## Why

The informed responder stops the route one state earlier.

Ready Americana already uses the isolated response set and Turn-In is the designated best fresh defense.

Under fresh PRESSURE / ESCAPE:

```text
Ready Americana + Turn-In
-> Contested
-> Ready target is consumed
-> Threat is not entered
```

The informed responder repeats this every time Top rebuilds Ready.

Because the current stamina cost is conditional on:

```text
action == Americana Submission Finish
and active stage exists
and final grade == Contested
```

it never fires in these Gate-B matches.

## Informed full-match evidence

100 matched seeds:

```text
PRESSURE/ESCAPE fixed:
  taps=0
  Threat=0
  escapes=28
  timeouts=72
  stamina median=0/0
  RESETs=0/0
  completed setup builds=1476

PRESSURE/ESCAPE recover:
  taps=0
  Threat=0
  escapes=22
  timeouts=78
  stamina median=0/7
  RESETs=0/0
  completed setup builds=1560

PRESSURE/PROTECT:
  taps=0
  Threat=0
  escapes=2
  timeouts=98
  stamina median=0/2
  completed setup builds=1768

PRESSURE/CONSERVE:
  taps=0
  Threat=0
  escapes=100
  stamina median=0/57

HOLD/ESCAPE:
  taps=0
  Threat=0
  escapes=100
  stamina median=93/91

CONSERVE/ESCAPE:
  taps=0
  Threat=0
  escapes=100
  stamina median=95/91

CONSERVE/PROTECT:
  taps=0
  Threat=8
  escapes=95
  timeouts=5
  stamina median=95/93
```

## Setup-policy debt remains visible

Under informed PRESSURE / ESCAPE the batch records:

```text
1476 completed setup builds
0 Threat entries
```

Top repeatedly rebuilds Americana setup even though informed Turn-In prevents entry.

This confirms the previously identified setup/policy churn. It is still not changed in this experiment.

## Conclusion

Do not change the Gate-B threshold or response weights.

The active-stage-only cost is too narrow to test the intended fatigue mechanism because informed defense prevents the active stage from existing.

The next smallest submission-specific experiment is to define the **Ready-Americana Contested defense** as part of the same submission-pressure hold:

```text
v0.3 submissions enabled
Ready Americana attempt
Turn-In / final grade Contested
-> responder pays the same LOW cost of 3 after resolution
```

This remains v0.3-only and does not change ordinary v0.2 Ready behavior.

Record the result before changing any other setup, stamina, or policy rule.
