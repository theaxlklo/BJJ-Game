# Position-aware initiative contract (B2a.1) — proposal

**Status: documentation only. No engine, test, fixture or gameplay change; Mount and Half Guard behavior is untouched.**
Tags: **[OWNER-DIRECTION]** already agreed by the owner, formalized here, not reopened · **[OBSERVED]** verified in the code or documents at `main` · **[PROPOSAL]** a design or number awaiting owner approval · **[OPEN]** an owner decision.
Nothing tagged PROPOSAL or OPEN is a rule until the owner approves it. The name of this file is provisional.

## 1. What is already decided (and is not reopened)

**[OWNER-DIRECTION]** Initiative at the start of a position combines three things:

1. **General Technique proficiency**: a fighter characteristic. Belt influences its starting distribution, but distributions overlap and individuals vary.
2. **Position-and-role proficiency**: expertise in *this* position in *this* role (`side_control/bottom`, `closed_guard/bottom`, ...), grown through the player's selected training focuses.
3. **The tactical advantage of the current position**: the position's own opening priority.

A sufficiently skilled or specialized fighter may overcome the normal positional opening priority. Side Control ordinarily favors Top. Closed Guard may favor Bottom. Genuinely neutral positions keep simultaneous sealed choices. **Mount and Half Guard keep their implemented behavior until the owner explicitly authorizes a change.** Individual **Memory Mastery** stays separate from general initiative priority so nothing is counted twice.

Consequence for SC-D2 (`SIDE_CONTROL_V0_PROPOSAL.md` §6.4): "Top first or Bottom first" stops being a binary choice. Side Control becomes a *biased* position whose favored role is Top, and a large enough skill gap can reverse the opening. With no fighter skill data yet, the contract reduces to "the favored role opens" (§8.4), so B2b can proceed without waiting for the career system.

## 2. What exists today **[OBSERVED]**

| Fact | Where |
|---|---|
| Mount `initiator` defaults to `"top"`; it flips after every accepted non-exit exchange; an exit leaves it unchanged | `mount_exchange.gd`; `POSITION_GRAPH.md` §4 (D2) |
| Half Guard: the Top opens at entry; strict alternation; a pass flips; an exit does not | `HALF_GUARD_V0_RULES.md` §4, §5.4, §6 |
| A transition grants **no** window, time or initiative to either fighter (D2); the receiving position decides its own first window | `POSITION_GRAPH.md` §4 |
| Four separate fields: identity, physical role, control authority, initiative (`Roles.initiative_id`) | `POSITION_CONTRACT.md` |
| Guide §15: initiative is *triggered*, not permanently owned; the controlling Top ordinarily acts first in established top positions; a Guard Bottom with a valid opening can initiate; the non-initiator always gets a legal response phase; equal authority uses §17 sealed simultaneous choices | Master Guide §15, §17 |
| Mount has a free-initiative mechanism (`free_initiative_pending`, `free_initiative_beneficiary`, `consume_free_window`); nothing generates free windows yet | `mount_match.gd` |
| Half Guard counts initiations per **role** (`top_initiation_count`, `bottom_initiation_count`) | `HALF_GUARD_V0_RULES.md` |
| `BjjFighterDefinition` has only `definition_id` and `display_name`. **No proficiency, belt or focus data exists.** | `fighter_definition.gd`, `F0_FIGHTER_FOUNDATION.md` |
| Half Guard's sealed protocol is **asymmetric** (the attacker seals, the defender answers from a public view). **No symmetric simultaneous protocol exists.** | `TACTICAL_PREPARATION_AND_FEINTS.md` §7, `HALF_GUARD_V0_ENGINE.md` |
| Ten declared position ids: `back_control`, `closed_guard`, `front_headlock`, `half_guard`, `leg_entanglement`, `mount`, `open_guard`, `side_control`, `standing`, `turtle` | `position_registry.gd` |

## 3. Separate the concerns

**[PROPOSAL]** Seven things that must never be inferred from one another:

| Concept | Meaning | Owner of the value |
|---|---|---|
| Fighter identity | Stable id for the whole match | match owner |
| Physical role | Position-local role name | position |
| Control authority | Side of the position's signed axis | position |
| **Initiative** | Who holds the current window | position, per its policy |
| **Timing protocol** | Sequential with response, or simultaneous sealed | position policy |
| **Proficiency inputs** | General and position-role skill, frozen for the match | match owner (from fighter data) |
| Memory mastery | Proficiency with a named technique | fighter data; **never an initiative input** |

