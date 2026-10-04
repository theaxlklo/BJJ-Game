# Stamina Economy — Rule-Change Definition of Done

## Status

**FROZEN FOR USER REVIEW — HARD STOP.**

This document defines the first rule-changing stamina-economy slice after the measurement-only PR.

It does **not** authorize implementation.

Implementation must not begin until the user explicitly reviews this committed DoD and authorizes crossing the HARD STOP.

## Base and branch

Base `main` after squash-merging measurement PR #7:

```text
3b38783df9134aed77e3be5460ea1d0b60edc458
```

Branch:

```text
review/stamina-economy-rule-dod
```

Frozen Mount enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Authoritative measurement documents:

```text
docs/STAMINA_ECONOMY_MEASUREMENT_DEFINITION_OF_DONE.md
docs/STAMINA_ECONOMY_FIRST_MEASUREMENT.md
```

## Purpose

The measurement slice established that the current stamina problem is not simply:

```text
both fighters reach zero
```

and it is not primarily:

```text
UNFUNDED vs UNFUNDED produces taps
```

The strongest observed economy failure is:

```text
an initiator with no fundable commitment can keep initiating at zero commitment cost
+
the responder can still be charged response commitment stamina
+
a Contested submission hold can add another provisional charge
+
existing CONSERVE recovery is spent back out before the defender reaches
the >=35 Exhausted-latch clear threshold
```

This slice changes **stamina settlement**, not action selection, Recognition probabilities, matchup grades, or submission progression rules.

The intended result is narrow:

1. an UNFUNDED attack must not force stamina expenditure from the responder;
2. the provisional hold cost must stop acting as an additive double charge when response commitment has already paid at least the hold amount;
3. the existing RECOVER behavior must be given a real opportunity to accumulate stamina and leave Exhausted without increasing its recovery rate or lowering the latch-clear threshold.

The slice deliberately **does not change UNFUNDED-vs-UNFUNDED commitment equality**.

## Evidence hierarchy from the first measurement

### Priority 1 — free attack forces paid defense

Surface E uses:

```text
Recognition=enabled
response commitment policy=RECOGNITION
Top behavior=PRESSURE / FIXED
Bottom baseline=ESCAPE
Bottom behavior mode=RECOVER
100 matches
seed=42
interval=5 s
100/100 starting stamina
```

Independent review reproduced:

```text
Bottom switches into CONSERVE=90
Bottom switches back to ESCAPE=0
median final stamina=0 / 2
```

The first measurement already records:

```text
Bottom behavior recovery=8,658
Top zero-stamina initiated attacks=1,949
zero-stamina submission advances=0
zero-stamina taps=0
Bottom Exhausted-latch clears=0
```

Independent review additionally measured:

```text
Bottom stamina spent responding to Top's 1,949 zero-stamina attacks
(response commitment + provisional hold)
= 6,202

6,202 / 8,658
= approximately 71.6% of Bottom's recovered stamina
```

This `6,202` value is **review-provided evidence, not yet checker-owned evidence**.

The implementation order below requires the checker to reproduce and record it before any rule change.

Surface B independent contrast:

```text
Bottom spend caused by Top zero-stamina attacks=95
```

The reason for the large Surface-E difference is that RECOVER repeatedly creates small amounts of spendable stamina for Bottom, while Top continues to initiate for zero commitment cost.

### Priority 2 — provisional hold is additive

Surface E State-2 holds:

```text
hold exchanges=1,490
FULL=100
PARTIAL=1,113
NONE=277

requested response commitment + hold fully fundable=100/1,490
commitment-only fundable but requested commitment + hold not fundable=1,366
```

Across all Surface-E hold exchanges:

```text
median responder stamina before response charge=4
median responder stamina after response charge=1

Bottom provisional hold spend=1,745
```

The existing LOW=3 hold cost was explicitly provisional in v0.3a.

This slice reviews how that cost is **settled**, while retaining the nominal 3-point hold burden.

### Priority 3 — UNFUNDED equality

