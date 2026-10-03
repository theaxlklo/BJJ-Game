# Stamina Economy — Measurement-Only Definition of Done

## Status

**FROZEN FOR USER REVIEW — HARD STOP.**

This document defines the first stamina-economy slice.

It freezes **what must be measured**. It does not authorize measurement instrumentation, checker implementation, stamina tuning, or any gameplay/mechanic change.

Implementation must not begin until the user explicitly authorizes crossing the HARD STOP after reviewing this committed DoD.

## Base and branch

Base `main`:

```text
6dd88c6bc37a854503163473f5d2c5d70eccae5c
```

Branch:

```text
review/stamina-economy-measurement
```

The frozen Mount enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Purpose

v0.4b established two facts on the standard informed surface:

1. the frozen defender that trusts its Recognition reads produces 6/100 taps;
2. fixed hedge policies restore 0 taps while spending more defender stamina and still ending at median 0 / 0 stamina.

The next question is not which Recognition probability or defender policy to tune.

The first stamina-economy slice must measure **where the current economy loses meaningful opportunity cost**.

No rule is proposed in this DoD.

## Existing stamina facts — observation targets, not amendment authority

Current commitment costs remain:

```text
LOW    = 3
MEDIUM = 7
HIGH   = 12
```

Current funding rule:

```text
effective commitment
= highest requested-or-lower level that can be fully paid

0-2 stamina   -> cannot fund LOW -> UNFUNDED
3-6 stamina   -> can fund LOW
7-11 stamina  -> can fund MEDIUM
12+ stamina   -> can fund HIGH
```

Current Exhausted latch:

```text
enter Exhausted at <=25% stamina
leave Exhausted only after recovering to >=35%
```

For the frozen standard PRESSURE / ESCAPE surfaces in this DoD, behavior does not recover stamina, so an entered Exhausted state will not leave through behavior recovery. Instrumentation must nevertheless use the actual runtime `StaminaBand.EXHAUSTED` flag and actual stamina value rather than assuming the band from a hard-coded number.

## Frozen diagnostic surfaces

All measurement surfaces use the **same 100 match indices and base seed 42**.

Shared configuration:

```text
matches=100
base seed=42
Top behavior=PRESSURE
Bottom behavior=ESCAPE
initiator requested commitment=MEDIUM
initial clock=300 seconds
starting axis=+1.50
interval=5 seconds
Top starting stamina=100
Bottom starting stamina=100
Bottom responder=INFORMED
v0.2 setup=enabled
v0.3a submissions=enabled
v0.3b stalling=disabled
v0.4a commitment semantics=enabled
```

Measure exactly these four matched policy surfaces:

### Surface A — public MATCH control

```text
v0.4b Recognition=disabled
response commitment policy=MATCH
```

### Surface B — Recognition trusts reads

```text
v0.4b Recognition=enabled
response commitment policy=RECOGNITION
```

This remains the historical v0.4b Gate-F policy.

### Surface C — Recognition one level above

```text
v0.4b Recognition=enabled
response commitment policy=RECOGNITION_HEDGE_ONE
```

### Surface D — Recognition always HIGH

```text
v0.4b Recognition=enabled
response commitment policy=RECOGNITION_ALWAYS_HIGH
```

The three Recognition surfaces must consume the existing deterministic Recognition streams unchanged.

RANDOM response commitment, FIXED_MEDIUM response commitment, alternative seeds, alternative behaviors, and alternative starting stamina are outside this first measurement slice.

## Measurement clock and state semantics

Stamina changes caused by exchanges are instantaneous in simulated time.

Time advances only through the existing time-advance path.

For duration accounting:

```text
each simulated interval is attributed to the stamina state
that exists immediately before that time-advancing interval
```

An instantaneous commitment / hold spend may change the state at the same timestamp; that changed state applies to the next interval.

This convention must make the three state durations sum exactly to elapsed simulated match time.

Do not infer duration from first-entry timestamps alone.