Why: physical elevation, axis sign and a temporary right to act answer different questions. Collapsing them is what makes "Bottom has initiative" or "Top lost control but still opens" impossible to express.

## 4. The contract **[PROPOSAL]**

### 4.1 Policy kinds (declared once per position, static)

| Kind | Opening rule | Skill inputs used? |
|---|---|---|
| `LEGACY_FIXED` | A declared role opens, then strict alternation: today's Mount and Half Guard | **No** |
| `BIASED_SEQUENTIAL` | A declared *favored role* opens unless the other fighter's skill advantage exceeds the position's edge; then strict alternation | Yes |
| `NEUTRAL_SIMULTANEOUS` | Nobody opens; both fighters seal a choice before reveal (§6) | **No**: skill never changes the protocol |

A policy is `{position_id, kind, favored_role, legacy_role, edge}`; unused fields are empty.

### 4.2 Decision function (pure, integers only, no clock, no randomness)

```text
score(fighter, position, role) = general[fighter] + role_proficiency[fighter][position, role]     # each 0..100, so 0..200

decide_opening(policy, role_map, inputs, entry_adjust = 0):
    LEGACY_FIXED:          opener = role_map[policy.legacy_role]                  reason legacy_fixed
    NEUTRAL_SIMULTANEOUS:  opener = none                                           reason neutral_simultaneous
    BIASED_SEQUENTIAL:
        fav, oth   = role_map[policy.favored_role], the other fighter
        margin     = score(oth, ..., oth's role) - score(fav, ..., favored role)
        edge_now   = policy.edge - entry_adjust                                    # entry_adjust >= 0, default 0 (§8.5)
        opener     = oth if margin > edge_now else fav                             # strict ">": a tie keeps the favored role
        reason     = skill_override | favored_holds | favored_holds_tie
```

Why integers and a strict comparison: a float or an "either order" tie-break would let two platforms disagree on one opening, which breaks replay. Why no division: dividing a weighted average introduces rounding rules; comparing the raw sums needs none.

### 4.3 When it is evaluated

