# Mount v0.4a — Feint Intent / Funding-Downgrade Amendment

## Status

PROPOSED — DESIGN ONLY.

This amendment is intentionally committed before mechanics implementation.

Implementation is **not authorized** by this document. After this amendment is committed, stop for review. Mechanics may change only after explicit current authorization.

## 1. Scope

This amendment resolves one v0.4a blocker only:

> Does a funding downgrade to effective LOW / UNFUNDED mean the initiator intended to feint?

Decision: **no**.

Requested commitment expresses continuation intent for the feint rule. Effective commitment expresses what the competitor can actually fund and remains authoritative for grade magnitude, affordability, cost, response comparison, and other effective-level mechanics.

No other v0.4a design criterion changes unless this document explicitly supersedes it.

## 2. Pre-amendment reference point

Reviewed PR:

```text
PR #5
branch: review/v04a-commitment-semantics
pre-amendment head: 59f24de09bc7b025e1d3e195595628fa2f199567
```

Frozen Mount-v0 enumeration digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

The matchup matrix is not changed by this amendment.

## 3. Evidence that triggered the amendment

Repository-recorded historical/random evidence at the pre-amendment head includes:

```text
v0.3a-style random:
  Tap=99/100
  Bottom median final stamina=12.5

v0.4a random response + RANDOM response commitment:
  Tap=25/100
  Bottom median final stamina=0.0
```

Additional review measurement, not yet owned by the checker at the pre-amendment head:

```text
v0.4a random response, both sides request fixed MEDIUM:
  Tap=15/100
  Reached Finish=42/100
  Top median final stamina=0
  Bottom median final stamina=0

successful active submission-stage exchanges blocked by the feint cap:
  1009
```

The exact `15/100`, `42/100`, and `1009` values must be remeasured by the branch checker/diagnostic surface after implementation. They are recorded here as the review evidence that caused the design question; they are not post-hoc tuning targets.

## 4. Pre-amendment mechanism

At the pre-amendment head the engine does:

```text
requested commitment
-> affordability
-> effective commitment
-> current-exchange grade transform

effective LOW / UNFUNDED
-> active-submission feint cap
```

Therefore this path is possible:

```text
requested MEDIUM
-> insufficient stamina
-> effective LOW or UNFUNDED
-> successful active submission exchange
-> feint cap
-> no stage advancement
```

The feint predicate currently cannot distinguish an intentional LOW request from a MEDIUM/HIGH request that was downgraded by funding.

That semantic collision is the only mechanic addressed by this amendment.

## 5. Supersession of the blanket effective-commitment rule

The original Definition of Done says:

> All tactical commitment effects use effective commitment, never merely requested commitment.

This amendment supersedes that sentence narrowly.

New rule:

```text
requested commitment:
  authoritative for feint intent

effective commitment:
  authoritative for funded tactical magnitude and funded tactical credit
```

Requested commitment remains intent/history/UI/funding-gap information, but **feint intent is now a gameplay use of that intent**.

No other requested-level tactical benefit is introduced.

## 6. Requested versus effective commitment

### Requested commitment controls

Requested initiator commitment controls only these v0.4a mechanics:

1. whether an active Americana attempt is intentionally feint-capped;
2. the stalling/progress classification that follows from that feint intent;
3. existing history/UI/diagnostic representation of what was requested.

Feint intent is:

```text
requested LOW
-> feint intent
-> active-stage feint cap applies
```

Continuation intent is:

```text
requested MEDIUM
requested HIGH
-> continuation intent
-> funding downgrade alone does not activate the feint cap
```

### Effective commitment controls

Effective initiator commitment remains authoritative for:

1. initiator commitment magnitude transform;
2. LOW/UNFUNDED compression of extreme grades;
3. HIGH amplification;
4. responder under-commitment comparison;
5. effective stamina cost and actual spend;
6. funding-gap calculation;
7. all existing effective-level commitment diagnostics other than feint-intent classification.

Effective responder commitment remains authoritative for:

1. response under-commitment comparison;
2. response stamina cost/spend;
3. response funding gap;
4. all current response-side commitment credit.

No responder feint rule is introduced.

## 7. Exhaustion and modifier order remain frozen

This amendment does not change the frozen order:

```text
raw / behavior / positional / Ready
-> pre-cost exhaustion
-> initiator effective-commitment magnitude
-> response under-commitment
-> final resolution
-> state transitions
-> costs
```

