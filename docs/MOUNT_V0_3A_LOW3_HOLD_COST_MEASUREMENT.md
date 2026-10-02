# v0.3a Ready + Active Hold-Cost Measurement — LOW=3 Is Insufficient

## Experiment

Submission-pressure stalemates pay the existing LOW action cost:

```text
3 stamina
```

after resolution when either:

```text
1. Ready Americana + final grade Contested, with v0.3 submissions enabled
2. active Threat / Control / Finish + final grade Contested
```

Ordinary v0.2 Ready exchanges remain response-cost free.

## Mechanical verification

Direct tests prove:

- active-stage Contested hold charges 3;
- Ready-Americana Contested hold charges 3 only under v0.3;
- the identical v0.2-only Ready exchange charges 0;
- a responder at 26 resolves the current exchange without exhaustion, then pays to 23 and is Exhausted only on the next exchange;
- Failure / Strong Failure that breaks the track does not also pay the hold cost.

## Informed Gate-B result

With the full informed Bottom responder and the standard Gate-B condition:

```text
Top PRESSURE
Bottom ESCAPE
MEDIUM commitment
100 matches
base seed 42
```

the result is:

```text
informed Tap = 0/100
Threat reached = 78
Control reached = 0
Finish reached = 0
random contrast Tap = 99/100
```

The Ready hold cost therefore succeeds at creating submission entry opportunities:

```text
Threat: 0 -> 78 matches
```

but it does not create a full-match finishing window.

## Why it still fails

At MEDIUM commitment, Top pays:

```text
7 stamina per initiated action
```

while an informed Bottom pays only:

```text
3 stamina per Contested submission hold
```

Both also pay their behavior stamina flow.

Under sustained PRESSURE / ESCAPE, Top reaches exhaustion at least as fast as Bottom. Once both are Exhausted:

```text
Top initiator modifier = -1
Bottom responder modifier = +1
net = 0
```

Turn-In returns to Contested.

So the responder does become tired enough to lose the stalemate in isolation, but the attacker is also exhausted by the time that happens. The full-match fatigue gap required by Gate E never persists.

## Informed full-match evidence

The Ready+active LOW=3 experiment measured:

```text
PRESSURE/ESCAPE fixed:
  taps=0
  Threat=78
  escapes=22
  timeouts=78
  final stamina median=0 / 0
  RESETs=0 / 0
  completed setup builds=468

PRESSURE/ESCAPE recover:
  taps=0
  Threat=78
  escapes=22
  timeouts=78
  final stamina median=0 / 3
  completed setup builds=468

PRESSURE/PROTECT:
  taps=0
  Threat=0
  escapes=2
  timeouts=98
  final stamina median=0 / 0
  completed setup builds=1768

PRESSURE/CONSERVE:
  taps=0
  Threat=0
  escapes=99
  timeouts=1
  final stamina median=0 / 48

HOLD/ESCAPE:
  taps=0
  Threat=0
  escapes=100
  final stamina median=93 / 91

CONSERVE/ESCAPE:
  taps=0
  Threat=0
  escapes=100
  final stamina median=95 / 91

CONSERVE/PROTECT:
  taps=0
  Threat=8
  escapes=95
  timeouts=5
  final stamina median=95 / 93
```

## Gate state

```text
A PASS
B OPEN
C PASS
D PASS
E PASS
```

Gate B remains honestly OPEN because its informed Tap rate is 0%.

## Setup-policy debt

The policy issue remains visible:

```text
PRESSURE / ESCAPE informed:
  468 completed setup builds
  78 Threat entries
  0 taps
```

and under PROTECT:

```text
1768 completed setup builds
0 Threat entries
```

Top can continue spending on setup progress despite repeatedly failing to convert that progress into submission entry.

This experiment does not change setup progression.

## Conclusion

LOW=3 is not enough to solve the response-cost debt under the current MEDIUM-commitment full-match economy.

Do not:

- move the Gate-B threshold;
- change response weights;
- claim Gate B is closed;
- raise the hold cost post-hoc merely until the batch passes.

Any next responder-cost rule should be justified independently of this result before implementation. A plausible next design question is whether submission-defense cost should scale with the actual attack commitment rather than using a fixed LOW cost, but that is a separate amendment and is not part of this experiment.
