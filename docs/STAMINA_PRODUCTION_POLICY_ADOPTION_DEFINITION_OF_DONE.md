# Stamina Production-Policy Adoption — Definition of Done

## Status

**FROZEN FOR USER REVIEW — HARD STOP.**

This document defines the production-policy adoption slice that follows the completed recovery-policy amendment.

It does **not** authorize implementation.

No production default, canonical game profile, settlement rule, or recovery-initiation behavior may change until the user explicitly reviews this committed DoD and authorizes implementation.

---

# Base and branch

Base `main` after squash-merging PR #9:

```text
51ada9c92849a1130881d78b8cf44a1e8936fb38
```

Branch:

```text
review/stamina-production-policy-adoption-dod
```

Frozen Mount enumeration digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Authoritative prior evidence:

```text
docs/STAMINA_ECONOMY_RULE_PRECHANGE_EVIDENCE.md
docs/STAMINA_ECONOMY_RULE_POSTCHANGE_MEASUREMENT.md
docs/STAMINA_RECOVERY_POLICY_STARTING_EVIDENCE.md
docs/STAMINA_RECOVERY_POLICY_AMENDMENT_FIRST_MEASUREMENT.md
```

---

# Decision entering this slice

The completed attribution/recovery amendment supports three separate decisions.

## Rule 1 — preferred for production adoption

Rule 1:

```text
initiator true effective commitment == UNFUNDED
-> responder commitment stamina charged=0
-> hold stamina charged=0
```

Isolated public-MATCH evidence:

```text
NONE:
Threat matches=78/100

RULE1_ONLY:
Threat matches=78/100
```

Rule 1 removes the free-attack -> paid-defense asymmetry without reproducing the public-MATCH Threat collapse.

## Rule 2 — deferred from production

Rule 2:

```text
funded response commitment covers the first 3 points
of the nominal provisional hold burden
```

Isolated public-MATCH evidence:

```text
RULE2_ONLY:
Threat matches=0/100

BOTH:
Threat matches=0/100
```

The full:

```text
78/100 -> 0/100
```

Threat collapse is therefore causally attributable to Rule 2.

**This slice does not redesign Rule 2.**

Rule 2 remains available as an explicit diagnostic/experimental capability, but the proposed production configuration must keep it disabled.

### Rule 2 intended to fix — additive response + provisional-hold double charging

Rule 2 was not arbitrary. It was introduced to address a measured stamina-economy problem in the existing provisional hold path:

```text
responder pays response commitment
+
Contested submission hold may charge up to another 3 stamina
```

The measurement slice showed that commitment-only affordability could therefore overstate the defender's real ability to pay a response-plus-hold burden.

Surface-E evidence included:

```text
State-2 hold exchanges=1,490
FULL/PARTIAL/NONE=100/1,113/277

commitment-only fundable
but requested commitment + hold not fully fundable=1,366
```

Rule 2 attempted to solve that by making the 3-point hold burden supplemental rather than additive.

Its isolated measurement then revealed a worse regression:

```text
public-MATCH Threat reach:
78/100 -> 0/100
```

Therefore deferring Rule 2 explicitly reopens this debt:

> **The legacy funded-response + provisional-hold path can still impose an additive stamina charge, and commitment-only affordability can still overstate the responder's true hold-inclusive affordability.**

That debt must remain named until Rule 2 is redesigned, replaced, or the provisional hold model itself is deliberately retained.

Do not silently treat "Rule 2 deferred" as "hold-settlement problem solved."

## LOW_WHILE_EXHAUSTED — preferred recovery candidate

Under the previous BOTH settlement configuration:

```text
                         CURRENT   RESET   LOW

Bottom final median           6      19     26
latch clears                  0     234     67
setup-builder attempts     1326       0   1114
RESET-with-route exposure      7     983      7
```

LOW preserved most setup activity while producing real Exhausted-latch clears.

RESET produced more clears and fewer timeouts, but eliminated exhausted-state setup construction and created much larger RESET-with-route exposure.

**LOW is the preferred candidate entering this slice.**

It is not yet adopted because the earlier LOW measurement used BOTH settlement rules.

The exact proposed production combination:

```text
Rule 1 ON
Rule 2 OFF
LOW_WHILE_EXHAUSTED
```

must be measured before promotion.

---

# Residual stalling interpretation

The completed amendment observed:

```text
RESET-with-progress-route exposure:
CURRENT=7
RESET=983
LOW=7

real v0.3b Warnings:
CURRENT=0
RESET=0
LOW=0
```

The zero real offenses are valid for the measured policies/seeds because frozen v0.3b counts legal defensive engagement as engagement and Top's normal defensive interactions reset Bottom's 20-second advancement clock.

This does **not** prove RESET is intrinsically stalling-safe.

A future opponent/policy that avoids qualifying defensive engagement could allow some of RESET's large exposure to become real offenses.

Because RESET is not the preferred production candidate, this remains residual design risk rather than a blocker for LOW.

Do not change v0.3b in this slice.

---

# P8 interpretation carried forward

The previous amendment froze:

```text
P8:
real v0.3b consequences were predicted to make recovery
less favorable for at least one passive candidate
```

Observed:

```text
OFF/ON gameplay identical=True
diverged matches CURRENT/RESET/LOW=0/0/0
```

Therefore:

```text
P8 = NOT CONFIRMED
```

means:

> the predicted stalling-induced gameplay divergence did not occur.

It does **not** mean the implementation, checker, or measurement failed.

No real v0.3b offense fired, so stalling ON had no gameplay consequence to apply.

This wording must remain explicit in the adoption measurement so later readers do not reinterpret `NOT CONFIRMED` as a failed gate.

---

# Central production-candidate hypothesis

The candidate to test is:

```text
Rule 1 ON
Rule 2 OFF
Bottom RECOVER initiation:
    LOW while Exhausted
    baseline MEDIUM after Exhausted clears
```

The expected causal chain is:

```text
UNFUNDED attacker cannot drain defender
+
Bottom does not spend MEDIUM=7 on every exhausted-state initiation
+
legacy/provisional hold settlement remains available because Rule 2 is OFF
->
Bottom can retain enough stamina to clear Exhausted
without collapsing informed Threat reach
and without eliminating setup activity
```

This is a hypothesis to measure before adoption.

---

# Production integration principle

Do **not** make historical feature flags disappear.

The project must preserve:

- legacy replay;
- PR #8 BOTH replay;
- Rule1-only diagnostics;
- Rule2-only diagnostics;
- CURRENT / RESET / LOW diagnostic recovery modes.

Production adoption must be represented through **one explicit canonical production configuration/policy entry point** rather than changing historical diagnostic defaults in-place.

The exact type/function name may follow the existing architecture, but it must provide one unambiguous way for the future playable frontend to request:

```text
production Mount-v0 stamina/recovery policy
```

The canonical production configuration must select:

```text
Rule 1 = ON
Rule 2 = OFF
Recovery initiation while Bottom RECOVER + Exhausted = LOW
Recovery initiation after Exhausted clears = baseline MEDIUM
```

It must **not** implicitly enable unrelated systems whose production status is outside this slice.

In particular, this DoD does not decide whether a future frontend globally enables/disables:

- v0.3b stalling;
- any future scoring system;
- AI policy choices unrelated to RECOVER;
- setup-rule changes.

The production stamina/recovery policy must be composable with those systems rather than silently selecting them.

---

# Required chronology after authorization

If and only if the user authorizes this committed DoD, implementation has **two authorization stages**.

## Stage 1 — handoff baseline / final preregistration

```text
1. add read-only LOW->MEDIUM handoff / re-exhaustion instrumentation only

2. do NOT add or run the Rule1-only + LOW production candidate yet

3. run the historical LOW+BOTH recovery surface on the same 100 seeds
   and measure re-exhaustion after every Exhausted-latch clear

4. also run CURRENT+Rule1-only as a control and report that it has
   no usable re-exhaustion denominator if latch clears remain zero

5. record cumulative re-exhaustion after:
   1 tick  = 5 s
   2 ticks = 10 s
   3 ticks = 15 s
   4 ticks = 20 s
   plus median/percentiles for time-to-re-exhaustion when observed

6. create:
   docs/STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md

7. copy A1-A10 into that document unchanged except A9, which must now
   freeze one explicit N-tick horizon and one explicit X% threshold
   using the measured historical LOW+BOTH handoff baseline

8. commit the preregistration document

9. HARD STOP again

10. user reviews the frozen A9 threshold and explicitly authorizes
    the actual production-candidate run
```

CURRENT+Rule1-only is still reported because it is the production settlement control, but prior evidence shows zero clears; if that remains true, it cannot define a percentage of clear events that re-exhaust.

