# Stamina Economy — First Measurement

## Status

FIRST MEASUREMENT RECORDED.

Measurement-only. No gameplay rule is changed or authorized by this document.

Frozen measurement DoD:

`docs/STAMINA_ECONOMY_MEASUREMENT_DEFINITION_OF_DONE.md`

Frozen reviewed DoD commit:

```text
ae8998bd86cdebb09d5c74f6f3222a299bcdaabf
```

The first implementation checkpoint was measured in GitHub Actions run #838. Its semantic checker passed all stamina-economy measurement gates A-H and reproduced the frozen v0.4b policy surfaces. A later instrumentation correction changed only the **reporting definition** of response-commitment shortfall on hold exchanges from post-downgrade spend shortfall to:

```text
requested response commitment cost - actual charged response commitment cost
```

That correction does not change any match state, outcome, affordability classification, stamina charge, duration, or first-measurement conclusion.

## Measurement meaning

A measurement gate PASS means:

```text
required evidence exists
+ stamina accounting reconciles
+ duration accounting reconciles
+ instrumentation does not perturb mechanics
+ reruns are deterministic
```

It does **not** mean the stamina economy is healthy.

## Frozen surfaces

All use 100 matches and base seed 42.

```text
A — public MATCH
B — Recognition, trusts reads
C — Recognition, one level above
D — Recognition, always HIGH
E — Recognition, trusts reads + Bottom RECOVER
```

Shared gameplay configuration remains the frozen DoD configuration.

## Measurement gates

First measurement:

```text
A PASS — exact three-state duration accounting
B PASS — middle-window affordability and hold-aware burden
C PASS — decisive exchanges classified by stamina state
D PASS — stamina-source accounting reconciles
E PASS — funded / UNFUNDED exchange states measured
F PASS — zero-stamina attacks exposed
G PASS — policy continuity and deterministic replay
H PASS — checker-owned structured evidence
```

Across five surfaces:

```text
500/500 match durations reconcile exactly
1000/1000 side stamina accounts reconcile exactly
24,035 initiated exchanges are classified
16,520 zero-stamina initiator attacks are exposed
instrumented vs uninstrumented mechanics: identical
deterministic replay: identical
```

The frozen Mount digest remains unchanged by the measurement work.

## Three-state result

States:

```text
State 1 — NOT_MUTUALLY_EXHAUSTED
State 2 — MUTUALLY_EXHAUSTED_NOT_BOTH_ZERO
State 3 — MUTUALLY_ZERO
```

### Surface A — public MATCH

```text
State 2 entered: 78/100
State 3 entered: 78/100

median first State 2: 55 s
median first State 3: 80 s

median State-2 duration: 25 s
median State-2 share: 8.3%

median State-3 duration: 220 s
median State-3 share: 73.3%

exits State 2 -> State 1: 0
```

### Surface B — trusts reads

```text
State 2 entered: 90/100
State 3 entered: 84/100

median first State 2: 55 s
median first State 3: 75 s

median State-2 duration: 22.5 s
median State-2 share: 8.3%

median State-3 duration: 225 s
median State-3 share: 75.0%

exits State 2 -> State 1: 0
```

### Surface C — one level above

```text
State 2 entered: 78/100
State 3 entered: 78/100

median first State 2: 45 s
median first State 3: 60 s

median State-2 duration: 15 s
median State-2 share: 5.0%

median State-3 duration: 235 s
median State-3 share: 78.3%

exits State 2 -> State 1: 0
```

### Surface D — always HIGH

```text
State 2 entered: 78/100
State 3 entered: 78/100

median first State 2: 45 s
median first State 3: 70 s

median State-2 duration: 25 s
median State-2 share: 8.3%

median State-3 duration: 230 s
median State-3 share: 76.7%

exits State 2 -> State 1: 0
```

### Surface E — trusts reads + Bottom RECOVER

```text
State 2 entered: 90/100
State 3 entered: 86/100

median first State 2: 55 s
median first State 3: 85 s

median State-2 duration: 137.5 s
median State-2 share: 45.8%

median State-3 duration: 80 s
median State-3 share: 26.7%

exits State 2 -> State 1: 0
Bottom switches into CONSERVE: 90
Bottom switches back to ESCAPE: 0
Bottom Exhausted-latch clears: 0
```

