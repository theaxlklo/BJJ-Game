# Match incentives and Heart of a Lion — owner decisions

**2026-10-12 — owner-approved gameplay direction; DOCUMENTATION ONLY; not implemented or balance-qualified.**
This is a future rules specification, not a change to the B1e-qualified engine, frozen Python reference, default graph, F0/F1, fixtures, oracle, match numbers or CI. Engine changes require a separately approved, opt-in implementation slice.

## Sources and scope

- Game-wide match rules: [Master Development Guide §§40–42](../../docs/BJJ_GAME_MASTER_DEVELOPMENT_GUIDE.md).
- Integrated B1e evidence: [MATCH_FLOW_DIAGNOSTICS.md](MATCH_FLOW_DIAGNOSTICS.md). In particular, pass-only and both-at-zero no-progress cases occur because score/penalty and recovery rules do not yet exist; B1e is **not** a gameplay balance result.
- Reference for the **IBJJF-specific** stalling and scoring interpretation: [archived June 2024 IBJJF Rules Book v6.1](https://www.ligabjj.com/ibjjfrules/2024JUN_IBJJF_Rules_EN.pdf), Articles 6.2.1, 7.2.1, 7.3.1. Pin and review the applicable current official edition and division before shipping. Nothing in this document certifies IBJJF compliance.
- Momentum and Heart of a Lion are **game-original modifiers**, **not** IBJJF rules. They require explicit opt-in or a labeled custom ruleset; a faithful/strict IBJJF preset cannot silently enable them.

## 1. Stalling — IBJJF penalties, not direct points deducted

**Owner clarification:** “Point deduction” meant the **IBJJF penalty process**: stalling can eventually award advantages or points to the opponent, or disqualify the offender. It **does not** mean subtracting one positional point from the staller on each turn.

For the archived June 2024 **adult** reference:
 
| Cumulative penalty | Result |
| --- | --- |
| First | Record a penalty against the offender. |
| Second | Record penalty; award **one advantage to opponent**. |
| Third | Record penalty; award **two points to opponent**. |
| Fourth | **Disqualify** offender. |

The cited reference, Article 7.3.1, counts **20 consecutive simulated seconds** of applicable lack of combativeness, rather than a literal third turn. Penalties for serious fouls and lack of combativeness accumulate under the reference. When **both** athletes receive their third lack-of-combativeness penalty, the reference calls for a restart standing; Standing/reset support is not implemented, so do **not** invent a positional hop or fake a match result.

The owner's earlier “more than two consecutive stalling turns” idea can be explored as a **visible early warning or detection heuristic** only. Its use remains **open**, and it must not override the configured IBJJF 20-second penalty threshold.

Progress matters rather than button activity: ineffective button spam is not automatically productive; legitimate failed efforts, emergency defense, or exhaustion by themselves are not automatically stalling. Stalling attribution needs position- and ruleset-specific simulated-clock evidence, including the IBJJF exceptions (for example a mount/back-control holder and a defender of an active dominant-position attack may be exempt under the referenced provisions).

**Not yet defined:** exact per-position classifier, warning UI, simulated-seconds accounting through interrupted windows, rulebook version/division policy, penalty ledger, and automatic referee criteria. Do not gate gameplay on an invented “two turns = penalty” mechanic.

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

## 4. Regressions and first implementation slice

Before coding, resolve open numeric and ordering questions; introduce no rule without reviewed tests. Recommended independent, opt-in gates:

1. **Stalling and referee accounting:** 19/20/21-second boundaries, valid defense, real but failed effort, pass spam, status freeze and third/combined penalty handling; score/advantage/penalties ledger field-by-field, no forced transition while Standing is absent.
2. **Momentum:** non-stalling opponent's benefit, no double awards, no bonus windows, test feint/timeout/direct indistinguishability from the defender's public view, saturating grade if adopted, deterministic replay.
3. **Heart of a Lion:** zero/zero versus zero/nonzero/latch-only; activation once; each fighter's own five turns under nonuniform initiative and changing positions; rejected and sealed inputs excluded; no clock or token changes at a refill; no triggers after ended/halted; cap/rounding/hysteresis; replay and match-owner continuity.
4. **Measurement:** keep the B1e harness and baseline reports unchanged; run new opt-in populations separately. Do not gate a policy-dependent frequency or silently retune frozen evidence.

**Separate question:** Ordinary, repeatable stamina conservation in Half Guard is still a distinct design decision. Heart of a Lion is a rare once-only emergency mechanic, not a substitute for a deliberate recover/conserve action.
