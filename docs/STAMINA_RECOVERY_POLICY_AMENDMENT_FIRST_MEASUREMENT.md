# Stamina Recovery Policy Amendment — First Measurement

## Status

FIRST UNTUNED MEASUREMENT RECORDED.

This document records the implementation authorized against:

```text
docs/STAMINA_RECOVERY_POLICY_AMENDMENT_DEFINITION_OF_DONE.md
```

Frozen DoD review head:

```text
dcc5984afbf2f575548be5511bd39f807dbf7f82
```

Base main after PR #8:

```text
b2299a1037b709d2d4a9893c615e4af5b55b4cfa
```

Starting evidence was committed before flag splitting or candidate-policy work:

```text
docs/STAMINA_RECOVERY_POLICY_STARTING_EVIDENCE.md
```

No stamina cost, recovery rate, Exhausted threshold, settlement rule, Recognition rule, matchup grade, setup rule, submission rule, or v0.3b stalling rule was tuned in response to the results below.

The recovery-initiation candidates remain **diagnostic batch policies**, not selected game defaults.

---

# Starting evidence

The checker reproduced the review-provided Surface E destination accounting exactly before later implementation.

```text
LEGACY
Bottom defensive spend=10,821
  response=9,076
  hold=1,745
Bottom own-attack spend=6,091
Bottom own attacks=2,516
Bottom RESETs=29
Bottom behavior recovery=8,658

BOTH PR8 rules
Bottom defensive spend=3,872
  response=3,872
  hold=0
Bottom own-attack spend=11,994
Bottom own attacks=2,387
Bottom RESETs=18
Bottom behavior recovery=7,950
```

This confirms the starting causal observation:

```text
defensive drain falls by 6,949
while own-attack spend rises by 5,903
```

The current recovery behavior is generating stamina, but the existing initiation policy spends much of it again.

---

# Independent settlement attribution

The PR8 umbrella was split into two independently opt-in diagnostic capabilities while retaining the old umbrella as the exact BOTH compatibility path:

```text
NONE
RULE1_ONLY
RULE2_ONLY
BOTH
```

Compatibility:

```text
NONE == historical legacy: true
explicit Rule1 + Rule2 == PR8 umbrella BOTH: true
```

The new explicit flags default to false.

## Surface A — public MATCH

| Mode | Tap | Escapes | Timeout | Threat matches | Threat entries | Bottom defensive spend | Bottom own spend |
|---|---:|---:|---:|---:|---:|---:|---:|
| NONE | 0 | 22 | 78 | 78 | 1,950 | 4,364 | 3,038 |
| RULE1_ONLY | 0 | 22 | 78 | 78 | 1,950 | 4,364 | 3,038 |
| RULE2_ONLY | 0 | 22 | 78 | **0** | **0** | 3,818 | 3,584 |
| BOTH | 0 | 22 | 78 | **0** | **0** | 3,818 | 3,584 |

Rule 1 alone leaves public-MATCH Threat reach unchanged.

Rule 2 alone reproduces the entire:

```text
78/100 -> 0/100
```

Threat-reach collapse.

The P6 warning from PR #8 is therefore now experimentally attributed to Rule 2, not merely inferred.

## Surface B — trust-read Recognition

| Mode | Tap | Escapes | Timeout | Threat matches | Threat entries | Control | Finish |
|---|---:|---:|---:|---:|---:|---:|---:|
| NONE | 6 | 11 | 83 | 58 | 578 | 395 | 320 |
| RULE1_ONLY | 9 | 12 | 79 | 59 | 533 | 355 | 372 |
| RULE2_ONLY | 6 | 15 | 79 | 50 | 502 | 284 | 203 |
| BOTH | 7 | 14 | 79 | 50 | 436 | 331 | 205 |

Rule 1's local invariant remains exact:

```text
true-UNFUNDED initiator
-> responder spend=0
```

Rule 2's local invariant remains exact:

```text
funded response commitment covers the first 3 hold points
-> additive double-charge cases=0
```

In Rule2-only mode, legacy spend on an UNFUNDED initiator may remain because Rule 1 is intentionally disabled. That is not a Rule-2 failure.

## Surface E — trust reads + Bottom RECOVER

