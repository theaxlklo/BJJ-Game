# Tactical preparation, feints and defensive counterplay (game-wide design)

**Status: DESIGN PROPOSAL (HG-26 direction). The direction is owner-approved; every number, rule, name, schema and code below is a proposal until the owner accepts it
by decision id.** The owner has **provisionally approved** the Half Guard v0 prototype choices (two local readiness tracks `top_base` and `bottom_frame`, `None/Partial/Ready` starting
`Partial/Partial`, option M with Knee Shield and Knee Pin as the governed counters, preparation and defensive effort in B1b, feints in later B1g/B1h). **These are Half Guard prototype
choices, not frozen game-wide numerical rules.** This document describes a **conceptual contract** that each position may adopt. It adds no runtime interface, base class, registry, shared
data format or code, and it changes no Mount behavior. Position-local rules (techniques, conditions, costs, outcomes, information timing) live in each
position's own proposal; the first is `HALF_GUARD_V0_PROPOSAL.md` §12 (HG-26A–F).

Depends on: `AGENTS.md` (determinism, stable identity/role/authority/initiative, no unapproved mechanics), Master Guide v10.4 §§5.2a (decision windows), 7,
15–17, 20, 21 (setup progress), 22 (commitment), 27 (feints), 58A–58B (memories), `EXCHANGE_SETTLEMENT.md`, `POSITION_CONTRACT.md`, `POSITION_GRAPH.md`,
`HALF_GUARD_V0_PROPOSAL.md`.

## 1. Owner-approved direction and non-negotiable constraints

Three interconnected concepts, intended for every applicable position (Standing, guards, Side Control, Mount, Back Control and others):

1. **Positional preparation** — build, maintain, weaken or remove the physical conditions that techniques and defenses need.
2. **Feints** — commit to a deceptive *apparent* technique, then execute a different *real* technique, possibly drawing an inappropriate response.
3. **Defensive effort** — powerful counters need appropriate preparation and may carry stamina or positional tradeoffs.

Constraints that apply to every position that adopts them:

* **No random chance.** Every outcome is a function of public state, sealed commands and published tables (Guide §20: no hidden dice).
* **No frame-rate, animation or wall-clock effect on any decision.** Deadlines and timeout fallbacks are session-layer metadata (Guide §5.2a); the simulation consumes
  resolved commands only.
* **No automatic combo chain and no free extra turn.** A feint is **one logical exchange**: its apparent and real phases are internal to one resolution. They produce no
  extra decision window, no extra initiative, no extra clock advance and no separate history exchange.
* **Preserve stable identity, role, authority and initiative as distinct** (`AGENTS.md`). Preparation belongs to a *fighter*, addressed through the current role map.
* **Existing funding and exhaustion rules are not bypassed.** Costs use the position-independent commitment policy (LOW/MEDIUM/HIGH → 3/7/12 under the current
  cost policy; funding downgrades to what the pool can afford; unfunded handling; the Exhausted modifiers).
* **No unapproved mechanics become approved by being documented here.** Technique memories, Fight IQ, recognition tiers and game plans are not approved (see §9).

### 1.1 Relationship to Guide §27 (an explicit, owner-approved departure)

Guide §27 states a *preferred* feint model: "a feint is a real low-commitment threat", with the UI never lying, a cheap threat answerable by a cheap defense, no
progress beyond a first threat stage at low commitment, and no nearly free stamina drain by repeated feints. The owner direction (apparent technique, different real
technique, hidden until the defender commits) **replaces the preferred model for positions that adopt it**. This proposal keeps the safeguards of §27 where they remain
meaningful:

| §27 safeguard | How the proposal keeps it |
| --- | --- |
| The UI does not lie | The public view states the truth: the *apparent* technique, the public cues and — if GP-2 is accepted — the list of real techniques this fighter is *currently eligible* to conceal. It never labels the apparent technique as the real one. |
| A cheap threat is answerable cheaply | A feint costs its commitment cost plus a separately funded surcharge (§5.4; candidate +3), so a LOW feint (6) is answered by a LOW response (3) at no undercommitment penalty and still costs the attacker more. Optional rule HG-26E-4: a LOW-effective feint cannot cause a position exit. |
| Repeated feints are not a free drain | The attacker pays the surcharge on every feint, the defender does not; a *called* feint also costs the attacker progress (§6.3); an unfunded feint is refused (so Rule 1 cannot make it free). |

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Condition** | A named, per-fighter, per-position state that techniques or responses read (for example a pressure base or a frame structure). Declared by the position. |
| **Tier** | The ordinal value of a condition. Default vocabulary: `None` < `Partial` < `Ready`, exactly the Guide §21 names and the Mount `americana_tier`/`trap_tier` precedent. Integers `0..2`. |
| **Direct technique** | A technique resolved from the published raw-grade table without reading any condition. Always available when the position's own legality allows it. |
| **Prepared technique** | A technique whose grade, eligibility or outcome reads a condition the acting fighter must have built. Preparation is *advantage*, never a precondition for being legal (all legal defenses stay accessible, `AGENTS.md`). |
| **Builder / weakener / consumer** | An accepted exchange that raises one's own condition, lowers the opponent's condition, or spends a condition when a prepared technique is attempted. |
| **Defensive readiness** | A condition that a *response* reads. A **powerful response** is one whose strength is governed by readiness. |
| **Defensive effort** | The price of a powerful response: the responder's chosen response commitment (existing LOW/MEDIUM/HIGH) and the wear the response puts on its own condition. |
| **Apparent technique** | The technique the defender is shown. |
| **Real technique** | The technique that actually resolves; equal to the apparent technique for a direct attack. |
| **Sealed intent** | The attacker's committed command, held privately by the executor until the defender's response is committed. |
| **Bite** | The defender's response is a best counter to the *apparent* technique (the response the apparent threat invites). |
| **Call** | The defender's response is a best counter to one of the real techniques the attacker is eligible to conceal. |
| **Balanced response** | A response whose worst-case result across the direct apparent technique and every eligible feint is acceptable (≤ 0 for the attacker). |
| **Public view** | The detached, closed-schema snapshot a controller may read (§7.2). |

## 3. The conceptual contract a position declares when it adopts the concepts

This is a **checklist for a position proposal**, not an interface. A position that adopts preparation, defensive effort or feints states each item in its own document,
with deterministic values:

1. **Conditions:** the list, the owning fighter side, the tier meaning, the entry value and any decay/hysteresis (a position without drift states "no decay").
2. **Readers:** which techniques are *prepared* (and the per-tier grade shift) and which responses are *powerful* (and the per-tier shift), plus the order of the shifts in
   the grade pipeline (shifts are applied sequentially and saturate at each step, as the existing settlement does).
3. **Writers:** which accepted exchanges build, weaken, remove or consume which condition, under what outcome threshold, and the floor/ceiling.
4. **Defensive effort:** how response commitment and condition wear price a powerful response, and what a successful defense does.
5. **Feint table:** the *explicit* list of eligible apparent→real pairs, each with required conditions and the side that may use it. Pairs are not derived automatically.
6. **Counterplay proof:** for every eligible apparent technique, at least one response that holds the attacker to a bounded result whatever mode was chosen (§6.4).
7. **Information model:** alternating or simultaneous, and which facts are public (§7).
8. **Funding rules** for feints (§5.4) and the unfunded policy.
9. **Test obligations** (§8) including indistinguishability and anti-peeking.

**Generalization rule.** No shared runtime abstraction is created until a *second* position needs the same mechanism **and** a *third* confirms the shape
(rule of three), or until the owner authorizes migrating Mount. Until then every position implements its own few integers locally and shares only this vocabulary and
the test obligations. Mount already has offensive per-target setup tiers (`americana_tier`, `trap_tier`, `None/Partial/Ready`); Half Guard preparation would be a second
instance of the *vocabulary*, not a reason to refactor frozen, parity-qualified Mount code.

## 4. What is game-wide and what stays position-specific

