# R1 — Response Commitment / Provisional-Hold Affordability: Characterization and DoD

## Status

**PROPOSED DoD / PREREGISTRATION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

Documentation, characterization and preregistration only. No gameplay, policy, settlement or default change has been made. No candidate has been implemented or run. This becomes binding only after the user reviews this exact SHA and explicitly selects an R1 outcome (section 5).

```text
branch:              review/r1-hold-inclusive-affordability
base (main):         1e2b5e3ffbf6f8a8051775d48c20063cc3abdedd
canonical policy:    PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged; Rule 1 ON, Rule 2 OFF, D3-B)
frozen digest:       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
selected direction:  option (a) — keep additive settlement; examine decision-time affordability
characterization:    src/bjj_game/diagnostics/r1_affordability.py (observer only)
evidence:            docs/evidence/r1_affordability_characterization.json
pinning tests:       tests/test_r1_affordability_characterization.py
```

Reproduce:

```bash
PYTHONPATH=src python3 -m bjj_game.diagnostics.r1_affordability
PYTHONPATH=src python3 -m unittest tests.test_r1_affordability_characterization
```

---

# 0. Renaming and frozen premise

The debt formerly called **"Rule 2 double charge"** is renamed:

> **R1 — Response commitment / provisional-hold affordability.**

**Semantics A is intentional and authoritative.**

```text
responder pays: response commitment charge
              + provisional Contested-hold charge (LOW = 3)

The hold is a separate cost of surviving/maintaining a contested
submission lock. R1 does NOT attempt to remove that additive burden.
```

Reason: the hold charge was introduced in v0.3a (`docs/MOUNT_V0_3A_HOLD_STAMINA_AMENDMENT.md`) because responses cost nothing and informed defenders were never submitted (Tap 0/100, Threat 0). It is a submission-pressure mechanic, not accounting overlap.

**Rejected alternative (historical, preserved).**

```text
Rule 2 / semantics B: funded response commitment covers the 3-point hold
measured: public-MATCH Threat reach 78/100 -> 0/100
          (docs/STAMINA_ECONOMY_RULE_POSTCHANGE_MEASUREMENT.md, P6)
status:   rejected as a production answer; remains a diagnostic capability, OFF
```

**Reinterpretation of "179".** The E-PROD count of 179 "additive double-charge cases" is defined as `response_charged >= 3 and hold_charged > 0` on funded-initiator holds (`src/bjj_game/diagnostics/stamina_recovery_policy.py:200`). It counts how often semantics A applies. It is **not** a defect count. No R1 gate may treat additive response + hold charging as invalid in itself.

---

# 1. Mechanics as they exist (read from code; unchanged)

1. **Resolution before costs.** `MountMatch.attempt()` resolves the exchange and applies setup and submission effects, then charges stamina (`src/bjj_game/engine/match.py:1477-1545`, "Current exchange semantics are fixed before costs are charged").
2. **Settlement order (responder).** First the response commitment (`spend_up_to(response_effective_cost)`, or 0 under the Rule 1 waiver). Then, if the exchange is a provisional hold, a second `spend_up_to(hold_request)`. With Rule 2 OFF, `hold_request = 3`, or 0 under the Rule 1 waiver.
3. **Hold paths (Top initiator only; the responder is always Bottom).**
   - `FINISH`: Americana Submission Finish with an **active submission stage**, final grade Contested.
   - `ARM_READY`: Americana Arm Isolation with the target **Ready** (v0.3a), final grade Contested.
   On all characterized surfaces, holds outside these two paths = **0**.
