# Mount v0.4b — Recognition First Measurement

## Status

AUTHORITATIVE FIRST v0.4b MEASUREMENT.

The Recognition probabilities and response policy were frozen before this measurement in:

`docs/MOUNT_V0_4B_RECOGNITION_DEFINITION_OF_DONE.md`

Frozen DoD commit:

```text
aaf00ed85a44478558f70b6361c3ef3adcb20473
```

Base `main`:

```text
a13e677cffe2be36d67576ee8dc4325f197ed9ba
```

First full checker measurement was obtained on the implementation line before any Recognition tuning. GitHub Actions run #779 exposed the result while three older tests still expected Recognition to be absent / Gate B to remain OPEN. Those stale expectations were subsequently updated without changing the frozen d6 model, response-commitment policy, commitment costs, grades, exhaustion, matchup matrix, or Gate-B range.

## Frozen Recognition model measured

Each exchange independently reads:

```text
requested intent
effective capability
```

Each signal uses its own d6:

```text
1   -> one rank lower
2-5 -> exact
6   -> one rank higher
```

with endpoint clamps.

Requested ranks:

```text
LOW < MEDIUM < HIGH
```

Effective ranks:

```text
UNFUNDED < LOW < MEDIUM < HIGH
```

No probability was changed after the first result was observed.

## Standard v0.4b informed batch

Frozen configuration:

```text
matches=100
base seed=42
Top=PRESSURE
Bottom=ESCAPE
initiator requested commitment=MEDIUM
clock=300
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

Measured:

```text
Tap=6/100
Threat=58/100
Control=38/100
Finish=21/100
submission-stage attempts=1622
```

The unchanged v0.3a Gate-B criterion is:

```text
0% < informed Tap rate < 50%
```

Therefore:

```text
v0.3a Gate B PASS
6.0% is inside the frozen range
```

This is the first untuned v0.4b result.

## v0.4b gates

### Gate A — PASS

```text
Recognition disabled=False
Recognition enabled=True
invalid v0.4b without v0.4a rejected=True
v0.4a gates all PASS=True
```

### Gate B — PASS

Exhaustive Recognition mapping:

```text
cases=432
mismatches=0
```

The frozen d6 map is bounded to exact or one adjacent rank with endpoint clamps.

### Gate C — PASS

```text
true requested/effective can differ=True
recognized reads can differ=True
intent-roll independence=True
capability-roll independence=True
```

Requested intent and effective capability remain separate signals.

### Gate D — PASS

Twin hidden-truth states with the same perceived signals:

```text
same requested response commitment=True
same legal informed response=True
```

The informed policy consumes perception rather than hidden initiator truth.

### Gate E — PASS

```text
truth-authority cases=2
Recognition-read resolution mismatches=0
```

Once response choice and requested response commitment are fixed, changing Recognition reads does not change true grade, axis, costs, submission transition, or feint behavior.

### Gate F — PASS

```text
Recognition present=True
informed Tap=6/100
v0.3a Gate B=PASS
```

No Gate-B range or Recognition probability changed to obtain this result.

### Gate G — PASS

The standard Recognition batch replays identically from seed 42.

```text
replay_equal=True
```

The stamina-pacing observation is present and deterministic.

### Gate H — PASS

```text
frozen raw matrix entries=18
v0.4a Gates A-I PASS with v0.4b disabled
v0.3b Gates A-F PASS
```

No frozen matchup, cost, exhaustion, setup, submission, feint, hold-cost, or stalling rule changed.

## Stamina-pacing observation

This comparison uses the same 100 seeds.

### v0.4a public-MATCH informed control

```text
Tap=0/100
Finish=0/100

final stamina median:
  Top=0.0
  Bottom=0.0

median first Exhausted time:
  Top=55.0 s
  Bottom=45.0 s

matches ever Exhausted:
  Top=78
  Bottom=78
  both=78

total responder commitment stamina charged=7168
```

### v0.4b Recognition informed

```text
Tap=6/100
Finish=21/100

final stamina median:
  Top=0.0
  Bottom=0.0

median first Exhausted time:
  Top=50 s
  Bottom=50 s

matches ever Exhausted:
  Top=91
  Bottom=91
  both=90

total responder commitment stamina charged=7352
```

Requested defender commitments:

```text
LOW=4218
MEDIUM=650
HIGH=155
```

Recognition direction counts:

```text
intent:
  lower=825
  exact=3337
  higher=861

capability:
  lower=197
  exact=4014
  higher=812

perceived-signal rank disagreements=4308
```

## Pacing interpretation

Recognition closes Gate B, but it does **not** solve mutual stamina exhaustion.

The final median remains:

```text
0 / 0
```

and both fighters become Exhausted in more matches on this specific surface:

```text
public MATCH: 78/100
Recognition:  90/100
```

That is an observation, not a failed v0.4b gate and not a tuning target.

Do not alter Recognition probabilities merely to improve stamina outcomes.

The historical result says imperfect information is sufficient to break the submission lock for the **frozen trust-the-read defender policy** under the frozen Gate-B criterion.

Later review added two fixed hedge-policy contrasts without changing this historical measurement. Both restore 0 taps. See `MOUNT_V0_4B_DEFENDER_POLICY_HEDGE_OBSERVATION.md`.

Therefore the 6/100 result must not be generalized to every reasonable defender policy. Stamina-pacing / stamina-economy remains separate design debt for later work.

## First-CI expectation failures

The first measured run also exposed three stale regression expectations:

1. CLI expected v0.3a Gate B to remain OPEN.
2. v0.3a DoD test expected global Recognition capability to be absent.
3. v0.3b DoD test expected global Recognition capability to be absent.

The checker itself reported PASS and the measured v0.4b gates A-H were PASS.

Those tests were changed only to acknowledge the new v0.4b capability and preserve historical v0.3b scope. No gameplay mechanic was changed in response.

## Frozen digest

The expected digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Final exact-head verification must still confirm this digest before PR review.

## Later review qualification

The original 6/100 value remains authoritative for the frozen trust-read policy.

A later checker-owned review observation uses the same seeds and Recognition reads with:

```text
trusts reads
one level above
always HIGH
```

The hedge policies produce 0 taps. This does not amend Gate F; it narrows the interpretation of its PASS and establishes stamina-economy debt.

See:

`docs/MOUNT_V0_4B_DEFENDER_POLICY_HEDGE_OBSERVATION.md`