### Fact

The existing RECOVER policy does not climb out of Exhausted on this frozen surface.

It does materially change *where time is spent*: compared with fixed trust-read Surface B, it converts much of the mutual-zero regime into the mutually-Exhausted middle regime.

It does not produce a single observed Exhausted -> non-Exhausted latch clear.

This is an observation, not a recovery-rule recommendation.

## Where the decisive submission exchanges happen

### Surface B — trusts reads

```text
State 1:
  taps=2
  under-commitment-caused taps=1

State 2:
  taps=4
  under-commitment-caused taps=4

State 3:
  taps=0
  under-commitment-caused taps=0
```

Therefore:

```text
all 6 historical trust-read taps occur before mutual zero
4/6 taps occur in State 2
5/6 taps are directly attributable to responder under-commitment
4/5 under-commitment-caused taps occur in State 2
```

This sharpens the earlier v0.4b finding.

“Both are Exhausted” was too broad to identify the mechanism, and “both are at zero” is not where the taps occur.

The decisive window is primarily:

```text
both Exhausted
but not both zero
```

### Hedge surfaces

Surface C — one level above:

```text
State 2 taps=0
State 3 taps=0
```

Surface D — always HIGH:

```text
State 2 taps=0
State 3 taps=0
```

### Recovery surface

Surface E:

```text
State 1 taps=2
State 2 taps=3
State 3 taps=0

State-2 under-commitment-caused taps=3
```

RECOVER does not eliminate the same tired-state conversion channel.

## Middle-window affordability

The fixed initiator policy requests MEDIUM, so no measured initiator has a true effective HIGH commitment in these State-2 probes. The “HIGH attacker / no higher selectable hedge” count is therefore zero on B-E.

### Surface B — trusts reads

State-2 exchanges:

```text
358
```

Initiator affordability ceiling:

```text
UNFUNDED 141
LOW       36
MEDIUM    54
HIGH     127
```

Responder affordability ceiling:

```text
UNFUNDED 136
LOW       52
MEDIUM    51
HIGH     119
```

Responder relative affordability:

```text
higher than initiator: 87
equal:                181
lower:                 90
```

Can fund one selectable level above the initiator's true effective commitment:

```text
167 / 358 = 46.6%
```

Responder's actual requested commitment fully fundable:

```text
202 / 358 = 56.4%
```

Initiator's requested MEDIUM fully fundable:

```text
181 / 358 = 50.6%
```

### Surface C — one level above

```text
State-2 exchanges=246
hedge-one fundable=142/246 = 57.7%
actual defender request fundable=112/246 = 45.5%
initiator requested MEDIUM fundable=126/246 = 51.2%
```

### Surface D — always HIGH

```text
State-2 exchanges=312
hedge-one fundable=78/312 = 25.0%
actual HIGH defender request fundable=78/312 = 25.0%
initiator requested MEDIUM fundable=0/312
```

### Surface E — trusts reads + Bottom RECOVER

```text
State-2 exchanges=4,173
hedge-one fundable=1,871/4,173 = 44.8%
actual defender request fundable=1,915/4,173 = 45.9%
initiator requested MEDIUM fundable=269/4,173 = 6.4%
```

### Fact

There is substantial real defender hedge headroom in State 2.

The defender does not need infinite stamina for hedging to matter. On the trust-read surface, it can fully fund one selectable level above the attacker's true effective commitment on nearly half of State-2 exchanges.

This is a measured fact, not a decision that the defender *should* hedge.

## Hold-aware affordability

The hold measurement confirms that commitment-only affordability overstates the defender's available room on Contested submission holds.

### State-2 holds

Surface B — trusts reads:

```text
hold exchanges=85
FULL=43
PARTIAL=13
NONE=29

commitment request fundable
but requested commitment + hold not fully fundable=8
```

Surface C — one level above:

```text
hold exchanges=39
FULL=12
PARTIAL=20
NONE=7

commitment request fundable
but requested commitment + hold not fully fundable=5
```