4. **The response commitment is chosen without considering affordability.** None of the batch modes (`_response_commitment_for_exchange`, `src/bjj_game/interfaces/batch.py:951`) reads the responder's own stamina. The engine then funds it with `effective_commitment`, the highest requested-or-lower level fully payable from the current stamina. The hold is not part of that check.
5. **Response id is chosen after the commitment,** by `_informed_bottom_response_id`, as the minimum predicted final grade under that commitment. Resolution is deterministic. Without Recognition the prediction is exact. With Recognition it uses the perceived initiator effective commitment.
6. **A hold shortfall has no mechanical consequence.** The outcome is already fixed when the hold is charged. A responder who cannot pay the full 3 still keeps the Contested result. The shortfall is only recorded (`submission_hold_stamina_shortfall_history`).

So the defect named in the adoption DoD ("commitment-only affordability can overstate hold-inclusive affordability") shows up in only one way: **a best-effort hold charge on a responder who is nearly out of stamina.**

---

# 2. Characterization (observer only; evidence file is authoritative)

Surfaces: canonical production settings from `PRODUCTION_STAMINA_RECOVERY_POLICY`.

- A-PROD and B-PROD: `canonical_surface_kwargs`.
- E-PROD: `canonical_kwargs(seed, "OFF")` (stalling OFF + shadow), seeds 42 and 142.
- 100 matches each.

The observer delegates the real response choice exactly once. It evaluates counterfactual lower commitments only through the non-mutating preview API. Inertness is pinned: summary identity with and without the observer, replay identity, and wrapper restoration.

## 2.1 Frozen baselines reproduced

| Surface | Threat matches / entries | Tap | Additive (semantics A) |
|---|---|---|---|
| A-PROD | **78 / 1,950** | **0** | 78 |
| B-PROD | 59 / 533 | **9** | 137 |
| E-PROD 42 | 61 / 683 | 5 | **179** |
| E-PROD 142 | 57 / 495 | 4 | 177 |

## 2.2 Where the historical 1,366 went (Surface E, seed 42)

| Configuration | Holds | Hold request > 0 | Commitment-only fundable, + hold not | Hold stamina charged |
|---|---|---|---|---|
| Pre-change (no settlement rules, CURRENT) | 1,589 | 1,589 | **1,366** (reproduces exactly) | 1,745 |
| + LOW_WHILE_EXHAUSTED only (Rule 1 OFF) | 1,599 | 1,599 | 1,277 | 2,010 |
| + Rule 1 only (CURRENT) | 1,566 | 163 | **4** | 479 |
| Gate-G policy (Rule 1 + LOW) | 1,422 | 179 | 0 | 537 |
| **E-PROD canonical (D3-B)** | 1,425 | 179 | **0** | 537 |

**Rule 1 alone removes 1,362 of the 1,366.** Most hold exchanges have an UNFUNDED initiator, and Rule 1 waives their hold entirely. The 1,366 target cited in the plan was measured on a configuration that production no longer runs.

## 2.3 Production hold settlement

| Surface | Holds | Rule-1 waived | Funded-initiator | FULL / PARTIAL / NONE | Hold charged / shortfall | **Commitment-only fundable, + hold not** |
|---|---|---|---|---|---|---|
| A-PROD | 1,950 | 1,794 | 156 | 78 / 0 / 1,872 | 234 / 234 | **78** |
| B-PROD | 1,434 | 1,291 | 143 | 135 / 2 / 1,297 | 408 / 21 | **6** |
| E-PROD 42 | 1,425 | 1,246 | 179 | 179 / 0 / 1,246 | 537 / 0 | **0** |
| E-PROD 142 | 1,392 | 1,213 | 179 | 176 / 1 / 1,215 | 529 / 8 | **2** |

NONE includes every Rule-1 waived hold (request 0). Shortfall counts only funded-initiator holds that could not be paid in full.

## 2.4 Decision-time knowledge, by required category

**(i) FINISH — hold eligibility known before the choice** (active stage is public). Whether a hold happens still depends on the predicted grade.

