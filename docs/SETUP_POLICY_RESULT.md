# Setup Policy — Result

## Status

**OUTCOME = SP-JOINT.** Debts 4 (setup-policy valuation) and 5 (initiator tactical commitment selection) are **merged into one controlled tactical-evaluator slice**.

This is a docs-only closure record. There are no gameplay, policy or default changes.

```text
frozen characterization checkpoint:  990823519b2c8fe39dd206847037803481e1b840
                                     docs/SETUP_POLICY_CHARACTERIZATION.md (unchanged)
exact-head CI on 9908235:            run 37460433501 — PASS on Python 3.11 and 3.13
branch:                              review/setup-policy-characterization
base (main):                         71683cb4ee4fa4c37915162f5b7d5e4c0b108453
frozen digest:                       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Decision record

| Item | Decision |
|---|---|
| Outcome | **SP-JOINT** (selected by the user after reviewing `9908235`) |
| SP-MINIMAL (anti-churn rule) | **NOT SELECTED.** No temporary anti-loop rule: it would change gameplay before the evaluator exists, and could suppress delayed opportunities created by state change between build and use. |
| SP-S1 (informed static gate) | **REJECTED BY CHARACTERIZATION.** It blocks 99%+ of production Top setups. |
| `EscapeFirstInitiatorPolicy`, `MountSetupPolicy`, commitment selection | **UNCHANGED** |
| Candidate runs, commitment tuning | **None** |

## Reason

Setup is not fundamentally broken. Top's evaluator uses the **wrong defender model**: it treats Bottom as random-blind when Bottom is informed. The policy predicts about 55% Ready conversion versus about 14% actual, and 57% versus 0% on PROTECT.

The value of a setup also depends on the **stamina/exhaustion/axis state at Ready use time**, and commitment choice is one of the main drivers of that future state. Solving setup and commitment separately would mean building two projection systems.

## Requirements carried forward (binding on the joint preregistration)

E1-E6 from `docs/SETUP_POLICY_CHARACTERIZATION.md` section 4:

| ID | Requirement |
|---|---|
| E1 | Opponent model matches the responder actually faced, or is declared and its calibration reported. |
| E2 | Ready-target value is evaluated at the projected use-time state (at least stamina/exhaustion bands and axis band). |
| E3 | No unbounded zero-conversion churn (PROTECT today: 982 Readys, 0 conversions). |
| E4 | Submission access preserved as a gated quantity (A-PROD Threat 78 prominent; Tap A 0, B 9, E-PROD 5 / 4; builds per Threat entry). Floors and tolerances are frozen before any run. |
| E5 | Predicted-vs-actual calibration reported for every candidate. |
| E6 | Deterministic and dependency-free; no hidden tuning; documented tie-breaks; RNG order unchanged. |

## Architectural constraints (added at selection; rules on what may be built, not outcome thresholds)

| ID | Constraint |
|---|---|
| A1 | **Bounded and deterministic.** Not a general game-tree AI. It uses the engine's existing exact transition/probability math and consumes **no RNG** while evaluating alternatives. Tie-breaks are explicit. |
| A2 | **One shared value representation.** Setup and commitment choices are evaluated through the same `TacticalValue`, not two independent ranking systems. |
| A3 | **Deterministic tuple, not a weighted utility score.** For example: terminal/submission value, escape value, setup/future tactical value, positional value, stamina consequence, risk/defender counter-value. The exact ordering is frozen in the preregistration. Arbitrary coefficients (`0.4 × submission + 0.25 × axis − …`) are not allowed, because they create tuning parameters. |
| A4 | **Commitment comparison.** A normal attack is evaluated as `action × {LOW, MEDIUM, HIGH}` against the correct responder model. |
| A5 | **Bounded setup projection.** A builder is projected only far enough to value its eventual Ready use at the projected stamina/exhaustion/axis state, never by recursively playing the match. |
| A6 | **Recognition is not randomness.** The evaluator models only what the initiator may know. With an imperfect perceived state, it evaluates from that perceived state against the responder behavior actually expected, and reports calibration (E5). The information mechanic is preserved and the AI is not omniscient. |

## Frozen controls and gates (to be numerically fixed in the joint preregistration, before any run)

- **Surfaces:** A-PROD, B-PROD, E-PROD (seeds 42 / 142, stalling OFF + shadow and ON) and the PROTECT probe.
- **Gate families with numeric floors frozen before any run:** submission access (A-PROD Threat 78 as the prominent preservation control), escapes/outcomes, setup churn, stamina/pacing, calibration.
- **Design goal, not a gate:** on PROTECT, the evaluator recognizes that repeated zero-value setup is not worth continuing indefinitely. No arbitrary maximum number of attempts (`k`) is frozen.

## Next

1. A fresh branch from the new `main` for the joint tactical evaluator, starting with **preregistration/DoD only**. It defines the evaluator contract, candidate policies, preservation surfaces, numeric gates and tie-break rules before any implementation or candidate run.
2. After the joint evaluator qualifies: **re-run the frozen late-recovery observer** (debt 3 re-evaluation).

Neither step is authorized by this record.

**HARD STOP.**
