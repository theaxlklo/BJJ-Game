# Stamina Production-Policy Adoption — Preregistration

## Status

**STAGE 1 COMPLETE — FROZEN — HARD STOP BEFORE STAGE 2.**

This document completes Stage 1 of
`docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md`.

It freezes A9 (`N`, `X`, `M`, and the margin rule) by mechanically applying the A9 selection procedure frozen in that DoD to the historical LOW+BOTH handoff baseline. No analyst choice was made.

It does **not** authorize the Rule1-only + LOW production-candidate run, any default change, or any canonical production configuration.

---

# Provenance

```text
branch:                  review/stamina-production-policy-adoption-dod
frozen DoD checkpoint:   6068bc991961fadccb95bc0546e07be49029fc6d
Stage-1A observer SHA:   9a7033598a30c47faae05868460f61d6b2b7e320
                         (CI green: Python 3.11 + 3.13, 368 tests,
                          digest exact, semantic checker PASS,
                          legacy entry point PASS)
frozen enumerate digest: 3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
measurement code:        src/bjj_game/diagnostics/stamina_adoption_handoff.py
regression test:         tests/test_stamina_adoption_handoff.py
```

The Stage-1B commit adds only the measurement module, its tests, and this document. Gameplay, observer, defaults, and the DoD are unchanged from the Stage-1A observer SHA.

---

# Stage-1 baseline surfaces

## LOW+BOTH historical baseline (primary A9 population)

The exact historical recovery-anchor surface (`_candidate_kwargs`, stalling OFF + shadow):

```text
Surface E trusts reads + Bottom RECOVER
matches=100, base_seed=42 (seeds 42..141)
initial_clock=300, interval=5s, starting_axis=1.50
Top PRESSURE / Bottom ESCAPE, commitment MEDIUM
Bottom responder INFORMED, response commitment RECOGNITION, v0.4b Recognition ON
v0.2 setup + v0.3a submissions + v0.4a commitment semantics ON
Rule 1 ON (unfunded responder cost waiver)
Rule 2 ON (supplemental hold settlement)
recovery_initiation_mode=LOW_WHILE_EXHAUSTED
v0.3b stalling OFF, shadow stalling ON
measure_reexhaustion_handoffs=True
```

Cross-checks:

```text
observer clear events=67 == existing recovery-policy collector latch clears=67
gameplay (observer output removed) == historical recovery-candidate cell: True
```

## CURRENT+Rule1-only control

The existing Surface E Rule1-only settlement-attribution cell:

```text
Surface E trusts reads + Bottom RECOVER, matches=100, base_seed=42
Rule 1 ON, Rule 2 OFF
recovery_initiation_mode=CURRENT
v0.3b stalling OFF, no shadow
measure_reexhaustion_handoffs=True
```

Cross-checks:

```text
observer clear events=0 == existing attribution-cell latch clears=0
gameplay (observer output removed) == historical attribution cell: True
```

---

# Stage-1 handoff measurement

Time is integer simulated seconds; 1 tick = 5 s. Censoring follows the frozen A9 rule independently at each horizon.

## LOW+BOTH historical baseline

```text
total clear events=67
total eventual re-exhaustions after a clear=59
clears remaining non-Exhausted through match end=8
time-to-re-exhaustion median/p25/p75=10/10.0/10.0 s
  (percentiles: statistics.quantiles(n=4, method="inclusive"))
```

| h | R(h) re-exhausted within h | survived through h | right-censored | admissible | rapid rate (unrounded) |
|---|---|---|---|---|---|
| 5 s (1 tick) | 0 | 63 | 4 | 63 | 0.0 |
| 10 s (2 ticks) | 59 | 4 | 4 | 63 | 0.9365079365079365 |
| 15 s (3 ticks) | 59 | 0 | 8 | 59 | 1.0 |
| 20 s (4 ticks) | 59 | 0 | 8 | 59 | 1.0 |

