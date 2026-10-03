# Mount v0.4a — Commitment Semantics Definition of Done

## Status

FROZEN BEFORE MECHANICS IMPLEMENTATION.

This slice starts from reviewed main:

~~~
c09973b4d2e1f0478e58c20ed50cd4d50588ba6f
~~~

Reviewed baseline:

~~~
242 tests PASS
modern semantic checker PASS
legacy checker PASS
frozen enumerate digest:
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
~~~

v0.4a exists to answer one narrow question:

> Can commitment become a real exchange-level tradeoff for both initiator and responder without changing the frozen Mount matchup table, hiding information, or introducing scoring?

This phase is the preferred precursor to Recognition because commitment becomes a meaningful information signal, but Recognition is not implemented here.

## 1. Scope

v0.4a adds:

- tactical meaning for initiator LOW / MEDIUM / HIGH commitment;
- per-exchange response commitment;
- response stamina funding using the existing 3 / 7 / 12 policy;
- an explicit runtime response-commitment capability;
- a LOW-feint submission cap;
- deterministic batch policies for response commitment;
- checker gates for compatibility, Gate-7 closure, dominance, stalemate preservation, feints, under-commitment direction, automatic Gate-B expiry, stalling interaction, and affordability.

v0.4a does not add Recognition, hidden commitment, scoring/rulesets, setup-policy valuation changes, new submissions, new positions, response-weight changes, matchup-table changes, stamina-cost tuning, exhaustion-threshold changes, hold-cost tuning, stalling-cadence changes, behavior-specific commitment bonuses, or technique-specific commitment multipliers.

## 2. Feature flag and compatibility

The engine gains an explicit v0.4a feature flag.

With v0.4a disabled, current main behavior must remain compatible on the existing deterministic surfaces.

With v0.4a enabled and both sides effectively MEDIUM, the current exchange ResolutionResult must match the corresponding pre-v0.4a exchange before future stamina consequences can affect later windows.

Full-match identity is not required under enabled MEDIUM/MEDIUM because the responder now legitimately spends stamina.

The frozen 18-entry raw Mount matchup matrix and enumerate digest remain unchanged.

## 3. Existing stamina funding remains authoritative

The existing cost policy remains:

~~~
LOW     3
MEDIUM  7
HIGH   12
~~~

For both initiator and responder:

~~~
requested commitment
-> highest fully payable requested-or-lower commitment
-> UNFUNDED if LOW cannot be paid
~~~

All tactical commitment effects use effective commitment, never merely requested commitment.

Requested commitment remains intent/history/UI/funding-gap information.

## 4. UNFUNDED semantics

UNFUNDED is an effective state below LOW:

~~~
UNFUNDED < LOW < MEDIUM < HIGH
~~~

UNFUNDED initiator commitment receives no MEDIUM/HIGH benefit, uses the same magnitude ceiling/compression as LOW, and is subject to the same submission feint cap as LOW.

UNFUNDED responder commitment receives no selectable-level commitment credit, counts as under-committed against any funded initiator commitment, and costs zero response-commitment stamina.

Existing exhaustion rules still apply independently.

## 5. Modifier order

The current-exchange order is frozen as:

~~~
1. raw matchup grade
2. behavior modifier
3. positional modifier
4. Ready override, where applicable
5. exhaustion modifier using PRE-COST stamina bands
6. initiator effective-commitment magnitude transform
7. response under-commitment modifier
8. Grade clamp
9. existing axis / clamp / Exit Map resolution
10. apply current-exchange state transitions
11. charge initiator effective commitment
12. charge responder effective commitment
13. charge existing provisional submission-hold LOW=3 cost, if applicable
~~~

Implementation may compute affordability before final resolution, but current-exchange exhaustion uses pre-cost stamina bands. Responder commitment cost and provisional hold cost are logged separately.

## 6. Initiator commitment magnitude

MEDIUM is identity.

HIGH amplifies ordinary non-Contested outcomes away from Contested:

~~~
Failure -> Strong Failure
Success -> Strong Success
~~~

Already-extreme grades and Contested remain unchanged.

LOW compresses extreme outcomes toward ordinary outcomes:

~~~
Strong Failure -> Failure
Strong Success -> Success
~~~

Failure, Contested, and Success remain unchanged.

UNFUNDED uses the LOW magnitude transform.

Thus HIGH can improve a winning exchange or worsen a losing exchange. Commitment is not pure upside.

## 7. Response commitment

A responder chooses LOW / MEDIUM / HIGH on the same exchange and uses the same 3 / 7 / 12 affordability policy.

After the initiator magnitude transform:

~~~
if responder effective commitment < initiator effective commitment
then initiator final grade +1
~~~