The historical LOW+BOTH policy is the primary A9 baseline because it has a real clear population:

```text
67 latch clears
```

The A9 threshold must be frozen **before** Rule1-only + LOW is run.

## Stage 2 — adoption candidate

Only after the second authorization:

```text
11. add a PROPOSED-PRODUCTION diagnostic configuration only
    Rule1 ON
    Rule2 OFF
    LOW_WHILE_EXHAUSTED

12. do NOT change any default yet

13. run the exact production-candidate measurements below

14. score A1-A10 as CONFIRMED / PARTIAL / NOT CONFIRMED

15. record first untuned production-candidate evidence

16. evaluate Gates A-H

17. if any adoption gate is OPEN:
      record it
      do not promote defaults/config
      do not tune
      write a separate amendment if needed

18. only if adoption gates pass:
      add the canonical production stamina/recovery entry point
      selecting Rule1 ON / Rule2 OFF / LOW recovery

19. prove canonical production output is identical to
    the already-measured proposed-production diagnostic

20. run full regression / digest / checker suite

21. record adoption verification

22. open/update PR

23. HARD STOP for user review

24. no merge without explicit authorization
```

The candidate is measured **before** it becomes canonical production behavior, and the re-exhaustion threshold is preregistered before the candidate is measured.

---

# Frozen production-candidate surfaces

Use exact matched 100-seed diagnostics.

## Surface A — public MATCH compatibility

Purpose:

```text
prove Rule 2 is absent and informed Threat access remains intact
```

Configuration is the existing Surface A, except settlement selection is explicitly:

```text
Rule 1 ON
Rule 2 OFF
```

Recovery LOW is irrelevant because Surface A does not use Bottom RECOVER.

## Surface B — trust-read competent defender

Purpose:

- re-measure frozen v0.3a Gate B;
- observe Threat / Control / Finish / Tap;
- ensure Rule1-only settlement remains coherent.

Configuration is existing Surface B with:

```text
Rule 1 ON
Rule 2 OFF
```

## Surface E-PROD — production recovery candidate

Configuration:

```text
existing Surface E
+
Rule 1 ON
Rule 2 OFF
+
Bottom behavior mode=RECOVER
+
LOW_WHILE_EXHAUSTED
```

Run:

```text
stalling OFF + shadow v0.3b
stalling ON using frozen v0.3b
```

Same 100 seeds in both.

---

# Required counters

For each production-candidate surface report:

- Tap;
- Half Guard exits;
- Open Guard exits;
- Reversal exits;
- total escapes;
- timeouts;
- final Top/Bottom stamina median;
- matches reaching Threat;
- Threat entries;
- Control entries;
- Finish entries.

For Bottom on Surface E-PROD report:

- behavior recovery;
- behavior spend;
- defensive response commitment spend;
- hold spend;
- total defensive spend;
- own-attack commitment spend;
- own initiated actions;
- RESET count;
- requested commitment counts while Exhausted;
- Exhausted-latch clears;
- CONSERVE -> ESCAPE switches;
- State2 -> State1 exits;
- non-Exhausted -> Exhausted re-entries after a clear;
- elapsed time from each clear to the next re-exhaustion;
- cumulative re-exhaustion within 1/2/3/4 behavior ticks (5/10/15/20 s);
- share of clear events that remain non-Exhausted through match end;
- State1 / State2 / State3 shares.

Setup interaction while Exhausted:

- Bridge attempts;
- setup-builder attempts;
- setup advances;
- Ready transitions;
- completed setup builds;
- escapes after measured setup builds;
- RESETs forgoing setup opportunity.

Stalling OFF + shadow:

- RESET-with-progress-route exposure;
- shadow threshold reaches;
- shadow Warnings;
- shadow penalties;
- shadow Position Resets;
- shadow boundary free initiative.

Stalling ON:

- real Warnings;
- penalties;
- Position Resets;
- free initiative;
- stalling penalty axis movement;
- matched OFF/ON divergence count.

---

# Gate A — Rule 1 remains exact

For every proposed-production true-UNFUNDED initiator exchange:

```text
responder commitment charged=0
hold charged=0
```

PASS requires zero violations.

Rule 1 semantics must remain identical to the isolated Rule1-only implementation measured in PR #9.

---

# Gate B — Rule 2 is absent from production candidate

PASS requires:

```text
effective Rule 2 = OFF
```

for all production-candidate surfaces.