| Surface | Eligible | Pred. Contested & held | Pred. Contested, not held | Pred. other, but held | Pred. other, not held |
|---|---|---|---|---|---|
| A-PROD | 1,872 | 1,872 | 0 | 0 | 0 |
| B-PROD | 1,148 | 885 | 16 | 181 | 66 |
| E-PROD 42 | 1,167 | 1,089 | 15 | 2 | 61 |
| E-PROD 142 | 1,129 | 1,047 | 28 | 5 | 49 |

**(ii) ARM_READY — the hold depends on the response and its result.**

| Surface | Eligible | Pred. Contested & held | Pred. Contested, not held | Pred. other, but held | Pred. other, not held |
|---|---|---|---|---|---|
| A-PROD | 156 | 78 | 0 | 0 | 78 |
| B-PROD | 440 | 315 | 31 | 53 | 41 |
| E-PROD 42 | 422 | 334 | 30 | 0 | 58 |
| E-PROD 142 | 420 | 340 | 18 | 0 | 62 |

Without Recognition (A-PROD) the prediction is exact. Under Recognition it is noisy.

**(iii) Ordinary exchanges (hold burden 0).** All Bottom-initiated exchanges (A 2,228; B 2,372; E 2,320 / 2,292) and every Top-initiated exchange outside the two paths. Hold-outside-path = 0 on every surface.

**(iv) Requested response commitment downgraded by stamina.** Downgrades over all exchanges: A 3,588; B 3,673; E 1,744 / 1,727. Downgrades on hold exchanges: A 1,794; B 1,282; E 1 / 3. On A and B almost all of these are Rule-1 waived holds.

**(v) Recognition / perceived commitment.** Under Recognition, the responder's view of whether the initiator is funded (the input Rule 1 uses) is often wrong:

| Surface | Path | Perceived funded, truly UNFUNDED (hold will be waived) | Perceived UNFUNDED, truly funded |
|---|---|---|---|
| B-PROD | FINISH / ARM | 183 / 53 | 3 / 1 |
| E-PROD 42 | FINISH / ARM | 180 / 43 | 3 / 1 |
| E-PROD 142 | FINISH / ARM | 170 / 51 | 2 / 0 |

**(vi) Rule 1 waiver.** Waived holds: A 1,794; B 1,291; E 1,246 / 1,213. On these the responder pays nothing at all, so affordability does not arise.

## 2.5 Two burden models

