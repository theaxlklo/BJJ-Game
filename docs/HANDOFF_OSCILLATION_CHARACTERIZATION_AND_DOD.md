# D1 handoff characterization and proposed frozen experiment DoD

Status: measurement-only D1; no fix authorized. This document freezes the proposed
D2 acceptance criteria at its committing SHA, before any candidate measurement.
User review must select and authorize an exact mechanic. Changes to these
criteria require a separate reviewed preregistration before candidate measurement.
No D2 candidate has been implemented or measured.

## Evidence lineage and scope

Canonical adopted checkpoint: `ee6cb6fcebb105e31224bead48a302811b27b59a`.
Production entry point: `src/bjj_game/interfaces/production_policy.py`.
Rule 1 ON, Rule 2 OFF, Bottom RECOVER initiation LOW while Exhausted and
baseline MEDIUM afterward. All raw defaults remain unchanged and opt-in.

Historical A9 baseline was highly oscillatory: 59/63 within 10 s. The adopted
candidate was also oscillatory: 64/69 = 0.927536231884058, match sensitivity
63/68. A9 validly passed its **relative** gate, X=0.975034786099515; it never
established absolute stability. Original candidate sample had only 37 admissible
clears; exactly one EXT-100 batch supplied the pooled 69. Gate G initially
remained OPEN because literal dictionaries were compared; that failure and the
instrumentation-only effective-settings correction remain in historical docs.
All adoption Gates A–H passed. Adoption does not discharge these debts.
Old Rule2-only collapsed public MATCH Threat from 78/100 to 0/100; it remains
OFF and deferred. Adopted E-PROD had 179 double-charge conditions. This slice
neither fixes nor remeasures that settlement debt.

D1 reproduces the two previously used batches, 100 matches each, base seeds 42
and 142 (individual responder seeds 42–241), 300 s, E-PROD OFF+shadow settings,
through the canonical policy. These are characterization of the adopted policy,
not measurements of a fix. No extra seed selection or outcome filtering.

Reproduce: `PYTHONPATH=src python -m bjj_game.diagnostics.handoff_characterization`,
then `PYTHONPATH=src python -m bjj_game.diagnostics.handoff_distributions`.
Ordered per-episode evidence: [compressed JSON trace](evidence/handoff_d1_trace.json.gz).
Read with `gzip -dc docs/evidence/handoff_d1_trace.json.gz`. The decompressed
JSON SHA-256 is `02d4574fd49e31496b15543897ea0b20894e35e6d7f16e350c1e831d5bc9361b`.
Distribution tables: [D1 distributions](HANDOFF_OSCILLATION_D1_DISTRIBUTIONS.md).
The diagnostic patches are scoped to that call, delegate each method once,
consume no RNG, and restore on exceptions. No engine, batch, domain, or canonical
policy code is modified. The tool is standalone and not safe for concurrent
in-process gameplay. Exact full BatchSummary identity, ordered trace replay,
ledger conservation and exception cleanup are tested.

## Root cause

`StaminaPool` already has hysteresis: enter <=25, clear >=35 for maximum 100.
`recover_up_to` does **not** clamp at 35: it adds the requested recovery subject
only to maximum capacity, then refreshes the latch. All 83 observed clears are
33 + 2 = 35 during a 5 s CONSERVE interval. This is a structural consequence
of this measured cadence and reachable stamina residues, not a universal promise
of the recovery primitive: other before-values, durations, remainders or pool
maxima can overshoot the threshold.

`AdaptiveBehaviorPolicy.choose` keys CONSERVE directly to the Exhausted latch.
The batch explicitly chooses behavior again after advance and before resolution.
At clear it therefore switches immediately to ESCAPE, and selects baseline
MEDIUM instead of exhausted LOW. Every non-timeout clear has a funded MEDIUM
Bottom action at the **same timestamp**, costing 7, with no intervening recovery
opportunity. At +5 and +10 s ESCAPE drains 1 each. Top's intervening attempt is
unfunded: Rule 1 waives the responder cost; there is no positive Bottom response
or provisional hold spend in any observed post-clear window.

For all 64 re-entries the ledger is exactly:

| Offset | Event | Stamina |
|---|---|---:|
| 0 | CONSERVE recovery clears latch (33 + 2) | 35 |
| 0 | MEDIUM Bottom initiation (-7) | 28 |
| 5 | ESCAPE behavior (-1); Top response charge 0 | 27 |
| 10 | ESCAPE behavior (-1) | 26 |
| 10 | MEDIUM Bottom initiation (-7), re-enters latch | 19 |