Surface A must retain the Rule1-only public-MATCH Threat behavior:

```text
matches reaching Threat=78/100
Threat entries=1,950
```

These values are a compatibility invariant here because:

- LOW recovery is not active on Surface A;
- Rule 1 alone already measured exactly 78/1,950;
- changing these values would indicate some unintended difference from the isolated Rule1-only path.

Do not tune another mechanic if this invariant fails.

---

# Gate C — LOW recovery actually fixes the deadlock under Rule1-only settlement

On Surface E-PROD stalling OFF:

PASS requires:

```text
Bottom Exhausted-latch clears > 0
CONSERVE -> ESCAPE switches > 0
State2 -> State1 exits > 0
```

No exact positive count is frozen.

Also report the exact counts and first-clear timing/stamina distribution.

For the LOW -> MEDIUM handoff, report:

```text
clear events
re-exhaustion events after a clear
time from clear -> re-exhaustion
re-exhaustion within 1 / 2 / 3 / 4 ticks
clear events surviving non-Exhausted through match end
```

The final preregistered A9 threshold from
`STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md`
is observational, not an additional Gate-C pass criterion unless the user explicitly amends this DoD before the candidate run.

A severe clear-then-relapse loop can therefore be visible even if the minimal Gate-C condition passes.

If any of the three remain zero:

```text
Gate C = OPEN
-> do not adopt LOW as production
-> no stamina tuning
-> separate amendment required
```

---

# Gate D — LOW preserves real tactical activity

The purpose of LOW over RESET is not merely to recover; it should preserve meaningful initiation/setup behavior.

PASS requires on Surface E-PROD while Bottom is Exhausted:

```text
setup-builder attempts > 0
Bridge attempts > 0
completed setup builds > 0
```

Also report comparisons against the prior BOTH-settlement candidate measurements:

```text
CURRENT setup builders=1,326
RESET setup builders=0
LOW+BOTH setup builders=1,114
```

No exact production-candidate setup count is frozen.

A material decrease is evidence for review, but only total collapse to zero makes this gate OPEN.

Do not alter setup progression to make Gate D pass.

---

# Gate E — competent-defender submission gate remains valid

Existing frozen criterion:

```text
0% < informed Tap < 50%
```

Re-measure Surface B using:

```text
Rule 1 ON
Rule 2 OFF
```

If inside the unchanged range:

```text
Gate E = PASS
```

If:

```text
Tap=0
OR
Tap>=50%
```

then:

```text
Gate E = OPEN
-> record regression
-> no Recognition/stamina/grade tuning
-> separate amendment / HARD STOP
```

Historical values remain visible:

```text
trust-read legacy=6/100
Rule1-only attribution measurement=9/100
BOTH PR8=7/100
```

The production candidate is not required to reproduce any one historical count exactly.

---

# Gate F — frozen v0.3b remains observational and unchanged

For Surface E-PROD run matched:

```text
stalling OFF + shadow
stalling ON
```

PASS requires:

1. shadow observer does not perturb OFF gameplay;
2. frozen real v0.3b implementation is unchanged;
3. all required stalling counters are populated;
4. matched divergence is reported honestly;
5. any real offense uses existing frozen consequences.

There is **no required favorable stalling outcome**.

If OFF clears Exhausted but ON does not:

```text
record it
do not change v0.3b
candidate adoption requires review
```

Residual RESET exposure remains documented even though RESET is not the proposed production policy.

---

# Gate G — canonical production configuration matches measured candidate

This gate is evaluated only after Gates A-F pass and the canonical production entry point is added.

PASS requires exact deterministic equivalence between:

```text
explicit diagnostic:
Rule1 ON
Rule2 OFF
LOW_WHILE_EXHAUSTED

and

canonical production stamina/recovery configuration
```

For matched A/B/E-PROD seeds compare at minimum:

- outcomes;
- axis;
- stamina;
- commitment requests/effective commitments;
- setup state;
- submission state;
- Recognition history;
- recovery mode behavior;
- stalling counters when explicitly enabled.

Any mismatch means the production wrapper/config is not merely adopting the measured candidate and Gate G is OPEN.

---

# Gate H — historical replay and defaults remain available

Production adoption must not erase historical evidence.

PASS requires:

```text
all raw legacy flags false
-> same legacy behavior as merged main

umbrella BOTH
-> same PR8 BOTH behavior

explicit Rule1-only
-> same isolated Rule1 behavior

explicit Rule2-only
-> same isolated Rule2 behavior

diagnostic CURRENT/RESET/LOW modes remain callable
```