## CURRENT+Rule1-only control

```text
total clear events=0
rate=N/A
usable denominator=0
reason=no clear events
```

| h | R(h) | survived | censored | admissible | rate |
|---|---|---|---|---|---|
| 5 s | 0 | 0 | 0 | 0 | N/A (no clear events) |
| 10 s | 0 | 0 | 0 | 0 | N/A (no clear events) |
| 15 s | 0 | 0 | 0 | 0 | N/A (no clear events) |
| 20 s | 0 | 0 | 0 | 0 | N/A (no clear events) |

---

# A9 — frozen values (mechanical application)

```text
R(5)=0
R(10)=59
R(15)=59
R(20)=59
T=R(20)=59
0.80*T=47.2

N = smallest h in {5,10,15,20}s with R(h) >= 0.80*T
  R(5)=0 < 47.2; R(10)=59 >= 47.2
N=10 s (2 ticks)

baseline admissible clears at N=63
baseline censored clears at N=4
baseline R(N)=59
p_baseline=59/63=0.9365079365079365 (unrounded)

X = 95% Wilson score upper bound, z=1.96, no continuity correction
X=0.975034786099515 (unrounded; authoritative)
X display=0.98 (rounded upward to 0.01; display only)

M=43 admissible clears (frozen independently)
```

Baseline STOP conditions:

```text
T=59 < 10?                                   no
no h reaches 0.80*T?                         no (N=10)
baseline admissible clears at N=63 < 43?     no
STOP: none — all baseline conditions satisfied
```

Frozen A9 candidate rule (margin / statistical rule, unchanged from the DoD):

```text
p_candidate = candidate re-exhaustions within N=10s
              / candidate admissible clears at N=10s   (unrounded)

A9 PASS iff
  candidate admissible clears >= 43
  AND unrounded p_candidate <= 0.975034786099515 (inclusive)

EXT-100 (seeds 142..241) runs iff original-100 candidate admissible
clears at N=10s < 43; pooled for A9 only; no second extension;
pooled admissible < 43 -> A9 UNSCOREABLE, Gate C OPEN, post-hoc DoD.
```

## LOW+BOTH match-level sensitivity (advisory, non-gating)

```text
episode level:
  admissible clears=63
  R(N)=59
  p_episode=0.9365079365079365

match level:
  matches with >=1 admissible clear=61
  matches with >=1 rapid re-exhaustion=58
  p_match=0.9508196721311475

gap=|p_episode - p_match|=0.014311735623210975
```

The baseline gap is not above 0.05, so no baseline clustering explanation is mandated. The candidate-side gap and the ordering-flip check can only be evaluated after the Stage-2 run.

## CURRENT+Rule1-only control A9

```text
rate=N/A, usable denominator=0, reason=no clear events
```

The control cannot define a percentage of clear events that re-exhaust. As the DoD anticipated, the production-settlement control still has no clears without LOW.

---

# Stage-1 observation for review (does not alter any rule)

The frozen procedure gives a **lenient** A9 threshold because the historical LOW+BOTH handoff itself oscillates:

```text
59 of 63 admissible clears re-exhaust within 10 s
every observed re-exhaustion happens at exactly 10 s after the clear
(median = p25 = p75 = 10 s; R(5)=0, R(10)=R(20)=59)
```

So `X=0.975034786099515` only fails a Rule1-only + LOW candidate that oscillates more than this baseline does, at a rapid rate above about 97.5% of admissible clears. A9 still guards against regressions from the baseline. It does not show that the LOW -> MEDIUM handoff is stable in absolute terms.

This observation is recorded for the user's Stage-2 authorization decision only. Under the change-control rules:

- `N`, `X`, `M`, and the margin rule above are frozen and are not edited here.
- Any stricter absolute stability criterion would need a new DoD commit labeled **post-hoc**. It could not be presented as part of this preregistration.

---

# Copied preregistration A1-A10

