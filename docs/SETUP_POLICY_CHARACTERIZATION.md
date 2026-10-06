# Setup Policy — Characterization and Proposed Decision

## Status

**CHARACTERIZATION ONLY — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

Observer-only. `EscapeFirstInitiatorPolicy`, `MountSetupPolicy`, gameplay, policy and defaults are unchanged. No candidate policy has been implemented or run. The candidate-gate counts in section 2.5 are counterfactual evaluations on baseline states, not candidate runs.

```text
branch:          review/setup-policy-characterization
base (main):     71683cb4ee4fa4c37915162f5b7d5e4c0b108453
frozen digest:   3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
observer:        src/bjj_game/diagnostics/setup_policy.py
evidence:        docs/evidence/setup_policy_characterization.json
pinning tests:   tests/test_setup_policy_characterization.py
```

Reproduce:

```bash
PYTHONPATH=src python3 -m bjj_game.diagnostics.setup_policy
PYTHONPATH=src python3 -m unittest tests.test_setup_policy_characterization
```

**Surfaces (100 matches each).**
- The historical v0.3a informed PRESSURE/PROTECT probe behind the `--check` debt line.
- Canonical A-PROD and B-PROD.
- Canonical E-PROD, seeds 42 and 142 (stalling OFF + shadow).

**Observer.**
- It wraps `EscapeFirstInitiatorPolicy.choose` and `MountMatch.attempt`, and delegates each real call once.
- For every real decision it also asks, read-only, what the same lexicographic policy would choose **without the setup tier** (setup probability forced to 0 for that query only).
- D3-B's LOCKOUT_HOLD counterfactual `choose()` calls are excluded (E-PROD 63 / 34). Their count is asserted equal to D3-B's recorded holds.
- Inertness is pinned: full `BatchSummary` identity, replay identity, and wrappers restored after normal exit and exceptions.

**Baselines reproduced.**
- PROTECT probe: Top completed builds **1,768**, Threat **0** (the `--check` debt line).
- A-PROD: Threat 78.
- B-PROD: Tap 9.
- E-PROD 42 / 142: outcomes match the D3-B record.

---

# 1. The policy as it is (code)

`EscapeFirstInitiatorPolicy.choose` (`src/bjj_game/interfaces/batch.py`) is lexicographic:

1. any escape probability > 0;
2. any submission-progress probability > 0;
3. any **setup-advance probability > 0**;
4. positional attack only if both raw and realized expected axis are > 0;
5. otherwise RESET.

A builder's setup probability is about 1: any real exchange advances it unless the Mount cap fully absorbs it. It counts as long as `_ready_target_has_value` says the eventual Ready target has *any* positive value. That value is computed under **`RandomBlindResponder` weighting**.

Setup rules (`MountSetupPolicy.default`):
- **Top:** High Mount Climb builds Americana Arm Isolation (the only route into the submission track).
- **Bottom:** Bridge builds Trap-and-Roll Escape.

Two builder successes take a target from None to Ready. Using the target consumes Ready.

---

# 2. Characterization

## 2.1 What setup displaces

| Surface | Side | Setup decisions | Without setup: RESET / position | Setup forgoes a *better* positional attack | Forgone expected axis (total) |
|---|---|---|---|---|---|
| PROTECT probe | Top | 1,964 | 1,834 / 130 | 127 | 7.46 |
| A-PROD | Top | 356 | 161 / 195 | 100 | 14.30 |
| B-PROD | Top | 900 | 674 / 226 | 141 | 20.12 |
| E-PROD 42 | Top | 895 | 557 / 338 | 189 | 23.05 |
| E-PROD 142 | Top | 886 | 611 / 275 | 152 | 19.42 |
| PROTECT probe | Bottom | 1,964 | 1,866 / 98 | 98 | 37.81 |
| A-PROD | Bottom | 1,846 | 1,846 / 0 | 0 | 0 |
| B-PROD | Bottom | 1,836 | 1,817 / 19 | 19 | 7.33 |
| E-PROD 42 | Bottom | 1,585 | 1,509 / 76 | 76 | 32.59 |
| E-PROD 142 | Bottom | 1,563 | 1,506 / 57 | 57 | 25.75 |

**Setup mostly replaces RESET, not a better attack.** "Builder progress ranked above axis loss" is mainly *setup over RESET*. It forgoes a strictly better positional attack in 6-28% of Top setup decisions (0.06-0.14 expected axis each) and 0-5% of Bottom's.