Definitions (responder's information only, at decision time):

```text
known-reserve burden      = cost(effective response) + 3 on any hold-eligible path
                            when the initiator is perceived funded
response-specific burden  = cost(effective response) + 3 only if the chosen
                            response's predicted grade is Contested and the
                            initiator is perceived funded
```

| Surface | Known-reserve flags unaffordable (FINISH+ARM) | ...of which no hold actually charged | Response-specific flags | ...actual hold charged | ...Rule-1 waived | ...no hold |
|---|---|---|---|---|---|---|
| A-PROD | 78 | 0 | 78 | 78 | 0 | 0 |
| B-PROD | 272 | 264 | 8 | 6 | 1 | 1 |
| E-PROD 42 | 3 | 3 | 1 | 0 | 1 | 0 |
| E-PROD 142 | 14 | 11 | 11 | 2 | 9 | 0 |

The **known-reserve model is rejected.** Under Recognition it overflags heavily: 264 of 272 on B had no hold charged. The only usable model is the **response-specific projected burden.**

## 2.6 Counterfactual: is there a free hold-aware downgrade?

For every response-specific unaffordable decision, the observer previewed each lower affordable commitment with the responder's own choice of response id.

| Surface | Flagged | No lower commitment exists | Free downgrade (affordable, no worse predicted grade) | Downgrade only with defensive loss | Lower-commitment predicted grades |
|---|---|---|---|---|---|
| A-PROD | 78 | 0 | **0** | 78 | LOW: Success ×78 |
| B-PROD | 8 | 2 | **0** | 6 | LOW: Success ×6, MEDIUM: Success ×1 |
| E-PROD 42 | 1 | 1 | **0** | 0 | — |
| E-PROD 142 | 11 | 11 | **0** | 0 | — |

**Every available lower commitment turns the predicted Contested hold into a Top Success, which advances the submission.** No hold-aware downgrade costs nothing on any production surface.

---

# 3. Findings (recorded before any candidate)

- **F1 — The named target is gone in production.** The 1,366 comes from a pre-Rule-1 configuration and still reproduces there exactly. Rule 1 removed 1,362 of them. Canonical production mismatch: **E-PROD 0 / 2, B-PROD 6, A-PROD 78.**
- **F2 — The remaining mismatch is a best-effort hold, not a hidden extra cost.** The responder keeps the Contested result and pays only what it has. Total production shortfall: A 234, B 21, E 0 / 8.
- **F3 — No free fix exists at choice time.** A hold-aware choice either:
  - **(H1)** downgrades only without defensive loss. That is provably **inert**: it changes 0 decisions on all four surfaces, so measuring it would be vacuous. Or:
  - **(H2)** downgrades even with defensive loss. That **adds submission pressure**: each changed decision trades a Contested hold for a Top Success that advances the stage.
- **F4 — A-PROD's 78 cases sit exactly on the preservation surface.** One per Threat match: MATCH-mode MEDIUM, responder at exactly 7 stamina, all FINISH and predicted Contested. The responder pays 7, reaches 0, and the hold charges 0 with a shortfall of 3. Any H2 change acts on the 78 / 1,950 / Tap 0 control.
- **F5 — Recognition makes even the projected burden unreliable.** About 170-180 FINISH decisions per Recognition surface perceive a funded initiator whose hold Rule 1 will in fact waive. In E-PROD 142, 9 of 11 flagged decisions would have been waived.

---

# 4. Preservation contract (binding on every R1 outcome)

| ID | Gate |
|---|---|
| R-P1 | Settlement semantics A unchanged: response commitment and provisional hold remain additive; hold nominal = LOW = 3; settlement after resolution. |
| R-P2 | Rule 1 exact: zero responder commitment and zero hold charged on unfunded-initiator exchanges. Rule 2 OFF: hold covered by response = 0 everywhere in production. |
| R-P3 | A-PROD exactly 78 Threat matches / 1,950 entries / Tap 0. B-PROD Tap 9. |
| R-P4 | `PRODUCTION_STAMINA_RECOVERY_POLICY`, `GATE_G_STAMINA_RECOVERY_POLICY`, D3-B, commitment costs, submission mechanics, raw `MountMatch` / batch defaults unchanged. |
| R-P5 | Frozen digest exact; full unit suite, semantic checker and legacy entry point PASS; exact-head CI on Python 3.11 and 3.13. |
| R-P6 | All historical evidence preserved, including the Rule 2 / B rejection and the original 1,366 measurement. |

---

# 5. Outcome decision for the reviewer

## R1-CLOSE — close by characterization (recommended)

No gameplay change. R1 closes with the semantics frozen as:

```text
Provisional hold settlement is BEST-EFFORT and ADDITIVE:
- response commitment is charged first, then the 3-point hold;
- the hold charges what the responder has left (Rule 1 waiver applies);
- a hold shortfall carries no penalty, because the Contested result is
  already fixed when stamina is charged.
```

Remaining design obligation, moved to **debt 7 (player-facing contract)** rather than solved in the engine:

> When a human responds on a hold-eligible window, the view must expose the **response-specific projected burden** (commitment cost + 3 if the selected response would be Contested and the initiator appears funded), computed only from information the responder has. The engine stays authoritative. The view is read-only, and no AI policy changes.

**Closure gates (all mandatory):**

| ID | Gate |
|---|---|
| C1 | R-P1 to R-P6 PASS. |
| C2 | Characterization reproduces exactly: the pinning test equals the committed evidence JSON on all four production surfaces, observer inert. |
| C3 | Production gameplay unchanged: the only `src/` addition is the observer module; existing pinned production fingerprints / D3-B tests unchanged and green. |
| C4 | Docs updated: debt renamed in `docs/PROJECT_PLAN_AND_STATUS.md`; best-effort semantics recorded; debt 7 carries the projected-burden requirement. |

## R1-H2 — hold-aware response at the cost of the hold (not recommended)

Include only if the reviewer wants **nearly empty defenders to lose contested holds.** That is a design decision to add submission pressure, not an accounting fix. Frozen semantics if selected:

```text
Bottom informed responder, hold-eligible window, opt-in flag (default OFF):
1. Mode selects the requested commitment c0 (unchanged). Response id chosen as today.
2. Projected burden B0 = cost(effective c0) + 3 if the predicted grade is Contested
   and the initiator is perceived funded; else cost(effective c0).
3. If B0 <= stamina: unchanged.
4. Else: take the highest c < effective c0 whose own projected burden <= stamina,
   re-choose the response id under c, and request c. If none exists: unchanged.
Settlement, resolution, Rule 1, costs: unchanged.
```

**Predictions (recorded now).** Changed decisions on the baseline trajectories: A 78, B 6, E-PROD 42 0, E-PROD 142 0. A-PROD's 78 matches each gain one Top Success at FINISH, so **A-PROD Tap is predicted to rise above 0.** That directly conflicts with R-P3.

**H2 gates (if selected):**

| ID | Gate |
|---|---|
| H-1 | R-P1, R-P2, R-P4 (with the opt-in flag), R-P5, R-P6. |
| H-2 | **R-P3 is replaced, not relaxed silently.** A-PROD Threat matches >= 78 with tolerance 0 downward. H2 acts only on FINISH and ARM_READY windows, and every A-PROD flag is at FINISH, which needs a Threat entry first. A-PROD and B-PROD Tap are reported, not gated, because changing them is the purpose of H2. |
| H-3 | Public-MATCH Threat entries: **no defensible tolerance can be derived from this characterization.** Every changed decision diverges the rest of that match, so baseline trajectories cannot bound later entries. Before authorizing H2, the reviewer must freeze a floor (or require a separate H2 characterization). |
| H-4 | E-PROD both seeds: escapes >= 25, timeouts <= 70, Tap <= 9 (the D3-B P4 limits), D3-B G1-G2 exact. |
| H-5 | Hold-aware decisions: every changed request is affordable including its projected hold; no change on non-hold windows; no change when B0 <= stamina. |

## R1-DEFER

Not recommended. The characterization already answers the open question, so deferral would only postpone a decision that the evidence supports making now.

---

# 6. Frozen for later (not part of this slice)

- **`ResponderSettlementPlan` refactor:** deferred to debt 7 or a dedicated non-gameplay refactor slice. Collapsing two responder spends into one is behavior-neutral (the latch is sticky and both spends only lower stamina), but it is not R1.
- **Hypothesis properties allowed** (to be added only after a DoD that adopts them):
  - charged components reconcile exactly with the actual stamina delta;
  - the Rule 1 waiver is exact;
  - no charge exceeds available stamina;
  - the effective commitment is never credited above what stamina funds;
  - Rule 2 OFF reproduces additive settlement;
  - non-hold exchanges are unaffected by any hold-aware logic.
- **Hypothesis property forbidden:** "response commitment and hold must never both charge" (that encodes the rejected Rule 2).

---

# 7. Hard-stop rules

Authorized and done in this slice: branch, observer-only characterization module, pinning tests, evidence JSON, this document, the status-document rename.

**Not authorized:** any R1 outcome (CLOSE, H2, DEFER) until the user selects one at this exact SHA; any engine, settlement, policy or default change; any candidate implementation or run; Hypothesis dependency; settlement-plan refactor; merge; squash; force-push.

**HARD STOP.**