Thus MEDIUM is a direct component of the budget violation, not just correlation;
the first MEDIUM alone does not re-enter. Two MEDIUM spends plus behavior drain
exceed the ten-point hysteresis reserve. Arithmetic substitution of LOW costs
would leave 27 after two spends and the same drain; this is a local ledger
counterfactual, **not** a simulated candidate or proof of longer stability.
At the next interval after re-entry RECOVER chooses CONSERVE again and LOW
initiation resumes. Recovery stops as a policy decision at clear, not inside
the primitive. First-spend delay is 0 for all 72 non-timeout clears; 11 clears
occur at timeout and have no subsequent action (censored, never stable successes).

Re-entry actions: Elbow-Knee 26, Bridge 25, Trap-and-Roll 13. The first action
is Bridge in 51 episodes, Trap-and-Roll in 17, Elbow-Knee in 4, timeout in 11.
All 72 first initiations request and effectively fund MEDIUM. Their Top
responders request MEDIUM/LOW/HIGH in 41/20/11 cases, respectively, and
effective responder commitment is unfunded in every case. Of the 19 episodes
without re-entry, 11 clear at timeout, 3 escape to Half Guard immediately at
clear after spending 7, and 5 reach timeout at +10 after spending 9. Thus all
five measured 10 s survivors end at that horizon; no episode demonstrates
continued non-Exhausted play beyond it. These terminal cases remain censored
at longer horizons, not evidence of stable handoff.

Setup building is common but no single action family uniquely causes re-entry;
the common cost and behavior policy do. The trace records requested/effective
initiator and responder commitments, Recognition reads, grades, setup tiers,
submission stage changes, actual/waived charges and each ordered mutation.

## Isolation assessment

The observed handoff failure requires no response+hold liability: all positive
post-clear spends here are Bottom initiation and behavior. Therefore D2 can be
isolated with Rule 2 OFF and Rule 1 unchanged. This establishes independence of
the measured causal path, not universal absence of coupling. A fix can alter
match trajectories, setup and submission opportunities, changing later exposure
to the live double-charge debt. Keep settlement identical and report those
exposures descriptively; defer their repair to R1. No Rule 2 replacement work
has begun.

## Candidate families (proposals only)

All families use integer deterministic comparisons at existing decision windows;
none require randomness or altered time steps. Costs, affordability, response
commitment selection and hold settlement remain as adopted. Any affected
Recognition read must reflect the actually selected request.

| Family and exact proposed semantics | State / visibility | Expected effect and risks / interactions |
|---|---|---|
| Raise latch clear threshold to 60/100, preserve entry 25 | Existing latch only; visible Exhausted duration changes | Gives 35-point reserve. Global pool change also affects Top and exhausted responder grade semantics; longer exhaustion, setup grades and Threat reachability can change. Too broad for first isolated experiment. |
| Bottom RECOVER reserve policy: enter recovery mode when Exhausted, retain CONSERVE + LOW through clear until reserve >=60, then baseline ESCAPE + MEDIUM before resolution | One explicit per-Bottom recovery-mode boolean; latch and recovery state separated. Must expose recovery state to players; no hidden timer | Targets the actual budget discontinuity, preserves Top and latch/responder grade rules. LOW remains a feint under v0.4a, changes setup and progression opportunities, may delay clears/escapes. CONSERVE changes drift; may increase RESET routes or stalling exposure. Request choice changes Recognition but not its algorithm. |
| Post-clear buffer: retain CONSERVE + LOW until 20 simulated seconds after clear, then baseline | Per-Bottom clear timestamp plus buffer state, visibly timed | Adds recovery time but net LOW cost leaves only +1 per 10 s when Top is unfunded. A fixed duration does not guarantee reserve. Free initiative may add costs without time; must expire by simulated time, not action count. Setup/Recognition and stalling risks as above. |
| Temporary LOW initiation only: retain LOW after clear until stamina >=45; baseline ESCAPE otherwise unchanged | Per-Bottom recovery phase boolean, reserve visibly stated | Prevents the first +10 re-entry locally but ESCAPE + LOW has negative net flow. Reserve 45 may never be reached, permanent LOW/feint behavior possible. Does not change Top/responder grades; setup selection and submission opportunities change. Weak candidate from traced budget. |
| Cap first two post-clear Bottom initiations at LOW, restore MEDIUM afterward | Per-Bottom counter including free initiations; visible two-action rule | Defers deficit rather than funds it. No extra recovery; can oscillate later. Counter consumption must include funded/unfunded attempts and exclude RESET by explicit rule. Changes Recognition and setup outcomes; no responder settlement changes. |
| Reserve-aware MEDIUM: request MEDIUM only if current stamina minus 7 remains >25, otherwise LOW if its cost preserves >25, otherwise RESET and CONSERVE for next interval | Can use current pool only, but must define behavior choice and RESET together; visible reserve affordability rule | Avoids immediate latch entry due to initiation but behavior or response spends can still cross 25. RESET can suppress setup builders and cause stalling/free initiative; repeated caps alter Recognition and submission pressure. Top unaffected, response cost unchanged. |
| Simpler buffer variant: preserve latch rules, Bottom CONSERVE continues after clear until >=60 but initiation immediately returns MEDIUM | Per-Bottom recovery-mode boolean, visible recovery state | With CONSERVE + MEDIUM, nominal net -3 per 10 s, so buffer may never fill. Rejected as a promising first family by accounting, not by candidate simulation. |