Do not delete Rule 2 code in this slice.

Do not make Rule 2 part of canonical production configuration.

Do not change raw dataclass/batch defaults in a way that makes historical test construction silently adopt production semantics.

The future frontend must opt into the canonical production configuration explicitly.

---

# Frozen non-goals

Do not in this slice:

- redesign Rule 2;
- remove Rule 2 diagnostic capability;
- reintroduce additive hold charging as a hidden production side effect;
- select RESET as production recovery behavior;
- change LOW/MEDIUM/HIGH costs;
- change CONSERVE recovery;
- change exhaustion 25/35 hysteresis;
- change Recognition;
- change UNFUNDED equality;
- change matchup grades/digest;
- change setup progression;
- change submission progression;
- change v0.3b;
- change scoring/timeout rules;
- change unrelated AI/initiator policies;
- start frontend implementation.

---

# Adoption-run pre-registration

The following predictions are frozen **before any Rule1-only + LOW candidate run**.

Anchors from the completed LOW+BOTH measurement:

```text
latch clears=67
Bottom final median=26
Half/Open/Reversal=31/15/5
timeouts=44
setup builders=1,114
RESET-with-route exposure=7
```

Scoring rules:

```text
Gates remain pass/fail exactly as defined elsewhere in this DoD.

Predictions A1-A10 are scored:
CONFIRMED
PARTIAL
NOT CONFIRMED

A prediction miss is not automatically a gate failure.

Every miss requires a written explanation in the measurement document.

No numeric range may be edited after the candidate run begins.
```

A1-A8 and A10 are frozen now.

A9 is intentionally completed only through the Stage-1 historical handoff baseline, committed in
`STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md`,
and subjected to a second HARD STOP before the candidate run.

## A1 — public-MATCH Threat compatibility

Frozen expectation:

```text
Threat matches=78/100
Threat entries=1,950
Tap=0/100
```

Expected: **exact**.

Rule1-only already produced these values, and recovery LOW is inactive on Surface A.

## A2 — latch clears

Hard observational floor:

```text
latch clears >=34
```

Expected range:

```text
40-120
```

Anchor:

```text
LOW+BOTH=67
```

The 34 floor is one-half of the previous LOW+BOTH result.

Gate C itself remains the minimal `>0` adoption gate; falling below 34 is therefore a prediction miss requiring review, not automatic gate failure.

## A3 — exhausted-state setup construction

Hard observational floor:

```text
setup-builder attempts >=557
```

Expected range:

```text
800-1,400
```

Anchor:

```text
LOW+BOTH=1,114
```

The 557 floor is one-half of the previous LOW+BOTH result.

Gate D still only becomes OPEN on total collapse to zero. A value from 1-556 would therefore PASS Gate D but score A3 NOT CONFIRMED and require explicit review before adoption.

## A4 — Bottom final stamina

Expected median:

```text
20-35
```

Anchor:

```text
LOW+BOTH=26
```

This is observational, not an independent gate.

## A5 — timeouts

Expected:

```text
30-75
```

Anchors:

```text
LOW+BOTH=44
CURRENT+BOTH=75
```

This is observational.

## A6 — LOW stalling exposure under Rule1-only

This must be re-measured; the prior value of 7 came from LOW+BOTH.

Expected:

```text
RESET-with-progress-route exposure <=15

real v0.3b:
Warnings=0
Penalties=0
Position Resets=0
```

Anchor:

```text
LOW+BOTH exposure=7
CURRENT+BOTH exposure=7
RESET+BOTH exposure=983
```

If exposure exceeds 15 or a real offense fires, record it as new evidence. Do not alter v0.3b.

## A7 — OFF+shadow versus real stalling ON

If no real offense fires, expected:

```text
OFF/ON gameplay identical=True
diverged matches=0/100
```

If a real offense fires, divergence is legitimate new evidence and A7 may be PARTIAL / NOT CONFIRMED without implying observer failure.

## A8 — exit split

Anchor:

```text
LOW+BOTH:
Half Guard=31
Open Guard=15
Reversal=5
```

Expected:

```text
Half Guard remains the largest of the three exit categories
Reversal <15% of matches
```

The full Half/Open/Reversal counts must be printed.

## A9 — LOW -> MEDIUM handoff / re-exhaustion

