# Mount v0.4b — Recognition Definition of Done

## Status

FROZEN FOR IMPLEMENTATION.

This Definition of Done is committed before v0.4b mechanics.

The user explicitly authorized implementation of the v0.4b slice, so this checkpoint does not require a second stop before coding. It still freezes the rules before any outcome measurement.

## Starting point

Base `main`:

```text
a13e677cffe2be36d67576ee8dc4325f197ed9ba
```

Branch:

```text
review/v04b-recognition
```

v0.4a is authoritative and remains unchanged when v0.4b is disabled.

Frozen Mount enumerate digest:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Purpose

v0.4a made commitment tactically meaningful but public.

The informed defender therefore receives exact commitment information and the frozen v0.3a Gate-B batch remains:

```text
Tap=0/100
Gate B OPEN
```

v0.4b adds imperfect commitment Recognition without changing the frozen Mount matchup matrix, commitment costs, exhaustion rules, feint semantics, submission grades, setup rules, or stalling rules.

Recognition is an information layer, not a grade modifier.

## Requested intent vs effective capability

v0.4a deliberately separates:

```text
requested commitment
-> intent
-> requested LOW is the feint-intent signal

effective commitment
-> funded capability
-> grade magnitude / cost / mismatch credit
```

v0.4b uses **Model C** from the pre-v0.4b design note:

```text
the defender receives separate noisy reads of:
1. requested intent
2. effective capability
```

Recognition must never collapse these two fields back into one value.

## Timing

The frozen exchange order becomes:

```text
initiator selects requested commitment
-> initiator effective commitment is derived from pre-cost stamina
-> defender Recognition reads requested intent and effective capability
-> defender chooses requested response commitment from those reads
-> defender chooses legal response using perceived capability
-> true exchange resolves from true initiator requested/effective commitment
   and the defender's actually affordable response commitment
-> costs are charged
```

Recognition happens before response commitment selection and before response choice.

It does not happen after resolution.

## Recognition noise

Recognition is intentionally simple and symmetric in v0.4b.

Each signal receives its own independent d6 roll.

For each signal:

```text
roll 1   -> read one rank lower
roll 2-5 -> exact read
roll 6   -> read one rank higher
```

Ranks clamp at the ends.

Requested-intent ranks:

```text
LOW < MEDIUM < HIGH
```

Effective-capability ranks:

```text
UNFUNDED < LOW < MEDIUM < HIGH
```

Consequences:

- no read can jump more than one rank;
- requested LOW cannot read below LOW;
- requested HIGH cannot read above HIGH;
- effective UNFUNDED cannot read below UNFUNDED;
- effective HIGH cannot read above HIGH;
- intent and capability rolls are independent and may disagree.

This 1/6 lower, 4/6 exact, 1/6 higher model is frozen before measurement. Do not tune it to hit a Tap rate.

## Deterministic batch RNG

The existing responder-choice and RANDOM response-commitment streams remain untouched.

For match index `i` and base seed `S`:

```text
intent-recognition RNG seed     = S + i + 2_000_003
capability-recognition RNG seed = S + i + 3_000_003
```

Each recognition exchange consumes exactly one `randint(1, 6)` from each recognition stream.

Recognition must be replayable from the batch seed.

## Defender commitment policy

v0.4b adds a Recognition response-commitment policy.

It is not the v0.4a public `MATCH` policy.

Given the two perceived signals:

```text
if perceived requested intent == LOW:
    request LOW response commitment

else:
    perceived effective UNFUNDED -> request LOW
    perceived effective LOW      -> request LOW
    perceived effective MEDIUM   -> request MEDIUM
    perceived effective HIGH     -> request HIGH
```

Why:

- perceived LOW intent is treated as a possible feint and the defender conserves stamina;
- otherwise the defender tries to match perceived force;
- UNFUNDED is not selectable, so LOW is the minimum requested response commitment.

The defender's own affordability still determines the **actual effective** response commitment.

Recognition can influence what the defender requests, but it can never grant unaffordable tactical credit.

## Defender response-choice policy

The informed defender continues to choose the legal response with the lowest perceived final grade.

For v0.4b, that preview must use:

```text
perceived initiator effective capability
+
defender's actually affordable effective response commitment
```

It must not use the true initiator effective commitment when choosing the response.

Tie-breaking remains the existing stable legal-response order.

The requested-intent read does not directly modify grade. Its current gameplay use is the defender response-commitment policy above.

## True resolution remains authoritative

Recognition is belief, not truth.

After the defender chooses a response and requested response commitment:

- feint intent still uses the initiator's **true requested** commitment;
- initiator magnitude still uses the initiator's **true effective** commitment;
- responder mismatch still uses the responder's **true effective** commitment;
- stamina costs use true requested/effective affordability;
- exhaustion order remains unchanged.

Two exchanges with the same true state, chosen response, and chosen response commitment must resolve identically even if their recognition reads differ.

## Runtime capability

v0.4b adds an explicit runtime Recognition capability.

It must not be detected by loose attribute-name matching.

Expected capability surface:

```text
v0.4b disabled -> recognition_enabled=False
v0.4b enabled  -> recognition_enabled=True
```

Enabling v0.4b without v0.4a commitment semantics is invalid.

## History / observability

Each v0.4b recognized exchange must expose enough data to distinguish:

- true requested intent;
- perceived requested intent;
- true effective capability;
- perceived effective capability;
- intent d6 roll;
- capability d6 roll;
- chosen requested response commitment.

Exact internal storage representation is not frozen.

Checker/batch diagnostics must count at minimum:

- intent reads;
- intent exact / lower / higher;
- capability reads;
- capability exact / lower / higher;
- exchanges where the two perceived signals imply different commitment ranks;
- requested response-commitment counts.

## Standard v0.4b informed batch

Freeze this diagnostic before measurement:

```text
matches=100
base seed=42
Top behavior=PRESSURE
Bottom behavior=ESCAPE
initiator requested commitment=MEDIUM
initial clock=300
starting axis=+1.50
interval=5 seconds
Top stamina=100
Bottom stamina=100
Bottom responder=INFORMED
response commitment policy=RECOGNITION
v0.2 setup=enabled
v0.3a submissions=enabled
v0.4a commitment semantics=enabled
v0.4b Recognition=enabled
```

The exact Tap result is unknown at freeze time.

Do not modify recognition probabilities, costs, grades, response weights, exhaustion, feint rules, or matchup entries merely to move the result.

## Stamina-pacing observation

v0.4a standard batches commonly finish with median stamina 0 / 0.

v0.4b must report whether imperfect commitment information changes that pacing.

Compare the v0.4a informed public-MATCH batch against the v0.4b informed Recognition batch using the same 100 seeds.

Report at minimum:

```text
Tap / Finish
Top final stamina median
Bottom final stamina median
median simulated time of first Top Exhausted entry
median simulated time of first Bottom Exhausted entry
matches where Top ever becomes Exhausted
matches where Bottom ever becomes Exhausted
matches where both ever become Exhausted
total responder commitment stamina charged
requested response commitment LOW / MEDIUM / HIGH counts
```

These are observations, not targets.

No v0.4b gate requires stamina to increase or exhaustion to disappear.

## v0.4b gates

### Gate A — feature-off compatibility

PASS requires:

- v0.4b disabled preserves v0.4a behavior exactly;
- v0.4a Gates A-I retain their frozen criteria and measurements when v0.4b is off;
- enabling v0.4b without v0.4a is rejected.

### Gate B — recognition mapping is frozen and bounded

PASS requires exhaustive recognition-policy checks proving:

- rolls 2-5 are exact;
- roll 1 moves exactly one rank lower or clamps;
- roll 6 moves exactly one rank higher or clamps;
- no two-rank jump exists;
- intent and capability use their separate rank sets.

### Gate C — requested and effective reads are genuinely separate

PASS requires deterministic probes demonstrating:

- requested and effective truth can differ;
- their recognized reads can differ;
- changing the intent roll alone cannot change the capability read;
- changing the capability roll alone cannot change the intent read.

### Gate D — informed policy consumes perception, not hidden truth

PASS requires twin probes with different true commitment states but the same frozen perceived signals to produce the same:

- requested response commitment;
- informed legal response choice,

when all other defender-visible state is the same.

The policy may not inspect true initiator commitment after the Recognition read is supplied.

### Gate E — true resolution remains authoritative

PASS requires identical true exchanges with the same chosen response/response commitment but different supplied Recognition reads to produce identical:

- final grade;
- axis result;
- submission transition;
- initiator cost;
- responder cost;
- feint-cap behavior.

### Gate F — competent-defender Gate B uses Recognition

The existing v0.3a Gate-B criterion is unchanged:

```text
0% < informed Tap rate < 50%
```

When Recognition is a live runtime capability, the Gate-B informed batch must use the frozen v0.4b Recognition policy rather than v0.4a public MATCH.

v0.4b Gate F PASS requires the unchanged v0.3a Gate B to PASS.

If it does not, record the failed measurement before proposing any amendment. Do not move the range or retune Recognition silently.

### Gate G — stamina-pacing measurement exists and is replayable

PASS requires the frozen public-MATCH vs Recognition comparison to report all metrics listed in **Stamina-pacing observation** and reproduce exactly on rerun with seed 42.

No directional stamina threshold is required.

### Gate H — existing scope remains frozen

PASS requires:

- frozen enumerate digest unchanged;
- v0.4a Gates A-I unchanged with v0.4b disabled;
- v0.3b stalling mechanics and gates unchanged;
- no matchup matrix change;
- no commitment-cost change;
- no exhaustion-threshold/order change;
- no setup-rule change;
- no submission-grade change;
- no feint-rule change;
- no hold-cost change;
- no stalling cadence/consequence change.

## Out of scope

v0.4b does not add:

- initiator LOW/MEDIUM/HIGH tactical selection AI;
- visual tells or animation;
- belt/rank-based Recognition skill;
- style/personality-based Recognition;
- memory of earlier opponent commitments;
- deliberate bluff frequency policy;
- action hiding;
- response hiding;
- reaction-time windows;
- new techniques;
- scoring;
- timeout judging.

Those may build on the information layer later.

## Change control

Sequence:

```text
freeze this DoD
-> implementation
-> tests
-> checker measurement
-> record first result
-> if a frozen gate fails, preserve the failed result before any amendment
-> PR review
-> explicit merge authorization
-> squash merge
```

Do not merge without explicit authorization.

Do not claim "everything passes" if any existing or v0.4b gate is OPEN or DEFERRED.