Current rule:

```text
UNFUNDED rank == UNFUNDED rank
-> no responder under-commitment modifier
```

Measured both-UNFUNDED exchanges:

```text
A 3,588
B 3,771
C 3,697
D 3,744
E 1,604
```

Across all five first-measurement surfaces:

```text
both-UNFUNDED submission advances=0
both-UNFUNDED taps=0
```

Therefore this slice **does not change UNFUNDED equality**.

It remains explicit design debt only if later evidence shows a need.

---

# Frozen rule changes

## Rule 1 — an UNFUNDED initiator cannot impose responder stamina cost

### Trigger

The rule is based on the initiator's **true effective commitment**, not raw stamina:

```text
initiator true effective commitment == UNFUNDED
```

Under the existing funding rule this normally means the initiator has 0-2 stamina and cannot fully fund LOW.

The important zero-stamina subset remains separately measured because it is the observed dominant Surface-E drain.

### Existing behavior that remains

The exchange still exists.

Do **not** make zero-stamina or UNFUNDED attacks illegal in this slice.

The following remain selected exactly as before:

- initiator action;
- responder legal response;
- Recognition intent read;
- Recognition capability read;
- responder requested commitment;
- responder true effective commitment for diagnostic/history purposes;
- base matchup grade;
- exhaustion modifier;
- commitment magnitude transform;
- response-undercommitment comparison;
- feint semantics;
- submission stage semantics.

### New settlement rule

When:

```text
initiator true effective commitment == UNFUNDED
```

then:

```text
responder commitment stamina charged = 0
provisional hold stamina charged = 0
```

The responder's selected/requested/effective commitment is **not rewritten** merely to hide the cost waiver.

The waiver is a stamina-settlement rule.

This preserves the information model:

```text
the defender may still misread the attacker
the defender may still choose LOW / MEDIUM / HIGH
the response action still resolves normally
but a threat that itself has no funded commitment cannot extract stamina
from the defender
```

### Resolution consequence

No new grade bonus or penalty is introduced.

For a fixed pre-exchange state, action, response, requested commitments, effective commitments, and Recognition read, the immediate:

- final grade;
- axis change;
- setup change;
- submission transition;
- feint behavior;
- terminal escape / Tap decision

must remain identical to the pre-rule engine.

Only stamina settlement and later trajectory may differ.

### Why the trigger is UNFUNDED, not exactly zero

The existing commitment model already defines:

```text
0-2 stamina
-> cannot fund LOW
-> effective commitment=UNFUNDED
-> initiator commitment cost=0
```

A 1- or 2-stamina attacker has the same zero commitment payment as a 0-stamina attacker.

The anti-asymmetry rule therefore uses the existing semantic boundary rather than inventing a special raw-zero rank.

The checker must still preserve a dedicated exactly-zero metric.

### Future-design dependency — free over-commit is safe only under current semantics

Under Rule 1, a responder facing an UNFUNDED initiator may still request HIGH while paying zero responder stamina.

That is acceptable **only because over-committing currently provides no direct bonus beyond the existing true/effective comparison semantics**.

Any future rule that rewards over-commitment, grants a defensive bonus for commitment above the attack, or otherwise makes excess requested/effective commitment beneficial must explicitly revisit Rule 1's zero-cost responder settlement.

This dependency must be carried forward as design debt; it is not changed in this slice.

---

## Rule 2 — the provisional hold cost is supplemental, not additive

The nominal provisional hold amount remains:

```text
3 stamina
```

The current behavior charges:

```text
response commitment
+
up to another 3 stamina for the hold
```

This creates additive double charging.

### New funded-initiator settlement

For a Contested exchange that actually invokes the provisional hold path, after responder commitment settlement:

```text
supplemental_hold_request
= max(0, 3 - responder_commitment_stamina_charged)
```

Then:

```text
supplemental_hold_charged
= min(responder stamina remaining, supplemental_hold_request)
```

Therefore, when the initiator is funded:

```text
responder charged LOW (3)
-> supplemental hold request=0
-> total response+hold burden=3

responder charged MEDIUM (7)
-> supplemental hold request=0
-> total response+hold burden=7

responder charged HIGH (12)
-> supplemental hold request=0
-> total response+hold burden=12

responder charged 0 because responder itself is UNFUNDED
-> supplemental hold request=3
-> charge up to remaining stamina
```

The hold amount becomes a **minimum hold burden**, not an additional 3 points on top of an already-funded response commitment.

### Practical consequence — Rule 2 nearly eliminates separate hold charging

Every funded response commitment already costs at least LOW=3.

Therefore, under Rule 2:

```text
funded responder LOW / MEDIUM / HIGH
-> supplemental hold request=0
```

A separate hold charge remains possible only when:

```text
initiator is funded
AND
responder true effective commitment == UNFUNDED
```

In that case the responder can have at most 0-2 stamina available, so the supplemental hold can charge at most 2.

If the initiator is also UNFUNDED, Rule 1 waives even that.

So this slice intentionally makes response commitment do almost all of the stamina-accounting work that the provisional hold cost was originally added to provide.

That is not treated as an accidental side effect; it is part of the reviewed design.

Because the provisional hold was introduced to keep an informed defender from making Threat effectively unreachable, the checker must separately report the post-change informed defender's:

- Ready -> Threat reach count / rate;
- total Threat entries;
- Control entries;
- Finish entries;
- taps;

for the frozen trust-read and public-MATCH informed surfaces.

Whether Threat reach collapses back toward the old v0.3a near-zero behavior is an **observation**, not a hidden pass target. If it does, record it and review it; do not restore the additive hold charge or tune another mechanic inside this slice unless a new amendment is reviewed.

### Rule-1 precedence

If:

```text
initiator true effective commitment == UNFUNDED
```

Rule 1 wins:

```text
responder commitment charged=0
supplemental hold requested=0
supplemental hold charged=0
```

An UNFUNDED attack cannot bypass Rule 1 through the hold path.

### Hold semantics unchanged

This rule does not change:

- which exchange counts as a provisional hold;
- Contested semantics;
- submission stage progression;
- submission break behavior;
- nominal provisional hold amount of 3;
- legal response selection.

Only the amount additionally charged after responder commitment is changed.

---

# Frozen implementation order

The implementation must preserve the failed baseline before changing mechanics.

## Step 1 — checker metric first, no mechanic change

Extend the existing stamina-economy structured measurement and checker to report, per surface:

### Zero-stamina initiator defender-drain metric

For every exchange where:

```text
initiator pre-exchange stamina == 0
```

record defender spend caused by that exchange:

```text
responder commitment charged
+
provisional hold charged
```

Report separately:

- initiator side;
- exchange count;
- response commitment charged;
- hold charged;
- total responder spend;
- responder spend by stamina state;
- responder spend by action ID;
- responder spend on submission vs non-submission actions.

For Surface E specifically report:

```text
Bottom spend caused by Top zero-stamina attacks
Bottom behavior recovery
zero-attack-caused Bottom spend / Bottom behavior recovery
```

### UNFUNDED initiator defender-drain metric

Separately report the same accounting for:

```text
initiator true effective commitment == UNFUNDED
```

so the exact-zero subset and the semantic UNFUNDED set cannot be conflated.

### Baseline checkpoint

Before any mechanic change, the implementation branch must run the frozen 100-seed surfaces and record the checker-owned baseline.

The Surface-E exact-zero metric must reproduce the review evidence:

```text
Top zero-stamina attacks=1,949
Bottom zero-attack-caused response+hold spend=6,202
Bottom behavior recovery=8,658
share approximately 71.6%
```

Surface B must reproduce:

```text
Bottom zero-attack-caused response+hold spend=95
```

If the checker does not reproduce those values, stop and resolve the accounting disagreement before changing mechanics.

The baseline evidence must be committed in a pre-change measurement document.

Only after that commit may Rule 1 / Rule 2 implementation begin.

---