Exhaustion still occurs before commitment magnitude.

HIGH may still magnify a fatigue-created swing.

No exhaustion threshold, grade rule, or modifier ordering is changed.

## 8. Active Americana semantics after amendment

### Requested LOW

A requested-LOW active submission attempt is a feint even if affordability later produces effective UNFUNDED.

```text
requested LOW
effective LOW or UNFUNDED
successful active-stage result
-> hold current submission stage
-> record requested-LOW feint cap
```

Failure still defends/breaks the track.

Contested still holds the track.

### Requested MEDIUM / HIGH

A MEDIUM/HIGH request expresses intent to continue.

```text
requested MEDIUM/HIGH
effective MEDIUM/HIGH/LOW/UNFUNDED
-> use effective commitment for grade/cost mechanics
-> do not feint-cap solely because funding downgraded the effective level
```

If the final grade is successful, ordinary submission-stage advancement occurs.

If the final grade is Contested, the stage holds.

If the final grade fails, the track defends/breaks as before.

This includes the deliberate edge case:

```text
requested MEDIUM/HIGH
-> effective UNFUNDED
-> effective cost 0
-> UNFUNDED/LOW magnitude semantics
-> if the final grade is nevertheless successful,
   ordinary submission advancement is allowed
```

UNFUNDED therefore means "could not fund LOW", not "intended to feint".

## 9. Ready Americana entry remains unchanged

The active-stage feint cap still does not prohibit creation of the initial Threat.

Requested LOW may still create a real Threat when all existing Ready-entry and final-grade requirements are met.

MEDIUM/HIGH funding downgrade does not add a new Ready-entry privilege; existing Ready and final-grade requirements remain authoritative.

## 10. Stalling interaction

v0.3b's definition of progress remains unchanged:

> progress is a legal attempt through a progress-capable route, not necessarily success.

The feint exception is now classified from requested intent.

```text
requested LOW active-stage attack
-> feint-capped
-> initiator advancement clock is not reset
-> legal defender still receives engagement credit

requested MEDIUM/HIGH active-stage attack
-> not feint-capped merely because effective commitment downgraded
-> normal progress-capable-route treatment
-> legal defender still receives engagement credit
```

No stalling cadence, warning/penalty/reset consequence, timing threshold, or other v0.3b rule changes.

## 11. Gate E is explicitly superseded

The original Gate E wording based on effective LOW/UNFUNDED is superseded by this section.

### Amended Gate E — requested-intent feint cap

PASS requires all of the following:

1. requested LOW Ready Americana can still enter Threat in at least one legal state;
2. requested LOW active Threat cannot advance to Control on a successful exchange;
3. requested LOW active Control cannot advance to Finish on a successful exchange;
4. requested LOW active Finish cannot Tap on a successful exchange;
5. the requested-LOW cap remains true when requested LOW is itself UNFUNDED;
6. requested MEDIUM/HIGH downgraded to effective LOW is **not** feint-capped;
7. requested MEDIUM/HIGH downgraded to effective UNFUNDED is **not** feint-capped;
8. for those MEDIUM/HIGH downgrade probes, a successful final grade produces the ordinary legal stage transition;
9. funding downgrade alone produces zero feint-cap events.

The checker must expose the cause, not only the effective level.

At minimum report:

```text
requested-LOW feint caps
MEDIUM/HIGH funding-downgrade successful active-stage attempts
MEDIUM/HIGH funding-downgrade feint caps
```

PASS requires:

```text
MEDIUM/HIGH funding-downgrade feint caps = 0
```

No tap-rate target is part of Gate E.

## 12. Gate H is explicitly superseded only in its feint predicate

The original stalling invariant remains, but "feint-capped" is determined by requested LOW.

Required isolated probes:

```text
A. requested LOW active-stage feint
   Top clock:    20 -> 20
   Bottom clock: 20 -> 0

B. requested MEDIUM/HIGH,
   funding-downgraded to effective LOW or UNFUNDED,
   legal active-stage attempt
   -> must not be classified as a feint
   -> normal v0.3b progress-capable-route handling applies
```

For a deterministic successful probe B, both engagement clocks are expected to reset under existing v0.3b semantics:

```text
Top clock:    20 -> 0
Bottom clock: 20 -> 0
```

No other Gate H criterion changes.

## 13. Gates that remain unchanged

