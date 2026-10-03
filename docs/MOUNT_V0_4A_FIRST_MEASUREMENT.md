# Mount v0.4a — Commitment Semantics First Measurement

> **SUPERSEDED FOR FINAL CLOSURE.** Preserve this file as historical evidence of the first green implementation. Independent audit later found (1) a sequential grade-clamp ordering bug in the resolver path and (2) an incomplete Gate-C state surface that fixed responder commitment at MEDIUM. Both were corrected without changing the frozen v0.4a semantics or thresholds. The authoritative closure measurement is `MOUNT_V0_4A_AUDITED_FINAL_MEASUREMENT.md`.

## Status

AUTHORITATIVE v0.4a IMPLEMENTATION MEASUREMENT.

The implementation follows the pre-mechanics frozen contract in:

`docs/MOUNT_V0_4A_COMMITMENT_SEMANTICS_DEFINITION_OF_DONE.md`

## Evidence head

```text
5a92f07f35dbe4a3ae784ecaaf61e77a6769165c
```

GitHub Actions push run:

```text
#694
```

Both supported Python versions passed:

```text
Python 3.11: 264 tests PASS
Python 3.13: 264 tests PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen enumerate digest:

```text
expected=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
actual=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The frozen 18-entry Mount matchup matrix is unchanged.

## Implemented commitment meaning

The selectable costs remain:

```text
LOW     3
MEDIUM  7
HIGH   12
```

Existing affordability remains authoritative:

```text
requested commitment
-> highest fully payable requested-or-lower commitment
-> UNFUNDED if LOW cannot be paid
```

All tactical effects use effective commitment.

### Initiator magnitude

```text
MEDIUM:
  identity

HIGH:
  Failure -> Strong Failure
  Success -> Strong Success

LOW / UNFUNDED:
  Strong Failure -> Failure
  Strong Success -> Success
```

Contested is unchanged by initiator magnitude alone.

HIGH therefore increases both upside and exposure rather than acting as a universal bonus.

### Response commitment

Response commitment uses the same affordability and cost policy.

```text
responder effective commitment < initiator effective commitment
-> initiator final grade +1
```

Equal or greater response commitment gives no grade bonus.

The +1 is applied exactly once regardless of gap size.

### Frozen modifier order

The executable order is:

```text
raw
-> behavior
-> positional
-> Ready override
-> pre-cost exhaustion
-> initiator commitment magnitude
-> response under-commitment
-> grade clamp / existing positional resolution
-> state transitions
-> initiator commitment cost
-> responder commitment cost
-> existing provisional hold LOW=3, if applicable
```

Current exchange exhaustion therefore never changes retroactively because the current response cost crossed an exhaustion threshold.

## Runtime capability

v0.4a uses an explicit match capability rather than static response-catalog metadata.

```text
v0.4a disabled -> response commitment capability False
v0.4a enabled  -> response commitment capability True
```

The v0.3a Gate-B auto-expiry therefore fires from a real runtime feature.

## Gate A — PASS

Compatibility / MEDIUM identity:

```text
cases=1152
enabled MEDIUM/MEDIUM mismatches=0
disabled response-parameter mismatches=0
```

Feature-off current exchange behavior is unchanged.

Enabled effective MEDIUM/MEDIUM preserves the current `ResolutionResult`; future match state may differ because the responder now pays stamina.

## Gate B — PASS

The existing v0.2 Gate 7 now reads:

```text
PASS
low_strictly_dominates=False
higher-commitment advantage states=172
```

No new Gate-7 threshold was invented.

LOW no longer strictly dominates simply because it is cheapest.

## Gate C — PASS

No selectable commitment globally dominates another:

```text
measured states=288
dominating pairs=none
```

Dominance uses the pre-frozen definition combining cost with final grade, terminal exit attainment, and realized initiator-favorable axis movement.

## Gate D — PASS

Matched/overmatched commitment preserves actual fresh Contested states:

```text
cases=360
breaks=0
active-Americana cases=72
```

### Intermediate false OPEN

The first checker implementation reported:

```text
cases=396
breaks=36
Gate D OPEN
```

Investigation showed those 36 were active-Americana states that were **not Contested before v0.4a**.

The frozen Gate-D requirement says:

> across every measured fresh Contested state

so those states were outside the gate population.

The probe was corrected to first establish the pre-v0.4a state as Contested, then apply matched/overmatched commitment.

No commitment mechanic, cost, grade transform, threshold, or response rule changed to obtain the final PASS.

This failed intermediate measurement remains visible in branch history.

## Gate E — PASS

LOW/UNFUNDED feint semantics:

```text
LOW Ready Americana entry to Threat=True
active capped cases=6
violations=0
MEDIUM/HIGH ordinary advances=2/2
```

LOW can create a real Threat.

LOW/UNFUNDED cannot advance beyond Threat or Tap.

The UNFUNDED probe uses both competitors Exhausted so the generic -1/+1 exhaustion modifiers cancel; this proves the successful exchange is held by the feint cap itself rather than by one-sided exhaustion.

## Gate F — PASS

Response under-commitment:

```text
comparisons=864
regressions=0
strict attacker improvements=646
```

A lower responder commitment never hurts the attacker relative to matched commitment and helps in many measured states.

## Gate G — PASS

Automatic Gate-B expiry:

```text
disabled capability=False
enabled capability=True
informed response commitment mode=MATCH
v0.3a Gate B=OPEN
```

The competent-defender measurement actually runs the v0.4a MATCH response-commitment policy.

The expiry is not a hard-coded status switch.

## Gate H — PASS

Feint / stalling interaction:

```text
Top advancement clock:    20 -> 20
Bottom advancement clock: 20 -> 0
```

A LOW active-stage feint cannot fake progress to reset the attacker's stalling clock.

The defender receives defensive-engagement credit for answering the real threat.

No v0.3b cadence, consequence, or threshold changed.

## Gate I — PASS

Responder affordability:

```text
request HIGH with 5 stamina:
  effective LOW
  cost=3
  funding gap=9
  under-commitment modifier=+1

request HIGH with 2 stamina:
  effective UNFUNDED
  cost=0
  funding gap=12

effective-equivalence mismatches=0
```

Requested commitment cannot leak unaffordable tactical credit.

## v0.3a Gate B — DEFERRED -> OPEN

The self-expiring deferral has now triggered:

```text
response_commitment_present=True
recognition_present=False
```

The unchanged criterion resumes:

```text
0% < informed Tap rate < 50%
```

Measured competent defender:

```text
informed Tap=0/100
Threat=78
Control=0
Finish=0
stage attempts=2028
```

Therefore:

```text
v0.3a Gate B OPEN
```

This is an expected and useful result.

Public MATCH commitment does not solve the competent-defender lock. It demonstrates that a later information/Recognition layer still has real work to do.

The Gate-B threshold was not changed.

## Random contrast

The standardized historical v0.3a random contrast was:

```text
Tap=99/100
Bottom median final stamina=12.5
```

With v0.4a random response choice plus independent RANDOM response commitment:

```text
Tap=25/100
Bottom median final stamina=0.0
```

The competent MATCH defender remains:

```text
Tap=0/100
Bottom median final stamina=0.0
```

The corrected frozen prediction did not require random taps to rise relative to the old baseline.

What it predicted was that public MATCH defense would remain stronger than the random commitment/response contrast and that responder stamina pressure would increase.

Both are observed.

These batch numbers are observations, not tuning targets.

## Response + hold-cost overlap

An isolated Contested Americana hold at MEDIUM/MEDIUM records:

```text
response commitment charge=7
provisional hold charge=3
total responder loss=10
Bottom stamina: 100 -> 90
```

The two costs remain separate in history.

The provisional LOW=3 hold rule is not retuned in v0.4a.

## Replayability

RANDOM response commitment uses a deterministic RNG separate from the existing response-choice RNG.

The commitment draw is consumed only when a real exchange occurs, not on RESET-only windows.

Regression coverage runs identical random-commitment batches twice and requires identical summaries.

## v0.3b regression surface

The historical v0.3b gates remain valid.

In particular its Gate E is now explicitly scoped to the v0.3b feature surface:

```text
v03b_response_commitment_present=False
recognition_present=False
current global v0.3a Gate B=OPEN
```

This preserves the historical statement that v0.3b itself did not introduce response commitment while allowing the later v0.4a capability to expire Gate B.

No v0.3b rule was changed.

## SETUP-POLICY DEBT

Still unchanged and visible:

```text
V0.3a SETUP-POLICY DEBT:
builder progress is ranked above axis loss;
informed PROTECT builds=1768,
Threat entries=0
```

v0.4a adds no initiator commitment-selection AI and does not attempt to repair that policy debt.

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
- automatic v0.3a Gate-B deferral.

The last item means the **deferral** is closed, not Gate B itself.

Gate B is now OPEN from live evidence.

## What remains open

v0.4a deliberately does not solve:

- v0.3a Gate B competent-defender finishing;
- Recognition / information;
- ruleset scoring and the meaning of timeout outcomes;
- SETUP-POLICY DEBT;
- the provisional status of the LOW=3 submission-hold cost.

No next phase is selected by this measurement alone.
