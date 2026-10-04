# Stamina Economy Rule Change — Post-Change Measurement

## Status

POST-CHANGE MEASUREMENT RECORDED.

The frozen rule-change DoD is **not fully satisfied**:

```text
Gate D = OPEN
```

No tuning was performed after observing Gate D OPEN.

The current rule implementation therefore returns to review with the failed recovery hypothesis preserved as evidence.

## Change-control lineage

Base main after measurement PR #7:

```text
3b38783df9134aed77e3be5460ea1d0b60edc458
```

Original reviewed rule-change DoD:

```text
7a992f6ea5ae8eaa4ab9c36606d1d25788868c06
```

Clarified pre-change checkpoint DoD:

```text
6279f28ea1878c244b77e4f064cda6f5c374fcef
```

Authoritative pre-change evidence:

```text
docs/STAMINA_ECONOMY_RULE_PRECHANGE_EVIDENCE.md
```

The checker reproduced the pre-change causal baseline before Rule 1 / Rule 2:

```text
Surface E Top exact-zero attacks=1,949
Bottom response/hold/total drain=5,010/1,192/6,202
Bottom behavior recovery=8,658
drain/recovery=71.63%

Surface B combined exact-zero defender drain=95
Top -> Bottom=29
Bottom -> Top=66
```

## First untuned post-change measurement

The first complete post-change mechanics run was GitHub Actions run #898.

No stamina, Recognition, hold, cost, threshold, or policy value was changed in response to that result.

A later reporting-only commit added explicit post-change drain and pre/post hold-settlement lines. GitHub Actions run #900 produced the same gate and gameplay results.

## Verification

Reporting-complete run #900, Python 3.13:

```text
317 tests PASS
semantic checker PASS
legacy entry point PASS

expected digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2

actual digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The historical measurement gates remain replayable with the settlement capability disabled.

---

# Gates A-I

```text
A PASS — pre-change defender-drain evidence is frozen
B PASS — UNFUNDED initiator imposes zero responder stamina cost
C PASS — provisional hold is supplemental rather than additive
D OPEN — existing RECOVER still cannot leave Exhausted
E PASS — Recognition and immediate-resolution semantics remain intact
F PASS — v0.3a competent-defender Gate B remains inside 0% < Tap < 50%
G PASS — stamina accounting reconciles exactly
H PASS — deferred mechanics remain frozen
I PASS — structured evidence and deterministic replay
```

Only Gate D is OPEN.

An OPEN design gate is not the same thing as a checker failure. The checker executes successfully and reports the failed design result.

---

# Gate A — pre-change evidence

PASS.

The checker continues to reproduce:

```text
Surface B exact-zero:
Top -> Bottom=29
Bottom -> Top=66
combined=95

Surface E Top exact-zero:
exchanges=1,949
response=5,010
hold=1,192
total=6,202
Bottom recovery=8,658
share=0.7163
```

The failed economy is therefore preserved rather than overwritten by the new rules.

---

# Gate B — Rule 1

Rule:

```text
initiator true effective commitment == UNFUNDED
-> responder commitment charged=0
-> supplemental hold charged=0
```

Post-change five-surface result:

```text
true-UNFUNDED exchanges=16,485
exact-zero subset=16,255
charged violations=0
```

PASS.

## Surface E causal result

Pre-change Top exact-zero -> Bottom:

```text
1,949 exchanges
response drain=5,010
hold drain=1,192
total=6,202
```

Post-change Top exact-zero -> Bottom:

```text
1,812 exchanges
response drain=0
hold drain=0
total=0
```

Pre-change Top true-UNFUNDED -> Bottom:

```text
2,001 exchanges
total drain=6,419
```

Post-change:

```text
1,857 exchanges
total drain=0
```

Rule 1 therefore removes the targeted free-attack -> paid-defense asymmetry exactly.

Bottom behavior recovery on Surface E changes from:

```text
8,658 -> 7,950
```

because the match trajectory itself changes. The relevant Rule-1 invariant is the zero defender charge on UNFUNDED initiator exchanges, not preservation of the old recovery total.

## Other surfaces

Every exact-zero and true-UNFUNDED initiator direction on A-D also records:

```text
response/hold/total=0/0/0
```

---

# Gate C — Rule 2

Rule:

```text
supplemental hold request
= max(0, 3 - responder commitment stamina charged)
```

with Rule 1 overriding the hold charge when the initiator is UNFUNDED.

Five-surface result:

```text
hold exchanges=6,534
settlement mismatches=0
additive double-charge cases=0
```

PASS.

The standard five surfaces produce **zero supplemental hold stamina charged** after the change.

The deterministic unit probe separately preserves the narrow case where a funded initiator faces an UNFUNDED responder with 2 stamina:

```text
response charged=0
supplemental hold requested=3
supplemental hold charged=2
shortfall=1
```

So Rule 2 has not made supplemental hold charging impossible in the engine. It has made it absent on these five standard surfaces.

## Old vs new hold settlement

### A — public MATCH

```text
pre:
  holds=1,950
  separate hold requested/charged=5,850/234