# Definition-of-Done gates

## Gate A — pre-change defender-drain evidence is frozen

PASS requires:

1. exact-zero and semantic-UNFUNDED initiator metrics are separately structured;
2. Surface E reproduces:
   - 1,949 Top zero-stamina attacks;
   - 6,202 Bottom stamina charged because of those attacks;
   - 8,658 Bottom behavior recovery;
   - approximately 71.6% drain/recovery share;
3. Surface B reproduces 95 Bottom stamina charged by Top zero-stamina attacks;
4. the response-vs-hold split is printed even though no split value is predeclared here;
5. the failed baseline is committed before mechanic changes.

This gate freezes evidence, not a desired post-change value.

---

## Gate B — UNFUNDED attacks impose zero responder stamina cost

### Deterministic unit probes

At minimum test:

```text
initiator stamina=0
requested MEDIUM
true effective=UNFUNDED

initiator stamina=1
requested MEDIUM
true effective=UNFUNDED

initiator stamina=2
requested HIGH
true effective=UNFUNDED
```

For each, test responders that can otherwise fund LOW, MEDIUM, and HIGH.

PASS requires:

```text
responder commitment charged=0
hold charged=0 when hold path occurs
```

while selected response/commitment and immediate resolution remain unchanged.

### Boundary control

Probe:

```text
initiator stamina=3
requested LOW
true effective=LOW
```

Rule 1 must **not** apply.

Normal responder commitment settlement and Rule-2 hold settlement apply.

### Frozen-surface batch requirement

After implementation, on every frozen surface:

```text
defender response+hold stamina charged
on true-UNFUNDED initiator exchanges
= 0
```

and specifically:

```text
Surface E Bottom spend caused by Top zero-stamina attacks=0
Surface B Bottom spend caused by Top zero-stamina attacks=0
```

This is a hard rule invariant, not an observational target.

---

## Gate C — provisional hold no longer double-charges funded response commitment

For an actual hold exchange with a funded initiator:

```text
supplemental hold request
= max(0, 3 - response commitment charged)
```

Required deterministic probes:

### LOW responder

```text
response charged=3
supplemental hold requested=0
combined response+hold charged=3
```

### MEDIUM responder

```text
response charged=7
supplemental hold requested=0
combined response+hold charged=7
```

### HIGH responder

```text
response charged=12
supplemental hold requested=0
combined response+hold charged=12
```

### UNFUNDED responder with funded initiator

Example:

```text
responder starts with 2
response effective=UNFUNDED
response charged=0
supplemental hold requested=3
supplemental hold charged=2
supplemental hold shortfall=1
combined charged=2
```

### UNFUNDED initiator override

Regardless of responder stamina or requested commitment:

```text
initiator true effective=UNFUNDED
-> response charged=0
-> supplemental hold requested=0
-> hold charged=0
```

### Batch invariant

No funded-response hold exchange may satisfy:

```text
response commitment charged >= 3
AND
supplemental hold charged > 0
```

The checker must report zero such additive double-charge cases.

---

## Gate D — existing RECOVER can actually leave Exhausted

Use the exact frozen Surface E configuration.

Do not modify:

- CONSERVE recovery rate;
- behavior stamina quantum;
- Exhausted entry threshold;
- Exhausted latch-clear threshold;
- RECOVER policy switching threshold.

PASS requires at least one deterministic observed:

```text
Bottom Exhausted -> non-Exhausted latch clear
```

and at least one:

```text
Bottom behavior switch CONSERVE -> ESCAPE
```

in the 100-seed Surface-E diagnostic.

There is **no required count beyond nonzero**.

Also report:

- number of latch-clearing matches;
- total latch clears;
- first latch-clear time distribution;
- stamina at latch clear;
- State-2 -> State-1 exits;
- State-2 re-entries after recovery;
- Bottom final stamina median;
- State-1/2/3 duration shares;
- taps / escapes / timeouts.

These are observational except for the nonzero ability to leave Exhausted.

The gate is intentionally minimal:

```text
prove the deadlock is broken
without tuning a desired recovery frequency
```

---

## Gate E — Recognition and immediate resolution semantics remain intact

This stamina settlement slice must not alter Recognition or matchup meaning.

PASS requires:

### Recognition invariants

Unchanged:

```text
requested intent truth
effective capability truth
independent d6 reads
one-rank lower/exact/higher mapping
endpoint clamps
trust-read defender policy
hedge-one diagnostic policy
always-HIGH diagnostic policy
```

### Immediate exchange equivalence

For matched isolated probes with identical:

- pre-exchange position;
- stamina;
- action;
- response;
- requested commitments;
- true effective commitments;
- Recognition read;
- behavior;
- submission stage;

the new rules may change only:

```text
responder stamina charged
supplemental hold stamina charged
post-exchange stamina
later trajectory
```

They may not directly change:

- final grade;
- axis delta;
- setup transition;
- submission stage transition;
- feint cap;
- escape destination;
- Tap determination.

This gate contains **no batch outcome requirement**.

---

## Gate F — v0.3a competent-defender Gate B is re-measured, not tuned

The frozen criterion remains exactly:

```text
0% < informed Tap < 50%
```

After Rule 1 and Rule 2, rerun the standard informed Recognition surface and report the new tap count.

The exact historical value:

```text
6/100
```

is historical evidence only and is not required to remain numerically identical after an authorized stamina rule change.

### PASS / OPEN semantics

If:

```text
0% < informed Tap < 50%
```

then Gate F is PASS.

If the post-change result is:

```text
0%
OR
>=50%
```

then:

```text
Gate F = OPEN
```

and the result must be recorded as a regression against the frozen v0.3a criterion.

Do **not** tune:

- Recognition probabilities;
- trust-read policy;
- commitment costs;
- stamina recovery;
- hold settlement;
- grade modifiers;
- Gate-B thresholds;

inside the same implementation merely to force Gate F to PASS.

Instead:

```text
record the failed measurement
-> stop rule tuning
-> write a separate design amendment / DoD
-> commit it
-> HARD STOP
-> user review
-> only then make any corrective mechanic change
```

This is the same failure discipline as Gate D.

The checker must also print the historical 6/100 value beside the new result so the regression is visible rather than silently replacing history.

---

## Gate G — stamina accounting remains exact

For every frozen surface, match, and side:

```text
starting stamina
+ behavior recovery
- behavior spend
- initiator commitment charged
- responder commitment charged
- supplemental hold charged
= final stamina
```

must reconcile exactly.

The checker must separately report:

- responder charge waived by Rule 1;
- nominal response commitment that would have been charged absent Rule 1;
- supplemental hold request;
- supplemental hold charged;
- supplemental hold shortfall;
- hold amount already covered by response commitment;
- exact-zero-attack defender spend;
- UNFUNDED-attack defender spend;
- defender spend / behavior-recovery share.

Do not hide waived or covered amounts inside net totals.

---

## Gate H — deferred mechanics remain frozen

This slice must **not** change:

### Commitment

```text
LOW=3
MEDIUM=7
HIGH=12
```

Do not change:

- requested -> effective funding downgrade;
- commitment magnitude transform;
- HIGH amplification;
- LOW/UNFUNDED compression;
- response-undercommitment +1 rule;
- requested-LOW feint intent semantics;
- exhaustion-before-commitment modifier order.

### Exhaustion / behavior stamina

Do not change:

- starting stamina;
- stamina maximum;
- Exhausted entry threshold;
- >=35 latch-clear threshold;
- PRESSURE spend;
- ESCAPE spend;
- CONSERVE recovery;
- 5-second behavior quantum;
- RECOVER policy decision rule.

### Recognition

Do not change:

- d6 probabilities;
- mapping;
- truth/perception separation;
- RNG streams;
- trust-read policy;
- hedge-one policy;
- always-HIGH policy.

### Submission

Do not change:

- Ready / Threat / Control / Finish / Tap stages;
- success/Contested/failure transition semantics;
- failure break behavior;
- which exchanges invoke provisional hold;
- nominal hold amount of 3.

Only the **settlement of that 3-point amount** changes under Rule 2.

### Action legality

Do not make zero-stamina or UNFUNDED attacks illegal in this slice.

Their legality remains unchanged so this slice isolates stamina settlement.

### UNFUNDED equality

Do not change:

```text
UNFUNDED == UNFUNDED
-> no responder-undercommitment modifier
```

This is explicitly deferred.

### Other systems

Do not change:

- Mount matchup matrix or digest;
- setup policies;
- stalling cadence/consequences;
- scoring;
- timeout rules;
- initiator tactical commitment policy;
- random response-commitment weighting.

---

## Gate I — checker, regression, and review boundary

The primary semantic checker must print a named section for this rule-changing slice containing:

1. pre-change zero-attack defender-drain baseline;
2. post-change zero-attack defender drain;
3. semantic-UNFUNDED initiator defender drain;
4. responder charge waived by Rule 1;
5. old-vs-new hold settlement accounting;
6. additive double-charge count;
7. Surface-E recovery/latch-clear results;
8. informed Threat-reach / Threat / Control / Finish / Tap observations;
9. stamina-source reconciliation;
10. v0.3a Gate-B historical + post-change status, including PASS vs OPEN;
11. frozen digest.

Structured values must be available to tests; prose parsing alone is insufficient.

### Required tests

At minimum add regression tests for:

- exactly 0 / 1 / 2 stamina initiator Rule-1 trigger;
- 3-stamina LOW-funded boundary;
- LOW/MEDIUM/HIGH responder hold coverage;
- UNFUNDED responder partial supplemental hold;
- UNFUNDED initiator hold override;
- immediate-resolution equivalence;
- exact source reconciliation;
- Surface-E nonzero latch clear;
- Surface-E CONSERVE -> ESCAPE switch;
- zero defender drain from zero-stamina attacks;
- zero defender drain from all true-UNFUNDED attacks;
- unchanged UNFUNDED equality;
- unchanged digest.

### Measurement interpretation

A later PASS must distinguish:

```text
rule invariant PASS
```

from:

```text
observed gameplay distribution
```

The following are **not** pass/fail targets in this slice:

- exact tap count; the only tap pass/fail rule is the separately frozen Gate-F range;
- exact Threat / Control / Finish counts;
- exact escape count;
- exact timeout count;
- final stamina median;
- number of State-2/State-3 entries;
- frequency of recovery beyond the required proof that recovery can occur;
- hedge-one or always-HIGH outcome count.

Do not tune the rules to restore any historical observational number.

---

# Required implementation chronology after authorization

If and only if the user authorizes implementation of this DoD:

```text
1. add checker metric for defender spend caused by zero-stamina / UNFUNDED attacks
2. run frozen pre-change surfaces
3. reproduce 6,202 / 8,658 Surface-E evidence and Surface-B 95
4. commit pre-change measurement document
5. only then implement Rule 1 and Rule 2
6. add/update unit and regression tests
7. run all existing gates, including Gate F PASS/OPEN without tuning
8. run exact frozen A-E surfaces
9. compare observed results against predeclared P1-P6 predictions
10. record post-change measurement, including Threat reach and hedge comparison
11. open/update PR for review
12. HARD STOP for user review
13. no merge without explicit authorization
```

If Step 3 does not reproduce the independent review numbers, implementation stops before mechanic changes.

---

# Predeclared outcome predictions

These predictions are written **before any Rule-1 / Rule-2 prototype or post-change batch run**.

They are directional hypotheses, not pass/fail targets, except where an existing frozen gate separately defines a requirement.

Do not revise them after seeing results.

## Prediction P1 — trust-read taps

Baseline:

```text
Surface B trust-read taps=6/100
```

Prediction:

```text
post-change trust-read taps will decrease or stay near the low end
of the existing range rather than increase materially
```

Reason:

```text
the defender should retain more stamina
-> fewer tired-state under-commitment opportunities are expected
```

A drop to 0 is plausible and would make the separately defined v0.3a Gate F OPEN; it must not be tuned away automatically.

## Prediction P2 — public-MATCH informed taps

Baseline:

```text
Surface A public MATCH taps=0/100
```

Prediction:

```text
public-MATCH informed taps remain at or near 0
```

Reason:

```text
the current public-MATCH defender already suppresses submissions strongly;
preserving defender stamina is not expected to create new submission conversion
```

This is observational only.

## Prediction P3 — final stamina

Baseline fixed surfaces:

```text
A/B/C/D median final stamina=0/0
```

Baseline Surface E:

```text
median final stamina=0/2
```

Prediction:

```text
responder final stamina will increase on at least some surfaces,
most visibly Surface E
```

No exact median is predicted.

Top/initiator final stamina is not predicted to increase from these settlement changes.

## Prediction P4 — middle-window and mutual-zero occupancy

Prediction:

```text
Surface E will still enter the mutually-Exhausted middle window,
but will spend less of its later trajectory trapped there / at mutual zero,
and will demonstrate at least one return to State 1
```

For A-D:

```text
State-2 / State-3 entry rates or duration shares may decline or be delayed
because responder stamina is no longer drained by UNFUNDED initiators
```

No exact frequency is predicted.

## Prediction P5 — hedge comparison

Baseline:

```text
trusts reads: 6 taps
hedge-one:     0 taps
always HIGH:   0 taps
```

Prediction:

```text
hedge-one and always-HIGH will continue to be at least as submission-resistant
as trust-read, but the size and cost of their advantage may change
because Rule 1 removes responder stamina cost on UNFUNDED attacks for every policy
```

No exact tap, escape, spend, or stamina target is predicted.

The comparison must still be printed on identical seeds.

## Prediction P6 — Threat reach after hold settlement

Because Rule 2 nearly abolishes a separate funded-response hold charge:

```text
Threat reach may fall relative to the current v0.4b measurement
```

The direction is uncertain enough that no pass target is frozen.

In particular, if informed Threat reach collapses toward the old v0.3a near-zero behavior that originally motivated the provisional hold cost, record that result explicitly and treat it as design evidence.

Do not retune inside this slice merely to restore a preferred Threat rate.

---

# Expected causal test

The predictions above do not predeclare a required final match distribution beyond the separately frozen gates.

This section freezes the causal hypothesis being tested:

```text
CURRENT:
UNFUNDED/free initiator
-> responder can still spend
-> hold can spend again
-> CONSERVE recovery is repeatedly drained
-> Exhausted latch never clears

AFTER RULE 1 + RULE 2:
UNFUNDED initiator cannot drain responder
+
funded response commitment covers the first 3 points of hold burden
-> defender retains more recovered stamina
-> existing CONSERVE may accumulate toward 35
-> Surface E must demonstrate at least one actual latch clear
```

If Rule 1 and Rule 2 satisfy their local invariants but Surface E still has zero latch clears, Gate D remains OPEN.

If the re-measured competent-defender tap rate falls outside `0% < Tap < 50%`, Gate F remains OPEN.

For either failure:

```text
record the result
-> do not tune inside the same slice
-> write a separate design amendment
-> commit it
-> HARD STOP
-> user review
```

Do **not** change recovery rate, thresholds, commitment costs, Recognition, hold settlement, or Gate-B thresholds merely to force the failed gate to PASS.

Either failure is new evidence requiring another reviewed design amendment.

---

# Hard stop

This commit authorizes **nothing beyond design review**.

Do not:

- implement Rule 1;
- implement Rule 2;
- add the checker metric;
- run a mechanic-changing experiment;
- change any stamina rule;
- change any hold settlement;
- change action legality;
- change UNFUNDED equality;

until the user explicitly authorizes implementation after reviewing this committed DoD.

The next valid action after this document is committed is:

```text
STOP
-> present DoD for user review
-> wait for explicit implementation authorization
```