- **Exactly once per position entry** (including the match's first position). Never inside a window, never when a window closes, never at a timer.
- After the opener, **existing strict alternation continues** (a non-exit exchange flips the initiator; an exit does not). Skill therefore decides *who gets the first window*, not who owns the position. This cannot create a monopoly, a deadlock or extra turns.
- Inputs are a **frozen snapshot taken at match creation** and passed in immutably. A position never reads career data, and career changes (promotion, respec, new focus) take effect at the next match. Replays and saves reproduce the same opening because the recorded inputs, not live fighter data, drive it.
- A **missing input is a refusal with zero mutation** (`missing_proficiency`); no position silently invents a default. Until fighter data exists, the match owner supplies an explicit provisional profile (§8.4).
- The result is one detached event, `initiative_decided`: `position_id, kind, opener_id, favored_id, scores by fighter id, edge, effective_edge, margin, overridden, reason`. A replay verifier recomputes it from the recorded inputs and must match byte for byte.
- It grants **no window, no clock change and no charge**: it names who opens the next window the position would open anyway (D2 stays true).

### 4.4 Alternatives considered

| Variant | Description | Verdict |
|---|---|---|
| **V1 (this proposal)** | Skill contest at entry only | Simple, deterministic, cannot snowball |
| V2 | Re-contest at every window | Repeated initiative theft, passive runaway advantage, much harder to test. **Deferred**; revisit only with measured evidence |
| V3 | Skill changes the timing protocol (neutral becomes sequential) | Contradicts the owner direction that neutral positions keep simultaneous choices. **Rejected** |

## 5. Who may use which stat (no double counting) **[PROPOSAL]**

| Quantity | Opening priority | Execution / grade | Learning speed |
|---|---|---|---|
| General Technique | **Yes** | No (v0) | No |
| Position-role proficiency | **Yes** | No (v0) | Focus accelerates growth of this stat |
| Memory mastery (named technique) | **No** | Existing/future memory rules decide | Its own progress |
| Belt | Only as the starting distribution of General Technique; never a trump | No | No |

Using General Technique or position proficiency to change grades, costs or legality needs its own owner approval and a balance test. A test must assert that `decide_opening` accepts no mastery input.

## 6. Timing protocols

### 6.1 Sequential with response **[OBSERVED, unchanged]**

The initiator chooses an action and commitment; the responder always has a legal response; one `window_id`; the simulated clock advances once per bounded exchange. Half Guard's asymmetric sealed variant stays Half Guard's.

### 6.2 Simultaneous sealed **[PROPOSAL, not implemented; its own future slice]**

Requirements, taken from Guide §17 and the existing information discipline:

- Both fighters commit before either choice is visible; the second commit reveals nothing about the first (public views stay redacted until reveal).
- **One** `window_id`, **one** clock advance and one history exchange per resolved pair.
- Resolution is a deterministic function of the pair (Guide §18 action tags), independent of which fighter sealed first or of fighter-id order.
- Each commit is admitted or refused atomically; a refusal leaves everything byte-identical.
- A missed real-world deadline uses a deterministic, published fallback per fighter; it never reveals the other commit.

```text
OPEN ──seal A──> A_SEALED ──seal B──> RESOLVING ──atomic reveal+resolve──> CLOSED
  └─seal B──> B_SEALED ──seal A──┘            (A and B are symmetric; order must not change the outcome)
CLOSED ──position rule──> stays NEUTRAL_SIMULTANEOUS
                      └─> triggered initiative: SEQUENTIAL with a named initiator (position-declared trigger, Guide §15/§17)
```

## 7. Position matrix **[PROPOSAL]**

Policy kinds are *placeholders until each position's own rules sheet is accepted*. Only the Mount and Half Guard rows describe current behavior.

| Position | Implemented | Proposed kind | Favored role | Candidate edge (score units) | Notes |
|---|---|---|---|---|---|
| `mount` | Yes | `LEGACY_FIXED` | `top` opens | n/a | Preserved exactly; `initiator` default `top`, strict alternation |
| `half_guard` | Yes (opt-in) | `LEGACY_FIXED` | `top` opens at entry | n/a | Preserved exactly |
| `side_control` | Proposal only | `BIASED_SEQUENTIAL` | `top` (pin) | **40** (§8.2) | Resolves SC-D2 as a consequence, not a freeze; Bottom keeps real initiated escapes from the alternation |
| `closed_guard` | No | `BIASED_SEQUENTIAL` | `bottom` ("may favor Bottom") | 24 | Triggered openings (Guide example: Bottom Triangle Ready) are position-local rules |
| `back_control` | No | `BIASED_SEQUENTIAL` | the back attacker | 60 | Role vocabulary differs from top/bottom; per its sheet |
| `standing` | No | `NEUTRAL_SIMULTANEOUS` | none | n/a | Skill does not alter the protocol |
| `open_guard` | No | `NEUTRAL_SIMULTANEOUS` | none | n/a | Owner review at its rules sheet; a transient setup may trigger sequential initiative |
| `turtle`, `front_headlock`, `leg_entanglement` | No | **[OPEN]** | — | — | No proposal; decide at each rules sheet |

## 8. Numbers proposed for owner approval **[PROPOSAL; none is accepted]**

### 8.1 Scale and composition

- General Technique `G` and role proficiency `R` are integers `0..100`. `score = G + R` (`0..200`); the weights are `1:1`, the simplest choice, and an owner decision (OD-2).
- At fighter creation `R` starts equal to `G` for every position-role (so an unfocused fighter is never penalized below general skill); focus and experience raise it later. Within-belt variance is assigned once at creation and stored (owner's illustrative belt ranges, **not accepted**: White 10–35, Blue 25–50, Purple 40–65, Brown 55–80, Black 70–95).

### 8.2 Edge sizing: exact enumeration, not simulation

The edge is the score margin the non-favored fighter needs to take the opening. Each cell is the exact probability that the **non-favored** fighter opens, both fighters unfocused (`R = G`), skill uniform over the illustrative belt ranges, strict `>` (§9 describes the script). Edges are in score units (`2 x` skill points when `R = G`).

| Favored-role belt vs other belt | edge 16 (8 pts) | edge 24 (12 pts, owner's illustrative) | **edge 40 (20 pts)** | edge 60 (30 pts) |
|---|---|---|---|---|
| same belt (any belt) | 0.226 | 0.135 | 0.022 | 0.000 |
| Blue favored vs **White** other | 0.004 | 0.000 | 0.000 | 0.000 |
| White favored vs **Blue** other (one belt up) | 0.719 | 0.592 | 0.311 | 0.081 |
| White favored vs Purple other (two up) | 0.985 | 0.947 | 0.799 | 0.481 |
| White favored vs Brown other (three up) | 1.000 | 1.000 | 0.999 | 0.902 |
| White favored vs Black other (four up) | 1.000 | 1.000 | 1.000 | 1.000 |
| Blue vs Blue, other is a +15 specialist | 0.481 | 0.342 | 0.135 | 0.009 |
| Blue vs Blue, other is a +30 specialist | 0.719 | 0.592 | 0.311 | 0.081 |
| Blue vs Blue, **both** +15 specialists in their own roles | 0.226 | 0.135 | 0.022 | 0.000 |

Reading it: with the owner's illustrative +12-point edge (24), an adjacent-belt gap reverses the opening about 59% of the time, so the position's priority is mostly erased across belts. An edge of 40 keeps the pin meaningful between adjacent belts (31% reversal), lets a clear two-belt gap override it (80%), and treats a same-belt +15 specialist as a real but not dominant threat (13.5%). An edge of 60 makes the position strongly sticky, which fits Back Control. **Recommendation:** Side Control 40, Closed Guard (Bottom favored) 24, Back Control 60, as a starting point for playtest measurement, not as balance truth. OD-4.

### 8.3 Worked examples (edge 24, `score = G + R`)

| Case | Favored `G/R` | Other `G/R` | Margin | Opener |
|---|---|---|---|---|
| Equal fighters | 50/50 | 50/50 | 0 | favored |
| Blue-ish Bottom vs White-ish Top | 22/22 | 37/37 | +30 | **other** (override) |
| Black Bottom vs White Top | 22/22 | 82/80 | +118 | **other** |
| Equal `G`, Bottom +20 specialist | 50/50 | 50/70 | +20 | favored |
| Exactly at the edge | 50/50 | 62/62 | +24 | favored (strict `>`) |
| One over the edge | 50/50 | 62/63 | +25 | **other** |
| Top specialist vs generalist Bottom | 50/70 | 60/60 | 0 | favored |

### 8.4 Before fighter data exists **[PROPOSAL]**

The match owner passes an explicit, recorded provisional profile (`G = R = 50` for both fighters). Every margin is 0, so every `BIASED_SEQUENTIAL` position opens for its favored role. For Side Control that is exactly the Top-first behavior in `SIDE_CONTROL_V0_PROPOSAL.md`, recorded as a *consequence of the provisional profile*, not a frozen rule. Tests for B2b use explicit stable inputs.

### 8.5 Entry tempo adjustment **[OPEN, default 0]**

After a Knee Slice the passing fighter produced the exit and, if favored, also opens Side Control: consecutive personal opportunities across two positions, with no free window or clock. Rather than choose a side, the contract carries `entry_adjust` (default **0**) that lowers the favored role's edge when the favored fighter produced the entry transition. Candidate values are decided only after the measurement plan in §12 shows whether it matters. OD-8.

## 9. Method for the numbers

The table in §8.2 is reproducible exactly (no randomness): for every integer pair `g1` in the favored belt range and `g2` in the other belt range, with `R = G` (plus the stated specialist offset, clamped at 100), count the pairs with `(g2 + r2) - (g1 + r1) > edge`, divided by the number of pairs. The illustrative ranges are the owner's; they are **not** accepted and not the real belt system.

## 10. Edge cases

| # | Case | Proposed rule | Reason |
|---|---|---|---|
| 1 | Equal scores / margin exactly at the edge | Favored role opens (`favored_holds_tie`) | Deterministic; the position's priority is the default |
| 2 | Missing or out-of-range proficiency | Refuse entry, `missing_proficiency` / `invalid_proficiency`, zero mutation | Fail closed; no silent default |
| 3 | Mount / Half Guard | Policy `LEGACY_FIXED`; inputs ignored; replays byte-identical to today | Preserve existing behavior |
| 4 | Chains (Mount → Half Guard → Side Control) | One decision per entry, using the proficiency of the role the fighter **now** holds in the **new** position | Role proficiency is keyed `(position, role)`, not identity or axis |
| 5 | Roles swap on a reversal | Same: the roles at entry decide which `R` applies | Same |
| 6 | Neutral → sequential after a trigger | The position declares the trigger and the named initiator; no skill contest | Guide §15/§17 |
| 7 | Opener cannot act (exhausted) | Every window must offer at least one legal action (Side Control v0 has the free pass); skill can never choose an opener with no legal action | No deadlock |
| 8 | Free windows (#63 priority tokens) | Orthogonal: a free window's beneficiary overrides alternation for that window only; the opening decision creates none | Separate rule family |
| 9 | Decision deadline expiry | Independent of initiative; existing published fallbacks apply; simultaneous needs its own | Three timeout systems stay separate |
| 10 | Frozen inputs vs mid-match career change | Impossible by construction; inputs are a match-creation snapshot | Replay determinism |
| 11 | Passive monopoly | Not possible: alternation after the opener; there is no repeated contest | V1 design |
| 12 | Information leak | Opening reveals only scores and the opener, never a sealed choice; neutral positions seal before reveal | Sealed decisions stay sealed |
| 13 | Memory mastery as an input | Not accepted; a test asserts it | No double counting |

## 11. Per-fighter completed-turn tracking (for future 3-turn stalling and 5-turn Heart of a Lion)

**[PROPOSAL]** A match-owner ledger **keyed by fighter id**, never by role, carried across positions (Half Guard's role-keyed initiation counters stay as they are). Per fighter: `personal_turns_completed` and `consecutive_inactive_turns`. A *personal turn* is an **accepted, resolved, normal exchange in which that fighter was the initiator**; in a simultaneous exchange each fighter's own sealed action counts once. Rejections, menu views, a bare seal of feint intent and unresolved protocol phases never count. A responder's response is part of the initiator's exchange and does not add a second turn. **[OPEN]** (OD-9): whether a response counts, and how D3-B holds, passes and free windows count; the owner's text in `MATCH_INCENTIVES_HEART_OF_A_LION.md` leaves these unfrozen. The ledger lives above the positions so alternation changes (positions with different opening rules) never skew "five of their own turns".

## 12. Compatibility and test plan (design only; nothing is implemented)

**Compatibility invariants:** Mount and Half Guard suites, oracles and pinned counts are unchanged; replays of existing matches are byte-identical; no existing public API, test or fixture is edited; Python under `src/` is untouched; a graph built by any existing constructor behaves exactly as today.

**Negative-first tests (each leaves state byte-identical):** missing / extra / mistyped proficiency keys, `bool` or float where an int is required, out-of-range values, unknown position id or role, a policy with an unknown kind or a missing favored role, a mastery input, a second decision for the same entry, a decision while a window is open, a mismatched role map.

**Deterministic matrix:** equal ratings; adjacent belts; underdog Top and underdog Bottom; high-skill Bottom in Side Control and Closed Guard; low-technique Top in Open Guard (no override, protocol unchanged); two White Belts with different two-focus selections; identical belt and `G` with different focus histories; respec retaining earned proficiency (next match only); off-focus legal moves unaffected; promotion unlocking a focus; save/load and replay reproducing the same `initiative_decided` records; margin = edge and edge + 1; input permutations (fighter-id order must not matter).

**Measurement plan before any numeric acceptance:** after B2c exists, run the B1e-style harness with fixed provisional profiles across a belt-pair grid and report opener distribution, consecutive-opportunity frequency after Knee Slice, and any window starvation. These are evidence, not gates the doc pre-commits.

## 13. Staging after approval (nothing starts without the owner)

1. Owner reviews this document and SC-D1–SC-D15 together.
2. B2b: Side Control rules sheet and independent oracle, with the policy and provisional profile as explicit inputs (so it never waits for the career system).
3. B2c/B2d: typed engine and the Knee Slice receiver, using `decide_opening` for the first window.
4. Later, separate slices: fighter proficiency data, the symmetric simultaneous protocol (§6.2), the per-fighter turn ledger, memory mastery.

## 14. Owner decisions

| Id | Decision | Recommendation |
|---|---|---|
| OD-1 | Accept §3 (seven separate concerns) and the three policy kinds | Accept |
| OD-2 | Scale `0..100`, `score = G + R`, weights `1:1`; `R` starts equal to `G` | Accept |
| OD-3 | Skill decides the opening only (V1); V2 deferred; V3 rejected | Accept |
| OD-4 | Edges: Side Control 40, Closed Guard 24, Back Control 60 (or choose from §8.2) | Accept as playtest starting values |
| OD-5 | Strict `>`; a tie keeps the favored role | Accept |
| OD-6 | Inputs frozen at match creation; changes apply next match | Accept |
| OD-7 | Provisional profile `G = R = 50` until fighter data exists (§8.4) | Accept |
| OD-8 | `entry_adjust` exists, default 0; decide a value after measurement | Accept |
| OD-9 | Personal-turn definition (§11), including responses, D3-B holds, passes, free windows | Review |
| OD-10 | Policies for `turtle`, `front_headlock`, `leg_entanglement`, and confirming `open_guard`/`closed_guard` | Decide at each rules sheet |
| OD-11 | Mount / Half Guard stay `LEGACY_FIXED`; any conversion is a separate authorized slice | Accept |
