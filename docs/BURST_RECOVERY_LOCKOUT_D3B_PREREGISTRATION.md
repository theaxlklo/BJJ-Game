# D3-B Preregistration — One Exhausted LOW Token, Then Strict Initiation Lockout

## Status

**PROPOSED PREREGISTRATION REVISION — FROZEN AT ITS COMMITTING SHA — HARD STOP FOR REVIEW.**

This revision selects **D3-B** as the D3 candidate. It is documentation only. It becomes binding only after the user reviews this exact SHA and explicitly authorizes D3-B implementation and measurement. D3-B has not been implemented or run.

```text
D3 research + D3-A preregistration:  2fb24d56ea5a8b0be24051fd95a64b05fa61666a  (unchanged)
                                     docs/BURST_RECOVERY_LOCKOUT_D3_RESEARCH_AND_PREREGISTRATION.md
branch:                              review/burst-recovery-lockout-d3
adopted baseline (PR #10):           ee6cb6fcebb105e31224bead48a302811b27b59a
canonical policy:                    PRODUCTION_STAMINA_RECOVERY_POLICY (unchanged)
frozen digest:                       3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
D2 record:                           v1e fe229cb = D2 FAIL (criterion 4); v1f 88a01e9 = preregistered, never run
```

**Lineage.**

```text
D3-A 2fb24d5  strict Exhausted initiation lockout     preregistered, not implemented, not run;
                                                      superseded before any run
D3-B (this)   one Exhausted LOW token per episode,     selected candidate
              then strict initiation lockout
```

Review record at `2fb24d5`, user decisions:
1. Choose Family B.
2. Add a non-vacuous tactical gate (G7).
3. Adapt G3 to B's recovery timing.
4. Tighten P5: any real v0.3b enforcement fails the candidate.

The D3-A document stays unchanged as research and preregistration evidence. Its sections 1-5 (history, why D2 failed, problem definition, external references: none, engine audit) apply to D3-B unchanged and are not repeated here.

**Why B.** In the adopted affected region, the value of Exhausted LOW is front-loaded: the first Exhausted LOW (T+10) produced the most escapes, and continued LOW grinding is the debt. D3-B keeps exactly one Exhausted tactical chance per Exhausted episode, then stops the grind:

```text
Adopted:  too much Exhausted offense (LOW every window; the latch rarely clears)
v1e:      too little offense (holds from +10 s; criterion 4 FAIL)
D3-B:     clear MEDIUM, +10 s MEDIUM, one Exhausted LOW, then mandatory recovery
```

---

# 1. Evidence used to freeze populations

Source: the existing adopted-control event logs in `docs/evidence/handoff_d2_v1e_evidence.json.gz` (runs `control/42/OFF+shadow`, `control/142/OFF+shadow`). No new run was made. "Armed Exhausted entry" means the first Exhausted entry after the first clear.

- **Entry.** In all 63 matches with an armed Exhausted entry, it is the Bottom MEDIUM at clear + 10 s, from 26 to **19**.
  - 19 of those 63 entry attempts ended the match by escape (8 in the seed-42 batch, 11 in seed 142).
  - **44 matches continue past entry:** 25 in the seed-42 batch and 19 in seed 142.
- **The token window is the adopted T+10 window.** Of the 44 continuing matches, 42 reach a Bottom window at T+10 with Bottom **Exhausted at 23**, not free, and the adopted policy makes a **LOW attempt** (no RESET) there. The other 2 time out at T+10, before any Bottom window.
- **Token-window escapes in the adopted policy** (escape-attempt matches, by match index within the batch):
  - seed 42: matches **24, 48, 76** (all Reversal);
  - seed 142: match **45** (Open Guard).

**Frozen G7 population** (original-100 = seed-42 batch; matches continuing past armed Exhausted entry in the adopted prefix), **25 matches**:

```text
0, 1, 7, 12, 13, 21, 23, 24, 26, 32, 36, 38, 44, 48, 50, 51, 56, 68, 69, 74, 75, 76, 88, 90, 96
```

Adopted outcomes in this population: **10 Bottom escapes** (Reversal 4, Open Guard 5, Half Guard 1), 15 timeouts, 0 Tap.

**Frozen G3 eligible population** (continuing past entry, with at least 60 s remaining at entry), **25 matches**:

```text
seed 42:  0, 7, 12, 21, 23, 26, 38, 44, 48, 51, 56, 69, 74, 75, 76        (15)
seed 142: 6, 22, 24, 25, 27, 45, 66, 70, 92, 95                            (10)
```