Only one +1 step is applied regardless of gap size.

Equal or greater response commitment gives no mismatch modifier. Defensive over-commitment has no free grade bonus; its cost is the tradeoff.

## 8. Contested and stalemate semantics

The initiator magnitude transform alone never changes Contested.

Therefore Contested remains Contested when the responder is at least as committed as the initiator.

An under-committed responder may explicitly turn Contested into Success through the +1 mismatch rule.

Existing v0.3a fresh informed stalemates must remain Contested when the defender matches or exceeds the attacker's effective commitment.

## 9. Feints

The frozen v9 rule is authoritative:

> a low-commitment feint cannot advance beyond THREAT.

LOW and UNFUNDED are feint-capped.

A LOW/UNFUNDED Ready Americana may still create a real Threat when all existing entry and final-grade requirements are met.

Once the Americana track is active, LOW/UNFUNDED may not produce Threat -> Control, Control -> Finish, or Finish -> Tap.

A successful but feint-capped active-stage exchange leaves the current stage unchanged. Failure still defends/breaks the track; Contested still holds it.

## 10. Feints and stalling

At an active submission stage, a LOW/UNFUNDED feint-capped attack cannot advance and therefore does not reset the initiator's advancement clock as progress engagement.

The responder's legal defense still counts as defensive engagement; being required to answer a real threat must not make the defender look idle.

No v0.3b cadence, consequence, Gate-A threshold, or Gate-F invariant changes.

## 11. Public commitment

Commitment is public in v0.4a. Recognition is absent.

The competent informed responder may therefore select commitment with knowledge of the initiator's effective commitment.

Hiding or imperfectly recognizing commitment belongs to a later Recognition phase.

## 12. Batch response-commitment policies

v0.4a adds deterministic response-commitment modes:

FIXED_MEDIUM — always request MEDIUM; used for compatibility.

MATCH — request the initiator's effective commitment when funded; if initiator is UNFUNDED, request LOW. Used for competent/informed Gate-B defense.

RANDOM — choose LOW / MEDIUM / HIGH from a deterministic per-match RNG independent of the existing response-choice RNG.

No initiator commitment-selection AI is added in v0.4a. Existing batch initiator commitment remains an explicit supplied value. SETUP-POLICY DEBT is therefore not modified.

## 13. Gate A — compatibility / MEDIUM identity

PASS requires:

1. v0.4a disabled preserves existing current-exchange results;
2. enabled MEDIUM/MEDIUM produces the same current ResolutionResult as the corresponding pre-v0.4a exchange across the exhaustive measurement surface;
3. the frozen enumerate digest remains exactly 3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2.

Response stamina differences after the exchange are excluded from immediate-result identity.

## 14. Gate B — v0.2 Gate 7 closes

The existing Gate-7 concept remains authoritative: a higher commitment must create a better current outcome somewhere so LOW no longer strictly dominates merely because it is cheaper.

PASS requires:

~~~
v0.2 Gate 7 PASS
higher-commitment advantage states > 0
~~~

No threshold is invented or moved.

## 15. Gate C — no global selectable-level dominance

Commitment X globally dominates Y only if:

1. cost(X) <= cost(Y);
2. X is no worse than Y on every measured fully-funded state for final grade, terminal exit attainment, and realized initiator-favorable axis movement;
3. X is strictly cheaper or strictly better in at least one measured state.

PASS requires no LOW/MEDIUM/HIGH level globally dominates another. Report pairwise evidence.

UNFUNDED is not selectable and is excluded from this pairwise gate.

## 16. Gate D — matched commitment preserves stalemates

Across every measured fresh Contested state:

~~~
responder effective commitment >= initiator effective commitment
-> final grade remains Contested
~~~

At minimum this includes every reachable fresh Americana Threat / Control / Finish informed-defense state.

PASS requires zero matched-or-overcommitted stalemate breaks.

## 17. Gate E — feint cap

PASS requires:

1. LOW Ready Americana can still enter Threat in at least one legal state;
2. LOW/UNFUNDED active Threat cannot advance to Control;
3. LOW/UNFUNDED Control cannot advance to Finish;
4. LOW/UNFUNDED Finish cannot Tap;
5. MEDIUM/HIGH remain capable of ordinary legal stage advancement where the existing final grade allows it.

## 18. Gate F — under-commitment only helps the attacker

For otherwise-identical fully-funded exchanges, compare lower response commitment with matched response commitment.

PASS requires zero states where under-commitment worsens initiator final grade, loses a terminal exit obtained by the matched case, or produces worse initiator-favorable realized axis movement; and at least one state must strictly improve for the initiator.

