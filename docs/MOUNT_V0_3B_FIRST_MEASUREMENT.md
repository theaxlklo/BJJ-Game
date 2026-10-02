# Mount v0.3b — First Measurement

## Evidence head

Mechanics/checker head:

```text
3fc9f295f923d73945209f6be1a315fa956ca633
```

GitHub Actions push run:

```text
#522
```

Both Python 3.11 and Python 3.13 passed:

```text
236 tests PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The frozen 18-entry Mount-v0 matchup table remains unchanged.

## Cadence implemented

Each competitor owns an independent advancement clock measured in simulated seconds.

Frozen threshold:

```text
20 seconds
```

A legal progress-capable attempt resets the initiator's clock.

A legal response to that progress-capable attempt resets the defender's clock.

RESET does not reset the clock.

A RESET becomes an offense only when:

```text
progress-capable route exists
and
advancement clock >= 20s
```

First offense:

```text
persistent Warning
```

Later offense:

```text
one visible Mount-band step toward the non-stalling player
```

Boundary later offense:

```text
FREE INITIATIVE WINDOW
```

The free window costs zero simulated seconds.

## Progress semantics

Progress is classified before the responder chooses and from the real current mechanics surface.

Recognized channels are:

- terminal escape;
- submission entry/advancement;
- setup advancement;
- favorable realized positional movement.

A route is progress-capable if at least one legal response path can create one of those channels.

Once such an action is attempted, the attempt is engagement even if the actual response produces Contested or Failure.

This keeps success separate from engagement.

## v0.2 Gate 2 closes

The historical observation still exists:

```text
RESET LOCK PROBE:
Top PRESSURE+RESET vs Bottom ESCAPE+RESET
-> TIMEOUT — Mount retained
-> axis +4.00
-> Locked
```

That old two-sided probe is retained as historical evidence, but it cannot assign individual stalling ownership.

The v0.3b one-sided Top ownership probe now reports:

```text
Warning = 1
penalty = 1
final axis = +2.80
final band = Strong
locked timeout = False
```

Therefore:

```text
v0.2 Gate 2: OPEN -> PASS
```

The transition is caused by executable stalling evidence, not a hand-edited status.

## v0.3b gates

### Gate A — PASS

```text
warnings=1
penalties=1
final axis=+2.80
final band=Strong
locked_timeout=False
```

A Top player with an active submission route cannot repeatedly RESET and retain unchanged Locked control.

### Gate B — PASS

Fresh informed submission stalemate:

```text
attempts=3
Top penalties=0
Bottom penalties=0
stage=Threat
Top advancement clock=0
Bottom advancement clock=0
```

Repeated legal Americana attempts into informed Turn-In Contested holds count as engagement for both competitors.

Successful stage advancement is not required.

### Gate C — PASS

```text
Top warnings/penalties=1/1
Bottom warnings/penalties=1/1
```

The exact same per-player tracker, 20-second threshold, persistent warning, and penalty ladder can penalize either side.

### Gate D — PASS

Loose-boundary probe:

```text
Warning=1
free initiative windows=1
axis +0.50 -> +0.50
band Loose
match clock 300 -> 300
```

The penalty does not cross Neutral.

The non-stalling player receives the v9 Section-33 free initiative window instead, with zero simulated-time cost.

### Gate E — PASS

```text
response_commitment_present=False
recognition_present=False
v0.3a Gate B=DEFERRED
```

v0.3b does not silently add either capability that would expire the v0.3a Gate-B deferral.

## Interval/cadence invariants

Regression coverage pins:

```text
STALLING_THRESHOLD_SECONDS = 20
```

and checks interval values:

```text
2
5
7
```

No offense is possible below 20 simulated seconds.

The first eligible RESET at or after 20 seconds produces the offense.

The threshold is never translated into a window count.

## Prediction probe

Paired 100-seed PRESSURE / ESCAPE comparison:

```text
Top RESETs:
  v0.3a baseline 0
  v0.3b          0

random taps:
  v0.3a baseline 99
  v0.3b          99

informed taps:
  v0.3a baseline 0
  v0.3b          0

standard random-batch v0.3b warnings:
  Top 0
  Bottom 0

standard random-batch v0.3b penalties:
  Top 0
  Bottom 0
```

### Prediction 1 — Top RESET count falls

**Not confirmed in the standard batch.**

The baseline policy already recorded zero Top RESETs under PRESSURE / ESCAPE, so there was no RESET count available to reduce.

This is not a gate failure. It shows the normal policy was already actively choosing progress in that condition.

### Prediction 2 — random-response Tap rate changes little

Confirmed in the strongest possible descriptive sense for this matched probe:

```text
99 -> 99
```

No threshold is attached to this observation.

### Prediction 3 — informed-defender Tap remains zero

Confirmed descriptively:

```text
0 -> 0
```

v0.3b correctly does not solve the deferred fatigue-cancellation problem.

### Prediction 4 — Locked becomes harder to retain by resting

Confirmed by Gate A:

```text
Locked -> Strong
```

after the persistent Warning followed by the next qualifying offense.

## Standard-batch interpretation

The standard PRESSURE / ESCAPE policy produces:

```text
0 stalling warnings
0 stalling penalties
```

for either side.

That is desirable evidence.

v0.3b is not randomly perturbing an already-engaged match. It activates when a player deliberately chooses RESET while a real progress route exists and their 20-second clock has matured.

## Free initiative implementation

A boundary penalty marks the non-stalling player as the immediate initiative beneficiary.

The batch runner consumes that window before normal drift:

```text
no match.advance()
no behavior-stamina tick
no simulated-time cost
```

The beneficiary still uses normal action legality and normal action stamina/commitment rules.

## Gate-B deferral remains untouched

The existing v0.3a competent-defender evidence remains:

```text
random PRESSURE / ESCAPE Tap=99/100
informed PRESSURE / ESCAPE Tap=0/100
```

and Gate B remains:

```text
DEFERRED
```

with automatic expiry still waiting for:

```text
response commitment
or
Recognition/information
```

v0.3b adds neither.

## Setup-policy debt remains untouched

v0.3b does not alter the existing:

```text
SETUP-POLICY DEBT:
builder progress is ranked above axis loss
informed PROTECT builds=1768
Threat entries=0
```

That remains later work.

## Result

Current gate surface:

```text
v0.2 Gate 1 PASS
v0.2 Gate 2 PASS
v0.2 Gate 3 PASS
v0.2 Gate 4 PASS
v0.2 Gate 5 PASS
v0.2 Gate 6 ACCEPTED
v0.2 Gate 7 OPEN

v0.3a Gate A PASS
v0.3a Gate B DEFERRED
v0.3a Gate C PASS
v0.3a Gate D PASS
v0.3a Gate E PASS

v0.3b Gate A PASS
v0.3b Gate B PASS
v0.3b Gate C PASS
v0.3b Gate D PASS
v0.3b Gate E PASS
```

No response commitment, Recognition mechanic, matchup grade, response weight, stamina threshold, commitment cost, provisional LOW=3 submission-hold cost, or Gate-B threshold was changed to obtain this result.