Both populations are determined by the adopted prefix. D3-B's gameplay must equal the adopted gameplay up to and including the token decision (gate G6). The implementation must therefore reproduce exactly these populations; a mismatch is a G6 failure.

---

# 2. D3-B semantics (frozen)

## Scope (unchanged from D3-A)

- Bottom only, on E-PROD only: RECOVER (ESCAPE baseline), v0.2 setup ordering, v0.4a, `LOW_WHILE_EXHAUSTED`, Rule 1 ON, Rule 2 OFF, no settlement umbrella, baseline MEDIUM. Every other configuration requesting D3-B is rejected. D3-B is inactive on Surfaces A and B, and Top is never affected.
- A new opt-in diagnostic mode, separate from v1e, v1f and D3-A. v1e's code path and pinned evidence stay unchanged and reproducible.
- No change to costs, recovery amounts, behavior rates, drift rates, the 25/35 hysteresis, Recognition, response selection, settlement, setup, submission or stalling rules, or the canonical production policy.
- **Behavior is untouched.** Exhausted RECOVER Bottom already uses CONSERVE. There is no override.

## State

```text
armed           : bool  per match; True from Bottom's first Exhausted -> non-Exhausted clear
token_consumed  : bool  per Exhausted episode; reset to False whenever the latch clears
```

- An **Exhausted episode** runs from an armed latch entry (any cause: initiation spend, responder commitment, provisional hold, behavior drain) to the next latch clear or the match end.
- Every armed latch entry starts a new episode, with a fresh token.
- All state is per match and is discarded at match end. There is no timer, no other counter and no stamina grant.

## State machine

```text
UNARMED ──(first latch clear)──> ARMED_NORMAL
ARMED_NORMAL ──(latch enters Exhausted, any cause)──> ARMED_EXHAUSTED_TOKEN
ARMED_EXHAUSTED_TOKEN ──(first Bottom decision window while Exhausted:
                          token consumed)──> ARMED_LOCKOUT
ARMED_EXHAUSTED_TOKEN ──(latch clears before any Bottom decision)──> ARMED_NORMAL
                                     (structurally impossible on E-PROD: >= 25 s to recover)
ARMED_LOCKOUT ──(latch clears)──> ARMED_NORMAL
any state ──(match end)──> discarded (PENDING_AT_END recorded if Exhausted and armed)
```

## Decision at a Bottom decision window (normal or free)

The latch is read at the window: after its advance (if any) and the post-advance behavior re-choice, before action selection.

```text
if not armed or Bottom is not Exhausted:
    adopted decision, unchanged
    (unarmed Exhausted -> LOW_WHILE_EXHAUSTED; non-Exhausted -> baseline MEDIUM;
     policy.choose -> no action -> genuine RESET)

elif not token_consumed:                       # first armed Exhausted decision of the episode
    token_consumed := True                     # consumed whatever happens next
    adopted Exhausted decision, unchanged:
        request LOW; policy.choose(match)
        action    -> ordinary LOW attempt (funding, Recognition, response, settlement unchanged)
        no action -> genuine RESET via reset_window() (counted, stalling-evaluated; P5 applies)

else:                                          # token already consumed, still Exhausted
    LOCKOUT_HOLD: MountMatch.recovery_hold()   # no initiation, no spend, initiative -> Top
```

Frozen details:

- **The token is consumed by the first armed Exhausted Bottom decision of the episode,** normal or free, whether it yields an attempt or a genuine RESET. A no-action result does not preserve the token, so repeated no-action windows cannot retry it.
- **Entry inside a Bottom window.** If the latch enters Exhausted during the advance just before a Bottom window (behavior drain), that same window is the token window.
- **Entry at a Top window.** If the latch enters Exhausted during a Top exchange (responder commitment or provisional hold), Bottom's next window is the token window.
- **An UNFUNDED token LOW** (stamina below 3) is an ordinary UNFUNDED attempt. It spends 0, Rule 1 waives Top's charges, and the token is consumed.
- **After the token, until the latch clears or the match ends,** every Bottom decision window is `LOCKOUT_HOLD`. That includes free windows: the free window is consumed, there is no advance, and the lockout persists.
- **The lockout ends at the latch clear** (only `advance()` recovery can clear it). If the clear happens in the advance just before a Bottom window, that window is ordinary adopted play (ESCAPE re-choice, baseline MEDIUM). If it happens before a Top window, Bottom's next window is ordinary.
- **Defensive responses are unchanged:** response commitment, provisional holds, Rule 1 waivers, Recognition and response selection.
- **`MountMatch.recovery_hold()` is reused unchanged,** with history in `recovery_hold_history`. The collector distinguishes `TOKEN_LOW`, `TOKEN_RESET` and `LOCKOUT_HOLD`. No new engine transition or field is added. A docstring note is the only engine-file change permitted at implementation.