## 19. Gate G — genuine automatic Gate-B expiry

The static response-catalog attribute scan is superseded by a real runtime capability.

Required regression:

~~~
v0.4a disabled -> response commitment capability False
v0.4a enabled  -> response commitment capability True
~~~

When capability is reported present, the v0.3a Gate-B competent-defender batch must actually run with v0.4a response commitment enabled and MATCH commitment.

The self-expiring status rule remains:

~~~
neither response commitment nor Recognition -> DEFERRED
either capability exists -> evaluate unchanged Gate-B range
~~~

The unchanged range is:

~~~
0% < informed Tap rate < 50%
~~~

v0.4a does not tune toward that range.

## 20. Gate H — feints cannot dodge stalling

At an active Americana stage:

~~~
LOW/UNFUNDED feint-capped attack
-> initiator advancement clock is not reset

legal defender response
-> defender advancement clock is reset
~~~

PASS requires both in isolated deterministic probes.

## 21. Gate I — affordability authority

Response commitment obeys the existing funding rule.

Examples:

~~~
request HIGH with 5 stamina
-> effective LOW
-> charge 3
-> tactical comparison uses LOW

request HIGH with 2 stamina
-> UNFUNDED
-> charge 0
-> tactical comparison uses UNFUNDED
~~~

A defender gets no tactical credit from an unaffordable requested level.

Current-exchange exhaustion uses the pre-cost responder band; response commitment cost affects future state only.

## 22. Provisional submission-hold cost

The existing provisional hold cost remains LOW=3 when its current conditions trigger.

With v0.4a enabled, response commitment cost and hold cost may both be charged on one exchange. Keep and log them separately. Do not tune either from this overlap during v0.4a.

## 23. Gate-B batch configuration after expiry

Competent-defender batch:

~~~
100 matches
base seed 42
Top PRESSURE
Bottom ESCAPE
initiator commitment MEDIUM
response commitment mode MATCH
5:00 clock
starting axis +1.50
5-second interval
100 / 100 stamina
escape-first / submission-aware initiator policy
informed Bottom response choice
v0.2 setup enabled
v0.3a submissions enabled
v0.3b stalling disabled
v0.4a commitment semantics enabled
~~~

Random contrast is the same except random response choice and RANDOM response commitment.

The RANDOM commitment RNG is independent from response-choice RNG.

## 24. Predictions frozen before results

Predictions are observations, not tuning targets:

1. v0.2 Gate 7 becomes PASS.
2. v0.3a Gate B leaves DEFERRED.
3. With public commitment and MATCH defense, v0.3a Gate B is expected to become OPEN with informed Tap still near 0 because matched commitment alone does not solve mutual-exhaustion cancellation.
4. RANDOM response commitment should create more attacker-favorable exchanges than MATCH because some responses under-commit.
5. Bottom stamina should deplete faster in v0.4a Gate-B batches because responses now have direct commitment cost.
6. Response-cost + provisional hold-cost overlap should increase responder stamina pressure and must be reported rather than tuned away.
7. SETUP-POLICY DEBT remains visible and unresolved.

There is no prediction that setup builders switch to LOW because this phase adds no initiator commitment-selection policy.

## 25. Risks

Response + hold double cost: measure, do not silently delete either charge.

Public perfect matching: Gate B may move DEFERRED -> OPEN at 0 taps. That is acceptable evidence for Recognition.

Exit distribution shifts: measure HIGH/under-commitment effects; do not tune the raw matrix.

UNFUNDED edges: requested levels must not leak tactical benefit after downgrade.

Stalling: feints must not become fake progress engagement.

## 26. SETUP-POLICY DEBT and scoring

SETUP-POLICY DEBT is not solved here. It does not strictly require scoring to be studied, but scoring will eventually provide a stronger ruleset objective.

Ruleset/scoring remains separate work.

## 27. Verification discipline

Before review:

~~~
python -m unittest discover -s tests -v
python -m bjj_game --check
python -m mount_v0 --check
frozen --enumerate SHA-256
~~~

must pass on both supported CI versions.

The checker must expose v0.4a Gates A-I plus resulting v0.2 Gate 7 and v0.3a Gate B statuses.

Failed intermediate measurements that influence design must remain committed.

## 28. Change control

If a gate fails:

1. record the failure;
2. do not move criteria after seeing the result;
3. do not retune 3 / 7 / 12 to make a gate pass;
4. do not modify the frozen matchup matrix;
5. do not change response weights;
6. do not alter exhaustion thresholds;
7. do not alter the provisional hold cost without a separate amendment;
8. return to design review before changing the frozen rule.

Implementation starts only from this committed DoD.