A9 tests for a clear-then-relapse loop that the existing latch-clear gates do not detect.

Definitions:

```text
clear event:
Bottom Exhausted latch transitions Exhausted -> non-Exhausted

re-exhaustion:
the same Bottom subsequently transitions non-Exhausted -> Exhausted

time-to-re-exhaustion:
simulated seconds from clear timestamp to the next re-exhaustion
```

Stage-1 baseline must measure the historical LOW+BOTH policy on the exact same 100 seeds and report cumulative re-exhaustion within:

```text
1 tick  = 5 s
2 ticks = 10 s
3 ticks = 15 s
4 ticks = 20 s
```

Also report:

- total clear events;
- total re-exhaustions after a clear;
- median time-to-re-exhaustion;
- p25/p75 when defined;
- clears that remain non-Exhausted through match end.

CURRENT+Rule1-only must be reported as a control. If it again produces zero clears, its re-exhaustion percentage is explicitly:

```text
N/A — no clear-event denominator
```

The historical LOW+BOTH clear population is the primary handoff baseline because it previously produced:

```text
67 clears
```

After that baseline—and before any Rule1-only + LOW run—create and commit:

```text
docs/STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md
```

That file must freeze:

```text
A9 horizon N = <explicit tick count and seconds>
A9 maximum acceptable prediction threshold X = <explicit % of clear events>
historical LOW+BOTH rate at N
reason for choosing N and X
```

Then:

```text
HARD STOP
-> user review
-> explicit authorization
-> only then run Rule1-only + LOW
```

No A9 number may be selected after seeing the production candidate.

A9 is scored CONFIRMED / PARTIAL / NOT CONFIRMED in the final measurement document.

## A10 — trust-read Tap gate

Expected:

```text
0% < Tap < 50%
```

This is also Gate E.

Historical context:

```text
legacy trust-read=6/100
Rule1-only=9/100
BOTH=7/100
```

No exact tap count is predicted.

---

# Required measurement document

After authorized implementation, create:

```text
docs/STAMINA_PRODUCTION_POLICY_ADOPTION_FIRST_MEASUREMENT.md
```

It must contain:

1. exact candidate configuration;
2. Gates A-H;
3. A1-A10 preregistration comparison;
4. A/B/E-PROD outcome tables;
5. Half/Open/Reversal exit split;
6. recovery/stamina budget;
7. LOW -> MEDIUM re-exhaustion / handoff analysis;
8. setup interaction;
9. shadow/real stalling comparison;
10. canonical-production equivalence if promotion occurs;
11. explicit Rule 2 deferred status and named additive-hold debt;
12. residual RESET/stalling risk;
13. clear separation between facts and remaining design debt.

---

# Adoption outcome states

The slice has only three valid conclusions.

## ADOPTED

Allowed only if Gates A-H all PASS.

Then:

```text
canonical production stamina/recovery policy
= Rule1 ON
+ Rule2 OFF
+ LOW_WHILE_EXHAUSTED
```

This still requires PR review and explicit merge authorization.

## CANDIDATE REJECTED / OPEN

If any adoption gate is OPEN:

```text
do not create or enable canonical production adoption
record evidence
keep existing defaults
write separate amendment if a correction is desired
```

## MEASUREMENT FAILURE

If evidence is incomplete, nondeterministic, or accounting does not reconcile:

```text
stop
fix instrumentation only
rerun before any adoption decision
```

---

# What remains after this slice

Even if this adoption succeeds, frontend work still waits.

Remaining engine/design debt must be explicitly closed or deferred before frontend implementation, including at least:

- Rule 2 redesign vs permanent deferral;
- setup-policy debt;
- initiator tactical commitment-selection policy;
- scoring / timeout meaning if required for the first playable ruleset;
- final player-facing state/input contract.

Those should be handled as separate controlled slices rather than folded into this adoption.

---

# HARD STOP

This commit authorizes **design review only**.

Do not:

- add re-exhaustion instrumentation;
- run the historical LOW+BOTH handoff baseline;
- run the Rule1-only + LOW production candidate;
- add a canonical production configuration;
- change any default;
- adopt Rule 1 for production;
- adopt LOW for production;
- redesign or delete Rule 2;
- change stalling/setup/stamina rules;
- start frontend work;

until the user explicitly authorizes implementation after reviewing this committed DoD.

The next valid action is:

```text
STOP
-> present committed production-adoption DoD
-> user review
-> explicit implementation authorization
```
