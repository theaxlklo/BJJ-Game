# Mount v0.3b — Position Reset Final Measurement

> **SUPERSEDED FOR GATE-A / GATE-2 CLOSURE.** This document correctly proved that Position Reset escalation fixed the single 5:00 / 5-second timeout sample, but a later timing-independent sweep showed three 7-second cases at an exact post-reset Locked share of 0.500. Under the subsequently frozen strict `<0.50` criterion, Gate A and Gate 2 are OPEN. The authoritative current measurement is `MOUNT_V0_3B_POST_RESET_STEADY_STATE_MEASUREMENT.md`.

## Status

AUTHORITATIVE v0.3b CLOSURE MEASUREMENT.

This file supersedes the early Gate-A conclusion in `MOUNT_V0_3B_FIRST_MEASUREMENT.md`.

## Mechanics evidence head

```text
113775b7236a200e2c5c94891a34158cb96acfac
```

GitHub Actions push run:

```text
#555
```

Both Python interpreters passed.

```text
Python 3.11: 238 tests PASS
Python 3.13: 238 tests PASS
modern semantic checker PASS
legacy checker PASS
```

Frozen enumerate digest:

```text
expected=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
actual=3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Why a second measurement was required

The original Gate-A probe stopped after:

```text
offense 1 -> Warning
offense 2 -> one-band penalty
```

and read the state immediately after the first penalty.

That produced:

```text
+4.00 Locked -> +2.80 Strong
```

but did not run to timeout.

The corrected full-match probe exposed the real result of the first two rungs alone:

```text
Warning=1
one-band penalties=13
Position Resets=0
final axis=+4.00
final band=Locked
locked_timeout=True
Locked windows=59/59
```

Therefore:

```text
v0.3b Gate A OPEN
v0.2 Gate 2 OPEN
```

on the one-band-only mechanics.

That failure is preserved in:

`MOUNT_V0_3B_FULL_MATCH_STALLING_FAILURE.md`.

## Frozen escalation applied

The v9 Section-33 ladder was then completed as:

```text
offense 1
-> persistent Warning

offense 2
-> one visible-band penalty
   or free-initiative boundary consequence

offense 3+
-> Position Reset
```

Mount-v0 Position Reset uses the existing canonical start:

```text
axis = +1.50
band = Stable
```

No stalling cadence or numeric penalty magnitude was tuned from the failed result.

## Corrected full-match Gate A

The authoritative probe runs the full 5:00 clock.

Measured result:

```text
Warning=1
one-band penalties=1
Position Resets=12
final axis=+3.00
final band=Strong
locked_timeout=False
Locked windows=24/59
```

Therefore:

```text
v0.3b Gate A PASS
```

The important distinction is that PASS is now evaluated **at timeout**, not immediately after an early penalty.

Deliberate Top RESET with a persistent progress route no longer finishes the match in Locked.

## v0.2 Gate 2

The historical two-sided RESET observation remains visible:

```text
RESET LOCK PROBE:
Top PRESSURE+RESET vs Bottom ESCAPE+RESET
-> TIMEOUT — Mount retained
-> +4.00 Locked
```

That historical probe cannot assign individual stalling ownership because both players deliberately RESET.

The corrected one-sided ownership probe now supplies full-match evidence:

```text
v03b_warnings=1
v03b_penalties=1
v03b_position_resets=12
v03b_final_band=Strong
locked_timeout=False
```

Therefore:

```text
v0.2 Gate 2 PASS
```

Gate 2 no longer passes because of a temporary early Strong state.

It passes because the complete match fails to retain Locked under deliberate one-sided stalling.

## Gate B — engaged stalemate remains protected

```text
attempts=3
Top penalties=0
Bottom penalties=0
stage=Threat
advancement clocks=0/0
```

Fresh informed Turn-In holds the Americana stage at Contested.

The attacker is engaged by making the legal advancement attempt.

The defender is engaged by making the legal response.

Neither is punished.

```text
v0.3b Gate B PASS
```

## Gate C — symmetric attribution remains

```text
Top warnings/penalties=1/1
Bottom warnings/penalties=1/1
```

Both competitors remain subject to the same 20-second clock and first two offense rungs.

```text
v0.3b Gate C PASS
```

## Gate D — Neutral boundary remains protected

```text
Warning=1
free initiative windows=1
axis +0.50 -> +0.50
band Loose
simulated clock unchanged
```

The one-band offense-2 penalty still cannot cross Neutral.

At the boundary, the non-stalling player receives the frozen zero-time free initiative window.

```text
v0.3b Gate D PASS
```

## Gate E — competent-defender deferral remains intact

```text
response_commitment_present=False
recognition_present=False
v0.3a Gate B=DEFERRED
```

Position Reset escalation adds neither response commitment nor an information/Recognition system.

```text
v0.3b Gate E PASS
```

## Normal-play guard

The stronger escalation remains absent from standard engaged play.

Random responder standard batch:

```text
Top warnings=0
Bottom warnings=0
Top one-band penalties=0
Bottom one-band penalties=0
Top Position Resets=0
Bottom Position Resets=0
```

Informed responder standard batch:

```text
Top warnings=0
Bottom warnings=0
Top one-band penalties=0
Bottom one-band penalties=0
Top Position Resets=0
Bottom Position Resets=0
```

Checker result:

```text
V0.3b NORMAL-PLAY GUARD [PASS]
```

This is executable regression protection, not a tuning target.

## Prediction probe

Matched 100-seed PRESSURE / ESCAPE:

```text
Top RESETs:    0 -> 0
random taps:  99 -> 99
informed taps: 0 -> 0

v0.3b standard random:
warnings Top/Bottom=0/0
penalties Top/Bottom=0/0
Position Resets Top/Bottom=0/0
```

The pre-implementation prediction that Top RESET count would decrease remains unconfirmed because baseline Top RESET count was already zero.

The submission predictions remain exactly unchanged.

## Position Reset scope

The Position Reset changes only Mount positional control:

```text
axis -> +1.50
band -> Stable
```

It does not clear:

- stamina;
- exhaustion;
- setup state;
- Americana submission stage;
- stalling Warning/offense history;
- match clock.

This avoids encoding the false assumption that an Americana threat is inherently Mount-exclusive.

## Final gate surface

```text
v0.2
1 PASS
2 PASS
3 PASS
4 PASS
5 PASS
6 ACCEPTED
7 OPEN

v0.3a
A PASS
B DEFERRED
C PASS
D PASS
E PASS

v0.3b
A PASS
B PASS
C PASS
D PASS
E PASS

V0.3b NORMAL-PLAY GUARD PASS
```

## Unchanged debts

This change does not close:

```text
v0.2 Gate 7:
commitment meaning OPEN

v0.3a Gate B:
competent-defender submission finish DEFERRED

v0.3a SETUP-POLICY DEBT:
builder progress can outrank axis loss
```

No response commitment, Recognition mechanic, stamina threshold, submission-hold cost, exhaustion modifier, response weight, matchup grade, or Gate-B threshold was changed to close v0.3b.
