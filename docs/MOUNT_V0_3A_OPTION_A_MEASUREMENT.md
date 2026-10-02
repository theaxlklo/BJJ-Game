# v0.3a Option-A Measurement — Stalemate Semantics Expose Gate-B Mismatch

## Evidence head

The complete Option-A mechanics/checker surface is present by:

```text
4c9d465524d4960d0d705ec8ec3aa6595525ef77
```

GitHub Actions push run:

```text
#425
```

Both Python 3.11 and Python 3.13 passed:

```text
208 tests PASS
frozen enumerate digest unchanged
modern checker PASS
legacy checker PASS
```

Frozen digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Option A is mechanically working

Active Americana stages inherit Ready isolation legality:

```text
legal:
  Forearm Frame
  Turn-In Recovery

illegal while isolation holds:
  Tight Elbows / Arm Defense
```

Stage semantics are:

```text
Success / Strong Success
  -> advance
  -> Finish success taps

Contested
  -> hold current stage
  -> no axis loss
  -> no track break

Failure / Strong Failure
  -> break track
  -> axis -1.00 toward Bottom
```

Direct tests prove Tight Elbows cannot reappear after isolation.

## Gate surface

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
B OPEN
C PASS
D PASS
E PASS
```

### Gate A

```text
Locked submission-progress probability = 0.571
policy_selected = True
```

### Gate B

The frozen target remains:

```text
0% < Tap rate < 50%
```

Measured standard random-response batch:

```text
Tap = 98/100 (98.0%)
Threat = 99
Control = 98
Finish = 98
submission-stage attempts = 664
```

Gate B is therefore honestly OPEN.

### Gate C

Under the reachable fresh baseline `PRESSURE / ESCAPE` stage surface:

```text
Threat: 2 reachable / 2 best-Contested / 0 defender wins / 0 guaranteed attacker
Control: 2 reachable / 2 best-Contested / 0 defender wins / 0 guaranteed attacker
Finish: 2 reachable / 2 best-Contested / 0 defender wins / 0 guaranteed attacker
```

Fresh informed defense is now a stalemate rather than a guaranteed defender win.

### Gate D

```text
attacker-only exhaustion changes = 36
defender-only exhaustion changes = 36
both-Exhausted cancellation mismatches = 0/72
```

### Gate E

Isolated informed-response sequence:

```text
Top Fresh
Bottom Exhausted
Threat start
best legal response every stage = Turn-In Recovery

Threat:  Success
Control: Success
Finish:  Success
-> Tap
```

So an informed Exhausted defender is no longer a perfect submission lock.

## What the 98% means

The fixed random response mix now projects correctly through isolation:

```text
Frame = 4
Turn-In = 3
```

At a fresh submission stage:

- Frame advances the attacker;
- Turn-In holds the stage.

A hold does not reset submission progress. Therefore a random responder that keeps sampling eventually chooses Frame enough times to walk Threat -> Control -> Finish in almost every five-minute match.

This is no longer a response-legality bug.

It is also not evidence that a competent informed fresh defender is nearly always submitted. Gate C proves the opposite: the informed best response can hold every fresh stage.

The 98% result shows that the current Gate-B random-response batch and the phrase **"fresh competent defender survives most matches"** are no longer measuring the same thing once correct stalemate semantics exist.

Changing response weights or the <50% threshold to force Gate B green would hide that mismatch and is not authorized.

## v0.3b connection

A fresh informed defender can repeatedly hold Threat/Control/Finish with Turn-In.

That is precisely the next question already assigned to v0.3b:

```text
What happens when a legitimate progress route exists,
but one side can deliberately hold/stall the exchange?
```

Option A therefore moves the unresolved problem out of false perfect-response lock and into the intended stalling/progress layer.

## Stamina observation after Option A

The earlier pre-Option-A observation was:

```text
median Top stamina = 0
median Bottom stamina = 0
Top RESETs = 0
Bottom RESETs = 0
```

After Option A, the standard batch ends faster because random defenders are usually tapped:

```text
median Top stamina = 2
median Bottom stamina = 9
Top RESETs = 0
Bottom RESETs = 0
```

So saturation is still severe but is no longer literally 0/0 at the median in the standard batch.

The deeper observation remains: the scripted policy never RESETs, and late mutual exhaustion / pacing should not be tuned inside v0.3a merely to change these numbers.

## Behavior sweep

```text
Bottom ESCAPE:
  taps=98
  escapes=1
  timeouts=1

Bottom PROTECT:
  taps=31
  escapes=0
  timeouts=69

Bottom CONSERVE:
  taps=75
  escapes=19
  timeouts=6
```

PROTECT can turn Turn-In from Contested into Failure and break the active track, so strategic behavior now materially changes submission survival.

## Change-control conclusion

Do not merge v0.3a under the original frozen DoD while Gate B remains OPEN.

Do not tune:

- response weights;
- raw grades;
- stamina costs;
- commitment costs;
- Gate-B threshold.

The next review decision should address the measurement/design relationship between:

1. random-response match-level Tap rate (current Gate B);
2. informed fresh stalemate (Gate C);
3. informed exhausted vulnerability (Gate E);
4. v0.3b stalling/progress rules.

Option A itself should remain: it resolves the legality contradiction and removes the perfect-response submission lock.