## Three mutually exclusive stamina states

Every simulated-duration interval and every initiated exchange must be classified into exactly one of these states.

### State 1 — NOT_MUTUALLY_EXHAUSTED

```text
Top band != Exhausted
OR
Bottom band != Exhausted
```

### State 2 — MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO

```text
Top band == Exhausted
AND
Bottom band == Exhausted
AND
NOT (Top stamina == 0 AND Bottom stamina == 0)
```

This is the critical middle window.

It deliberately includes cases where:

- both still have positive stamina;
- one is already at zero while the other still has stamina;
- either side can still fully fund LOW, MEDIUM, or HIGH.

Do not collapse this window into “1-25” by assumption. Record the actual stamina values and runtime bands. On the frozen no-recovery surfaces, its positive-stamina values will normally lie within the Exhausted range.

### State 3 — MUTUALLY_ZERO

```text
Top stamina == 0
AND
Bottom stamina == 0
```

Both competitors will also be Exhausted here.

## Gate A — state-duration accounting

For every surface and match, measure:

- first Top Exhausted timestamp;
- first Bottom Exhausted timestamp;
- first entry into State 2;
- first entry into State 3;
- number of entries into each state;
- total simulated seconds in State 1;
- total simulated seconds in State 2;
- total simulated seconds in State 3;
- each state's share of elapsed match time.

PASS requires for every measured match:

```text
State 1 seconds
+ State 2 seconds
+ State 3 seconds
= elapsed simulated match time
```

No target is imposed on any duration or share.

Report at minimum, per surface:

- matches entering State 2;
- matches entering State 3;
- median first-entry time for State 2;
- median first-entry time for State 3;
- median State-2 seconds and share;
- median State-3 seconds and share;
- p25 / p75 for State-2 and State-3 share.

## Gate B — middle-window affordability

At **every initiated exchange in State 2**, record the pre-cost actual stamina for the initiator and responder.

For each side derive the highest commitment level it could fully fund at that moment:

```text
0-2  -> UNFUNDED ceiling
3-6  -> LOW ceiling
7-11 -> MEDIUM ceiling
12+  -> HIGH ceiling
```

This is an affordability ceiling, not the commitment the side requested.

For every Surface B/C/D State-2 exchange, report:

### Per-side affordability

For initiator and responder separately:

- can fund LOW count / share;
- can fund MEDIUM count / share;
- can fund HIGH count / share;
- affordability ceiling counts: UNFUNDED / LOW / MEDIUM / HIGH.

### Affordability cross-table

Produce a 4 x 4 exchange-count table:

```text
initiator affordability ceiling
x
responder affordability ceiling
```

using:

```text
UNFUNDED
LOW
MEDIUM
HIGH
```

### What each side actually asks for

For initiator and responder separately, report:

- requested LOW / MEDIUM / HIGH;
- requested commitment fully fundable at exchange start;
- requested commitment downgraded to a lower funded level;
- requested commitment becomes UNFUNDED;
- requested -> effective transition counts.

For the initiator's fixed requested MEDIUM policy, these metrics are still required; do not omit them because the requested level is constant.

### Defender hedge headroom

In State 2, report how often the responder has more affordability than the initiator.

At minimum:

```text
responder affordability ceiling > initiator affordability ceiling
responder affordability ceiling == initiator affordability ceiling
responder affordability ceiling < initiator affordability ceiling
```

Also report the count where the responder can fully fund **one selectable commitment level above the initiator's true effective commitment**, capped at HIGH:

```text
initiator true effective UNFUNDED -> responder can fund LOW
initiator true effective LOW      -> responder can fund MEDIUM
initiator true effective MEDIUM   -> responder can fund HIGH
initiator true effective HIGH     -> no higher selectable level exists
```

HIGH-attacker exchanges must be reported separately rather than counted as a failed hedge opportunity.

Finally, for each defender policy, report whether the defender's **actual requested response commitment** is fully fundable at exchange start.