**Preserved by construction** (identical prefix through the token decision):
- the clear-window MEDIUM;
- the +10 s MEDIUM;
- the first Exhausted LOW (T+10).

---

# 3. Hand traces, all entry and parity cases

Rules used throughout:
- Exhausted Bottom: CONSERVE +2 per advance, i.e. +4 per 10 s at Bottom windows.
- Non-Exhausted Bottom: ESCAPE -1 per advance.
- LOW costs 3 and MEDIUM costs 7; the latch clears at >= 35.
- Top PRESSURE and UNFUNDED (as observed post-clear in all 63 matches).
- Alternating initiative, no free windows.
- T is the entry time: the time of the advance or exchange in which the latch enters Exhausted.

## Case MEDIUM entry at a Bottom window (e = stamina after the MEDIUM)

Token at T+10 (stamina e+4 -> e+1). Then holds at T+20, T+30, ...

| e | Token window | Holds (Bottom windows) | Clear | Entry -> clear | Next |
|---|---|---|---|---|---|
| **19** (from 26) | T+10: 23 -> LOW -> 20 | 24, 28, 32 | **T+50 at a Bottom window, 36** | **50 s** | MEDIUM 36 -> 29; ESCAPE 28, 27; T+60: MEDIUM 27 -> **20** (new episode) |
| **20** (from 27) | T+10: 24 -> 21 | 25, 29, 33 | **T+45 at a Top window, 35** | **45 s** | T+50: ESCAPE -> 34, MEDIUM -> 27; ESCAPE 26; T+60: ESCAPE -> **25, Exhausted by behavior drain** at a Bottom window (new episode) |
| 21 (from 28) | T+10: 25 -> 22 | 26, 30, 34 | T+45 at a Top window, 36 | 45 s | T+50: ESCAPE 35, MEDIUM -> 28; 27; T+60: 26, MEDIUM -> 19 |
| 22 (from 29) | T+10: 26 -> 23 | 27, 31 | T+40 at a Bottom window, 35 | 40 s | MEDIUM -> 28; 27, 26; T+50: MEDIUM -> 19 |

## Case behavior-drain entry inside a Bottom window (e = 25; token in the same window)

| e | Token window | Holds | Clear | Entry -> clear | Next |
|---|---|---|---|---|---|
| **25** | T: 25 -> LOW -> 22 | 26, 30, 34 | **T+35 at a Top window, 36** | **35 s** | T+40: ESCAPE 35, MEDIUM -> 28; 27; T+50: 26, MEDIUM -> **19** |

## General bound (any entry, including responder-caused)

With the token LOW spending 3, the latch clears after `n = ceil((38 - s_tokenbase)/2)` Exhausted advances, counted from the stamina at entry. Here `s_tokenbase` is the entry stamina for drain or Bottom-window entries, and the stamina after the first advance for Top-window entries.

- For MEDIUM entries at a Bottom window: **clear within 60 s ⇔ e >= 14**. A token RESET (no spend) or an UNFUNDED token clears sooner.
- Entries at 13 or below are reachable only through funded responder or provisional-hold charges. **None was observed post-clear** (204 Top attempts, 0 charged). These would be late (G3 failures).

## Traced steady state (from the first armed entry)

```text
episode e=19 (60 s) -> episode e=20 (60 s) -> drain episode e=25 (50 s) -> e=19 ...
```

- **Super-cycle:** 170 s with 3 episodes; 5 MEDIUM attempts, 3 token LOW attempts and 9 lockout holds out of 17 Bottom windows (8 attempts out of 17).
- **First episode** (entry 19 at clear+10): Bottom windows clear+20 = LOW, clear+30 / +40 / +50 = holds, clear+60 = the clear window, MEDIUM at 36.
- **Compared with D3-A:** one extra attempt (the first Exhausted LOW), 10 s longer recovery (50 s instead of 40 s), and 3 holds in both.

---

# 4. Expected tactical effects and predictions (recorded before any run)