post:
  holds=780
  nominal hold burden=2,340
  covered by response commitment=468
  supplemental requested/charged=0/0
```

### B — trusts reads

```text
pre:
  holds=1,502
  requested/charged=4,506/442

post:
  holds=1,267
  nominal=3,801
  covered by response=429
  supplemental requested/charged=0/0
```

### C — hedge one level

```text
pre:
  holds=1,430
  requested/charged=4,290/290

post:
  holds=1,214
  nominal=3,642
  covered by response=282
  supplemental requested/charged=0/0
```

### D — always HIGH

```text
pre:
  holds=1,950
  requested/charged=5,850/234

post:
  holds=1,950
  nominal=5,850
  covered by response=234
  supplemental requested/charged=0/0
```

### E — trusts reads + Bottom RECOVER

```text
pre:
  holds=1,589
  requested/charged=4,767/1,745

post:
  holds=1,323
  nominal=3,969
  covered by response=450
  supplemental requested/charged=0/0
```

This confirms the DoD's warning: on normal funded exchanges, Rule 2 nearly abolishes the separate hold charge.

---

# Gate D — RECOVER remains unable to leave Exhausted

OPEN.

Surface E post-change:

```text
matches clearing Bottom Exhausted latch=0
total latch clears=0
CONSERVE -> ESCAPE switches=0
State 2 -> State 1 exits=0
State-2 re-entries after recovery=0
first latch-clear time=None
```

The required nonzero proof of recovery does not exist.

Per the frozen failure path:

```text
Gate D = OPEN
-> record result
-> do not tune this slice
-> future corrective mechanic requires a separate design amendment / DoD
-> HARD STOP
```

No recovery rate, threshold, commitment cost, hold rule, or Recognition rule was changed after this result.

## What did improve

The failure is not “nothing changed.”

Surface E stamina-state share changes:

```text
                   pre      post
State 1            19.3%     20.9%
State 2            49.2%     71.2%
State 3            31.5%      7.9%
```

Bottom final median stamina:

```text
2 -> 6
```

Outcomes:

```text
pre Surface E:
  taps=5
  escapes=9
  timeouts=86

post:
  taps=5
  escapes=20
  timeouts=75
```

Rule 1 / Rule 2 greatly reduce the deepest mutual-zero state and improve Bottom's retained stamina, but the system now spends more time in the **mutually Exhausted but not both zero** state.

It still does not accumulate enough stamina to clear the existing >=35 Exhausted latch.

This is new evidence, not authorization to change the recovery threshold or rate.

---

# Gate E — immediate exchange semantics

PASS.

Existing Recognition Gates B-E remain PASS.

Isolated old-vs-new settlement probes:

```text
cases=2
immediate-resolution mismatches=0
```

For fixed choices and pre-exchange state, the settlement capability does not directly change:

- base resolution;
- final grade;
- axis result;
- submission transition;
- Tap state;
- escape result.

It changes responder stamina settlement and therefore may change later trajectory.

---

# Gate F — competent-defender Gate B

PASS.

Frozen criterion remains:

```text
0% < informed Tap < 50%
```

Historical trust-read result:

```text
6/100
```

Post-change:

```text
7/100
```

The exact historical value was not a target.

No Recognition probability, policy, commitment cost, grade, or Gate-B threshold was tuned.

---

# Gate G — exact accounting

PASS.

```text
500/500 post-change match records reconcile for both sides

response stamina explicitly waived by Rule 1=4,750
hold burden explicitly covered by response commitment=1,863
```

Waived and covered amounts remain separate from actual stamina charges.

---

# Gate H — deferred mechanics

PASS.

Unchanged:

```text
Mount matrix entries=18
frozen digest=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2

commitment costs:
LOW=3
MEDIUM=7
HIGH=12