No family is selected. The reserve-policy family has a direct budget rationale,
but its refill time is a major limitation: CONSERVE gains 4 and LOW spends 3
per 10 s cycle, only +1 net here. Filling from 35 to 60 would nominally require
250 additional seconds with continued initiation, generally beyond this match.
It may therefore fail coverage; a higher reserve is not recommended on its own
merely because it improves conditional survival. Faster recovery would require
a separately specified choice (for example fewer initiations), with its own
RESET/stalling/setup consequences reviewed before implementation. Its proposed 60 reserve comes from
the traced unfunded-Top budget: through inclusive +30 s there can be four
Bottom MEDIUM initiations (28) plus six ESCAPE quanta (6); 25 + 28 + 6 + 1 = 60
leaves 26. Funded responder/hold costs or free initiative can violate this bound;
60 is not a proof of universal stability. Longer LOW recovery may fail the
coverage/escape gates below. No thresholds will be tuned after results.

## Proposed frozen D2 DoD — NEW post-adoption criterion

These criteria are frozen as a proposal by the D1 commit. They become the
experiment contract only after explicit user review/authorization. Historical
A9 and X are preserved separately, never used as an absolute stability test.

### Sampling and denominators

Run the exact two E-PROD batches above, 100 each, seeds 42 and 142, OFF+shadow
and ON, plus adopted-policy controls at the canonical checkpoint/settings.
No adaptive extensions, seed replacement, tuning, or outcome exclusions.
Evaluate both pooled episode results and first-clear-per-match results.
A horizon admits an episode if re-entry occurs within the inclusive horizon or
it is observed through the horizon; otherwise right-censor. Successful escape
before horizon is censored for stamina survival, and reported separately.
No-clear matches and clears at timeout are never survival successes.
Report both each batch and pooled results, every failure, censored counts and
all 5/10/15/20/30 s horizons, complete 10/20/30 spend/recovery histograms,
first actions, first-clear times and repeated cycles. Keep original adoption
numbers beside new results.

### A. Preservation (all mandatory)

1. Public MATCH Surface A (original 100 seeds/settings) exactly preserves 78
   Threat matches, 1,950 Threat entries, Tap 0. Surface B exactly preserves Tap
   9/100. The scoped recovery fix must remain inactive on non-RECOVER surfaces.
2. Rule 1: zero responder commitment **or hold** charged on unfunded initiator
   exchanges. Rule 2 remains OFF, charges/refunds and their semantics unchanged.
3. Bottom stamina within [0,100], no fabricated recovery, no negative costs;
   E-PROD original-100 final median >=29. Setup-builder availability retained;
   report attempts/advances/completions and post-clear action distributions.
4. Original-100 escapes >=25 (adopted 35 minus a preregistered ten-match margin),
   each destination count within +/-10 of adopted Half Guard 16, Open Guard 10,
   Reversal 9; timeouts <=70 (adopted 60 +10). These are pragmatic ten percentage
   point tolerances, not statistical equivalence claims. Tap <=9/100.
5. RESET-with-progress-route exposure <=23/100 (adopted 13 +10); no real warning,
   penalty or position reset in E-PROD. OFF/ON gameplay divergence 0/100 for
   both seed batches when no offense fires, using full gameplay identity.
6. Frozen Mount-v0 digest exactly
   `3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2`;
   full unit suite on all locally available supported Python versions, semantic
   checker and legacy entry point PASS; deterministic replay of full gameplay
   traces; observer ON/OFF full summary identity.