The amendment does not move or reinterpret these v0.4a criteria:

```text
Gate A — compatibility / MEDIUM identity
Gate B — v0.2 Gate 7 closes
Gate C — no global selectable-level dominance
Gate D — matched commitment preserves fresh Contested stalemates
Gate F — response under-commitment only helps attacker
Gate G — genuine automatic Gate-B expiry
Gate I — responder affordability authority
```

Gate I still requires unaffordable responder commitment to receive only effective-level tactical credit.

The v0.3a Gate-B numerical criterion remains unchanged:

```text
0% < informed Tap rate < 50%
```

This amendment does not tune toward that range.

## 14. Required batch remeasurement

After implementation, re-run the same deterministic 100-seed surfaces and record them before any further design change.

### Historical comparison

Record the unchanged historical v0.3a-style random reference:

```text
Tap count
Reached Finish count, if available on the same measurement surface
Top median final stamina
Bottom median final stamina
```

### v0.4a fixed-MEDIUM diagnostic

Configuration:

```text
100 matches
base seed 42
Top PRESSURE
Bottom ESCAPE
initiator requested commitment MEDIUM
random Bottom response choice
response commitment FIXED_MEDIUM
5:00 clock
starting axis +1.50
5-second interval
100 / 100 stamina
v0.2 setup enabled
v0.3a submissions enabled
v0.4a commitment semantics enabled
```

Record:

```text
Tap count
Reached Finish count
Top median final stamina
Bottom median final stamina
requested-LOW feint caps
MEDIUM/HIGH funding-downgrade successful active-stage attempts
MEDIUM/HIGH funding-downgrade feint caps
```

Because the initiator request is fixed MEDIUM, expected requested-LOW feint caps are zero.

PASS-relevant expectation:

```text
MEDIUM/HIGH funding-downgrade feint caps = 0
```

The resulting Tap count is observational. There is **no** requirement to restore 99/100.

### v0.4a RANDOM response-commitment diagnostic

Keep the existing RANDOM response-commitment comparison.

Its equal LOW/MEDIUM/HIGH selection is a diagnostic distribution only. It is not gameplay policy and not a gate.

Record the same outcome/stamina/cap-cause fields.

Only requested LOW may create feint-cap events.

Tap count remains observational.

## 15. No initiator commitment policy is added

The batch initiator still receives an explicitly supplied commitment.

This amendment does not add a LOW/MEDIUM/HIGH tactical selection policy.

Therefore:

```text
Gate 7 PASS
```

continues to mean commitment has measurable capability across the state space, not that current batch play chooses commitment tactically.

That policy debt remains explicit.

## 16. Observability requirement

The current history records effective-level feint-cap text.

Implementation must make the reason unambiguous enough for the checker to distinguish:

```text
intent cap:
  requested LOW

funding downgrade:
  requested MEDIUM/HIGH
  effective LOW/UNFUNDED
  not capped for that reason
```

The exact internal representation is not frozen. The semantic distinction and checker-visible counts are frozen.

## 17. Out of scope

Do not change as part of this amendment:

- frozen matchup matrix;
- frozen enumeration digest;
- 3 / 7 / 12 commitment costs;
- exhaustion thresholds;
- exhaustion-before-commitment modifier order;
- setup mechanics or setup valuation;
- submission base grades;
- submission failure/Contested semantics;
- responder choice weights;
- RANDOM response-commitment weighting;
- provisional submission-hold LOW=3 cost;
- stalling cadence or consequences;
- v0.3a Gate-B range;
- Recognition/information;
- scoring/ruleset semantics;
- initiator commitment-selection policy.

## 18. Verification after implementation

After explicit authorization to implement, required verification remains:

```text
python -m unittest discover -s tests -v
python -m bjj_game --check
python -m mount_v0 --check
frozen --enumerate SHA-256
```

The frozen digest must remain exactly:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Add regression coverage for the amended requested/effective split and remeasure Gates A-I.

Do not claim "everything passes" if any design gate is OPEN or DEFERRED.

## 19. Change-control checkpoint

Sequence from this document:

```text
evidence
-> amendment committed
-> STOP FOR REVIEW
-> explicit implementation authorization
-> mechanics
-> regression tests
-> checker remeasurement
-> PR review
-> explicit merge authorization
-> squash merge
```

No mechanics implementation is authorized by committing this amendment.
