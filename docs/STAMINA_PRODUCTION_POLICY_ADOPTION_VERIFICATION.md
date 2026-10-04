# Stamina Production-Policy Adoption — Verification

## Status

**ADOPTED (Gates A-H all PASS) — PENDING PR REVIEW — MERGE NOT AUTHORIZED.**

This document completes DoD steps 20-23 of
`docs/STAMINA_PRODUCTION_POLICY_ADOPTION_DEFINITION_OF_DONE.md`:

- the canonical production stamina/recovery entry point was added;
- it was proven deterministically identical to the measured PROPOSED-PRODUCTION diagnostic (Gate G);
- the full regression ran.

```text
Stage-2 measurement checkpoint: 17e2e687caedbba5e8ef61c7821f1968f2448406
canonical entry point:          src/bjj_game/interfaces/production_policy.py
Gate G verification code:       src/bjj_game/diagnostics/stamina_adoption_verification.py
tests:                          tests/test_production_policy.py
                                tests/test_stamina_adoption_verification.py
frozen digest:                  3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

Per the DoD, ADOPTED still requires PR review and explicit merge authorization.

---

# Canonical production entry point

```python
from bjj_game.interfaces.production_policy import PRODUCTION_STAMINA_RECOVERY_POLICY
```

`ProductionStaminaRecoveryPolicy` is fixed and has no knobs. The single canonical instance is `PRODUCTION_STAMINA_RECOVERY_POLICY`, also returned by `production_stamina_recovery_policy()`.

```text
Rule 1 (unfunded responder cost waiver) = ON
Rule 2 (supplemental hold settlement)   = OFF (deferred)
Bottom RECOVER + Exhausted initiation   = LOW_WHILE_EXHAUSTED
initiation after Exhausted clears       = baseline commitment (MEDIUM)
```

- `match_settings()` returns MountMatch settlement settings only: umbrella OFF, Rule 1 ON, Rule 2 OFF.
- `batch_settings(bottom_behavior_mode=...)` returns those settings plus recovery initiation. That is LOW under Bottom RECOVER. Without RECOVER, no recovery-initiation policy is active, so CURRENT is used; the batch rejects LOW without RECOVER anyway.

It does **not** select v0.4a commitment semantics, v0.3b stalling, shadow stalling, Recognition, setup/submission features, scoring, response policy, or any initiator commitment. Those stay separate decisions that compose with it. Settlement still requires v0.4a, and constructing a MountMatch with the policy but without v0.4a raises, exactly as before.

Raw `MountMatch` and `run_escape_first_batch` defaults are unchanged. All settlement flags still default to False and recovery initiation to CURRENT. Historical construction does not silently adopt production semantics, and the frontend must opt in explicitly.

---

# Gate G — canonical equals measured candidate

Each canonical run removes every stamina/recovery setting from the frozen surface and rebuilds it only from `PRODUCTION_STAMINA_RECOVERY_POLICY`. It is then compared with the measured diagnostic run on the same 100 seeds (42..141).

Compared:
- the full `BatchSummary`: outcomes, axis, stamina, commitment counts, Recognition, setup, submission, stamina-economy accounting, recovery-policy trajectories, shadow/real stalling counters, and A9 handoff episodes;
- per-match gameplay state: the full RunHistory (action, response, grade, requested/effective/response commitment, Recognition, setup, submission, hold, and stalling histories), clock, axis, band, initiator, position, both stamina pools, behavior meters, exit, setup/submission state, stalling tracker, free initiative, and the effective settlement flags.

| Surface | effective settings equal | summary equal | diverged matches |
|---|---|---|---|
| A public MATCH | True | True | 0/100 |
| B trust-read | True | True | 0/100 |
| E-PROD OFF+shadow | True | True | 0/100 |
| E-PROD ON | True | True | 0/100 |

**Gate G = PASS.**

Negative control: the same comparison with Rule 2 switched ON on E-PROD reports unequal settings, unequal summaries, and diverged matches. The check does detect a non-equivalent policy.

## Recorded evaluation history

```text
first Gate G evaluation: OPEN
```

The first evaluation included an extra check I added beyond the DoD criterion: literal equality of the kwargs dicts. It reported `settings equal=False` on Surfaces A and B, even though every summary was equal and every surface had 0/100 diverged matches. The canonical policy passes `recovery_initiation_mode=CURRENT` explicitly, while the diagnostic omits it and gets the batch default, CURRENT. These are the same configuration.

This was a comparison bug in my verification code (a DoD MEASUREMENT FAILURE: fix instrumentation only, then rerun). It was not a policy difference. The check was corrected to compare *effective* settings, with omitted batch parameters resolved to their defaults, and rerun. The DoD's Gate G criterion (deterministic output equivalence) was not changed, and it was satisfied in both evaluations.

---

# Gates A-H (final)

| Gate | Status | Evidence |
|---|---|---|
| A — Rule 1 remains exact | **PASS** | UNFUNDED responder spend 0 on A/B/E-PROD OFF/ON. A and B identical to the isolated Rule1-only cells. |
| B — Rule 2 absent | **PASS** | Hold covered by response = 0 everywhere. Surface A 78/1950. |
| C — LOW fixes the deadlock + A9 | **PASS** | Latch clears 46, CONSERVE->ESCAPE 38, State2->State1 46. A9 pooled 64/69 = 0.927536231884058 <= X 0.975034786099515 (EXT-100 triggered for sample adequacy). |
| D — tactical activity preserved | **PASS** | Builders 1227, Bridge 1227, completed builds 1107. |
| E — competent-defender Tap | **PASS** | Surface B Tap 9/100. |
| F — frozen v0.3b observational | **PASS** | Shadow nonperturbation; real W/P/PR/free 0/0/0/0; divergence 0/100. |
| G — canonical equals measured | **PASS** | 4 surfaces, 0/100 diverged on each, summaries equal. |
| H — historical replay/defaults | **PASS** | Raw defaults unchanged. Legacy, PR8 BOTH, and Rule1-only replays intact. CURRENT/RESET/LOW callable. |

Gates A-F and H are unchanged from the Stage-2 measurement at `17e2e68`; see `docs/STAMINA_PRODUCTION_POLICY_ADOPTION_FIRST_MEASUREMENT.md`.

---

# Adoption outcome

```text
ADOPTED
canonical production stamina/recovery policy
= Rule1 ON + Rule2 OFF + LOW_WHILE_EXHAUSTED
```

Still required: PR review and explicit merge authorization.

# Debt carried forward unchanged (not solved by adoption)

- **LOW -> MEDIUM handoff oscillation.** About 93% of admissible clears re-exhaust at exactly 10 s, and every clear happens at the 35 threshold. A9 passed only as the frozen *relative* gate; absolute handoff stability is still an open design question.
- **Rule 2 additive response + provisional-hold debt.** It is active in production with Rule 2 OFF: 179 double-charge cases on E-PROD. Rule 2 stays deferred; its redesign versus permanent deferral is still open.
- Late recovery (median first clear at 240 s of 300 s). Fewer escapes and more timeouts than LOW+BOTH, as a configuration effect.
- Setup-policy debt, initiator commitment-selection policy, scoring/timeout meaning, and the player-facing contract stay open. Frontend work still waits, per the DoD.

---

# HARD STOP

Do not merge, squash, change defaults, or start frontend work without explicit user authorization.