The block below is copied unchanged from the frozen DoD, from `# Adoption-run pre-registration` through the end of `## A10`. A9 is completed only by the frozen-values section above. A regression test asserts that this block is byte-identical to the DoD.

<!-- BEGIN VERBATIM DoD A1-A10 -->
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

**Status: adoption-gate criterion after Stage-1 preregistration.**

A9 is still scored `CONFIRMED / PARTIAL / NOT CONFIRMED` as a prediction, but it also supplies a mandatory Gate-C criterion once its numeric threshold is frozen.

A candidate can therefore:

```text
have >0 latch clears
yet still fail adoption
because the LOW -> MEDIUM handoff re-exhausts too rapidly
```

Definitions:

```text
clear event:
Bottom Exhausted latch transitions Exhausted -> non-Exhausted

re-exhaustion:
the same Bottom subsequently transitions non-Exhausted -> Exhausted

time-to-re-exhaustion:
simulated seconds from that clear timestamp to its next re-exhaustion
```

Each clear event is treated as a separate handoff episode.

If a later re-exhaustion is followed by another clear, that later clear begins a new episode.

## Right-censoring rule

The final A9 horizon is `N` ticks, frozen later in the preregistration document.

For a clear event:

### Observed rapid re-exhaustion

If Bottom re-enters Exhausted within `N` ticks before the match ends:

```text
count as re-exhausted-within-N
```

This event is fully observed even if fewer than `N` ticks remain after the clear, because the re-exhaustion itself was seen.

### Observed survival through N

If Bottom remains non-Exhausted for at least the complete `N`-tick horizon:

```text
count as survived-through-N
```

### Right-censored clear

If the match terminates before the full `N`-tick horizon and no re-exhaustion was observed:

```text
count as right-censored
exclude from the within-N rate denominator
report separately
```

A right-censored event must **never** be counted as a successful non-re-exhaustion merely because the match ended.

The within-N denominator is therefore:

```text
re-exhausted-within-N
+
survived-through-N
```

and explicitly excludes:

```text
right-censored-without-observed-re-exhaustion
```

For every surface report:

- total clear events;
- re-exhausted-within-N;
- survived-through-N;
- right-censored;
- usable uncensored denominator;
- rapid re-exhaustion rate;
- total eventual re-exhaustions after a clear;
- median time-to-re-exhaustion;
- p25/p75 when defined;
- clears remaining non-Exhausted through match end.

## Stage-1 horizon sweep

Before choosing `N`, the historical LOW+BOTH baseline must report cumulative re-exhaustion within:

```text
1 tick  = 5 s
2 ticks = 10 s
3 ticks = 15 s
4 ticks = 20 s
```

For each horizon, apply the same censoring rule independently.

CURRENT+Rule1-only must also be reported as a control.

If it again produces zero clear events, report:

```text
rate=N/A
usable denominator=0
reason=no clear events
```

Do not fabricate a 0% rate from an empty denominator.

The historical LOW+BOTH clear population is the primary handoff baseline because it previously produced:

```text
67 clears
```

## Numbers deliberately deferred to preregistration

This DoD freezes the **measurement semantics and gate status now**.

It deliberately does **not** freeze the following values yet:

```text
N = rapid-re-exhaustion horizon

X = maximum acceptable rapid re-exhaustion threshold

minimum usable uncensored clear-event count

margin / uncertainty rule used to judge X
```

Those four numeric decisions must be based only on the historical Stage-1 baseline, then committed in:

```text
docs/STAMINA_PRODUCTION_POLICY_ADOPTION_PREREGISTRATION.md
```

before any Rule1-only + LOW candidate run.

The preregistration document must mechanically apply the frozen A9 selection procedure above and state:

- `R(5)`, `R(10)`, `R(15)`, `R(20)`;
- `T=R(20)`;
- the mechanically selected `N`;
- baseline admissible count at `N`;
- baseline censored count at `N`;
- unrounded baseline `p`;
- unrounded Wilson `X` using z=1.96 and no continuity correction;
- display-only X rounded upward to 0.01;
- frozen `M=43`;
- whether all baseline STOP conditions are satisfied;
- the LOW+BOTH match-level sensitivity report;
- the Rule1-only CURRENT control or N/A if it has zero clear events.

There is no remaining analyst discretion to choose `N`, `X`, `M`, or a margin after seeing the Stage-1 data. The Stage-1 data are inputs to the formulas frozen in this DoD.

Then:

```text
HARD STOP
-> user review
-> explicit second authorization
-> only then run Rule1-only + LOW
```

No A9 number may be selected or changed after seeing production-candidate data.

## A9 selection procedure — frozen before baseline

Population:

```text
historical LOW+BOTH baseline
100 original seeds
```

Censoring uses the already-frozen A9 rule:

- observed re-exhaustions always count;
- clears with insufficient follow-up and no observed event are excluded from that horizon's denominator;
- censored clears are reported separately.

Define for each horizon:

```text
h in {5, 10, 15, 20} seconds

R(h) =
number of observed re-exhaustions within h

T = R(20)
```

### Select N

```text
N =
smallest h in {5,10,15,20}s
such that R(h) >= 0.80 * T
```

Selection uses the observed-event counts `R(h)`, not the censored denominators.

### Baseline rate

At selected `N`:

```text
p_baseline =
re-exhaustions within N
/
baseline admissible clears at N
```

Compute this value unrounded.

### X — fixed Wilson procedure

```text
X =
upper bound of the 95% Wilson score interval
for baseline p at N

z = 1.96
no continuity correction
```

For `k` rapid re-exhaustions among `n` admissible baseline clears:

```text
phat = k / n

center =
(phat + z^2/(2n)) / (1 + z^2/n)

half =
[z / (1 + z^2/n)]
* sqrt(phat*(1-phat)/n + z^2/(4n^2))

X = center + half
```

All calculation and candidate comparison use **unrounded X**.

For display only:

```text
reported X =
X rounded upward to the next 0.01
```

Display rounding must never alter the verdict.

### M — minimum admissible sample size

Frozen independently from the Wilson calculation:

```text
M = 43 admissible clears
```

Derivation:

```text
worst-case normal-approximation 95% half-width <= 0.15

1.96 * sqrt(0.25 / n) <= 0.15

n >= 42.684...
-> M = 43
```

This normal-approximation derivation is only the fixed adequacy rule for `M`; it is not the interval used to compute `X`.

### Baseline STOP conditions

STOP before candidate execution, with no substitute rule, if any are true:

```text
T = R(20) < 10
(includes T=0)

no h in {5,10,15,20}s satisfies R(h) >= 0.80*T

baseline admissible clears at selected N < 43
```

On STOP:

```text
do not invent another N
do not invent another X
do not weaken M
do not run the Rule1-only + LOW adoption candidate
new DoD commit required and labeled post-hoc
```

### Candidate A9 verdict

Using the same frozen `N`:

```text
p_candidate =
candidate re-exhaustions within N
/
candidate admissible clears at N
```

Compute unrounded.

PASS requires:

```text
usable candidate admissible clears >= 43

and

unrounded p_candidate <= unrounded X
```

The boundary is inclusive.

If the candidate has fewer than 43 admissible clears after the permitted extension procedure below:

```text
A9 = UNSCOREABLE
Gate C = OPEN
post-hoc DoD required
```

### Statistical limitation

This is deliberately a guard against obvious oscillation regressions, not a formal equivalence or non-inferiority test.

The gate compares:

```text
candidate point estimate
vs
baseline Wilson upper bound
```

It does not include candidate-side uncertainty in the PASS comparison.

---

# A9 candidate extension — frozen before Stage 1

The extension exists only to make A9 scoreable when the original candidate batch has too few admissible clear episodes.

The frozen seed set is the `EXT-100` list and SHA-256 already defined in the Stage-1 inertness section.

