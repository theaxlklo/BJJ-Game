# Mount v0.4b — Defender Policy Hedge Observation

## Status

POST-IMPLEMENTATION OBSERVATIONAL CORRECTION.

This document does **not** amend the frozen v0.4b Recognition model, its d6 probabilities, the Gate-B numeric range, or the historical 6/100 first measurement.

It clarifies the scope of v0.4b Gate F and records a reproducible policy-robustness observation discovered during review.

## Historical result remains authoritative for the frozen policy

The frozen v0.4b DoD defines a defender that takes its Recognition reads at face value.

That policy remains:

```text
perceived requested LOW
-> request LOW

otherwise:
  perceived effective UNFUNDED -> LOW
  perceived effective LOW      -> LOW
  perceived effective MEDIUM   -> MEDIUM
  perceived effective HIGH     -> HIGH
```

The historical first measurement remains:

```text
trusts reads:
Tap=6/100
v0.3a Gate B PASS under the unchanged 0% < Tap < 50% criterion
```

Nothing in this observation rewrites that result.

The precise statement is now:

> v0.4b Gate F PASS applies to the **frozen trust-the-read defender policy**.

It is not evidence that every reasonable defender policy under imperfect Recognition satisfies the Gate-B range.

## Reproducible three-policy comparison

All three policies use the identical standard Gate-B configuration and seeds:

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
v0.2 setup=enabled
v0.3a submissions=enabled
v0.4a commitment semantics=enabled
v0.4b Recognition=enabled
```

They use the same Recognition reads and the same informed legal-response choice. Only the defender's requested response-commitment policy differs.

### Policy 1 — trusts reads

Frozen Gate-F policy.

```text
Tap=6
Escapes=11

response requests:
  LOW=4218
  MEDIUM=650
  HIGH=155

defender response-commitment stamina charged=7352
median final stamina Top / Bottom=0 / 0
```

### Policy 2 — one level above

Start with the frozen trust-read requested commitment and raise it by one selectable level:

```text
LOW    -> MEDIUM
MEDIUM -> HIGH
HIGH   -> HIGH
```

Measured:

```text
Tap=0
Escapes=22

response requests:
  MEDIUM=4054
  HIGH=582

defender response-commitment stamina charged=8843
median final stamina Top / Bottom=0 / 0
```

### Policy 3 — always HIGH

The defender still receives the same Recognition reads and uses perceived capability to choose the legal response, but always requests HIGH response commitment.

Measured:

```text
Tap=0
Escapes=22

response requests:
  HIGH=4612

defender response-commitment stamina charged=9480
median final stamina Top / Bottom=0 / 0
```

## Under-commitment timing

The checker now splits under-commitment by the **pre-cost stamina bands at exchange initiation**.

```text
before mutual Exhausted
-> at least one competitor is not yet in the Exhausted band

after mutual Exhausted
-> both competitors are already in the Exhausted band
```

This is deliberately **not** the same as both competitors being at zero stamina. The Exhausted band begins at <=25 and persists until recovery to >=35.

A tap is counted as **under-commitment-caused** only when:

1. the exchange starts from submission Finish;
2. the exchange produces Tap;
3. the responder-undercommitment modifier is +1; and
4. removing that +1 would drop the finishing grade below Success.

That is narrower than merely counting taps that happen on an under-committed exchange.

### Trusts reads

```text
under-commitment events:
  before mutual Exhausted=311
  after mutual Exhausted=108

under-commitment-caused taps:
  before mutual Exhausted=1
  after mutual Exhausted=4
```

Five of the six taps are therefore directly attributable to responder under-commitment under this definition.

The timing does **not** confirm the hypothesis that decisive hedge value occurs almost entirely before mutual exhaustion. Most under-commitment events occur before mutual exhaustion, but four of the five under-commitment-caused taps occur after both competitors are already in the Exhausted band.

### One level above

```text
under-commitment events:
  before mutual Exhausted=1
  after mutual Exhausted=45

under-commitment-caused taps:
  before mutual Exhausted=0
  after mutual Exhausted=0
```

### Always HIGH

```text
under-commitment events:
  before mutual Exhausted=0
  after mutual Exhausted=78

under-commitment-caused taps:
  before mutual Exhausted=0
  after mutual Exhausted=0
```

## Interpretation

The hedge policies restore the 0-tap competent-defender lock while also doubling escapes:

```text
trusts reads:    6 taps / 11 escapes
one level above: 0 taps / 22 escapes
always HIGH:     0 taps / 22 escapes
```

They spend more response stamina but still finish with the same 0 / 0 median stamina.

This means the correct v0.4b conclusion is narrower than the original prose:

```text
Recognition + frozen trust-read defender
-> Gate B PASS

Recognition + fixed hedge-one defender
-> 0 taps

Recognition + always-HIGH defender
-> 0 taps
```

Do **not** tune Recognition misread probabilities or defender policy to force policy-robust Gate-B success.

## Named debt

### STAMINA-ECONOMY DEBT

Current stamina saturation weakens the opportunity cost of defensive over-commitment.

Relevant observations:

- all three policies finish at median 0 / 0 stamina;
- hedge-one spends 1491 more response-commitment stamina than trust-read;
- always-HIGH spends 2128 more than trust-read;
- neither higher-spend policy pays a final-stamina penalty on the standard surface;
- both remove all taps and increase escapes from 11 to 22;
- decisive under-commitment remains possible after both competitors enter the Exhausted band.

The exact mechanism at zero also remains a design question:

```text
both effective commitments UNFUNDED
-> ranks compare equal
-> no response under-commitment modifier
```

In addition, a zero-stamina initiator may still make an UNFUNDED attack at zero commitment cost.

Those rules predate v0.4b but now interact strongly with fatigue-driven submission conversion and defender hedging.

## Checker ownership

`python -m bjj_game --check` now prints:

```text
V0.4b DEFENDER-POLICY HEDGE OBSERVATION
```

with the three named policies, identical seed set, outcome/spend/stamina results, and pre/post-mutual-Exhausted under-commitment/tap counts.

These policy comparisons are observational.

They do not change v0.4b Gate F, which remains scoped to the frozen trust-read defender.

## Next phase

The next phase should measure stamina economy before proposing any stamina rule.

See:

`docs/STAMINA_ECONOMY_MEASUREMENT_PHASE_SCOPE.md`