UNFUNDED == UNFUNDED
-> responder under-commitment modifier=0
```

The historical measurement slice also continues to PASS with settlement disabled.

Recognition probabilities/RNG/policies, exhaustion thresholds, CONSERVE rate, action legality, submission progression, setup, stalling, and matchup grades were not changed.

---

# Gate I — structured evidence / replay

PASS.

```text
post-change surfaces=5
deterministic replay_equal=True
```

Gate D remains visibly OPEN without being converted into a checker execution failure.

---

# P1-P6 prediction comparison

The predictions were committed before any Rule-1 / Rule-2 prototype.

They are not rewritten here.

## P1 — trust-read taps

Prediction:

```text
decrease or stay near the low end rather than increase materially
```

Observed:

```text
6 -> 7
```

Direction:

```text
UP
```

**Prediction did not get the direction right.**

The increase is small and Gate F still passes, but the predeclared directional hypothesis was not confirmed.

---

## P2 — public-MATCH taps

Prediction:

```text
remain at or near 0
```

Observed:

```text
0 -> 0
```

**Prediction confirmed.**

---

## P3 — final stamina

Prediction:

```text
responder final stamina rises on at least some surfaces,
most visibly Surface E
```

Observed:

```text
A 0/0 -> 0/0
B 0/0 -> 0/0
C 0/0 -> 0/0
D 0/0 -> 0/0
E 0/2 -> 0/6
```

**Prediction confirmed narrowly on Surface E.**

The fixed active surfaces A-D still terminate at median 0/0.

---

## P4 — middle-window / mutual-zero occupancy and recovery

Prediction:

```text
Surface E spends less of its late trajectory trapped in the depleted states
and demonstrates >=1 return to State 1
```

Observed:

```text
State 3 share: 31.5% -> 7.9%
State 2 share: 49.2% -> 71.2%
State 1 share: 19.3% -> 20.9%

latch clears=0
State2 -> State1 exits=0
```

**Prediction is mixed and the required recovery portion failed.**

The rules strongly reduce mutual zero, but mostly move time into State 2 rather than restoring non-Exhausted play.

This is exactly why Gate D is OPEN.

---

## P5 — hedge comparison

Prediction:

```text
hedge-one and always-HIGH remain at least as submission-resistant as trust-read
```

Observed post-change taps:

```text
trust reads=7
hedge one=0
always HIGH=0
```

Response commitment spend:

```text
trust=7,319
hedge=8,900
always HIGH=9,480
```

Historical spend:

```text
trust=7,352
hedge=8,843
always HIGH=9,480
```

**Prediction confirmed.**

The hedge policies still eliminate taps on these seeds, though the spending differences shift.

---

## P6 — Threat reach after hold settlement

Prediction:

```text
Threat reach may fall;
if it collapses toward old v0.3a behavior, record it rather than silently fix it
```

Observed public MATCH:

```text
matches reaching Threat:
78 -> 0

Threat entries:
1,950 -> 0

Control:
0 -> 0

Finish:
0 -> 0

Tap:
0 -> 0
```

Observed trust-read Recognition:

```text
matches reaching Threat:
58 -> 50

Threat entries:
578 -> 436

Control entries:
395 -> 331

Finish entries:
320 -> 205

Tap:
6 -> 7
```

**The warning case occurred on public MATCH.**

Public-MATCH informed Threat reach collapses completely after the settlement changes.

This does not violate Gate F, because Gate F is the frozen trust-read Recognition competent-defender surface.

It is nevertheless significant design evidence: the old provisional hold charge was originally introduced because informed Threat reach had collapsed, and the new supplemental settlement recreates that collapse on the public-MATCH control.

No mechanic was changed to compensate.

---

# Surface outcome summary

```text
A public MATCH
  Tap 0
  Escapes 22
  Timeouts 78
  final stamina 0/0

B trusts reads
  Tap 7
  Escapes 14
  Timeouts 79
  final stamina 0/0

C hedge one level
  Tap 0
  Escapes 23
  Timeouts 77
  final stamina 0/0

D always HIGH
  Tap 0
  Escapes 22
  Timeouts 78
  final stamina 0/0

E trusts reads + Bottom RECOVER
  Tap 5
  Escapes 20
  Timeouts 75
  final stamina 0/6
```

---

# Facts established by this implementation

1. The pre-change ~72% free-attack drain was real and checker-reproducible.
2. Rule 1 eliminates responder stamina charge on all measured true-UNFUNDED initiator exchanges.
3. Rule 2 eliminates additive double charging on all measured hold exchanges.
4. The standard surfaces require no supplemental hold charge after Rule 2; the isolated UNFUNDED-responder case remains supported.
5. Surface E spends far less time at mutual zero.
6. Surface E still never clears the Exhausted latch.
7. Surface E instead shifts strongly into the mutually-Exhausted/not-both-zero window.
8. Trust-read Gate B remains valid at 7/100.
9. Hedge-one and always-HIGH remain 0-tap policies on these seeds.
10. Public-MATCH Threat reach collapses from 78/100 to 0/100.
11. Trust-read Threat reach declines from 58/100 to 50/100.
12. Recognition/immediate resolution, commitment costs, UNFUNDED equality, exhaustion thresholds, and the frozen matchup matrix remain unchanged.

---

# Review boundary

The current implementation must not be tuned further inside this slice.

The two pieces of evidence that require design review are:

```text
Gate D OPEN:
existing RECOVER still cannot leave Exhausted

P6 warning realized:
public-MATCH Threat reach collapses 78/100 -> 0/100
```

Any corrective mechanic requires a separately written amendment / Definition of Done and another literal HARD STOP.

No such amendment is included in this document.

The next valid step is PR review.