## Trigger — sample adequacy only

Run EXT-100 **if and only if**:

```text
original-100 Rule1-only + LOW candidate
admissible clears at frozen N < 43
```

The trigger must never depend on:

- candidate `p`;
- whether candidate `p` is above or below `X`;
- A2;
- whether A9 appears likely to pass;
- any exit/outcome result;
- any other favorable or unfavorable measurement.

Because `N` is already frozen from Stage 1, the adequacy trigger is mechanically defined before candidate execution.

## Execution

If triggered:

```text
run exactly one 100-seed EXT-100 batch
using the same code commit
and the same frozen enumerate digest
as the original candidate run
```

No second extension is allowed.

## A9 scoring only

If original-100 admissible clears at `N` are at least 43:

```text
score A9 on original 100 only
do not run EXT-100
```

If extension is triggered:

```text
pool original-100 + EXT-100 admissible clear episodes
recompute:
- admissible clears
- R(N)
- p_candidate
```

Then:

```text
PASS =
pooled admissible clears >=43
AND
pooled unrounded p_candidate <= unrounded X
```

If pooled admissible clears remain below 43:

```text
A9 = UNSCOREABLE
Gate C = OPEN
post-hoc DoD required
```

## Isolation

EXT-100 is an A9 sample-adequacy contingency only.

The following remain scored exclusively on the original 100 candidate seeds:

```text
A1
A2
A3
A4
A5
A6
A7
A8
A10
all non-A9 adoption gates and outcome summaries
```

In particular, the A2 floor of 34 total clears cannot be rescued or altered by EXT-100.

---

# A9 match-level sensitivity — advisory, non-gating

This report exists because multiple clear episodes can come from the same match, while the authoritative Wilson procedure treats clear episodes as the gating observations.

Population:

- same selected `N`;
- same admissible clear episodes used by the authoritative A9 calculation;
- LOW+BOTH baseline always uses its baseline population;
- if EXT-100 is triggered for the candidate, the pooled original+EXT population is used for candidate sensitivity.

A match whose only clear episodes are right-censored at `N` is excluded from the match-level denominator, matching the episode-level admissibility rule.

For each match with at least one admissible clear at `N`:

```text
match_reexhausted = true
if ANY admissible clear in that match
re-exhausts within N
```

For baseline and candidate report:

```text
episode-level:
  admissible clears
  R(N)
  p_episode

match-level:
  matches with >=1 admissible clear
  matches with >=1 rapid re-exhaustion
  p_match

gap:
  abs(p_episode - p_match)
```

All rates and comparisons below use unrounded values.

## Mandatory explanation trigger

A written clustering explanation is required if **either** condition holds in either baseline or candidate:

```text
abs(p_episode - p_match) > 0.05
```

or if the candidate-vs-baseline ordering flips between levels.

Ordering flip is defined exactly as:

```text
sign(p_candidate - p_baseline) at episode level
differs from
sign(p_candidate - p_baseline) at match level

using strict inequalities

equality at either level is NOT a flip
```

The ordering comparison uses unrounded values.

The explanation must describe the clustering pattern and why the episode-level and match-level views differ.

It may not change any preregistered rule or verdict.

## Advisory only

`p_match`:

- cannot PASS or FAIL A9;
- cannot alter `X`;
- cannot alter `N`;
- cannot trigger EXT-100;
- cannot change Gate C;
- cannot rescue a failed/UNSCOREABLE A9;
- cannot authorize retuning.

The episode-level Wilson procedure remains authoritative.

---

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
<!-- END VERBATIM DoD A1-A10 -->

---

# HARD STOP

Stage 1 is complete. Do not:

- run the Rule1-only + LOW production candidate;
- run EXT-100;
- add a canonical production configuration;
- change any default;
- edit any frozen A9 value, A1-A10 range, or gate;

until the user reviews this exact preregistration commit and explicitly authorizes Stage 2.
