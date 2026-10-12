# Match incentives and Heart of a Lion — owner decisions

**2026-10-12 — owner-approved gameplay direction; DOCUMENTATION ONLY; not implemented or balance-qualified.**
This is a future rules specification, not a change to the B1e-qualified engine, frozen Python reference, default graph, F0/F1, fixtures, oracle, match numbers or CI. Engine changes require a separately approved, opt-in implementation slice.

## Sources and scope

- Game-wide match rules: [Master Development Guide §§40–42](../../docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md).
- Integrated B1e evidence: [MATCH_FLOW_DIAGNOSTICS.md](MATCH_FLOW_DIAGNOSTICS.md). In particular, pass-only and both-at-zero no-progress cases occur because score/penalty and recovery rules do not yet exist; B1e is **not** a gameplay balance result.
- Reference for the **IBJJF-specific** stalling and scoring interpretation: [archived June 2024 IBJJF Rules Book v6.1](https://www.ligabjj.com/ibjjfrules/2024JUN_IBJJF_Rules_EN.pdf), Articles 6.2.1, 7.2.1, 7.3.1. Pin and review the applicable current official edition and division before shipping. Nothing in this document certifies IBJJF compliance.
- Momentum and Heart of a Lion are **game-original modifiers**, **not** IBJJF rules. They require explicit opt-in or a labeled custom ruleset; a faithful/strict IBJJF preset cannot silently enable them.

## 1. Stalling — game-specific third-turn trigger, IBJJF-inspired consequence

**Updated owner decision (2026-10-12):** The intended game's activity rule is **NOT** the official IBJJF inactivity threshold. To keep the video-game match moving, the **third consecutive personal turn spent without meaningful offensive or defensive activity triggers a stalling penalty**. A fighter may be inactive for two of their own consecutive turns without a penalty; the third is punishable. Count the streak **separately by stable fighter ID**, across position changes, not as three global windows (initiative can be unequal). A consumed normal decision is eligible for evaluation; a rejected command, sealed-but-unresolved feint, or mere UI observation is not a turn.

| Inactivity streak for one fighter | Target game rule |
| --- | --- |
| First consecutive inactive personal turn | Allowed |
| Second consecutive inactive personal turn | Allowed; visible impending-penalty warning is a presentation proposal |
| Third consecutive inactive personal turn | **Stalling penalty event** |
| Further inactive turns | Repeated-offense cadence and reset behavior remain **open**; do not invent a counter reset or extra penalty |

Meaningful engagement resets or prevents the inactivity streak under a **future, explicit activity classifier**. Real attack, escape, and legitimate defense attempts must not be treated as stalling *simply because they fail*, even when exhausted. Meaningless action spam must not reset it. An ordinary pass or deliberate rest without progress is an **inactive** turn, unless a separately defined legitimate defensive context exempts it. A player with no legal defense must not be automatically punished for an opponent's unanswerable action; referee/defense exemptions still require definition.

**Penalty consequence, deliberately distinct from official timing:** Carry forward the owner's IBJJF-*inspired* penalty progression as the proposed match scoring policy: 1st penalty recorded; 2nd awards opponent one advantage; 3rd awards opponent two points; 4th disqualifies. These are **not** negative positional-point deductions. Integrating inactivity offenses with any other foul penalties, handling repeated third-plus inactive turns, and all exceptions require a separate ruleset decision before code. Momentum is a separate non-scoring benefit, not an automatic point penalty.

**Reference only — not this game's trigger:** The archived [June 2024 IBJJF Rules Book v6.1](https://www.ligabjj.com/ibjjfrules/2024JUN_IBJJF_Rules_EN.pdf), Articles 7.2.1 and 7.3.1, describes the cumulative penalty structure and an applicable **20 consecutive seconds** of lack of combativeness. The owner explicitly chose the game-specific **third-personal-turn** threshold instead. Call this mode **custom game stalling with IBJJF-inspired scoring**, not a faithful IBJJF inactivity implementation. An optional strict IBJJF mode, if supported later, must retain its own accurate referee/timing/exemption rules; this specification does not modify that mode.

**Not yet frozen:** activity classifier per position, forced holds/emergency defenses, whether a successful defense immediately clears the count, warning UX, ledger integration, scoring consequence of repeat penalties, referee tie handling, and the effect of simultaneous initiative. Do not make positional transitions or award points merely because a window passed.

## 2. Momentum — opponent's passive time becomes an opportunity

**Approved direction:** When fighter A truly stalls under the future activity classifier, fighter B may build **Momentum** representing time to set up a stronger **next eligible attack**. Momentum is a non-scoring gameplay advantage and should reward exploiting an opening; it does not directly move the axis, grant extra initiatives/windows, or count as an IBJJF penalty. Each fighter's source events and pending benefit must be traceable in deterministic match-level state.

**Suggested shape, NOT frozen:** A bounded buff affecting an attack's effective result/grade, consumed on a qualifying legal accepted attack. This suggestion is **not** approval of a +1 modifier, an accumulation ladder or a duration.

**Still open:** precise gain trigger (warning versus adjudicated stalling), strength, maximum stacks, expiration across positions, what counts as the “next attack,” fallback/feint interactions, consumption on failure, defensive/timeout paths, simultaneous-turn resolution, and eligibility in points versus custom submission-only modes. No modifiers, formulae or menu entries are authorized by this specification.

## 3. Heart of a Lion — once-per-match mutual exhaustion event

**Approved owner behavior**
1. Trigger **only when both fighters are at exactly zero stamina** in an eligible, still-active match state. “Both at zero” means both current stamina pools read 0 at one authoritative boundary; it does **not** require both to have reached zero on the same exchange. The existing **Exhausted** latch at nonzero stamina is **not** sufficient.
2. Immediately restore **50% of each fighter's own maximum stamina**. Ordinary commitment funding, stamina expenditures and exhaustion-latch semantics continue; no cost is waived.
3. Give **each fighter five of their own normal completed decision turns**: ten individual fighter turns in total, possibly spread across more or fewer than ten global decision-window boundaries depending on initiative/position flow. This is a count of existing legal opportunities, **not** ten invented windows or an alteration of match time.
4. Once **both fighters have completed five counted turns**, restore each surviving fighter to **100% of their own maximum stamina** at the next authoritative settlement boundary, then proceed normally.
5. **Once per match**, including across positional transitions. Never re-arm after re-depletion. An ended match, tap, expiry of the regulation clock or unsupported-transition halt cannot grant extra actions or force full restoration.

**Confirmed safeguards**
- Neither activation nor completion opens a window, advances the clock, inserts an attack, resumes an ended match, alters the position/roles, or bypasses submissions and penalties.
- Legal failed actions are **not automatically** adjudicated as stalling, especially when an athlete has insufficient stamina. Ordinary stalling is a different match-policy system.
- No repeat activation; no mutually exhausting to farm refills.

**Implementation requirements (proposed contract, NOT code approval)**
- Store once-only `consumed` and phase (`inactive`/`active`/`completed`) at the **match owner**, plus a five-turn remaining counter keyed by stable fighter ID. Preserve these across position changes, unchanged on rejected commands, seal-only or read-only calls.
- Count only **accepted, resolved normal personal decision turns**. Rejections, viewing menus, merely sealing feint intent, and unresolved protocol phases **do not** count. Whether an accepted D3-B hold, ordinary pass, simultaneous decision or specialized controller opportunity counts needs an explicit test matrix prior to code; do not assume one window equals one fighter turn.
- Apply state changes **once**, at deterministic settlement boundaries, with explicitly reviewed order relative to normal costs, score, terminal outcomes, transitions and exhaustion-latch recomputation. No direct UI or frame-driven mutation.
- Define integer rounding for capacities where 50% is fractional (normal 100-capacity examples do not settle it); maintain stamina bounds and ordinary exhaustion hysteresis. Do not create float/nondeterministic stamina.
- Remain inactive in strict IBJJF configuration unless the user explicitly chooses a **modified** game ruleset. The player's conceptual rule is approved; its ruleset activation policy needs owner sign-off before implementing.

## 4. After Heart of a Lion is spent — zero-stamina last-resort choices

**Owner-approved contingency:** If **both fighters are at exactly zero stamina** and Heart of a Lion's one-time phase has **fully completed** (and cannot reactivate), the match must not be left with an unplayable zero-stamina menu. While this mutual-zero condition holds, give each fighter legal, position-appropriate last-resort choices:

- **Eligible LOW memories** (the lowest-commitment versions of learned techniques) may still be *attempted* as meaningful actions at zero stamina, subject to positional/technique legality and available defenses. A legal attempt does not become stalling simply because it fails. These are not free automatic wins, extra turns or bypasses of submission defense.
- **REST** may be selected for up to **two consecutive personal turns** without a stalling penalty. Rest consumes the fighter's existing normal turn and match time, counts as inactivity, and does not grant a bonus window. The **third consecutive inactive/rest turn** triggers the game-specific stalling penalty in §1. Rest should restore some capacity only if a separately approved deterministic rest-economy rule defines an amount; none is set here.

**Important implementation incompatibility:** the current LOW funding cost is **3 stamina**, so a zero-stamina LOW-memory attempt is *not already legal* in the B1e engine. The new exception needs an explicit future admission/funding and grading rule: how to allow a qualifying LOW memory at zero, with what exhaustion disadvantage/cost (if any), without making all LOW attacks indefinitely free or bypassing ordinary commitment rules. Likewise Half Guard v0 currently has **no recovery action**; this document does not secretly grant REST recovery or claim it exists. The Memory system's concrete metadata/eligibility interface also remains unimplemented.

The stalling streak is shared across all inactivity/rest decisions by a fighter; alternating REST with meaningless passes does **not** erase it. Only meaningful activity under the future classifier can clear it. Whether fallback eligibility continues when one fighter regains stamina, and exactly when REST restoration occurs relative to the inactivity penalty, remain design questions. There is no reactivation of Heart of a Lion.

## 5. Regressions and first implementation slice

Before coding, resolve open numeric and ordering questions; introduce no rule without reviewed tests. Recommended independent, opt-in gates:

1. **Game stalling and referee accounting:** personal inactive turns 1/2/3; alternating unequal-initiative windows; distinct fighters' counters; valid defense, exhausted but real failed effort, pass spam and REST spam; penalty trigger exactly on third, with repeat-offense behavior separately approved; score/advantage/penalties ledger field-by-field; no forced transition while Standing is absent. If strict IBJJF mode is added, test its time-based thresholds separately.
2. **Momentum:** non-stalling opponent's benefit, no double awards, no bonus windows, test feint/timeout/direct indistinguishability from the defender's public view, saturating grade if adopted, deterministic replay.
3. **Heart of a Lion:** zero/zero versus zero/nonzero/latch-only; activation once; each fighter's own five turns under nonuniform initiative and changing positions; rejected and sealed inputs excluded; no clock or token changes at a refill; no triggers after ended/halted; cap/rounding/hysteresis; replay and match-owner continuity.
4. **Mutual-zero contingency:** completed versus available/active Heart of a Lion; both zero versus one zero; eligible and ineligible LOW memories, positional legality, explicit zero-funding exception, regular stamina costs elsewhere, REST turns 1/2/3, no recovery without approved numeric rule, penalty counters and status freeze. Test finite ability to act, deterministic replay and non-stalling legitimate failures.
5. **Measurement:** keep the B1e harness and baseline reports unchanged; run new opt-in populations separately. Do not gate a policy-dependent frequency or silently retune frozen evidence.

**Separate question:** Ordinary, repeatable stamina conservation in Half Guard is still a distinct design decision. Heart of a Lion is a rare once-only emergency mechanic, not a substitute for a deliberate recover/conserve action.
