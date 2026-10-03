# Mount v0.4a — Feint Intent Pre-Change Measurement

## Status

HISTORICAL PRE-MECHANICS EVIDENCE.

This document records the funding-downgrade / feint-cap behavior before the approved feint-intent amendment is implemented.

It is not a tuning target.

## Reference

Amendment:

`docs/MOUNT_V0_4A_FEINT_INTENT_FUNDING_AMENDMENT.md`

Measurement checkpoint:

```text
ad74c04a434e606cc7dea435878b0b1cc6d58c63
```

At this checkpoint the only additions after the approved amendment are diagnostic/checker/test instrumentation. The runtime feint mechanic is still the pre-amendment effective-commitment rule.

GitHub Actions:

```text
workflow: test
run:      #735
Python:   3.11 / 3.13
```

## Fixed-MEDIUM diagnostic

Configuration:

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

Checker result:

```text
Tap=15/100
Reached Finish=42/100
Top median final stamina=0.0
Bottom median final stamina=0.0

submission feint caps=1009
requested-LOW feint caps=0
MEDIUM/HIGH funding-downgrade successful active-stage attempts=1009
MEDIUM/HIGH funding-downgrade feint caps=1009
```

The test `test_pre_amendment_fixed_medium_funding_feint_evidence` pins those values at this historical checkpoint.

## Mechanism established

The batch has no requested-LOW initiator actions:

```text
initiator requested commitment=MEDIUM
requested-LOW feint caps=0
```

Nevertheless, 1009 successful active submission-stage attempts are feint-capped:

```text
requested MEDIUM
-> insufficient stamina
-> effective LOW / UNFUNDED
-> successful active-stage exchange
-> feint cap
```

Therefore all 1009 caps on this surface are caused by the funding downgrade being interpreted as feint intent.

That is the failed design measurement that motivates the approved amendment.

## Verification at the measurement checkpoint

GitHub Actions run #735 passed on Python 3.11 and 3.13:

```text
267 tests PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen Mount-v0 enumerate digest:

```text
expected=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
actual=  3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
PASS
```

The pre-amendment v0.4a gate surface remains:

```text
A PASS
B PASS — higher-commitment advantage states=172
C PASS — states=864, dominating_pairs=none
D PASS — cases=360, breaks=0, active-Americana cases=72
E PASS under the superseded effective-LOW/UNFUNDED rule
F PASS — comparisons=864, regressions=0, strict improvements=646
G PASS — v0.3a Gate B OPEN, informed response commitment MATCH
H PASS under the superseded effective-feint predicate
I PASS — affordability equivalence mismatches=0
```

Gates E and H are the only v0.4a gates whose feint predicate is superseded by the approved amendment.

## Change-control consequence

The post-amendment implementation must not aim at a Tap count.

It must instead establish:

```text
requested LOW remains feint-capped
requested LOW remains capped when itself UNFUNDED

requested MEDIUM/HIGH downgraded to effective LOW / UNFUNDED
-> not feint-capped solely because of funding

fixed-MEDIUM requested-LOW caps=0
fixed-MEDIUM funding-downgrade feint caps=0
```

All outcome/stamina changes after that semantic correction are measurements to report.

No matchup, commitment cost, exhaustion threshold, response weight, setup rule, submission grade, hold cost, or stalling cadence is authorized to change in order to influence those observational outcomes.