This is the primary measurement requested by review: how often the attacker and defender can afford what they ask for in the mutually-Exhausted-but-not-both-zero window.

PASS requires complete, deterministic accounting. There is no required direction.

## Gate C — decisive exchanges by stamina state

For each of the three states, and for every surface, count at minimum:

- total initiated exchanges;
- exchanges with responder under-commitment modifier +1;
- submission-stage attempts;
- successful submission-stage advances;
- transitions into Threat;
- transitions into Control;
- transitions into Finish;
- Taps;
- under-commitment-caused Taps using the existing narrow v0.4b attribution rule;
- escape-ending exchanges;
- timeouts ending from matches that had entered the state.

For every State-2 under-commitment event and every State-2 decisive submission/escape exchange, preserve enough diagnostic context to aggregate:

- initiator stamina;
- responder stamina;
- initiator affordability ceiling;
- responder affordability ceiling;
- initiator requested commitment;
- initiator true effective commitment;
- responder requested commitment;
- responder true effective commitment;
- response-undercommitment modifier;
- submission stage before / after when applicable;
- final grade;
- terminal outcome when applicable.

The first slice does not assert that decisive events *should* occur in any particular state.

## Gate D — stamina-source accounting

For each surface, match, and side, separately account actual charged/recovered stamina by source:

```text
initiator commitment spend
responder commitment spend
provisional submission-hold spend
behavior spend
behavior recovery
other existing source, if discovered
```

Do not use nominal requested costs where actual charged cost is available.

For behavior flow, report gross spend and gross recovery separately rather than only net change.

PASS requires per-match/per-side reconciliation:

```text
starting stamina
+ behavior recovery
- behavior spend
- initiator commitment charged
- responder commitment charged
- provisional hold charged
- any explicitly identified other charged source
= final stamina
```

If instrumentation discovers another existing stamina mutation source, it must be named and reported. It may not be silently folded into “other” for final closure.

### Provisional hold double-charge

Specifically measure when the defender pays both within the same submission-hold exchange:

```text
response commitment charged
+
provisional hold charged
```

Report:

- count of double-charge exchanges;
- total response-commitment stamina charged on them;
- total provisional-hold stamina charged on them;
- total combined charged stamina;
- the three-state split of those exchanges;
- responder pre-charge stamina distribution;
- whether the combined charges move the responder into Exhausted or zero.

The provisional LOW=3 hold rule itself remains untouched.

## Gate E — funded / UNFUNDED exchange states

At each initiated exchange, classify the true effective commitment pair as:

```text
both funded
initiator funded / responder UNFUNDED
initiator UNFUNDED / responder funded
both UNFUNDED
```

Report each category by the three stamina states and by surface.

For `both UNFUNDED`, explicitly report:

- exchange count;
- response-undercommitment modifier distribution;
- submission-stage attempts;
- successful submission advances;
- Taps;
- escapes.

The existing rule remains observationally frozen:

```text
UNFUNDED rank == UNFUNDED rank
-> equal commitment rank
-> no responder under-commitment modifier
```

Whether that rule should change is outside this DoD.

## Gate F — zero-stamina attacks

At every initiated exchange where the initiator starts with exactly zero stamina, report:

- total zero-stamina attacks;
- action IDs;
- requested commitment;
- effective commitment;
- effective commitment cost;
- response requested/effective commitment;
- final-grade distribution;
- successful positional attacks;
- submission-stage attempts;
- successful submission advances;
- Taps;
- escapes caused by the exchange;
- responder stamina and affordability ceiling.

The current behavior is not changed:

```text
initiator stamina=0
-> cannot fund LOW
-> effective commitment=UNFUNDED
-> effective commitment cost=0
-> attack still resolves
```

PASS requires the checker to expose the observed counts and to reproduce them exactly from the frozen seeds.

There is no target for how many such attacks should succeed.

## Gate G — policy-comparison continuity

The four frozen surfaces must remain mechanically identical to their pre-measurement behavior.