## 2.2 Realized cost of building

| Surface | Side | Realized axis per build (initiator-signed) | Stamina spent | Builds that reached Ready |
|---|---|---|---|---|
| PROTECT probe | Top | **−1.000** | 5,516 | 982 |
| A-PROD | Top | −0.992 | 2,492 | 178 |
| B-PROD | Top | −0.854 | 2,464 | 449 |
| E-PROD 42 | Top | −0.868 | 2,462 | 441 |
| E-PROD 142 | Top | −0.879 | 2,471 | 438 |
| PROTECT probe | Bottom | −0.199 | 5,998 | 884 |
| A-PROD | Bottom | −0.085 | 2,303 | 363 |
| B-PROD | Bottom | −0.168 | 2,901 | 561 |
| E-PROD 42 | Bottom | +0.191 | 6,353 | 724 |
| E-PROD 142 | Bottom | +0.182 | 6,135 | 703 |

The Top climb costs about 0.85-1.0 axis per build on every surface. Bottom's Bridge is roughly axis-neutral, and positive on E-PROD.

## 2.3 What Ready pays off

| Surface | Top Ready Arm Isolation uses | Threat entries | Taps | Climbs per Threat entry | Bottom Ready Trap-and-Roll uses | Escapes from it |
|---|---|---|---|---|---|---|
| PROTECT probe | 884 | **0** | 0 | ∞ | 884 | 2 |
| A-PROD | 156 | 78 | 0 | 4.6 | 355 | 0 |
| B-PROD | 440 | 59 | 9 | 15.3 | 521 | 2 |
| E-PROD 42 | 422 | 61 | 5 | 14.7 | 701 | 8 |
| E-PROD 142 | 420 | 57 | 4 | 15.5 | 683 | 1 |

On every surface, **all of Top's submission access comes through this chain.** Bottom's Trap-and-Roll seldom exits. Its value is mostly positional.

## 2.4 Calibration: the policy's own estimate versus reality

Successes at Ready-target uses, summed over uses:

| Surface | Top Arm Isolation: policy estimate (random-blind) | **Informed-defender model** | **Actual** | Bottom Trap-and-Roll: estimate / actual |
|---|---|---|---|---|
| PROTECT probe | 501.9 / 884 (57%) | 0 | **0** | 1.7 / 2 |
| A-PROD | 122.5 / 156 (79%) | **78** | **78** | 0 / 0 |
| B-PROD | 246.0 / 440 (56%) | 21 | **59** | 2.3 / 2 |
| E-PROD 42 | 231.8 / 422 (55%) | 24 | **61** | 4.7 / 8 |
| E-PROD 142 | 229.1 / 420 (55%) | 23 | **57** | 3.0 / 1 |

- **Top's valuation is wrong by about 4x on production and is unbounded on PROTECT.** The policy values Ready Arm Isolation as if Bottom responded at random. On every surface Bottom is an **informed** responder.
- The informed-defender model is **exact without Recognition** (A-PROD 78/78, PROTECT 0/0). It uses the same engine call, Ready response set, stalemate override, exhaustion modifier and band condition, with minimum grade instead of random weighting. With Recognition it is **conservative** (24 vs 61): misreads help Top.
- **Bottom's valuation is calibrated,** because Top's responder really is random-blind on every surface.

## 2.5 Counterfactual candidate S1: gate setup on informed Ready value *at decision time*

S1 allows a Top builder only if Ready Arm Isolation would succeed now against an informed defender. Evaluated on every baseline Top setup decision:

| Surface | Top setup decisions | S1 would block | Of which the fallback is position / RESET |
|---|---|---|---|
| PROTECT probe | 1,964 | **1,964** | 130 / 1,834 |
| A-PROD | 356 | **356** | 195 / 161 |
| B-PROD | 900 | **899** | 225 / 674 |
| E-PROD 42 | 895 | **893** | 336 / 557 |
| E-PROD 142 | 886 | **880** | 273 / 607 |

S1 stops the PROTECT churn, but it would remove essentially every Top setup decision on the production surfaces. Yet those same chains produce A-PROD's 78 Threat entries, which the informed model predicts **exactly at use time**.