**Gameplay identical by construction** up to and including the token decision of the first armed episode. Preserved exactly:
- all pre-clear outcomes;
- all clear-window and +10 s MEDIUM escapes, including the **18 escapes v1e lost**;
- the **4 adopted T+10 Exhausted LOW escapes** (seed-42 matches 24, 48, 76; seed-142 match 45).

Original-100 consequences:

- **P4** (global, unchanged):
  - escapes: 25 preserved before the token, plus 3 at the token = **28 preserved by construction** (>= 25 met);
  - timeouts: at most 45 + 22 = 67 (<= 70 met);
  - Tap: 5 fixed, plus any new Taps among 22 matches (fails only with >= 5 new Taps);
  - Half / Open / Reversal: the preserved 15 / 5 / 8 split is within tolerance.

  As in D3-A, **P4 is effectively satisfied by construction**. The tactical test is G7.
- **G7:** 3 of the 25 frozen matches end in a Bottom escape by construction (24, 48, 76). **D3-B must produce at least 2 more escapes among the remaining 22 matches.** Those matches had 7 adopted escapes: Exhausted LOW at T+20 (3 Open), T+30 (1 Open, 1 Reversal), T+40 (1 Open), and a non-Exhausted MEDIUM at T+140 (1 Half). All 7 come after the token, in windows D3-B holds or reaches from a different state.

**Predicted risk for G7, material.** D3-B's later chances are its post-lockout MEDIUM bursts:
- at clear+60 and clear+70 in the first cycle, which needs the first entry at 240 s or earlier to fit (a Bottom window at 290 s at the latest);
- and later cycles.

During a lockout, Bottom holds instead of attacking, while Exhausted CONSERVE drifts the axis +0.75 per 5 s toward Top. Post-lockout MEDIUMs will therefore often start in STRONG/LOCKED (-1 positional modifier for Bottom). The closest measured analogue is v1e's post-release MEDIUMs: **3 escapes in 92 attempts**, mostly from Locked/Strong. About 13 matches in the frozen population leave room for at least one post-lockout burst. At that rate, the expected additional escapes are **about 1**, against **2 required**. **G7 is predicted to be at material risk of FAIL.** This estimate is recorded before the run; it is not a gate value, and the gate stays as frozen.

**G3** (traced): every eligible first episode enters at 19 and clears at 50 s, or ends earlier through a token escape (seed-42 matches 48 and 76 and seed-142 match 45 are eligible token escapes). The only predicted failure source is a funded Top charge during the episode. **Predicted near 25/25.**

**P5:** lockout holds cannot cause a stalling offense. A token RESET is a genuine RESET, but the adopted logs show the token window always yields an attempt (42/42). Bottom's clock is zeroed when it is the engaged defender of Top attempts during the lockout. **Predicted 0 real offenses**, at risk only if a later genuine RESET finds an accumulated clock.

**Drift, compared with the adopted policy:**
- **During the lockout:** both policies use CONSERVE. The adopted LOW attempts can push the axis back toward Bottom; D3-B's holds do not. D3-B is likely tighter (more STRONG/LOCKED).
- **After the clear:** D3-B uses ESCAPE (+0.50) while the adopted Bottom stays Exhausted on CONSERVE (+0.75), about -0.5 axis per 10 s toward Top relative to adopted.
- **Net effect:** to be measured.

**Cycling:** the steady-state super-cycle of section 3 (episodes about every 50-60 s). The adopted policy re-cleared in only 1/63 matches.

---

# 5. Gates (frozen)

All mandatory gates must pass for a D3-B design-gate PASS. Any failure means **FAIL**: record it and STOP, with no tuning and no gate change. Inadequate or missing evidence means **OPEN**. Unit, checker and CI PASS never soften a FAIL or an OPEN.

## Preservation (mandatory)