| Game-wide (this document) | Position-specific (each position's proposal) |
| --- | --- |
| Vocabulary and the `None/Partial/Ready` tiers | Which conditions exist, what they are called, their entry values |
| Direct versus prepared technique; preparation is advantage, not legality | Which techniques are prepared and the grade shifts |
| Defensive readiness and defensive effort as a pair | Which responses are powerful, the effort numbers, the wear rule |
| A feint is one exchange; apparent ≠ real; defender commits before reveal | The eligible feint pairs, required conditions, bite/miss adjustments |
| Sealed-intent commit-and-reveal ordering, public-view schema discipline, refusal-without-mutation | Concrete action/response vocabularies, option reasons |
| Funding: direct cost plus a separately funded surcharge; all-or-nothing; unfunded feints refused; exhaustion unchanged | The surcharge value, whether a LOW feint may exit, position-specific caps |
| Deterministic replay and anti-peeking obligations | Fallback response for a timed-out defender (published per position) |
| Symmetry: any side may prepare, attack, defend and feint *if the position declares it* | Which side gets which feint |

## 5. Preparation, defensive readiness and defensive effort

### 5.1 Direct versus prepared techniques

A direct technique reads only the published raw-grade table (plus the existing positional modifier). A prepared technique additionally reads one of the acting fighter's
conditions: a higher tier improves its grade, a lower tier worsens it, the neutral tier leaves the table unchanged. Choosing the neutral tier as the entry value makes the
position's baseline table the *neutral-state table*, so adding preparation does not silently retune the base grades.

### 5.2 Techniques that establish or compromise preparation

* **Establish:** a successful accepted exchange raises the acting fighter's own condition by one tier.
* **Compromise:** a successful accepted exchange lowers the *opponent's* condition by one tier.
* **Consume:** attempting a prepared technique at the top tier spends one tier (the attempt, not only success, so a prepared technique cannot be repeated for free).
* Changes happen only inside accepted exchanges. A rejected command changes nothing. A position with drift or flow states any decay explicitly; the default is none.
* Tiers are bounded `0..2`; builders do not create hidden carry-over (carry-over export is a separate schema decision).

### 5.3 Defensive readiness and effort

A **powerful response** reads the responder's own condition: a ready structure gives its full or enhanced counter; an unprepared structure gives a weak one. The effort is
priced with existing quantities only:

* **Response commitment** (existing). Proposal: a powerful response whose *funded effective* commitment is below `MEDIUM` counts as unprepared (the effort was not made). `HIGH` additionally preserves the
  structure when the defense succeeds **only if the charge was actually paid**: a Rule 1 waiver removes the charge, so it cannot buy the preservation. `MEDIUM` spends one tier when the defense succeeds
  or fails decisively. Requested, funded-effective and charged commitment are three distinct quantities (`HALF_GUARD_V0_PROPOSAL.md` §12.3.1). These are position-local numbers (see HG-26C).
* **Condition wear** — the positional tradeoff. Repeating a powerful response degrades the structure that powers it, so a defender cannot repeat the same best counter
  indefinitely for free. Rebuilding spends the defender's *own initiative window* (an action that builds the condition) and so costs tempo.
* Ordinary (non-governed) responses stay free of wear. Whether *every* response should be governed is a position-local choice with a measured tradeoff
  (`HALF_GUARD_V0_PROPOSAL.md` §12.1.5, option S).

### 5.4 Funding (a feint costs the direct cost plus a separately funded surcharge)

* The cost of a *direct* exchange is the existing cost of the attacker's *effective* commitment: LOW 3, MEDIUM 7, HIGH 12 (current policy), after the existing funding downgrade.
* **Owner concept: a feint costs more than an ordinary technique.** Candidate rule (a numeric decision, GP-10): a feint costs the cost of its effective commitment **plus a surcharge `s`**, illustrative
  `s = +3` (the LOW cost). The premium is the surcharge, applied equally at every tier (LOW 3 → 6, MEDIUM 7 → 10, HIGH 12 → 15). **Choosing HIGH is not itself a premium**: a direct HIGH costs 12.
* **Funding is all-or-nothing and separate.** The surcharge is reserved first, then the commitment is funded from the remainder with the existing `determine`: `determine(requested, available − s)`;
  if `available < s` or the result is unfunded, the feint is refused without mutation. The commitment may *downgrade* exactly as a direct technique's does; the surcharge never partially funds and
  is never waived. Actual spending is one `spend_up_to(s + effective_cost)` that, because funding was checked first, charges the full amount.
* **Rule 1** (an unfunded initiator waives the responder's charge) cannot apply to a feint, because an unfunded initiator cannot feint; the responder is never charged a surcharge.
* An unfunded or under-funded feint is refused, never silently turned into a direct technique. The price of a feint is therefore both a stamina premium for the attacker and, if the feint is
  called, positional (§6.3). Any other additional effort (a cooldown, a second currency) is not proposed.
* **Exhaustion** is unchanged: an Exhausted attacker's real technique is shifted −1 and an Exhausted defender's response +1 against the defender, exactly as for a direct technique.
* This section is for the later feint slice; the first preparation slice contains no feint cost code. The Half Guard arithmetic and boundary tests are in `HALF_GUARD_V0_PROPOSAL.md` §12.5.

### 5.5 Symmetry

Preparation, attack, defense and feints are side-agnostic concepts. A position declares, per side, its conditions, prepared techniques, powerful responses and feint pairs.
There is no rule that only Top attacks or only Bottom defends; legality is position-local.

## 6. Feints

### 6.1 Concept

A feint is a single logical exchange with two *labels*: the **apparent** technique (shown) and the **real** technique (sealed). The apparent technique never resolves
independently; it determines what the defender sees and, through *bite*, how the real technique is adjusted. A direct attack is the degenerate case apparent = real.

### 6.2 Defender commitment before reveal

The defender chooses a response and a response commitment from the **public view only**. The real technique is revealed and resolved after the response is committed. The
defender cannot tell whether the visible attack is direct or a feint from the public view alone (indistinguishability, §8.1).

### 6.3 Calling a bluff, biting, balanced defense and failure

Relative to the public view, a defender's response falls into classes that the tests compute from published tables (the UI may label them but the labels are non-authoritative):

* **Bite** (best counter to the apparent technique): if the attacker is feinting, the response is committed against the wrong threat; the real technique is shifted **+1**
  in the attacker's favor.
* **Not a bite** (anything else): if the attacker is feinting, the real technique was telegraphed or answered elsewhere; the real technique is shifted **−1** (the feint
  failed to deceive). This is the feint failure cost.
* **Call** (best counter to a real technique the attacker may conceal): wins against the feint, may lose if the attacker was direct.
* **Balanced** (worst case ≤ 0 across direct and every eligible feint): never decisively beaten by either mode.

The ±1 adjustments are applied to the *real* technique after readiness shifts and before exhaustion in the position's pipeline. These specific values are proposals
(HG-26B). Excessive stamina use is bounded by funding: a fighter that repeatedly feints pays the direct cost plus the surcharge each time, and a *called* feint also
costs axis progress, so repeating a read feint is self-defeating.

### 6.4 Counterplay requirement

For every eligible apparent technique the position must show a response that holds the attacker to a bounded result (≤ 0 in the neutral state) whichever mode was chosen,
verified from the tables. A feint pair that fails this test is not admitted. In Half Guard v0 this test already rejects one candidate pair
(`HALF_GUARD_V0_PROPOSAL.md` §12.4).

### 6.5 Interaction with initiative and exhaustion

* The feint exchange consumes the attacker's single initiative like a direct exchange; initiative flips once (position-local rule). A called feint gives the defender
  **nothing beyond the attacker's −1**: no extra window, no initiative transfer in alternating positions (a position may declare otherwise explicitly, GP-9).
* Exhaustion modifiers, funding downgrades and the latch behave exactly as for direct techniques.
* The clock advances once per window (existing rule); internal phases do not advance it.

## 7. Information protocol (deterministic commit and reveal)

### 7.1 Alternating-decision positions (Mount, Half Guard and other top/bottom positions)

Single session executor, two commands, one atomic resolution:

| Step | Actor | Operation | Visible to |
| --- | --- | --- | --- |
| 0 | executor | Window opened for the initiator (existing `window_opened`). | both |
| 1 | initiator | `seal_intent(window_id, fighter_id, apparent, real?, commitment)` | accepted: initiator only sees its own sealed intent; public event `intent_sealed` carries only the public fields |
| 2 | defender | `respond(window_id, fighter_id, intent_serial, response, response_commitment)` — chosen from the public view | public event `response_committed` |
| 3 | executor | **Atomic**: reveal, validate, resolve, mutate once, emit `exchange_revealed` (full record) and the existing decision events, close the window. | both, after the reveal |

Steps 2–3 are one executor operation: no state exists in which a response is committed but unresolved, so a controller can never act between commitment and reveal. The sealed
state between steps 1 and 2 is durable executor state.

### 7.2 Who knows what

| Party | Knows |
| --- | --- |
| **Attacker** | Public state, its own sealed intent (real technique, whether it is a feint, requested commitment), the public view the defender sees. |
| **Defender** | Public state and the **public intent view**: window id, intent serial, initiator id, the apparent technique label, the public cue fields (requested commitment, if GP-3 accepts), the list of legal responses for the apparent technique and — if GP-2 accepts — the real techniques the attacker is currently eligible to conceal. It does **not** contain the real technique, an "is feint" flag, or any field derived from them. |
| **Simulation executor** | Everything. It alone holds the sealed intent and performs validation and resolution. |
| **Replay log** | The full resolved command sequence (seal then respond, including the sealed fields), kept executor-side; the public stream is the same sequence with sealed fields redacted until the reveal event. |

### 7.3 Admission, refusal and replay

Every refusal leaves *all* state, history, events and the sealed store unchanged, and its reason depends only on public state and the refusing fighter's own command (never on
the opponent's hidden intent), so refusals cannot be used to probe. Proposed codes (additive to the position's existing admission order):

* seal: `no_open_window`, `stale_window`, `window_initiator_changed`, `intent_already_sealed`, `unknown_action`, `feint_not_supported`, `feint_not_eligible`,
  `feint_real_equals_apparent`, `feint_requires_funding`, `invalid_commitment`, context errors, terminal errors.
* respond: `no_open_window`, `stale_window`, `no_sealed_intent`, `intent_serial_mismatch`, `not_responder`, `unknown_response`, `response_not_available_for_apparent`,
  `invalid_response_commitment`, `unsupported_cost_policy`.
* A replayed command (a consumed window id, an old intent serial) is `stale_window` / `intent_serial_mismatch`. Duplicated delivery cannot double-spend.
* **Cancellation.** A sealed intent is **irrevocable** (GP-4): withdrawing after the defender has been shown the public view would let an attacker probe defender behavior for free.
  The attacker's only pre-seal "cancellation" is not sealing. A defender's refused response leaves the sealed intent and window open; the defender may retry with a valid
  response. A timed-out defender receives the position's published deterministic fallback response (session metadata, never an arbitrary or random choice; Guide §5.2a).
* **Carry-over/export** while a window is open (including a sealed intent) is refused by the existing open-window rules; this document adds no export schema.

### 7.4 Deterministic replay

Replaying the resolved command log through a fresh executor reproduces identical events, state, histories and sealed-store contents. Nothing in the log is wall-clock or
random; deadlines and timeout reasons are session metadata kept outside the simulation log (Guide §5.2a).

### 7.5 Simultaneous-choice positions (future Standing)

Both fighters seal; reveal happens when both are locked or expired (Guide §§5.2a, 17, 58B.10). Differences from the alternating protocol:

| Aspect | Alternating | Simultaneous |
| --- | --- | --- |
| Sealed parties | One (initiator), then a response | Both fighters, independently, before either is revealed |
| What a defender sees | An apparent technique | **Nothing** from the other fighter's seal; legal-option previews and memory highlights must not leak it |
| Meaning of "apparent" | Visible label that invites a response (bite/call) | Has no public display before reveal, so *bite* has no object unless the position defines public cues *before* the lock (a setup or stance phase) |
| Expiry | Fallback response for the defender | Fallback for each missing seal |
| Order of resolution | Initiator first, then response | Joint table lookup after both seals |

Therefore **feints in simultaneous positions are not defined here** (GP-6): a Standing proposal must first define what public cues exist before locking, and may conclude that a
sealed pair choice already contains the bluff element. The sealed-intent *discipline* (closed public view, executor-held seals, refusal-without-mutation, replay) is identical.

## 8. Test obligations (headless, deterministic)

### 8.1 Protocol and information tests

1. **Closed schema:** the public intent view's key set is exactly the allow-list; it contains no real technique id, no feint flag and no value derived from them.
2. **Indistinguishability:** for every reachable state and apparent technique, the public view produced for a direct attack and for every eligible feint with that apparent
   technique are **deep-equal** (apart from fields that are intentionally public and identical by construction).
3. **Probing controller double:** an opponent controller given the public view recursively enumerates every object, dictionary and property it is handed (`get_property_list`,
   keys, values, nested arrays) and fails if any string equals a sealed id; it also attempts to read private members of the objects it received. A **mutation-sensitivity control**
   injects a deliberately leaky view and must make the probe fail.
4. **Source scan:** controller/decision-maker scripts do not reference the gateway's sealed store, private fields or executor internals.
5. **Atomicity:** there is no observable state with a committed response and an unresolved intent; a failure injected inside resolution leaves the pre-seal-plus-sealed state
   (or the pre-seal state) with no partial mutation.
6. **Refusal without mutation:** every code in §7.3, whole-snapshot equality before and after, precedence for multiple simultaneous faults, no probing through refusal reasons.
7. **Replay:** twice-run determinism of a seeded set of sealed commands; public-stream redaction equals the full log minus sealed fields before reveal.
8. **No extra window / clock / initiative:** a feint exchange yields the same number of windows, clock advance and initiative flips as the direct exchange it resembles.

### 8.2 Tactical tests (what they may and may not claim)

See `HALF_GUARD_V0_PROPOSAL.md` §12.7 for the Half Guard scenarios. The class distinction is mandatory for every position:

* **Structural reachability checks** (exact, CI-gateable): dominance, forced-exit searches, readiness transition tables, the counterplay admissibility rule, exact
  stamina arithmetic.
* **Game-balance evidence** (statistical, preregistered, never gating): populations of policies, exit-rate distributions, durations, exhaustion timing. These report and
  inform an owner decision; they are not pass/fail unless the owner pre-registers a threshold.

## 9. Technique memories and game plans (relationship, non-goals)

* Memories and game plans are **not approved**. This document only states how they would have to relate.
* A memory could *grant knowledge* (for example publish the eligible feint list, or recognise a low-commitment cue) or *modify a declared position-local number*
  (a builder's tier step, a readiness shift) **only through data a position already declares**. It could not add a feint pair that the position did not declare, and it could not
  bypass legality, funding or exhaustion.
* **Recognition/insight must never reveal sealed intent** before the reveal (Guide §58B.5: "must not reveal secret simultaneous choice early"). Public cues are the only channel.
* A game plan (a stored preference) selects among *legal* commands; it receives only the public view, so it cannot see the opponent's seal. A timed-out decision uses the position's
  published fallback, never a plan's guess.
* Both would be designed after at least one position has qualified preparation and the sealed-intent protocol.

## 10. Owner decisions (game-wide)

| Id | Decision | Recommended |
| --- | --- | --- |
| GP-1 | Confirm that the owner direction replaces Guide §27's *preferred* model for adopting positions, keeping the §27 safeguards of §1.1 | Yes |
| GP-2 | The list of real techniques a fighter is currently eligible to conceal is **public** (feint recognition baseline) | Yes; hiding it would make the UI a partial lie and is the natural future recognition upgrade |
| GP-3 | The attacker's *requested* commitment tier is a **public cue** (direct techniques gain no new hidden information) | Yes |
| GP-4 | A sealed intent is irrevocable | Yes |
| GP-5 | The timeout fallback for a defender is a published balanced response per position (session layer) | Yes |
| GP-6 | Feints in simultaneous positions are deferred until a Standing proposal defines pre-lock cues | Yes |
| GP-7 | Use the Guide §21 tier vocabulary `None/Partial/Ready` as integers `0..2`; no continuous internal values in the first implementation | Yes |
| GP-8 | Generalize into shared code only by the rule of three, or on explicit owner authorization to migrate Mount | Yes |
| GP-9 | A called feint grants the defender nothing beyond the attacker's shift (no extra initiative or window) unless a position declares otherwise | Yes |
| GP-10 | A feint costs the direct cost of its effective commitment plus a separately funded, all-or-nothing surcharge (illustrative +3); the value is a per-position numeric decision | Yes (value pending) |

## 11. Implementation status (B1g protocol, B1h feints)

B1g implemented the **sealed-intent protocol** of §7.1 for Half Guard (direct techniques) as an explicit opt-in wrapper over the Half Guard gateway. **B1h** implements the first real feints on top of it for Half Guard only, with the provisional owner decisions below (`HALF_GUARD_V0_RULES.md` §13, `HALF_GUARD_V0_ENGINE.md`). Nothing here creates a game-wide runtime interface (GP-8): every number, pair and code is a Half Guard prototype value.

| Decision | What is implemented | Status |
| --- | --- | --- |
| GP-2 (public list of eligible real techniques) | The public view carries `eligible_real_ids`: the pair table crossed with the public tier condition; independent of stamina, funding and the sealed command | accepted provisionally (owner, B1h) |
| GP-3 (requested commitment is a public cue) | `commitment_requested` is public in the view and in the public `intent_sealed` event; the funded effective commitment, a downgrade and the surcharge are not | accepted provisionally (owner, B1h) |
| GP-4 (a seal is irrevocable) | A pending seal blocks every other command; a refused response keeps it; a session end discards it without resolving or charging anything and refuses all later commands | accepted (owner, B1h) |
| GP-5 (published timeout fallback) | Ordinary defender decision timeout: Bottom Hip Frame LOW, Top Hip Pressure LOW, supplied by the session and enforced by the protocol (`fallback_not_published` otherwise). The only consequence is the existing undercommitment step | accepted for the Half Guard prototype (owner, B1h) |
| GP-9 (a called feint gives nothing beyond the attacker's shift) | No extra turn, token, window or initiative; the call's benefit is the −1 on the real technique | implemented |
| GP-10 (feint surcharge) | `s = +3`, all-or-nothing, funded first, requires `S ≥ 6` | accepted provisionally (owner, B1h) |
| HG-26B (pairs, ±1 bite) | FP-1 and FP-2 only; Flatten → Knee Slice excluded; bite `+1`, otherwise `−1`, after the readiness shifts and before exhaustion | accepted provisionally (owner, B1h) |
| HG-26E-4 (LOW feint cannot exit) | The funded **effective** LOW commitment removes the exit; the exchange otherwise resolves | accepted provisionally (owner, B1h) |
| §7.3 codes | `feint_real_equals_apparent`, `feint_not_supported`, `feint_not_eligible`, `feint_requires_funding`, `feint_without_action`, `fallback_not_published` are added; `unsupported_cost_policy` is not applicable (the cost policy is fixed) | implemented |
| GP-6, GP-7, GP-8 | unchanged (Standing deferred; tiers `0..2`; no shared abstraction) | unchanged |

The timeout of an ordinary missed decision, positional stalling (Guide §§41–42) and the emergency submission-defense expiry are three different systems; B1h implements only the first, only for a defender, and nothing in it is a stalling penalty or a free initiative window.
