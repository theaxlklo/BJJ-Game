# Mount v0.4a — Feint Intent Post-Amendment Measurement

## Status

AUTHORITATIVE POST-AMENDMENT v0.4a MEASUREMENT.

This document supersedes the pre-amendment v0.4a closure measurement only where the approved feint-intent amendment changes semantics or observations.

Historical evidence remains preserved in:

- `MOUNT_V0_4A_AUDITED_FINAL_MEASUREMENT.md`
- `MOUNT_V0_4A_FEINT_INTENT_PRECHANGE_MEASUREMENT.md`

## Design authority

Original frozen DoD:

`docs/MOUNT_V0_4A_COMMITMENT_SEMANTICS_DEFINITION_OF_DONE.md`

Independent audit amendment:

`docs/MOUNT_V0_4A_INDEPENDENT_AUDIT_AMENDMENT.md`

Approved feint-intent amendment:

`docs/MOUNT_V0_4A_FEINT_INTENT_FUNDING_AMENDMENT.md`

Validated implementation/checker head:

```text
0d83ab6a39c18b3224cb872052225482f2ded2fa
```

GitHub Actions:

```text
workflow: test
run:      #747
Python:   3.11 / 3.13
```

## Semantic change

The pre-amendment implementation conflated intent and affordability:

```text
requested MEDIUM/HIGH
-> funding downgrade
-> effective LOW / UNFUNDED
-> feint cap
```

The approved amendment now separates them:

```text
requested commitment
-> feint intent

effective commitment
-> funded grade/cost/mismatch capability
```

Only requested LOW activates the active-Americana feint cap.

A requested MEDIUM/HIGH attack downgraded by stamina to effective LOW or UNFUNDED is not a feint solely because of that downgrade.

## Modifier order unchanged

The amendment does not change:

```text
raw / behavior / positional / Ready
-> pre-cost exhaustion
-> initiator effective-commitment magnitude
-> response under-commitment
-> final resolution
-> state transitions
-> costs
```

HIGH can still magnify a fatigue-created swing.

No exhaustion threshold or commitment cost changed.

## Pre-change evidence

At historical checkpoint:

```text
ad74c04a434e606cc7dea435878b0b1cc6d58c63
```

the fixed-MEDIUM checker reproduced:

```text
Tap=15/100
Reached Finish=42/100
Top median stamina=0.0
Bottom median stamina=0.0

feint caps=1009
requested-LOW feint caps=0
MEDIUM/HIGH funding-downgrade successful active-stage attempts=1009
MEDIUM/HIGH funding-downgrade feint caps=1009
```

This measurement was committed before changing the mechanic.

It established that the batch contained no requested-LOW initiator actions and that all 1009 caps arose from interpreting funding downgrade as feint intent.

## Post-amendment fixed-MEDIUM diagnostic

Configuration remains:

```text
100 matches
base seed 42
Top PRESSURE
Bottom ESCAPE
initiator requested commitment MEDIUM
random Bottom response choice
response commitment FIXED_MEDIUM
5:00 clock
starting axis +1.50
5-second interval
100 / 100 stamina
v0.2 setup enabled
v0.3a submissions enabled
v0.4a commitment semantics enabled
```

Measured:

```text
Tap=99/100
Reached Finish=99/100
Top median final stamina=0.0
Bottom median final stamina=0.0

feint caps=0
requested-LOW feint caps=0
MEDIUM/HIGH funding-downgrade successful active-stage attempts=191
MEDIUM/HIGH funding-downgrade feint caps=0
```

The two amendment cap invariants are therefore:

```text
requested-LOW caps=0
funding-downgrade caps=0
```

on this fixed-MEDIUM surface.

The move from 15 to 99 taps is an observation, not a gate and not a tuning target.

No mechanic was adjusted to restore 99.

The reduced count of funding-downgraded successful attempts, 1009 -> 191, is also an emergent path-distribution change: successful attempts now advance instead of repeatedly holding the same stage under the old cap.

## Post-amendment RANDOM response-commitment diagnostic

RANDOM response commitment remains an equal LOW / MEDIUM / HIGH diagnostic choice from its independent deterministic RNG.

It is not a gameplay defender policy and not a gate.

Measured:

```text
Tap=94/100
Reached Finish=95/100
Top median final stamina=0.0
Bottom median final stamina=0.0

feint caps=0
requested-LOW feint caps=0
MEDIUM/HIGH funding-downgrade successful active-stage attempts=156
MEDIUM/HIGH funding-downgrade feint caps=0
```

The historical pre-amendment RANDOM contrast was:

```text
Tap=25/100
```

The post-amendment 94/100 result is observational.

The equal response-commitment weighting remains diagnostic only.

## Informed MATCH contrast

The competent informed defender remains:

```text
Tap=0/100
v0.3a Gate B=OPEN
```

The unchanged Gate-B criterion remains:

```text
0% < informed Tap rate < 50%
```

The feint-intent correction therefore does not solve the competent-defender information/Recognition issue.

## v0.4a Gate A — PASS

Unchanged:

```text
cases=1152
enabled MEDIUM mismatches=0
disabled response-parameter mismatches=0
```

## v0.4a Gate B — PASS

Unchanged:

```text
v0.2 Gate 7=PASS
higher-commitment advantage states=172
```

## v0.4a Gate C — PASS

Unchanged:

```text
states=864
dominating_pairs=none
```

## v0.4a Gate D — PASS

Unchanged:

```text
cases=360
breaks=0
active-Americana cases=72
```

## v0.4a Gate E — PASS

Amended criterion: requested LOW, not effective LOW/UNFUNDED, is the feint-intent signal.

Measured:

```text
LOW Ready entry=True
requested-LOW isolated cases=6
violations=0

fully-funded MEDIUM/HIGH advances=2/2
funding-downgrade advances=2/2
isolated funding-downgrade caps=0

fixed-MEDIUM requested-LOW caps=0
fixed-MEDIUM funding-downgrade successes=191
fixed-MEDIUM funding-downgrade caps=0
```

The requested-LOW isolated surface includes an UNFUNDED requested-LOW case, proving that lack of funding does not erase feint intent.

The MEDIUM/HIGH downgrade surface includes effective LOW and effective UNFUNDED cases, proving that funding loss alone does not create feint intent.

## v0.4a Gate F — PASS

Unchanged:

```text
comparisons=864
regressions=0
strict improvements=646
```

## v0.4a Gate G — PASS

Unchanged capability rule:

```text
disabled=False
enabled=True
v0.3a Gate B=OPEN
informed response commitment=MATCH
```

## v0.4a Gate H — PASS

Amended feint predicate.

Requested LOW:

```text
Top clock    20 -> 20
Bottom clock 20 -> 0
```

Funding-downgraded requested MEDIUM:

```text
effective commitment=LOW
Top clock    20 -> 0
Bottom clock 20 -> 0
```

Thus the requested-LOW feint does not fake progress, while a continuation-intent attack uses normal progress-capable-route engagement even when stamina downgrades its effective commitment.

No stalling cadence or consequence changed.

## v0.4a Gate I — PASS

Unchanged:

```text
HIGH response requested with 5 stamina:
  effective LOW
  cost=3
  funding gap=9
  mismatch=+1

HIGH response requested with 2 stamina:
  effective UNFUNDED
  cost=0
  funding gap=12

effective-equivalence mismatches=0
```

The amendment adds no requested-level funded tactical credit.

## Verification

GitHub Actions run #747:

```text
Python 3.11:
  270 tests PASS
  frozen digest PASS
  modern semantic checker PASS
  legacy checker PASS

Python 3.13:
  270 tests PASS
  frozen digest PASS
  modern semantic checker PASS
  legacy checker PASS
```

Frozen digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The frozen 18-entry Mount matchup matrix remains unchanged.

## Gate surface

```text
v0.2
1 PASS
2 PASS
3 PASS
4 PASS
5 PASS
6 ACCEPTED
7 PASS

v0.3a
A PASS
B OPEN
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

v0.4a
A PASS
B PASS
C PASS
D PASS
E PASS — amended requested-intent criterion
F PASS
G PASS
H PASS — amended requested-intent predicate
I PASS

V0.3b NORMAL-PLAY GUARD PASS
```

Do not summarize this state as "everything passes": v0.3a Gate B remains OPEN.

## Remaining policy/design debt

### Initiator commitment policy

No initiator LOW / MEDIUM / HIGH selection policy exists.

Gate 7 proves capability, not tactical policy usage.

### RANDOM response commitment

The equal LOW / MEDIUM / HIGH weighting is diagnostic only.

It is not frozen gameplay policy.

### Recognition question for v0.4b

Requested and effective commitment now have deliberately different meanings:

```text
requested = intent
effective = funded capability
```

The future v0.4b Recognition DoD must explicitly decide what the defender reads: requested intent, effective capability, separate signals for both, or another defined model.

This question is preserved in:

`docs/V0_4B_RECOGNITION_COMMITMENT_QUESTION.md`

That file is a future design note, not a v0.4b DoD and not implementation authorization.