7. Proposed candidate settings must have effective-settings and full gameplay
   equivalence across its explicit diagnostic entry points. Existing canonical
   production entry point remains identical to adopted controls and unchanged.
   Canonical integration requires separate authorization; candidate equivalence
   must not be falsely described as equality to unchanged adopted gameplay.
8. Preserve all historical evidence, including failed Gate G and old Rule 2.
   Report adoption A1–A10 and Gates A–H as historical results, not proof D2 passes.

### B. Absolute handoff stability (all mandatory)

9. **NEW** rate of re-exhaustion within 10 s <=0.20, both pooled episodes and
   first-clear-per-match admissible samples. Design intent: at least four out
   of five observed handoffs survive a complete alternating initiative cycle.
   This is an explicit normative stability target, not derived from A9's
   oscillatory baseline or a candidate result.
10. **NEW** within 30 s rate <=0.35 for both denominators. Intent: at least
    roughly two-thirds survive three initiative cycles; this prevents merely
    shifting the same failure from +10 to +20/+30. Threshold 0.35 is the rounded
    allowance of one-third failures, frozen upward by 0.0167 for finite samples.
11. Each pooled denominator at both 10 and 30 s >=43; 43 retains the historical
    worst-case normal binomial 95% half-width <=0.15 planning size, not an IID
    guarantee. Cluster sensitivity uses first-clear-per-match and must also
    reach 43; episode count alone cannot establish PASS. Report Wilson bounds
    descriptively; no confidence-bound substitution for these frozen rates.
12. Prevent apparent success by removing clears: original-100 matches with a
    clear >=45 (adopted 45), pooled matches with a clear >=82 (adopted 45+37).
    First-clear time median original-100 <=240 s and pooled <=240 s. Rates with
    inadequate samples remain **OPEN**, not PASS. Gate failures remain FAIL even
    if checker/unit tests PASS. No additional batch may rescue this experiment.

13. Do not claim a stable LOW-to-MEDIUM handoff by retaining LOW/CONSERVE
    until every match ends. Define policy handoff as the first post-clear
    decision window actually restoring both baseline behavior and baseline
    MEDIUM request. For policies with no separate recovery state this is the
    clear window. Require >=43 distinct pooled matches with such a return,
    and >=43 admissible first-return-per-match observations at both +10 and
    +30 s. Apply the same <=0.20 / <=0.35 re-entry limits from that return
    timestamp as well as from latch clear. A clear-to-return re-entry must
    also count as a failed handoff, never be dropped to select healthier
    later returns. Report return delays, pending-at-end recovery states and
    all pre-return re-entries. Inadequate return exposure is OPEN. This is a
    NEW guard against permanent recovery mode, not an adoption requirement.

### Decision and hard stops

All A and B criteria must pass for a D2 design-gate PASS. A candidate failing any
criterion is recorded with exact SHA/settings and STOP; no tuning or silent
criteria change. Missing evidence gives OPEN. After D1 commit/push: HARD STOP
for review of exact SHA, candidate selection and explicit D2 authorization.
After D2 evidence: HARD STOP again. No main changes, merge, squash, force-push,
frontend work or canonical production-policy changes are authorized here.

## Diagnostic development history

An initial tracing run aborted before writing evidence because Recognition-read
dataclasses were not JSON serializable. The observer serializer was corrected
to recursively detach dataclasses and enums. The successful run was reproduced
with the exact decompressed evidence hash above. This was an instrumentation
error, not a candidate/design-gate failure; no candidate was measured, and no
acceptance criterion was adjusted to pass results.

## D1 checkpoint local verification

| Python | Full unit suite | Result |
|---|---:|---|
| 3.11.17 | 421 tests | PASS |
| 3.13.16 | 421 tests | PASS |
| 3.14.8 | 421 tests | PASS |

Primary semantic checker and legacy `mount_v0 --check` on Python 3.11.17:
`STATUS: PASS`, no errors. Frozen enumeration digest matches exactly on the
three supported Python minors above (also pinned by the full unit suite).
Observer-specific final rerun: 3 tests PASS; trace reproduced with the exact
uncompressed evidence hash. Tests establish accounting, ordered replay, full
summary inertness under OFF/ON stalling and cleanup on exceptions. Existing
canonical-equivalence/adoption tests pass unchanged.

Only new diagnostics, tests and D1 evidence/documentation are added. No gameplay,
engine, domain, batch defaults, canonical policy or historical document changed.
D2 absolute gates: NOT RUN; no candidate implemented or measured. Passing unit
and semantic checks is not a D2 design-gate PASS. Exact-head CI is reported
separately after publication; no follow-up commit is needed to report it.