Instrumentation must not change:

- match outcomes;
- existing commitment selection;
- Recognition reads;
- legal-response selection;
- resolution grades;
- stamina charges;
- submission transitions;
- escape transitions;
- clocks.

At minimum, preserve the reviewed v0.4b policy observations:

```text
trusts reads:
  Tap=6
  Escapes=11
  responder commitment spend=7352
  median final stamina=0 / 0

one level above:
  Tap=0
  Escapes=22
  responder commitment spend=8843
  median final stamina=0 / 0

always HIGH:
  Tap=0
  Escapes=22
  responder commitment spend=9480
  median final stamina=0 / 0
```

The historical 6/100 Gate-F result remains scoped to the trust-read policy.

The hedge surfaces remain observations and do not redefine Gate F.

PASS requires identical deterministic reruns from base seed 42.

## Gate H — checker output and raw evidence

The primary semantic checker must print a clearly named stamina-economy measurement section that includes all Gate A-G summaries.

The measurement implementation must also expose machine-checkable structured values sufficient for regression tests; prose parsing must not be the only verification route.

The checker must distinguish:

```text
MEASUREMENT GATE PASS
```

from any future gameplay/design acceptance.

A measurement gate passes when the required evidence exists, reconciles, and replays deterministically.

It does **not** mean the stamina economy is healthy.

## Frozen prohibitions

During this measurement-only slice, do not change:

- Recognition d6 probabilities;
- Recognition rank mapping;
- trust-read / hedge-one / always-HIGH defender policies;
- commitment costs 3 / 7 / 12;
- commitment magnitude transforms;
- responder under-commitment rule;
- requested-LOW feint semantics;
- exhaustion enter threshold;
- exhaustion recovery threshold / hysteresis;
- behavior stamina rates;
- setup mechanics;
- submission grades or transitions;
- provisional LOW=3 hold cost;
- stalling mechanics;
- UNFUNDED rank/equality semantics;
- zero-stamina attack legality;
- Gate-B numeric threshold;
- frozen Mount matchup matrix or digest.

No new recovery rule, floor, reserve, regen, overdraft, exhaustion penalty, or stamina cap may be introduced in this slice.

## Out of scope

This DoD does not decide:

- whether UNFUNDED vs UNFUNDED should remain equal;
- whether zero-stamina attacks should remain legal;
- whether an Exhausted fighter should be allowed to request HIGH;
- whether commitment costs should change;
- whether behavior upkeep should change;
- whether the provisional hold cost should change;
- whether stamina should regenerate;
- whether stamina should have a nonzero reserve/floor;
- whether Recognition should be retuned;
- whether the competent defender should hedge in production gameplay.

Those are candidate questions for a later **rule-changing** DoD after this measurement is reviewed.

## Required outputs after implementation is authorized

The measurement slice must eventually produce:

1. checker-owned deterministic measurement output;
2. regression tests pinning accounting and replay invariants;
3. a first-measurement document recording the exact observed values;
4. an interpretation section that separates facts from candidate rule changes.

No rule-changing implementation belongs in that commit sequence.

## Change control — literal HARD STOP

This sequence is binding:

```text
create stamina-economy branch
-> draft measurement-only DoD
-> commit measurement-only DoD
-> HARD STOP
-> present frozen DoD commit for user review
-> wait for explicit instruction to implement
-> only then add measurement instrumentation / checker work
-> record first measurement before proposing a rule
-> review evidence
-> if a mechanic change is warranted:
     draft separate rule-changing DoD
     -> commit rule-changing DoD
     -> HARD STOP
     -> present it for user review
     -> wait for explicit instruction to implement
     -> only then change mechanics
-> regression / measurement
-> PR review
-> explicit merge authorization
-> squash merge
```

“Start stamina work,” “continue,” roadmap approval, approval of the future scope note, or approval of this branch existing does not authorize crossing this HARD STOP.

Only an explicit post-DoD instruction to implement the measurement slice does.