The difference is the state. At decision time the target is valued in the current state. By use time the state has changed (stamina and exhaustion bands, axis/band). **A static, current-state valuation would collapse submission access**: the same failure class as Rule 2 (Threat 78 → 0).

---

# 3. Findings

- **S1 — The debt reproduces and its mechanism is identified.** Any positive Ready value under a random-blind model admits a builder. On PROTECT the informed defender never lets Ready Arm Isolation succeed, so Top climbs 1,964 times (−1.0 axis each), reaches Ready 982 times, and converts 0.
- **S2 — The core defect is the opponent model, not the ranking order.** Top values its Ready target against the wrong responder (estimate about 55% vs actual 14% on production; 57% vs 0% on PROTECT). Bottom's model happens to be right and Bottom's setup behaves sensibly.
- **S3 — Setup mostly displaces RESET.** Strictly better positional attacks are forgone in 6-28% of Top and 0-5% of Bottom setup decisions, at 0.06-0.14 expected axis each.
- **S4 — Fixing the opponent model with a static lookahead is not safe.** Correct-model, current-state valuation (S1) blocks 99%+ of Top setups on production and would remove submission access. Ready value depends on the **projected state at use time**, mainly stamina and exhaustion bands, which are set by commitment selection (debt 5).
- **S5 — Bottom's setup is not the debt.** It is calibrated, roughly axis-neutral (positive on E-PROD), and almost always replaces RESET.

---

# 4. Proposed decision (for review)

## SP-JOINT — fold setup valuation into the tactical evaluator built for debt 5 (recommended)

Do not ship a standalone setup-policy change. A correct setup value needs the projected use-time stamina and exhaustion state, and that projection is exactly what debt 5's commitment evaluator must model. Two separate AI systems would duplicate it, which the project plan already warns against. Debts 4 and 5 therefore become one controlled slice: a shared deterministic `TacticalValue` evaluator used for both setup and commitment choices.

**Requirements frozen now from this evidence** (they bind the joint preregistration; gates are set there):

| ID | Requirement |
|---|---|
| E1 | **Opponent model matches the responder actually faced** (informed where the opponent is informed, random-blind only where it truly is), or the model is declared and its calibration reported. |
| E2 | **Ready-target value is evaluated at the projected use-time state** (at least stamina/exhaustion bands and axis band). Static current-state evaluation is shown in 2.5 to collapse submission access. |
| E3 | **No unbounded zero-conversion churn.** On the PROTECT probe, builder → Ready → failed use must not repeat without bound (today: 982 Readys, 0 conversions). |
| E4 | **Submission access is preserved as a gated quantity.** A-PROD Threat (78), Tap (A 0, B 9, E-PROD 5 / 4) and builds per Threat entry are reported, with floors and tolerances frozen in the joint preregistration before any run. |
| E5 | **Calibration reported.** Predicted-vs-actual Ready conversion (section 2.4 format) for every candidate. |
| E6 | **Deterministic and dependency-free.** No external AI framework, no hidden tuning, documented tie-breaks, and RNG order unchanged. |

**Closure gates for this slice:**

| ID | Gate |
|---|---|
| SP-1 | Characterization reproduces exactly; observer inert; counterfactual exclusion equals D3-B holds. |
| SP-2 | No gameplay change; digest exact; full suite, checker and legacy entry point PASS; exact-head CI on Python 3.11 / 3.13 (including full-history PG8). |
| SP-3 | Status document: debts 4 and 5 merged into one tactical-evaluator slice, with requirements E1-E6; the debt-3 re-evaluation then follows that slice. |

## SP-MINIMAL — narrow anti-churn rule now

For example: stop rebuilding a target after k consecutive failed Ready uses until the state changes. Not recommended. It needs a tuned k, leaves the valuation wrong, and would be replaced by the joint evaluator.

## SP-S1 — informed static gate

**Rejected by this characterization** (S4): it blocks 99%+ of production Top setups.

---

# 5. Hard-stop rules

Done in this slice: branch, observer-only module, pinning tests, evidence JSON, this document.

**Not authorized:** any outcome until the user selects one at this exact SHA; any change to `EscapeFirstInitiatorPolicy`, `MountSetupPolicy`, commitment selection, gameplay, policy or defaults; any candidate implementation or run; merge; squash; force-push.

The status document is not edited in this slice. SP-3 is applied only after an outcome is selected.

**HARD STOP.**
