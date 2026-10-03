# Future Stamina-Economy Phase — Measurement Scope

## Status

FUTURE DESIGN NOTE — NOT A DEFINITION OF DONE.

This file records what the next phase must measure before any stamina rule is proposed.

It does **not** authorize stamina-economy implementation.

## Problem statement

The current standard v0.4b surfaces routinely saturate stamina:

```text
median final stamina Top / Bottom = 0 / 0
```

A defender can spend substantially more by hedging against Recognition while still ending at the same final median stamina and improving both submission defense and escapes.

This creates two related concerns:

1. defensive over-commitment may lose its intended opportunity cost;
2. once both fighters are deeply depleted, commitment and Recognition may stop producing the tradeoffs they were intended to create.

The next phase must describe this economy quantitatively before proposing a fix.

## First slice must be measurement-only

The first stamina-economy Definition of Done must freeze **what to measure**, not a mechanic to change.

No stamina rule should be proposed in that first DoD.

### 1. Mutual-exhaustion duration

Measure across the frozen standard conditions:

- first time Top enters Exhausted;
- first time Bottom enters Exhausted;
- first time both are simultaneously Exhausted;
- total simulated seconds spent with both simultaneously Exhausted;
- share of elapsed match time spent mutually Exhausted;
- first time each reaches zero stamina;
- first time both are simultaneously at zero;
- total simulated seconds spent at mutual zero, if any.

Report distributions or at minimum count / median / relevant percentile summaries across the frozen seed set.

The distinction between **Exhausted band** and **zero stamina** must remain explicit.

### 2. Where stamina goes

Account stamina spend by source and side:

```text
initiator commitment
responder commitment
provisional submission-hold cost
behavior upkeep / recovery effects
other existing stamina sources, if any
```

The accounting must reconcile against stamina pool changes rather than relying only on nominal requested costs.

The provisional hold cost is especially important because a Contested submission hold can charge the defender:

```text
response commitment cost
+
provisional LOW=3 hold cost
```

in the same exchange.

Measure how often that double charge occurs and how much total stamina it consumes.

### 3. UNFUNDED equality

Measure the current rule explicitly:

```text
effective initiator commitment = UNFUNDED
effective responder commitment = UNFUNDED
-> ranks equal
-> response-undercommitment modifier = 0
```

Report how many exchanges occur in:

- both UNFUNDED;
- initiator UNFUNDED / responder funded;
- initiator funded / responder UNFUNDED;
- both funded;

and how those states correlate with submission-stage progress, Tap, escape, and timeout.

Whether two UNFUNDED competitors **should** compare as equal is a later design question, not a first-slice decision.

### 4. Free attacks at zero

Measure the existing behavior:

```text
initiator stamina=0
-> requested commitment cannot fund LOW
-> effective commitment=UNFUNDED
-> effective commitment cost=0
-> attack still resolves
```

Report:

- zero-stamina initiated attacks;
- zero-stamina submission-stage attacks;
- successful zero-stamina attacks;
- zero-stamina submission advances;
- zero-stamina taps;
- responder state on those exchanges.

This behavior predates v0.4b, but the phase must measure how it interacts with fatigue-based submission finishing.

### 5. Defender-policy comparison remains observational

Carry forward the identical-seed policies from the v0.4b review:

```text
trusts reads
one level above
always HIGH
```

Use them as stamina-economy probes.

Do not redefine v0.4b Gate F around them.

## Frozen prohibitions for the measurement slice

Until the measurement-only slice is reviewed, do **not** change:

- Recognition d6 misread probabilities;
- Recognition rank mapping;
- defender trust / hedge policies;
- LOW / MEDIUM / HIGH costs 3 / 7 / 12;
- Gate-B numeric range;
- commitment grade transforms;
- requested-LOW feint semantics;
- exhaustion thresholds or hysteresis;
- submission grades;
- setup mechanics;
- stalling mechanics;
- provisional LOW=3 hold cost;
- UNFUNDED comparison semantics;
- zero-stamina attack legality.

The purpose is diagnosis, not tuning.

## Required phase ordering — HARD STOP

The following sequence is literal and binding:

```text
create new stamina-economy branch
-> draft measurement-only Definition of Done
-> commit the DoD
-> HARD STOP
-> present the frozen DoD commit for user review
-> wait for explicit authorization containing a clear instruction to implement
-> only then add measurement instrumentation / checker work
-> record measurement
-> review evidence
-> draft a separate rule-changing DoD if a mechanic change is warranted
-> commit that rule-changing DoD
-> HARD STOP again
-> explicit implementation authorization
-> mechanic implementation
-> measurement / regression
-> PR review
-> explicit merge authorization
-> squash merge
```

“Start the phase,” “work on stamina,” roadmap approval, or approval of this future note does **not** authorize crossing either HARD STOP.

## Relationship to PR #6

PR #6 should merge, if approved, with:

- the original v0.4b 6/100 trust-read Gate-F result preserved;
- the three-policy hedge comparison marked observational;
- stamina-economy debt recorded.

The stamina-economy phase begins only after a separate branch and measurement-only DoD are created.