| ID | Gate |
|---|---|
| P1 | Surface A exactly 78 Threat matches / 1,950 Threat entries / Tap 0; Surface B Tap 9/100; D3-B rejected (inactive) on non-RECOVER surfaces. |
| P2 | Rule 1: zero responder commitment and zero provisional hold charged on unfunded-initiator exchanges. Rule 2 OFF: hold covered by response = 0. |
| P3 | Bottom stamina in [0,100]; no fabricated recovery (every increase is a CONSERVE behavior gain); no negative cost; original-100 Bottom final median >= 29. |
| P4 | Original-100 E-PROD: escapes >= 25; Half Guard 16 +/-10, Open Guard 10 +/-10, Reversal 9 +/-10; timeouts <= 70; Tap <= 9. Evaluated on OFF + shadow and ON; both must pass. |
| **P5** | **Tightened.** Original-100 RESET-with-progress-route exposure <= 23/100. Real v0.3b warning = 0, penalty = 0, position reset = 0 **in every candidate E-PROD run (both seeds, ON)**. Any real offense means **P5 FAIL**, whatever triggered it, and its cause is reported in full. OFF/ON gameplay divergence 0/100 in both batches. |
| P6 | Frozen digest exact; full unit suite, semantic checker and legacy entry point PASS; exact-head CI on Python 3.11 and 3.13; deterministic replay (full gameplay identity); observer ON/OFF identity; `recovery_hold()` invoked only by the v1e and D3-B modes; `recovery_hold_history` empty on every non-candidate surface; **v1e reproduces its recorded `fe229cb` evidence exactly** (existing pinned tests unchanged). |
| P7 | D3-B diagnostic entry points equivalent (effective settings and gameplay); the canonical production entry point equals the adopted controls and is unchanged; `PRODUCTION_STAMINA_RECOVERY_POLICY` unchanged. |
| P8 | All historical evidence preserved: D1, D2 v1-v1f, the v1e FAIL record, the D3-A preregistration, adoption records. |
| P9 | Anti-removal floors: clearing matches original >= 40 and pooled >= 75; first-clear median <= 250 s, original and pooled. Expected identical to adopted (45 / 82 / 240 s). |

## D3-B gates