| Mode | Tap | Escapes | Timeout | Threat matches | Bottom defensive | Bottom own attacks spend | Recovery | Bottom final median | Latch clears |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NONE | 5 | 9 | 86 | 60 | 10,821 | 6,091 | 8,658 | 2 | 0 |
| RULE1_ONLY | 5 | 15 | 80 | 60 | **4,401** | **11,982** | 8,426 | 6 | 0 |
| RULE2_ONLY | 5 | 11 | 84 | 51 | 9,701 | 6,836 | 8,358 | 2 | 0 |
| BOTH | 5 | 20 | 75 | 51 | **3,872** | **11,994** | 7,950 | 6 | 0 |

Rule 1 is the dominant cause of the defensive-drain reduction.

It also exposes the next blocker: with CURRENT initiation, Bottom converts the freed budget into its own MEDIUM attacks and still never clears Exhausted.

---

# Recovery-initiation candidate matrix

Exact Surface E was run with BOTH settlement rules under:

```text
CURRENT
RESET_WHILE_EXHAUSTED
LOW_WHILE_EXHAUSTED
```

Each candidate was run:

```text
stalling OFF + read-only shadow v0.3b
stalling ON using frozen real v0.3b
```

The stalling-OFF gameplay result is unchanged by enabling the shadow observer for all three candidates.

## Stalling OFF

| Candidate | Tap | Half Guard | Open Guard | Reversal | Timeout | Bottom final median | Defensive spend | Own-attack spend | Recovery | Own attacks | RESETs | Latch clears | CONSERVE→ESCAPE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 5 | 7 | 8 | 5 | 75 | 6 | 3,872 | 11,994 | 7,950 | 2,387 | 18 | **0** | **0** |
| RESET_WHILE_EXHAUSTED | 5 | **69** | 2 | 1 | **23** | 19 | 4,380 | **5,964** | 4,434 | **852** | **994** | **234** | **228** |
| LOW_WHILE_EXHAUSTED | 5 | 31 | **15** | **5** | 44 | **26** | 4,038 | 9,196 | **7,150** | 2,280 | 19 | **67** | **64** |

State-2 -> State-1 exits:

```text
CURRENT = 0
RESET   = 234
LOW     = 67
```

State shares:

```text
CURRENT:
State1 20.9%
State2 71.2%
State3  7.9%

RESET:
State1 42.1%
State2 57.9%
State3  0.0%

LOW:
State1 24.8%
State2 75.2%
State3  0.0%
```

Both candidate policies can therefore break the old recovery deadlock without changing stamina numbers.

That is **measurement evidence only**. Neither candidate is selected as a default by this amendment.

---

# Recovery budget

Bottom spend relative to behavior recovery:

```text
CURRENT
own / recovery       = 1.509
defense / recovery   = 0.487
total / recovery     = 1.996

RESET
own / recovery       = 1.345
defense / recovery   = 0.988
total / recovery     = 2.333

LOW
own / recovery       = 1.286
defense / recovery   = 0.565
total / recovery     = 1.851
```

These ratios cover the whole match, not only Exhausted windows, so they are descriptive rather than a per-window conservation equation.

The key direct result is the latch behavior:

```text
CURRENT 0 clears
RESET   234 clears
LOW      67 clears
```

---

# Setup-policy interaction while Bottom is Exhausted

The candidate policies differ substantially in how much tactical activity they preserve.

```text
                                    CURRENT   RESET   LOW

Bridge attempts                       1326       0    1114
setup-builder attempts                1326       0    1114
setup advances                        1162       0    1083
Ready transitions                      586       0     539
completed setup builds                1058       0    1025
escapes after measured setup builds      3       0       3
Exhausted RESETs                        18     994      19
RESETs forgoing setup opportunity       18     994      19
```

RESET obtains the strongest recovery result by completely giving up exhausted-state initiation/setup construction.

LOW preserves most of the CURRENT setup activity while still producing real latch clears.

This does **not** resolve the older setup-policy debt. Bridge/setup semantics remain frozen and require a separate slice if they are changed.

---

# Frozen v0.3b stalling interaction

## Shadow observer

On the stalling-OFF runs:

```text
shadow does not perturb gameplay:
CURRENT = true
RESET   = true
LOW     = true
```

RESET creates vastly more RESET-with-route exposure:

```text
shadow RESET-with-route:

CURRENT = 7
RESET   = 983
LOW     = 7
```

However, the shadow advancement clock never reaches an offense before another frozen engagement resets it.

Would-be consequences:

```text
                    Warning   Penalty   Position Reset   Free initiative

CURRENT                 0         0            0               0
RESET                   0         0            0               0
LOW                     0         0            0               0
```

A separate synthetic regression test drives the observer to 20 seconds and pins the frozen escalation:

```text
first offense  -> WARNING
second offense -> PENALTY
```

while proving the observer does not mutate real axis, clock, or stamina.

## Real stalling ON

The real frozen v0.3b runs show the same thing:

```text
                    Warnings   Penalties   Position Resets   RESET-with-route

CURRENT                 0          0             0                  7
RESET                   0          0             0                983
LOW                     0          0             0                  7
```

Bottom stalling penalty axis movement:

```text
CURRENT signed/absolute = +0.00 / 0.00
RESET   signed/absolute = +0.00 / 0.00
LOW     signed/absolute = +0.00 / 0.00
```

Boundary free-initiative consequences:

```text
CURRENT = 0
RESET   = 0
LOW     = 0
```

Matched OFF vs ON:

```text
CURRENT diverged matches = 0/100
RESET   diverged matches = 0/100
LOW     diverged matches = 0/100
```

Therefore every candidate's OFF and ON gameplay outcome is identical on these seeds.

The reason is important:

> **Frozen v0.3b counts legal defensive engagement as engagement. Top's normal attacks keep resetting Bottom's advancement clock before Bottom's recovery RESETs can reach the 20-second offense threshold.**

So RESET has high *stalling exposure* in the sense of RESET-with-route opportunities, but under the frozen rules it does **not** actually stall long enough to receive a Warning.

No stalling rule was weakened or changed to produce this result.

---

# Candidate outcomes with stalling ON

Because no actual v0.3b offense fires, the ON outcomes equal the OFF outcomes exactly.

```text
CURRENT
Tap=5
Half Guard=7
Open Guard=8
Reversal=5
Timeout=75
Latch clears=0

RESET_WHILE_EXHAUSTED
Tap=5
Half Guard=69
Open Guard=2
Reversal=1
Timeout=23
Latch clears=234

LOW_WHILE_EXHAUSTED
Tap=5
Half Guard=31
Open Guard=15
Reversal=5
Timeout=44
Latch clears=67
```

The amendment's reading rule therefore does not need to choose between an OFF-only and ON-viable candidate here: RESET and LOW clear Exhausted in both columns.

That still does not select either candidate as the permanent policy.

---

# Gates A-J

The checker-owned amendment gates are:

```text
A PASS — starting Surface-E destination evidence reproduced
B PASS — NONE and BOTH compatibility preserved
C PASS — Rule 1 isolated invariant
D PASS — Rule 2 isolated invariant
E PASS — CURRENT recovery blocker reproduced
F PASS — all three stalling-OFF recovery candidates measured
G PASS — real v0.3b + shadow interaction measured deterministically
H PASS — stamina/settlement/Recognition/matchup/stalling rules frozen
I PASS — default behavior remains merged-main compatible
J PASS — structured deterministic checker/review evidence
```

A PASS here means the frozen measurement/compatibility requirement is satisfied.

It does **not** mean a recovery policy has been selected or that every underlying design debt is closed.

---

# P1-P8 comparison

The predictions were frozen before implementation.

## P1 — Rule 1 isolation

Prediction:

```text
Rule1-only eliminates UNFUNDED defender drain
without reproducing the public-MATCH Threat collapse
```

Observed:

```text
A Threat matches 78 -> 78
B Threat matches 58 -> 59
E Threat matches 60 -> 60

Rule1-only UNFUNDED responder spend:
A/B/E = 0 / 0 / 0
```

**CONFIRMED.**

---

## P2 — Rule 2 attribution

Prediction:

```text
Rule2-only causes most of the public-MATCH Threat loss
```

Observed:

```text
public MATCH Threat matches:
78 -> 0

Threat entries:
1950 -> 0
```

**CONFIRMED more strongly than required.**

Rule 2 alone reproduces the full collapse.

---

## P3 — BOTH replay

Prediction:

```text
explicit Rule1 + Rule2 reproduces PR8 BOTH exactly
```

Observed:

```text
true
```

**CONFIRMED.**

---

## P4 — CURRENT recovery budget

Prediction:

```text
defensive spend remains greatly reduced,
own-attack spend consumes the freed recovery budget,
latch clears remain zero
```

Observed:

```text
defensive 10,821 -> 3,872
own attacks 6,091 -> 11,994
latch clears=0
```

**CONFIRMED.**

---

## P5 — RESET while Exhausted

Prediction:

```text
RESET sharply reduces own-attack stamina spend,
raises RESET count,
and has the strongest chance to reach >=35
```

Observed:

```text
own spend:
CURRENT 11,994
RESET    5,964
LOW      9,196

RESET count:
CURRENT 18
RESET   994
LOW      19

latch clears:
CURRENT   0
RESET   234
LOW      67
```

**CONFIRMED.**

The predicted setup cost also occurs: exhausted setup-builder attempts fall from 1,326 under CURRENT to 0 under RESET.

---

## P6 — LOW while Exhausted

Prediction:

```text
LOW reduces own spend versus CURRENT
while retaining more setup/escape activity than RESET;
it may or may not be sufficient to clear Exhausted
```

Observed:

```text
own spend 11,994 -> 9,196
setup builders RESET/LOW = 0 / 1,114
LOW latch clears = 67
```

**CONFIRMED, and LOW is sufficient to clear the latch on these seeds.**

---

## P7 — stalling exposure

Prediction:

```text
RESET gets the most stalling exposure;
CURRENT the least;
LOW likely between
```

Observed RESET-with-route exposure:

```text
CURRENT=7
RESET=983
LOW=7
```

But actual/shadow offenses:

```text
0 / 0 / 0
```

**PARTIAL.**

RESET is overwhelmingly the most exposed, but LOW ties CURRENT rather than falling between, and none reaches an actual offense.

---

## P8 — stalling feedback

Prediction:

```text
real v0.3b consequences make recovery less favorable
for at least the more passive candidate(s)
```

Observed:

```text
OFF == ON for every candidate
diverged matches=0/100 for CURRENT, RESET and LOW
```

**NOT CONFIRMED.**

No actual stalling consequence fires because legal defensive engagement resets Bottom's advancement clock.

The prediction remains in the record rather than being rewritten.

---

# Design evidence produced by this amendment

The measurement establishes:

1. Rule 1 is cleanly separable from Rule 2.
2. Rule 1 removes the UNFUNDED paid-defense asymmetry without causing the public-MATCH Threat collapse.
3. Rule 2 alone causes the entire public-MATCH 78 -> 0 Threat collapse.
4. The PR8 Gate-D failure under CURRENT is genuinely a policy-layer issue: Bottom spends freed stamina on its own MEDIUM attacks.
5. RESET while Exhausted breaks the recovery deadlock strongly.
6. LOW while Exhausted also breaks the recovery deadlock, less strongly, while preserving substantial setup/action activity.
7. RESET sacrifices all exhausted-state setup building in exchange for recovery.
8. LOW preserves most exhausted-state setup construction.
9. Frozen v0.3b does not punish any candidate on these seeds because ordinary legal defensive engagement prevents the advancement clock from reaching 20 seconds.
10. Shadow stalling is non-perturbing and agrees with the frozen escalation semantics.
11. The setup-policy debt remains relevant to comparing LOW vs RESET.
12. No candidate has been selected as the game default.
13. No amendment to Rule 2 has been authorized merely because its Threat effect is now isolated.

---

# Review boundary

This amendment intentionally stops before making the next design choices.

The review now has evidence for several separate decisions:

```text
1. Rule 1:
   keep / amend / remove?

2. Rule 2:
   keep / amend / remove?
   Its public-MATCH Threat collapse is now directly measured.

3. Recovery-aware initiation:
   none / RESET / LOW / another policy?

4. Setup-policy debt:
   resolve before selecting a recovery policy,
   or accept current setup semantics for the next slice?

5. Stalling:
   no current evidence requires changing v0.3b.
```

Those are separate review decisions.

This measurement document does **not** choose them.

Any new mechanic change requires the usual reviewed DoD / amendment and hard stop.