Surface D — always HIGH:

```text
hold exchanges=78
FULL=0
PARTIAL=0
NONE=78

commitment request fundable
but requested commitment + hold not fully fundable=0
```

Surface E — trusts reads + Bottom RECOVER:

```text
hold exchanges=1,490
FULL=100
PARTIAL=1,113
NONE=277

commitment request fundable
but requested commitment + hold not fully fundable=1,366
```

### Fact

The provisional hold charge is not a small bookkeeping edge on Surface E.

It repeatedly consumes the stamina the existing RECOVER policy creates, and most State-2 hold exchanges cannot pay the full hold after the response-commitment charge.

That does **not** decide whether the hold cost is wrong. It identifies the current charge as a major stamina sink that any later rule design must account for.

## Stamina-source accounting

All 1,000 side accounts reconcile exactly.

Aggregate charged/recovered stamina across 100 matches:

### Surface A — public MATCH

```text
Top:
  behavior spend=1,336
  initiator commitment=4,130
  responder commitment=3,038
  hold=0

Bottom:
  behavior spend=1,102
  initiator commitment=3,038
  responder commitment=4,130
  hold=234
```

### Surface B — trusts reads

```text
Top:
  behavior spend=1,394
  initiator commitment=4,401
  responder commitment=3,542
  hold=0

Bottom:
  behavior spend=1,322
  initiator commitment=3,827
  responder commitment=3,810
  hold=442
```

### Surface C — one level above

```text
Top:
  behavior spend=1,054
  initiator commitment=3,460
  responder commitment=4,140
  hold=0

Bottom:
  behavior spend=1,009
  initiator commitment=2,627
  responder commitment=4,703
  hold=290
```

### Surface D — always HIGH

```text
Top:
  behavior spend=1,180
  initiator commitment=3,272
  responder commitment=4,272
  hold=0

Bottom:
  behavior spend=1,102
  initiator commitment=2,180
  responder commitment=5,208
  hold=234
```

### Surface E — Bottom RECOVER

```text
Top:
  behavior spend=1,393
  behavior recovery=0
  initiator commitment=4,385
  responder commitment=3,571
  hold=0

Bottom:
  behavior spend=938
  behavior recovery=8,658
  initiator commitment=6,091
  responder commitment=9,076
  hold=1,745
```

### Fact

Surface E creates a large recovery throughput:

```text
Bottom behavior recovery=8,658
```

but still records:

```text
Exhausted-latch clears=0
```

The recovered stamina is consumed by the existing action/response/hold economy before the 35-point recovery threshold is reached.

## All hold exchanges — requested vs actually charged

Using the corrected response-shortfall definition:

### Surface A

```text
response requested / charged / shortfall:
6,474 / 1,092 / 5,382

hold requested / charged / shortfall:
5,850 / 234 / 5,616

combined requested / charged / shortfall:
12,324 / 1,326 / 10,998
```

### Surface B

```text
response:
5,182 / 1,117 / 4,065

hold:
4,506 / 442 / 4,064

combined:
9,688 / 1,559 / 8,129
```

### Surface C

```text
response:
10,285 / 915 / 9,370

hold:
4,290 / 290 / 4,000

combined:
14,575 / 1,205 / 13,370
```

### Surface D

```text
response:
23,400 / 936 / 22,464

hold:
5,850 / 234 / 5,616

combined:
29,250 / 1,170 / 28,080
```

### Surface E

```text
response:
5,521 / 5,447 / 74

hold:
4,767 / 1,745 / 3,022

combined:
10,288 / 7,192 / 3,096
```

Surface E is notably different: RECOVER makes the requested response commitment almost fully payable in aggregate, while the additional hold cost still has a large shortfall.

## UNFUNDED equality

True effective funding pairs include many exchanges where both competitors are UNFUNDED.

Counts:

```text
A: 3,588
B: 3,771
C: 3,697
D: 3,744
E: 1,604
```

For every measured both-UNFUNDED exchange:

```text
response-undercommitment modifier=0
```

Submission results in both-UNFUNDED exchanges:

```text
A advances/taps=0/0
B advances/taps=0/0
C advances/taps=0/0
D advances/taps=0/0
E advances/taps=0/0
```

### Fact

The current equality rule does exactly what the design says:

```text
UNFUNDED == UNFUNDED
-> no under-commitment
```

But on these five surfaces, mutual UNFUNDED is **not** the source of the successful submission conversions.

It is primarily part of the late depleted regime.

Whether UNFUNDED equality should remain a rule is still a later design question.

## Zero-stamina attacks

Total zero-stamina initiated attacks:

```text
16,520
```

By surface:

```text
A: 3,510
B: 3,752
C: 3,721
D: 3,588
E: 1,949
```

Every one records:

```text
initiator effective commitment=UNFUNDED
effective commitment cost=0
```

Submission-stage results from zero-stamina initiators:

```text
A attempts/advances/taps=1,716/0/0
B attempts/advances/taps=1,028/0/0
C attempts/advances/taps=1,041/0/0
D attempts/advances/taps=1,794/0/0
E attempts/advances/taps=1,096/0/0
```

### Fact

Free zero-stamina attacks are extremely common in this diagnostic, but **none produce a submission advance or Tap**.

They therefore are not the direct source of the v0.4b trust-read conversion.

They remain relevant because they allow the depleted match to continue generating exchanges at zero initiator commitment cost.

Whether they should remain legal is a later design question.

## Surface E changes the depleted regime, not the latch

Surface E produces an important distinction:

```text
State-3 time exists
but State-3 initiated exchanges=0
```

The sequence is:

```text
both may be zero at the start of a time interval
-> Bottom CONSERVE recovers stamina during advance()
-> decision exchange begins with Bottom above zero
-> exchange is State 2, not State 3
-> response / hold spending consumes recovered stamina
-> Bottom never reaches the >=35 latch-clear threshold
```

Observed State-2 exchanges on Surface E:

```text
4,173
```

Funding pairs in Surface E include:

```text
initiator UNFUNDED / responder funded=1,720
initiator funded / responder UNFUNDED=636
both UNFUNDED=1,604
both funded=1,192
```

The existing recovery policy therefore prevents many exchange-time mutual-zero states, but it does not restore a non-Exhausted defender on this surface.

## Facts vs candidate rule questions

### Facts established by this slice

1. Fixed PRESSURE/ESCAPE surfaces spend most of their late match in mutual zero.
2. The historical trust-read taps do **not** occur at mutual zero.
3. Four of six trust-read taps occur in the mutually-Exhausted/not-both-zero window.
4. All four of those State-2 taps are under-commitment-caused under the frozen attribution rule.
5. Defender hedge headroom is materially present in State 2.
6. Hold-inclusive affordability is substantially worse than commitment-only affordability.
7. Existing RECOVER generates large stamina recovery but never clears Bottom's Exhausted latch on Surface E.
8. RECOVER shifts decision exchanges from State 3 into State 2 rather than restoring State 1.
9. Both-UNFUNDED exchanges compare equal and produce no measured submission advances/taps.
10. Zero-stamina attacks are frequent but produce no measured submission advances/taps.
11. All stamina sources and state durations reconcile exactly.

### Candidate questions for a later rule-changing DoD

These are **questions only**, not recommendations:

- Should the provisional hold charge remain separate from response commitment?
- Should a recovering fighter have a way to retain recovered stamina long enough to clear the Exhausted latch?
- Should UNFUNDED vs UNFUNDED remain commitment-equal?
- Should a zero-stamina initiator be allowed to continue initiating at zero commitment cost?
- Should Exhausted-state commitment availability or consequences change?
- Should the stamina economy create a stronger opportunity cost for hedge-one / always-HIGH response policies?

No answer to those questions is authorized by this measurement document.

## Change-control boundary

Next sequence:

```text
finish measurement implementation
-> exact-head tests/checker/digest verification
-> PR review
-> review the evidence
-> if a rule change is warranted:
     draft a separate rule-changing DoD
     -> commit it
     -> HARD STOP
     -> user review
     -> explicit implementation authorization
```

No rule-changing DoD has been drafted by this document.
