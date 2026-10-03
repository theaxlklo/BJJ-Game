# Mount v0.4a — Audited Final Measurement

## Status

AUTHORITATIVE v0.4a CLOSURE MEASUREMENT.

This measurement supersedes `MOUNT_V0_4A_FIRST_MEASUREMENT.md` for closure while preserving that file as historical evidence.

Independent audit amendment:

`docs/MOUNT_V0_4A_INDEPENDENT_AUDIT_AMENDMENT.md`

## Audited mechanics head

```text
44fbf0d3d9338c2b609e740eb45fc973876bd0e0
```

Exact-head workflows:

```text
push #718 PASS
PR   #719 PASS
```

Both supported Python versions:

```text
266 tests PASS
frozen enumerate digest PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The frozen 18-entry Mount matchup matrix is unchanged.

## Independent audit finding 1 — sequential clamp order

The original implementation calculated commitment modifiers from sequential intermediate grades but then summed all numeric modifiers and reapplied the total to the pre-exhaustion grade.

That is incorrect when an earlier step clamps at Strong Failure / Strong Success and a later step moves back toward Contested.

Example class:

```text
base Strong Failure
exhaustion -1
-> Strong Failure (clamped)

MEDIUM magnitude
-> Strong Failure

under-committed response +1
-> Failure
```

A summed `-1 + 0 + 1 = 0` implementation incorrectly remained Strong Failure.

The engine now computes the target grade in the frozen sequential order:

```text
pre-cost exhaustion
-> initiator commitment magnitude
-> response under-commitment
```

When v0.4a contributes no tactical grade change, the historical exhaustion `ResolutionResult` is returned unchanged so compatibility includes diagnostic metadata, not only final grade.

Regression coverage now includes:

- a real exchange that exercises the clamp case;
- exhaustive grade-level coverage across:
  - all five Grades;
  - exhaustion -1 / 0 / +1;
  - initiator UNFUNDED / LOW / MEDIUM / HIGH;
  - responder UNFUNDED / LOW / MEDIUM / HIGH.

## Independent audit finding 2 — Gate C response-commitment surface

The original Gate C held responder commitment fixed at MEDIUM.

Because v0.4a makes response commitment part of exchange state, a global dominance claim must cover all selectable fully-funded responder levels.

Gate C now covers:

```text
responder LOW
responder MEDIUM
responder HIGH
```

for every otherwise-frozen ordinary exchange state.

The measured state count therefore expands:

```text
288 -> 864
```

No dominance criterion or threshold changed.

## Gate A — PASS

Feature-off compatibility and enabled MEDIUM/MEDIUM current-exchange identity:

```text
cases=1152
enabled_MEDIUM_mismatches=0
disabled_response-param_mismatches=0
```

Response stamina may change later match state when v0.4a is enabled; immediate `ResolutionResult` identity is preserved under effective MEDIUM/MEDIUM.

## Gate B — PASS

Existing v0.2 Gate 7:

```text
PASS
low_strictly_dominates=False
higher-commitment advantage states=172
```

Commitment now has real tactical meaning without retuning 3 / 7 / 12.

## Gate C — PASS

Full selectable response-commitment surface:

```text
states=864
dominating_pairs=none
```

No LOW / MEDIUM / HIGH initiator commitment globally dominates another under the frozen cost + outcome definition.

## Gate D — PASS

```text
fresh Contested cases=360
breaks=0
active-Americana cases=72
```

Matched or overmatched response commitment preserves actual fresh Contested states.

The historical false-OPEN measurement of 396 / 36 breaks remains in branch history; those 36 states were not Contested before v0.4a and were outside the frozen Gate-D population.

## Gate E — PASS

```text
LOW Ready entry=True
LOW/UNFUNDED capped cases=6
violations=0
MEDIUM/HIGH advances=2/2
```

LOW can create a real Threat.

LOW / UNFUNDED cannot advance an active submission beyond Threat or Tap.

## Gate F — PASS

```text
comparisons=864
regressions=0
strict improvements=646
```

A lower response commitment never worsens the initiator outcome relative to matched commitment and strictly improves many measured states.

## Gate G — PASS

Runtime capability:

```text
v0.4a disabled=False
v0.4a enabled=True
informed response commitment=match
v0.3a Gate B=OPEN
```

The Gate-B deferral auto-expires from a real runtime capability.

The informed Gate-B batch actually runs v0.4a response commitment with MATCH mode.

## Gate H — PASS

```text
Top advancement clock:
20 -> 20

Bottom advancement clock:
20 -> 0
```

A feint-capped active attack cannot manufacture progress credit for the initiator.

The defender still receives defensive-engagement credit.

## Gate I — PASS

Responder affordability remains authoritative:

```text
HIGH requested with 5 stamina:
effective LOW
response cost=3
funding gap=9
under-commitment modifier=+1

HIGH requested with 2 stamina:
effective UNFUNDED
response cost=0
funding gap=12

effective-equivalence mismatches=0
```

Requested commitment cannot leak unaffordable tactical benefit.

## v0.3a Gate B — DEFERRED -> OPEN

Response commitment is now live:

```text
response_commitment_present=True
recognition_present=False
```

The deferral auto-expires and the unchanged criterion resumes:

```text
0% < informed Tap < 50%
```

Audited informed MATCH result:

```text
Tap=0/100
Threat=78
Control=0
Finish=0
stage attempts=2028
```

Therefore:

```text
v0.3a Gate B OPEN
```

This is expected evidence.

Public perfect matching does not solve the competent-defender submission lock; Recognition/information remains later work.

Random contrast:

```text
Tap=25/100
```

Random response remains contrast only and is not a tuning target.

## v0.3b regression surface

All v0.3b gates remain PASS.

Gate E remains historically scoped:

```text
v03b_response_commitment_present=False
recognition_present=False
current global v0.3a Gate B=OPEN
```

v0.3b itself did not introduce response commitment; v0.4a legitimately supplies the later capability.

Time-based Gate A remains:

```text
26 cases
failing=0
max post-reset Locked time share=0.393
max post-reset window share=0.500 diagnostic only
max post-reset Locked dwell=11s
```

Directional Gate F remains:

```text
98 cases
backward=0
weaker_later=0
boundary_mismatches=0
Bottom-lowering=0
classic Bottom-lowering=0
```

Normal-play guard remains PASS.

## Response + hold overlap

Existing provisional submission-hold cost is unchanged.

A Contested MEDIUM/MEDIUM hold still records response commitment and hold cost separately:

```text
response commitment charge=7
provisional hold charge=3
Bottom total loss=10
```

No hold-cost tuning is part of v0.4a.

## SETUP-POLICY DEBT

Still visible and unchanged:

```text
informed PROTECT builds=1768
Threat entries=0
```

v0.4a adds no initiator commitment-selection AI and does not repair this policy debt.

## Current gate surface

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
E PASS
F PASS
G PASS
H PASS
I PASS

V0.3b NORMAL-PLAY GUARD PASS
```

## What v0.4a closes

Closed:

- v0.2 Gate 7 commitment meaning;
- response-side commitment capability;
- the v0.3a Gate-B **deferral**.

Gate B itself is not closed; it is now OPEN from live evidence.

## What remains open

- v0.3a Gate B competent-defender finishing;
- Recognition / information;
- ruleset scoring / timeout interpretation;
- SETUP-POLICY DEBT;
- provisional status of the LOW=3 hold cost.

No next phase is selected by this measurement alone.