| ID | Gate | Status |
|---|---|---|
| **G1** | **No Bottom initiation spend during lockout.** In every episode, after the token decision and until the latch clears or the match ends, Bottom initiation stamina spend = 0 (LOW, MEDIUM, HIGH, setup builders, UNFUNDED, any Bottom-initiated action). The token attempt itself is the one permitted spend. | MANDATORY |
| **G2** | **Token and lockout exactness.** At every armed Exhausted Bottom decision window: the first window of each episode is the token decision (`TOKEN_LOW` or `TOKEN_RESET`), and every later one is `LOCKOUT_HOLD`. Exactly one token decision per episode that reaches a Bottom window. 0 lockout holds while non-Exhausted or unarmed. 0 Bottom attempts or RESETs after the token while Exhausted. | MANDATORY |
| **G3** | **Bounded recovery after the token.** Population: each match's first armed Exhausted episode where the match continues past entry, pooled over both seeds, evaluated separately for OFF + shadow and ON (both must pass). Eligible if at least **60 s** remain at entry (frozen list, section 1). Adequacy: at least **20** eligible, otherwise OPEN. **Success:** the permitted token LOW produces a Bottom escape (successful terminal resolution), **or** the latch clears within **60 s** of entry (inclusive). **Failure:** Tap before the clear; timeout before the clear; any other non-Bottom terminal outcome before the clear; latch still Exhausted 60 s after entry. Requirement: at least **80%** successes among eligible episodes. | MANDATORY |
| G4 | Lockout clear to next armed Exhausted entry: full distribution, plus the share within 10 s. | REPORTED |
| G5 | Episodes per match (distribution, median, p90, max); episode durations (minimum, median, maximum). Every completed episode shorter than 25 s, or ending without a latch clear, is listed. | REPORTED |
| **G6** | **Prefix identity and burst preservation.** For every match and both stalling modes, the D3-B event log equals the adopted control's up to and including the first armed episode's token decision (the token attempt's outcome included). The frozen G3 and G7 populations are reproduced exactly. All 18 adopted +10 s MEDIUM escapes v1e lost, and the 4 adopted T+10 token-window escapes, are present. | MANDATORY |
| **G7** | **Affected-match tactical retention.** Population: the frozen 25 original-100 matches (section 1). At least **5 of the 25** must end in a Bottom escape (Half Guard, Open Guard or Reversal; any type counts) under D3-B. Tap and timeout do not count. Evaluated on OFF + shadow and ON; both must pass. Rationale: the adopted policy produced 10 escapes in this population, and D3-B must keep at least 50%. Together with the 25 prefix-preserved escapes, this implies at least 30 original-100 escapes, without rewriting P4. | MANDATORY |
| G6r | Seed-matched attribution, adopted vs D3-B and v1e vs D3-B (section 6). | REPORTED |

G3 values `60 s / 20 / 80% / 60 s`, user-chosen:
- 25 eligible first episodes are known from the adopted prefix, and a floor of 20 gives a real sample without equalling the maximum.
- The traced recovery is 50 s (worst case for MEDIUM entries), so 60 s gives one 10 s interval of tolerance.

D2 criteria 9-11, 13 and 16 are not D3 gates. D3-B intentionally re-exhausts at +10 s, and has no D2-style recovery-hold mode.

---

# 6. Required diagnostics (mandatory reporting; descriptive)

All D3-A section-13 diagnostics apply: episode records, per-opportunity lockout records including the inert counterfactual adopted request and action, the stamina ledger by source, recovery records, tactical effects, positional drift and band, seed-matched attribution, and traced prediction against reality. In addition:

- **Token:**
  - token decisions per episode: `TOKEN_LOW` vs `TOKEN_RESET`; action, requested and effective commitment, grade, band;
  - immediate exits by type;
  - setup activity from the token (builder, advance, Ready);
  - token windows that were free windows.
- **G3 breakdown:**
  - permitted-LOW escapes;
  - surviving episodes after the token;
  - surviving episodes clearing within 60 s, and late clears (with their entry stamina and cause);
  - Top terminal outcomes before the clear (Tap or exit);
  - timeouts before the clear.
- **Entry-case table:** episodes by entry stamina and cause (MEDIUM at 19/20/21/22, drain at 25, responder/provisional-hold entries), each with its measured entry-to-clear time against the section-3 trace.
- **G7 breakdown:** for each of the 25 frozen matches: adopted outcome, D3-B outcome, v1e outcome, the escaping attempt (time from clear and from entry, decision kind, commitment, band), and the D3-B post-lockout MEDIUM count and the band at each.
- **Fate of the 7 post-token adopted escapes** in the G7 population, and of the 1 non-Exhausted T+140 escape.
- **Seed-matched attribution (G6r):**
  - complete match-by-match transition tables, adopted vs D3-B and v1e vs D3-B;
  - escape preserved, lost or new;
  - timeouts recovered relative to v1e;
  - new timeouts;
  - Tap changes;
  - exit-type changes.
- **Steady state:** measured super-cycle composition against section 3 (episodes by entry stamina, MEDIUM / token LOW / hold counts per Bottom window).

# 7. Sampling and denominators

- **Candidate:** E-PROD, base seeds 42 and 142, 100 matches each, 300 s, stalling OFF + shadow and ON, with D3-B enabled.
- **Comparators** on the same seeds and stalling modes: the adopted canonical controls, and v1e as frozen (reproduced and checked equal to `fe229cb`).
- **No:** exploratory seeds, extensions, seed replacement, tuning, outcome exclusions, or reruns because a result looks unfortunate. A scoring-code bug may be fixed and rescored only with gameplay identity re-verified, and the fix must be recorded.
- **Original-100** means base seed 42. **Pooled** means both seeds, 200 matches, with seed-142 indices offset by 100 in pooled tables (the frozen lists in section 1 use within-batch indices).

# 8. Planned implementation surface (for review; not implemented)

- A new opt-in batch mode value, for example `D3B_EXHAUSTED_TOKEN_LOCKOUT`, with the configuration validation above. v1e and its pinned evidence stay unchanged.
- One per-match `armed` bit and one per-episode `token_consumed` bit in a batch-side controller. The decision hook described in section 2. No pre-advance override, no new engine code (docstring note only), `recovery_hold()` reused.
- A read-only collector extension: decision kinds `TOKEN_LOW` / `TOKEN_RESET` / `LOCKOUT_HOLD`, episode records, stamina-ledger sources, the inert counterfactual adopted action.
- **Synthetic unit tests, written and committed before the frozen run,** pinning:
  - the e=19 / 20 / 21 / 22 / 25 traces of section 3;
  - token consumption on attempt and on RESET;
  - no token retry;
  - a free-window token and a free-window lockout;
  - responses unchanged during the lockout;
  - lockout only while armed and Exhausted;
  - no RNG, RESET or stalling history from holds;
  - prefix identity against the adopted policy through the token;
  - inertness outside D3-B.

# 9. Hard-stop rules

After this commit: **HARD STOP** for review of this exact SHA and explicit D3-B authorization. After any D3-B evidence: HARD STOP again.

**Not authorized here:**
- D3-B or D3-A implementation, or any candidate run, including exploratory seeds;
- any change to `MountMatch`, `handoff_policy.py` or batch code;
- any change to v1e or its evidence;
- v1f implementation or measurement;
- D2 criteria changes;
- canonical production policy or raw default changes;
- PR #10 changes or merge, squash, force-push;
- Rule 2, setup-policy or commitment-selection work;
- frontend work.
