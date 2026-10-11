# Half Guard v0 — rules and feasibility proposal (B1a)

**Status: PROPOSAL for owner review. Nothing in this document is approved or implemented.** It changes no GDScript, no
Python, no test, no workflow, no fixture and no earlier PR. Every rule, number, name and table below is a **[PROPOSAL]**
until the owner approves it by decision id (`HG-1` … `HG-26`, §2; HG-26 is §12). The only code executed to prepare it is five throwaway
Python scripts outside the repository, reproduced verbatim in Appendices A–E, that check internal consistency, reachability and structural
dominance of the proposed tables. They are neither an oracle nor parity evidence. The game-wide design of tactical preparation, feints and
defensive counterplay (owner-approved direction, proposed details) is in [TACTICAL_PREPARATION_AND_FEINTS.md](TACTICAL_PREPARATION_AND_FEINTS.md).

Backend-first direction (owner): F1 stays available as an interactive Mount debugging interface and is not expanded.
The goal is deterministic position-to-position transitions, starting with Mount → Half Guard, so that complete matches
can later run from Standing without the interface.

Depends on: `POSITION_GRAPH.md` (§§1–12, questions Q1–Q8), `POSITION_TOPOLOGY.md` (§§6, 9, 11, 14, 15, 16, 19),
`POSITION_CONTRACT.md`, `CARRYOVER_EXPORT.md` (A3b), `F0_FIGHTER_FOUNDATION.md`, `F1_MOUNT_PRACTICE.md`,
Master Guide v10.4 §§7, 8, 11.4, 12–16, 19–22.

## 0. What this document delivers

1. Verified facts about what exists and what a second position can reuse (§1).
2. A decision register of every owner decision needed (§2).
3. A recommendation for each of Q1–Q8 with the exact deterministic rule, gameplay rationale, the simplest reusable
   component, alternatives and feasibility, the effect on Mount parity, the required tests and the unresolved owner
   decisions (§3).
4. A consolidated Half Guard v0 rules sheet that B1b can implement and an independent oracle can be written from (§4).
5. The entry specifications: a neutral entry request (B1b), the Mount edge adapter (B1c) and the opt-in graph integration (B1d) (§§5–6).
6. The independent test-only oracle plan (§7), architecture feasibility comparisons (§8), the slice plan with exact
   boundaries and the existing tests it does and does not touch (§9), measured prototype evidence (§10), risks (§11) and
   the prototype scripts (Appendices A–E).
7. **HG-26** (§12): the Half Guard-specific proposal for positional preparation, feint eligibility, defensive effort, counterplay, stamina and
   funding, the implementation boundary, adversarial test design, feasibility, the revised B1b gate and the HG-26 prototype findings.

Non-goals (unchanged): Standing, Closed/Open Guard, Side Control or any other position's mechanics, scoring, stalling,
Recognition, submissions, a Reversal landing, return to Mount, presentation work, Python engine changes, changes to F1.

## 1. Verified facts

### 1.1 What exists (checked in source at the F1 head `5886e49`)

| Fact | Where | Consequence for Half Guard |
| --- | --- | --- |
| The only position is Mount. Its exits come from Elbow-Knee Escape (SUCCESS → `Half Guard`; STRONG_SUCCESS → `Half Guard` at the Stable band, otherwise `Open Guard`) and Trap-and-Roll (≥ SUCCESS → unresolved `Reversal`). The A3d tests pin this inventory | `mount_catalog.gd`, `test_mount_slice.gd` | Half Guard is entered **only** by an Elbow-Knee Escape. Entry strength is not recorded in the exit label |
| The A3b carry-over record exports ids by role, stamina current/max/latch, behavior **remainders**, clock, last issued window id, the frozen D3-B fields, terminal flags and the exit. It omits Mount axis/band, held behaviors, setup tiers, submission stage, histories, initiative, authority, the window **interval** and the rules/RECOVER configuration | `mount_carryover.gd`, `CARRYOVER_EXPORT.md` | A receiver gets *state it must preserve* but no Mount-derived control values (D1). The cadence must come from somewhere else (§6.1) |
| `BjjStaminaPool.create(start, capacity)` derives the exhaustion latch from `start` alone. Thresholds: enter `floor(0.25 × max)` (inclusive `<=`), recover `ceil(0.35 × max)` (inclusive `>=`). `set_current` re-evaluates the latch. `BjjMountMatch._copy_pool` already restores a latch with `create(0, max)` + `set_current` | `stamina_pool.gd`, `mount_match.gd:128-131` | A latch can be restored with public API only, and production already does it (§5.4) |
| `BjjBehaviorStaminaPolicy.Meter(remainder)` accepts a remainder at construction | `behavior_stamina_policy.gd` | Meters restore without new API |
| Pure static, position-independent functions: `BjjGrade`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`. Position-independent objects: `BjjStaminaPool`, `BjjStaminaCostPolicy` (costs 3/7/12), `Meter` | `scripts/core/` | Half Guard needs **no new stamina or commitment math** |
| Mount-specific: catalog, resolver, rules (axis 0.10–4.00, bands, drift), setup tiers, the Americana submission, behaviors in production, RECOVER, D3-B. `BjjExchangeHistory` / `BjjExchangeResult` live in `core/` but are Mount-shaped | `scripts/positions/mount/`, `scripts/core/` | Not reused; Half Guard gets its own history and result shapes |
| `BjjMatchWindowGateway` owns window identity and admission, builds its own `BjjMountMatch`, and forces production policy (Rule 1 ON, Rule 2 OFF). `BjjPositionGraphMatch` wraps exactly one typed `_gateway`, logs events, classifies exits and halts on any exit. `classify_exit_from` returns `unknown_source_position` for any source other than Mount (pinned by tests and by POSITION_TOPOLOGY C-10). `submit()` hard-codes `POSITION_ID` | `mount_window_gateway.gd`, `graph_match.gd` | A second position needs a segment seam in the graph (§6) and a decision on how its exits are classified (HG-23) |
| The graph reads these views of its segment: `roles()`, `state_fields()`, `history_fields()`, `window_fields()`, `action_options()`, `response_options()`, `selected_commitment()`, `behavior_fields()`, `controller_fields()`, plus `carryover_segment()` (the graph is its only caller), and the `Report` schema (`closed`, `window_id`, `fighter_id`, `role`, `kind`, `transition.raw_destination`, `ended`) | `graph_match.gd` | A Half Guard segment must provide the same views **and** the same `Report` shape (§6.2). F0 reads only `roles()`, `state_fields()` and `behavior_fields()` |
| F1's controller reads `state.control_axis` and indexes `BjjMountRules.Band.keys()[state.band]` | `mount_practice_controller.gd:194-195` | A graph whose active segment is Half Guard would break F1's view; therefore default graphs must never contain Half Guard (HG-22) |
| The Python reference has **no** Half Guard and no non-Mount position. Existing oracles drive the unchanged `MountMatch.attempt` | `src/bjj_game/`, `GODOT_V1/tests/generate_*.py` | Half Guard needs a *new*, independent, test-only oracle (D6) |

### 1.2 Reuse map

| Component | Reuse in Half Guard | Change to existing code |
| --- | --- | --- |
| `BjjStaminaPool`, `BjjStaminaCostPolicy`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade` | Used as-is | None |
| `BjjBehaviorStaminaPolicy.Meter` | Carried (remainder preserved); not advanced in v0 | None |
| `BjjPositionContract` (`Roles`, `Command`, `Outcome`, `Transition`, `OptionList`) | `BjjHalfGuardContract extends BjjPositionContract` | None |
| `BjjMountCarryover.validate_segment` | The **Mount edge adapter** (B1c) validates the source record with the existing validator | None |
| `BjjPositionRegistry` | Destination ids (`side_control`, `open_guard`, `closed_guard`) are checked against it by a test | None |
| `BjjMountExchange.attempt` pipeline | **Re-implemented** as a smaller `BjjHalfGuardMatch.attempt` in the same order (§4.6); not shared | None (§8, row 5) |
| `BjjMatchWindowGateway` | A sibling `BjjHalfGuardWindowGateway` with the same views and the same nested `Report` class | None (Mount gateway untouched) |
| `BjjPositionGraphMatch` | A second, typed, nullable segment slot, an opt-in receiver constructor and a commit step | Deliberate, additive (B1d only) |

## 2. Decision register

Nothing below is approved. "Recommended" is this document's proposal; the owner may approve, amend or reject each id.

| Id | Decision | Recommended | Alternatives | Question |
| --- | --- | --- | --- | --- |
| HG-1 | Axis representation: signed integer **tenths**, range −40…+40, positive = Top passing advantage | Yes | Float like Mount; one-sided axis like Mount (positive-only) | Q1 |
| HG-2 | Five bands (BOTTOM_CONTROL, BOTTOM_EDGE, CONTESTED, TOP_EDGE, TOP_CONTROL) with the thresholds of §3 Q1 | Yes | Three bands; four bands without a neutral band | Q1 |
| HG-3 | Position-break lines at ±30, reached only by a deliberate, break-capable, successful technique; neutral (0) is an interior state, not a break. This **deliberately differs** from Guide §12/§14 "crossing neutral breaks the position", which the v10.4 clause "define the sign convention in each position's contract" permits for a guard-like contest | Yes | ±35; a break at neutral | Q1/Q8 |
| HG-4 | Entry axis fixed at **+5** (CONTESTED); authority = sign of the axis (none at exactly 0). Authority is **reported** (`Roles.control_authority_id`) and has no mechanical effect in v0 | Yes | Entry from the exit grade (needs a schema bump); entry at 0 or +10 | Q2 |
| HG-5 | First initiative after entry: **Top**; strict alternation after every accepted non-exit exchange or no-action pass; the exit exchange hands nothing over. Strict alternation (not Guide §15/§17 opening-triggered or sealed simultaneous choice) is a v0 simplification | Yes | Bottom first; opening-triggered initiative | Q3 |
| HG-6 | **No behaviors, no drift, no RECOVER, no D3-B in v0.** Time advances the clock only; carried meters stay frozen. Accepts the exhaustion consequences listed in Q4 | Yes | Reuse the flow policy with fixed behaviors (Q4 option B) | Q4/Q5/Q6 |
| HG-7 | Stamina and commitment: shared position-independent policies; v04 semantics always on; Rule 1 ON, Rule 2 OFF; baseline MEDIUM; **either fighter may choose any commitment** when initiating. **This departs from the AGENTS.md production invariant "LOW while Exhausted and baseline MEDIUM after clear"** because Half Guard has no RECOVER | Yes (as a flagged departure) | Mirror Mount's policy-selected commitment for an Exhausted fighter | Q5 |
| HG-8 | v0 catalog: Top Crossface, Flatten, Knee Slice; Bottom Underhook, Recover Guard (Guide §11.4 names). Deferred: Sweep, Wrestle-Up, Backstep, deeper half guard | Yes | Add Sweep/Wrestle-Up with explicitly unresolved destinations | Q8 |
| HG-9 | Response names and the 15 raw grades of §4.4 (new content). **Reviewed in §12.12: one single-cell candidate (C1: Knee Slice vs Hip Frame `0 → +1`) is recommended but not applied; the owner decides before the oracle** | Yes (C1 pending) | Any table with the same structural properties; keep C0 knowingly | Q8, §12.12 |
| HG-10 | Positional modifier: −1 for an initiator facing the opponent's CONTROL band | Yes | None; Mount-like asymmetric | Q8 |
| HG-11 | Exit map of §4.5 with labels `Side Control`, `Open Guard`, `Closed Guard`. The Recover Guard split (SUCCESS → Open Guard, STRONG → Closed Guard) is new landing content that needs T-2 provenance; Open Guard and Reversal stay honest halts; no return to Mount | Yes | Map STRONG Knee Slice to Mount; one guard for both grades | Q8 |
| HG-12 | Terminal rules: timeout only (no submissions, no tap, no scoring) | Yes | — | Q8 |
| HG-13 | One **neutral entry request** (ids by Half Guard role, per-fighter-id state) is the only way to build Half Guard, for both a Mount edge and tests/oracles. Scenario and normal-match starts are **not** registered (P-12) | Yes | A Mount-record-only receiver; register a scenario start now | Q2/Q7 |
| HG-14 | D3-B stays frozen inside the retained Mount segment, is never given to Half Guard, and `controller_fields()` is `{}` there | Yes | Per-position analogue (needs measurement) | Q6 |
| HG-15 | Latch restoration with public pool API only (the production `_copy_pool` pattern), proven by an exhaustive equivalence test; fall back to a validated pool factory only if the proof fails | Yes | New pool factory now | Q7 |
| HG-16 | Segment seam: keep the typed `_gateway` slot for Mount and add a **second typed, nullable Half Guard slot**; every graph pass-through branches on it. No `Variant`, no base class, no change to the Mount gateway. **This revises the "graph holds only one gateway" invariant that `test_position_graph_boundaries.gd` pins; approving HG-16 approves that revision** | Yes | `Variant` segment; abstract base class; one generic gateway | Q7 |
| HG-17 | Window ids continue from `last_issued_id + 1`; one new event `transition_committed`; the exit-producing window is consumed; no automatic window | Yes | — | Q3/Q7 |
| HG-18 | If building the receiver fails **after** an accepted exit exchange, the graph halts with `transition_entry_invalid` instead of rolling back. This **amends** `POSITION_GRAPH.md` §5 and §8 (whose letter says failed construction leaves state unchanged, which cannot hold once the exchange is settled). Needs explicit owner approval of the amendment | Yes | Roll back (needs a Mount seam) | Q7 |
| HG-19 | Independent oracle (§7): a new Python module under `tests/`, written from the approved rules, reusing only frozen position-independent stamina primitives, with a cross-check of its settlement helpers against Mount's private helpers and a mutation-sensitivity control (§7) | Yes | Translate the GDScript | §7 |
| HG-20 | Graph `carryover_export()` is **refused** (`carryover_unsupported_position`) while Half Guard is active; the v1 envelope validator is left unchanged; a v2 envelope is deliberately deferred, which **departs from POSITION_TOPOLOGY §9.3 step 5** ("a committing build must emit v2"). A graph halted with `transition_entry_invalid` is refused by the unchanged v1 validator (`inconsistent_graph_segment`) | Yes | Extend the envelope now | §6 |
| HG-21 | Slicing: **B1b** mechanics + neutral entry + latch proof + oracle + gateway conformance test; **B1c** Mount edge adapter; **B1d** opt-in graph integration. Each its own draft PR and exact-head CI. B1b and B1c must land (and compile) before B1d, because the graph's typed slot loads the Half Guard scripts for every graph | Yes | One combined slice | §9 |
| HG-22 | **Receivers are opt-in**: a separate constructor (`create_with_receivers`) builds a graph that may commit to Half Guard; `create` and every default graph keep today's behavior (all Mount exits halt). Flipping the default is a later, separately authorized step. The opt-in graph changes exactly **two** private-field pins (§9.3) | Yes | Commit by default (changes ~30 pinned assertions and breaks F1's view) | §6 |
| HG-23 | Classification adds **no new classification code**: the static `classify_exit_from` stays byte-identical (still `unknown_source_position` for a non-Mount source, pinned by C-10). The graph instance turns the static Mount answer `blocked / destination_not_implemented / <id>` into a `transition` iff `<id>` is in the receiver table, and classifies a Half Guard source's labels by calling the same unchanged function with Half Guard's own declarations (`{"half_guard": {"exits": EXIT_DESTINATIONS, "unresolved": []}}`) | Yes | A new instance-level classifier; change the static classifier | Q8/§6 |
| HG-24 | The Mount gateway object is **retained, frozen** after the commit (never advanced or submitted to again), so Mount's histories and D3-B record stay with the Mount segment as `POSITION_GRAPH.md` §6 says; Half Guard keeps its own histories | Yes | Keep only a detached record | §6 |
| HG-25 | The window cadence is captured by the opt-in graph from its own `configuration.interval` (default: that same Mount constant) and passed to the entry request; the Mount record is not extended. When the key is absent the default is the constant the Mount match itself uses (`BjjMountRules.DEFAULT_INTERVAL_SECONDS`), never a second literal | Yes | Add an interval to the record; fix 5 s and halt on mismatch | §5/§6 |
| HG-26A | **Positional preparation:** two integers `top_base` and `bottom_frame` (`None/Partial/Ready`), entry `Partial/Partial`, no decay (**provisionally approved**, option M **provisionally approved**); Crossface/Flatten/Underhook/Recover Guard write them, Knee Slice and Recover Guard read and consume them; shifts, pipeline order and uniform exit processing of §12.1 need acceptance. Local to Half Guard, no shared type | Yes | Option S (every response governed); direct baseline without preparation | §12.1 |
| HG-26B | **Feint eligibility** (deferred slice): explicit pairs FP-1 Crossface→Knee Slice and FP-2 Underhook→Recover Guard; FP-3 Flatten→Knee Slice rejected; bite adjustment ±1; apparent never resolves; real must be break-capable | Yes (design only; not in B1b) | Add FP-3; derive pairs automatically (rejected) | §12.2 |
| HG-26C | **Defensive effort (B1b):** governed responses Knee Shield (frame) and Knee Pin (base) (**provisionally approved**); shift −1/0/+2; effort table LOW/unfunded = tier None and no wear, MEDIUM wears on a decisive result, HIGH wears only on failure; **requested, funded-effective and charged commitment are distinct and HIGH preservation requires paid effort (Rule 1 waiver does not buy it)** | Yes | +1 for None (a Knee Shield fortress); every response governed; funded-only effort test | §12.3 |
| HG-26D | **Counterplay:** four routes (anticipate, avoid full commitment, balanced response, call) and the neutral-state admissibility rule for any feint pair | Yes | Hide the eligible reals (GP-2) | §12.4 |
| HG-26E | **Stamina and funding (B1h only):** a feint costs the direct cost of its effective commitment **plus a separately funded, all-or-nothing surcharge** (illustrative +3; HIGH is not itself a premium); unfunded or under-funded feint refused; LOW feint cannot exit | Yes (value pending) | Parity with a direct technique (superseded); a proportional surcharge | §12.5 |
| HG-26F | **Implementation boundary (provisionally approved):** B1b includes HG-26A/C as two ints plus constants (no shared interface); feints are separate slices B1g (sealed-intent protocol) and B1h (Half Guard feint rules); existing B1b/B1c/B1d/B1e/B1f unchanged | Yes | Direct-only B1b; a generic framework now | §12.6, §12.9, §12.13 |

## 3. Answers to Q1–Q8

"Mount parity" means: the frozen Python Mount reference, its fixtures and digest, the Mount GDScript, and the Mount parity suites
(the 256,992-assertion slice and the exchange/lifecycle/D3-B/contract oracles). "Existing tests" means the pinned suites listed in §9.

### Q1 — Half Guard axis: sign convention, range, bands, hysteresis

**Exact rule [HG-1, HG-2, HG-3].** The axis is a signed integer in **tenths**, `a ∈ [−40, +40]`. **Positive = Top passing advantage;
negative = Bottom retention/recovery advantage** (D1). Display is `a / 10` with one decimal; that float is a view only and is never
stored or compared. All arithmetic is integer, so there is no rounding.

Bands are ordinals `−2…+2`: `BOTTOM_CONTROL (−2)`, `BOTTOM_EDGE (−1)`, `CONTESTED (0)`, `TOP_EDGE (+1)`, `TOP_CONTROL (+2)`.
Initial band for an axis `a`: `|a| < 10 → 0`; `10 ≤ |a| < 25 → ±1`; `|a| ≥ 25 → ±2` (sign of `a`). After every axis change the band is
updated by applying the first matching hysteresis rule until none applies. The rules are mutually exclusive per band, so order is immaterial:

| Direction | Band change | Applies when |
| --- | --- | --- |
| toward Top | 0 → +1 | `a ≥ 12` |
| toward Top | +1 → +2 | `a ≥ 27` |
| toward Top | −1 → 0 | `a ≥ −8` |
| toward Top | −2 → −1 | `a ≥ −23` |
| toward Bottom | +2 → +1 | `a ≤ 23` |
| toward Bottom | +1 → 0 | `a ≤ 8` |
| toward Bottom | 0 → −1 | `a ≤ −12` |
| toward Bottom | −1 → −2 | `a ≤ −27` |

Legal axis/band pairs (context validation): band 0: `−12 < a < 12`; +1: `8 < a < 27`; +2: `a > 23`; −1: `−27 < a < −8`; −2: `a < −23`.
Appendix A asserts that every axis in range has a legal band and that every rule lands on a legal pair.

The axis changes only through accepted exchanges in v0 (no drift, HG-6) and is clamped to `[−40, +40]`. Crossing a break line alone does nothing
(§4.5).

**Where the numbers come from.** The hysteresis width (±0.2 around nominal boundaries at 1.0 and 2.5) mirrors Mount's ±0.2 width; the break lines
at ±3.0 are chosen so that a break needs the CONTROL band plus a successful technique: the prototype finds exits in 2–4 windows with full
cooperation and none against perfect counters. They are proposals for owner edit, not derived values. **Parity note:** entry is +5 and every step is a multiple of 10, so an unclamped axis is always ≡ 5 (mod 10); a break line of 30 therefore behaves like 35 until a clamp occurs, and an axis of exactly 0 appears only after a clamp (for example 40 → 20 → 0). The owner may prefer a different entry value or line. The one-sided alternative and ±35 are listed below.

**Gameplay rationale.** Guide §12 defines the universal axis as `−4…+4` and requires each guard-like position to name its contesting sides and sign
(v10.4 clarification); D1 requires an axis oriented toward Top passing advantage versus Bottom retention/offense. Authority is simply "who is ahead".
Neutral is an interior contest state here (HG-3), unlike Mount's one-sided axis where crossing the floor is the escape.

**Simplest reusable component.** The *shape* of `BjjMountRules` (initial band, hysteresis list, legal-pair check) as a new `BjjHalfGuardRules` with its
own constants. D1 forbids reusing, converting or deriving from Mount's axis, so the constants are new even where the pattern is borrowed.

**Alternatives and feasibility.** (a) One-sided axis `0.1…4.0`: least new code, but it cannot express "Bottom is ahead", contradicts D1's orientation and
makes authority constant. (b) Floats: matches Mount's style, needs `round_ten`, and A3b already showed float round trips are rejected by design.
(c) Three bands (no EDGE bands) or four bands without a neutral band: fewer thresholds, but a two-sided contest then has no neutral state. (d) Break
lines at ±35 make exits slower. Recommended: HG-1/2/3 as written. Cost: ~110 lines, no change to existing code.

**Effect on Mount parity.** None: no Mount file, fixture or Python source is touched.

**Required tests.** Literal band table over all 81 axis values; every hysteresis rule at and one tenth either side of its threshold, both directions, from
every legal starting band; multi-band jumps; legal-pair validation including rejection of impossible pairs; clamp at ±40; determinism; oracle replay of the
axis × band grid.

**Owner decisions.** HG-1, HG-2, HG-3.

### Q2 — Entry values and who holds control authority at entry

**Exact rule [HG-4, HG-13].** Every Half Guard built from an entry request starts at **axis +5, band CONTESTED (0)**. Control authority is a Half Guard
rule: the fighter on the positive side holds it (the `top` role when `a > 0`), the `bottom` role when `a < 0`, and **nobody** when `a == 0`
(`Roles.control_authority_id` is `""`). This is the contract's own definition ("the fighter on the positive/control side of the signed axis")
applied to a signed axis. Authority is reported only: in v0 it drives neither initiative nor grades.

For Mount → Half Guard the edge declares the identity role map (D1: the Mount Top stays `top`, the Mount Bottom stays `bottom` and has recovered
Half Guard). **The receiver itself accepts any validated role map and any source** (§5): the entry request names fighters by id, so a non-Mount source
(for example the Guide's Standing → Half Guard example, whose takedown assigns roles by outcome) can use it later without a Mount-shaped record.

**Gameplay rationale.** The escaping fighter has earned a *contested* guard, not a free one; Top keeps a slight edge. A fixed entry value keeps the A3b
schema unchanged and keeps D1's rule that no Mount number feeds Half Guard.

**Simplest reusable component.** Two constants and the sign rule; `Roles.control_authority_id` already exists.

**Alternatives and feasibility.** (a) Entry depends on the exit grade (SUCCESS vs STRONG at Stable): richer, but the record has no grade, so it needs a v2
schema and a Mount-side export change; deferred. (b) Entry at 0: authority becomes "none" at entry. (c) Entry at +10: an unearned head start.

**Effect on Mount parity.** None.

**Required tests.** Entry for a grid of valid requests; authority for literal axes (0, ±1, ±40); every invalid request refused; role-map variants including a
swapped bijection proving state follows the fighter id.

**Owner decisions.** HG-4, HG-13.

### Q3 — First initiative event and alternation

**Exact rule [HG-5, HG-17].** The exit-producing Mount window is consumed (D2): the transition grants no window, no extra action, no clock change and charges
nothing. The first window opens only when the caller calls `open_window()`, with id `last_issued_id + 1`; its owner is the **Top** (the fighter with
authority at entry). After every accepted non-exit exchange and every no-action pass the initiative flips; an exit exchange leaves it unchanged (the
position ends). Either initiator may take a no-action pass: it needs an open window, flips initiative, costs no stamina, appends the side to
`reset_window_history` and produces no grades. A window advances the clock by `min(interval, remaining)`; if that brings the clock to 0 the report is
`closed` and **no window opens** (timeout), so a submit can never meet a finished clock.

**Gameplay rationale.** Guide §15 and the v10.4 authority rule: the controlling top fighter ordinarily acts first; a bottom fighter acts when it has a
valid opening. D2 forbids a free follow-up for the escaper. Strict alternation is the turn structure the qualified Mount uses, so the window protocol,
F0 and F1 keep working. Opening-triggered initiative (Guide §15) and sealed simultaneous choice (§17) are the right long-term models but need setup and
trigger rules no approved decision defines.

**Simplest reusable component.** The window lifecycle of `BjjMatchWindowGateway` (§4.7), copied into a sibling gateway; alternation is one line.

**Alternatives and feasibility.** (a) Bottom first (momentum): invites an immediate second Bottom action. (b) Opening-triggered initiative: deferred (§11).

**Effect on Mount parity.** None. Mount's `initiator` after an exit is never read as a handoff.

**Required tests.** After commit no window is open and the counter equals the source's `last_issued_id`; the first window is the Top's with id `last_issued_id + 1`;
alternation over long sequences; no-action pass (open window required, initiator only, cost-free, recorded); exit leaves initiative unchanged;
timeout at the interval boundary with no window opened; zero clock change at the transition; replay determinism.

**Owner decisions.** HG-5, HG-17.

### Q4 — Does Half Guard use behaviors, and which stamina rates apply?

**Exact rule [HG-6].** **Half Guard v0 has no behaviors.** Time advances only the clock: no drift, no stamina flow, no behavior selection. The two `Meter`
remainders are carried into the receiver and **left unchanged** for the life of the segment, so they stay exact for a later position or a later behavior
rule. `behavior_fields()` returns `{"top": "", "bottom": ""}`.

**Gameplay rationale.** The behavior system is tied to Mount's measured production policy (PRESSURE/ESCAPE baseline, Bottom RECOVER, D3-B). Importing it
unmeasured would activate unapproved economics for both fighters; the repository's practice (D3-B and handoff-oscillation research) is to pre-register and
measure such rules. Dropping behaviors keeps the oracle small.

**Simplest reusable component.** None. `BjjBehaviorStaminaPolicy` stays untouched; only its `Meter` type is carried.

**Alternatives and feasibility.** (A) *Recommended:* no behaviors. (B) Reuse the flow policy with fixed behaviors (Top PRESSURE, Bottom ESCAPE, `CONSERVE`
when Exhausted) and no drift: free recovery, but RECOVER-like economics for both fighters without D3-B or measurement. (C) New Half Guard behaviors with
new rates: new stamina numbers, rejected for v0.

**Consequences the owner must accept (HG-6).**
* Stamina in Half Guard only falls. Appendix A: ~11 MEDIUM exchanges bring a fresh fighter to the Exhausted latch; random play leaves Half Guard in a median
  of 12–14 windows (a fresh entry therefore leaves 1–3 windows after the latch; an entry from a long Mount phase starts low and is exhausted for most of the
  segment).
* A fighter latched Exhausted at entry **stays** Exhausted for the whole segment (the recover threshold is unreachable without recovery).
* The no-action pass costs nothing, so passing dominates for an exhausted fighter and a rational stalemate to timeout exists; Mount has the same pass
  but also has recovery.
* Every Half Guard exit halts the graph (all destinations are unimplemented), so no continuing match exists past Half Guard.
* A human cannot reach Half Guard through F1 (F1 never selects Bottom actions), so v0 is a **mechanics-and-transition milestone**, not a player-facing position;
  a measured recovery rule is a separate slice (B1e, §9.4).

**Effect on Mount parity.** None.

**Required tests.** Time advance changes only the clock; pools and meters identical across any number of windows with no exchange; carried remainder equals the
entry's before and after windows and exchanges; `behavior_fields()` literal; no Half Guard code path references `BjjBehaviorStaminaPolicy` apart from the
`Meter` type (source scan).

**Owner decisions.** HG-6.

### Q5 — Stamina settlement inside Half Guard

**Exact rule [HG-7].** Position-independent policies, v04 commitment semantics always on (Half Guard has no legacy path):

1. Capture both historical bands before any cost; `exhaustion = BjjExhaustionPolicy.exchange(initiator_band, responder_band)`.
2. Initiator funding = `BjjStaminaCostPolicy.determine(requested, initiator.current)`; responder funding = `determine(response_commitment or MEDIUM, responder.current)`.
   `response_commitment` is supplied by the caller exactly as in Mount's `submit(...)`; empty means MEDIUM; anything else must be a valid commitment.
3. Grade: `g_pos = shift(raw, positional_modifier)`; `g_exh = shift(g_pos, exhaustion.modifier)`; `m = magnitude_modifier(initiator_effective, g_exh)`;
   `u = undercommitment_modifier(initiator_effective, responder_effective)`; `final = shift(shift(g_exh, m), u)`.
4. Apply axis, band, exit (§4.5) and initiative.
5. Spend the initiator's effective cost, then the responder's effective cost, each with `spend_up_to`. **Rule 1 ON** (an unfunded initiator waives the responder's
   cost; the Mount gateway already forces this) and **Rule 2 OFF** (no supplemental hold: no submissions). No RECOVER.
6. Baseline commitment `MEDIUM` (`selected_commitment()`); either fighter may request `LOW`, `MEDIUM` or `HIGH` when it initiates. The Mount rule
   `commitment_is_policy_selected` does not exist in Half Guard.

**Departure flagged (HG-7).** AGENTS.md preserves "LOW while Exhausted and baseline MEDIUM after clear" for Mount's production policy. That rule belongs to
Bottom RECOVER, which Half Guard does not have; allowing a free choice is a proposal, not a drift, and needs an explicit owner decision.

**Gameplay rationale.** The same settlement order the qualified Mount uses, so commitment, exhaustion and unfunded behavior mean the same thing in both
positions.

**Simplest reusable component.** `BjjStaminaCostPolicy`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade`, `BjjStaminaPool`, all unchanged. The
ordering is re-implemented once in `BjjHalfGuardMatch.attempt` (~60 lines) and checked against the oracle.

**Alternatives and feasibility.** (a) Refactor Mount's `attempt` into a shared settlement function: removes ~60 duplicated lines but touches the most heavily
qualified code (the exchange oracle: 14,631 scenarios / 8,851,698 comparisons, `EXCHANGE_SETTLEMENT.md`) for no behavior gain: rejected. (b) Mirror Mount's
policy-selected commitment for an Exhausted fighter: LOW for the Exhausted fighter on both sides; cheap to add later if the owner wants it.

**Effect on Mount parity.** None.

**Required tests.** Literal funding tables for every commitment × stamina; exhaustion modifier for all band pairs; magnitude and undercommitment cases; Rule 1
waiver; spend order; unfunded paths; oracle replay of the full grid; the oracle's helpers cross-checked against Mount's Python helpers.

**Owner decisions.** HG-7 (and HG-6 for the absence of RECOVER).

### Q6 — D3-B

**Exact rule [HG-14, HG-24].** Confirmed: D3-B is **frozen and never observed in Half Guard**. The retained Mount gateway keeps its D3-B controller exactly as the
exit left it; nothing ever calls it again. Half Guard has no controller, never calls `observe_advance` or `decide`, grants and consumes no token, and its
`controller_fields()` is `{}`. Entering Half Guard arms, re-arms and consumes nothing whatever the Bottom's band. Return to Mount stays unsupported, so no
reconciliation is designed.

**Gameplay rationale.** D3-B governs Mount's Bottom RECOVER; Half Guard has no RECOVER in v0, so nothing for it to govern. Freezing prevents a stale episode
from granting a second token on a later re-entry.

**Simplest reusable component.** None: absence plus the retained Mount gateway.

**Alternatives and feasibility.** A per-position analogue needs new rules and a measurement study; deferred with RECOVER.

**Effect on Mount parity.** None; D3-B evidence and digests are untouched.

**Required tests.** The retained Mount gateway's `controller_fields()` and every view are identical before the transition and after any amount of Half Guard play
(token counts unchanged); Half Guard exposes no controller; no Half Guard source references `BjjD3BController` (source scan).

**Owner decisions.** HG-14, HG-24, HG-6.

### Q7 — Gateway construction seam for carry-over

**Exact rule [HG-13, HG-15, HG-16, HG-17, HG-18, HG-22, HG-24, HG-25].**
1. **Neutral entry request** (B1b): one validated value, keyed by **fighter id**, builds a Half Guard match (§5.1). It is the only construction path.
2. **Mount edge adapter** (B1c): validates an A3b Mount record and *re-keys it by fighter id* into an entry request (§5.2). It reads no Mount object.
3. **Sibling gateway** `BjjHalfGuardWindowGateway`: the same views and the same nested `BjjMatchWindowGateway.Report` class, seeded with the entry's
   `last_issued_id`.
4. **Graph** (B1d): a second typed, nullable slot for the Half Guard gateway; an opt-in constructor with a receiver table; an atomic commit (§6).
5. Latch restoration uses public pool API (§5.4), proven before it is trusted.

**Gameplay rationale.** None directly: this is the seam that makes the transition atomic and keeps Mount untouched.

**Simplest reusable component.** `BjjMountCarryover.validate_segment`; `BjjStaminaPool.create` + `set_current` (the production `_copy_pool` pattern);
`Meter(remainder)`; `BjjPositionContract`.

**Alternatives and feasibility.** Detailed in §8. (1) *Sibling gateway + second typed slot* (recommended): ~240 new gateway lines and a dozen branched
pass-throughs, zero change to the Mount gateway; the dozen branches are reversible when a third position needs a real interface. (2) *`Variant` segment*:
every graph local needs an explicit type, and the `Report` schema is not enforced by the type system. (3) *Abstract base class on the Mount gateway*:
removes duplication but changes a class covered by the gateway, graph, contract, F0 and F1 suites. (4) *One generic gateway*: the largest refactor.

**Effect on Mount parity.** None for B1b/B1c. B1d changes the graph, not the Mount engine; with opt-in receivers (HG-22) the default graph's observable
behavior is byte-identical.

**Required tests.** Entry validity and invalidity per field; role re-keying (state follows the fighter id, not the role label); restore-then-advance
equivalence; no mutation of the source; window seeding; atomic commit; failure injection; conformance of the Half Guard gateway's views and `Report`
schema against the Mount gateway's (in B1b).

**Owner decisions.** HG-13, HG-15, HG-16, HG-17, HG-18, HG-20, HG-21, HG-22, HG-24, HG-25.

### Q8 — Catalog, responses and exit map (including Open Guard)

**Exact rule [HG-8 … HG-12, HG-23].** Full tables in §4.3–§4.5. In short:

* Top techniques: `Crossface`, `Flatten`, `Knee Slice` (break-capable). Bottom techniques: `Underhook`, `Recover Guard` (break-capable). Guide §11.4's
  `Sweep`, `Wrestle-Up`, `Backstep` and deeper half guard are **deferred**: Guide §11.4 lists no Standing destination for Half Guard, and a Sweep changes
  roles, so including them would need landings no decision defines — the situation of Mount's Reversal. They are candidates for later slices.
* Three responses per side; 15 matchups with deterministic raw grades (no hidden randomness, Guide §20).
* Exit map: Knee Slice with SUCCESS or better and the Top break line reached → `Side Control`; Recover Guard with the Bottom break line reached → `Open Guard`
  for SUCCESS, `Closed Guard` for STRONG_SUCCESS. All three receivers are unimplemented, so each is an **honest halt**: `transition_blocked` with reason
  `destination_not_implemented` and the declared destination id (HG-23: Half Guard's own declarations, evaluated by the graph instance; the static
  classifier still answers `unknown_source_position` for any non-Mount source, as C-10 pins).
* **The Mount STRONG_SUCCESS → `Open Guard` exit stays a halt** (the Open Guard receiver is a separate future slice; Mount's exit labels do not change;
  Reversal stays unresolved). Half Guard → Mount is not declared (return unsupported). Outgoing Half Guard edges declare no role maps because none can
  commit yet; a future receiver declares its own (AGENTS.md: exits need validated role mappings).
* Terminal: timeout only.

**Gameplay rationale.** The catalog uses the Guide's technique names and listed destinations (`Side Control`; `Guard`, which the exit map must resolve into
`Open Guard` or `Closed Guard`), keeps every defense closing some routes and leaving others open (Guide §16), and keeps each action's best counter available to
the responder, the property the qualified Mount has (§10). Response names are new content.

**Simplest reusable component.** The Mount catalog *pattern* (entities with side/kind/name, raw grades keyed `action|response`, an exit function) as a new
`BjjHalfGuardCatalog`; exit labels follow Mount's convention (a `BjjHalfGuardContract.EXIT_DESTINATIONS` table whose ids a test checks against `BjjPositionRegistry`).

**Alternatives and feasibility.** (a) Add `Sweep` and `Wrestle-Up` with explicitly unresolved destinations (as Reversal): more content and two more unresolved
exits; the missing landing rule is the real blocker. (b) Map a STRONG Knee Slice to `Mount`: reaches a position whose re-entry is unsupported, so it would
always halt. (c) One guard for both Recover Guard grades: loses the grade distinction Mount's own exit map makes. Recommended: the v0 catalog.

**Effect on Mount parity.** None. The A3d inventory (candidates versus emitted exits) is unchanged because Mount's catalog and contract are unchanged.

**Required tests.** Exact catalog pins in the A3d style: entity set; break-capable set; every cell of technique × final grade × (axis line reached or not) → label
(labels do not depend on the band); no other producible label; literal exit map; undeclared labels rejected; destination ids ⊆ registry; no `mount`
destination; oracle replay.

**Owner decisions.** HG-8, HG-9, HG-10, HG-11, HG-12, HG-23.

## 4. Half Guard v0 rules sheet (implementation-ready, all [PROPOSAL])

### 4.1 State

`BjjHalfGuardMatch` holds: `axis_tenths: int`, `band: int` (−2…+2), `initiator: String` (`"top"` | `"bottom"`), `top`/`bottom` (`BjjStaminaPool`),
`top_meter`/`bottom_meter` (`Meter`, carried, never advanced), `initial_clock`/`clock_seconds`/`interval_seconds` (ints), `exit_destination`/`exit_reason` (strings),
and a history. `ended = clock_seconds <= 0 or exit_destination != ""`; `submission_tapped` is always `false`. After an exit the match is terminal: every
later exchange is refused with `terminal_exchange`. Roles are `top` and `bottom`; the role map binds stable fighter ids to them (identity, role, authority and
initiative stay separate).

**History schema** (field names reuse Mount's where the meaning is the same; all arrays of strings/ints, appended once per accepted exchange unless noted):
`initiated_action_history`, `response_history`, `raw_grade_history`, `modified_grade_history` (the five names `Strong Failure … Strong Success`),
`initiator_effective_commitment_history`, `responder_effective_commitment_history` (`""` for unfunded), `band_change_history` (`"<before>-><after>"` per band change,
in order), `reset_window_history` (side of each pass), `top_initiation_count`, `bottom_initiation_count`.

### 4.2 Axis and bands — see Q1.

### 4.3 Catalog (stable ids; names are the Guide §11.4 names for techniques, new content for responses)

| Id | Side | Kind | Name | Break-capable |
| --- | --- | --- | --- | --- |
| `half_guard.top.crossface` | top | action | Crossface | no |
| `half_guard.top.flatten` | top | action | Flatten | no |
| `half_guard.top.knee_slice` | top | action | Knee Slice | **yes (pass → Side Control)** |
| `half_guard.bottom.underhook` | bottom | action | Underhook | no |
| `half_guard.bottom.recover_guard` | bottom | action | Recover Guard | **yes (→ Open Guard / Closed Guard)** |
| `half_guard.bottom_response.hip_frame` | bottom | response | Hip Frame | — |
| `half_guard.bottom_response.underhook_fight` | bottom | response | Underhook Fight | — |
| `half_guard.bottom_response.knee_shield` | bottom | response | Knee Shield | — |
| `half_guard.top_response.head_control` | top | response | Head Control | — |
| `half_guard.top_response.hip_pressure` | top | response | Hip Pressure | — |
| `half_guard.top_response.knee_pin` | top | response | Knee Pin | — |

No technique descriptions are invented here.

### 4.4 Raw grades (15 matchups; grade from the initiator's point of view, −2…+2)

| Top initiator \ Bottom response | Hip Frame | Underhook Fight | Knee Shield |
| --- | --- | --- | --- |
| Crossface | +1 | −1 | 0 |
| Flatten | −1 | +1 | +1 |
| Knee Slice | 0 | +2 | −2 |

| Bottom initiator \ Top response | Head Control | Hip Pressure | Knee Pin |
| --- | --- | --- | --- |
| Underhook | −1 | 0 | +1 |
| Recover Guard | +2 | +1 | −2 |

Design properties (checked in Appendices A and B): every action has a counter (≤ −1) and a favorable response (≥ +1); no response is best against everything; each
exit label is reachable by plain play with cooperating opponents; and **the two break-capable actions can never succeed against their −2 counter, even
after exhaustion and commitment settlement** (Appendix B: the best reachable final grade from a raw −2 is CONTESTED), so, **at the neutral readiness state**, a responder who always plays the
best counter can never be exited on (HG-26A makes this conditional on readiness, §12.1.4). Plain counters (raw −1) *can* be lifted to SUCCESS by an Exhausted, under-committed responder; that is intended
to let stamina matter.

### 4.5 Resolution and exit map

For initiator `side`, action `A`, response `R`, band `b`, axis `a` (tenths):

1. `raw = RAW[A|R]`; `positional = −1` if (`side == top` and `b == −2`) or (`side == bottom` and `b == +2`), else `0`.
2. Grade pipeline of Q5 → `final`.
3. `delta = +10 × final` for the Top, `−10 × final` for the Bottom; `proposed = a + delta`.
4. **Break check**, only for a break-capable action and `final ≥ SUCCESS`:
   * `Knee Slice` and `proposed ≥ +30` → exit label `Side Control`;
   * `Recover Guard` and `proposed ≤ −30` → `Open Guard` if `final == SUCCESS`, `Closed Guard` if `final == STRONG_SUCCESS`.
5. No exit: `axis = clamp(proposed, −40, +40)`, band updated by the hysteresis rules, initiative flips.
   Exit: the **same clamp and band update are applied** (a deliberate divergence from Mount, which keeps the unclamped crossing axis out of the stored axis
   and does not update the band at an exit), `exit_destination` and `exit_reason` are set, initiative is unchanged, the match is `ended`. The oracle compares
   the post-exit axis and band.
6. `exit_reason` text: `"<Technique name> reached the pass line with final grade <Grade name>"` for a pass, `"<Technique name> reached the escape line with final grade <Grade name>"`
   for a Bottom break.
7. Costs are spent after the grade is settled (Q5 order). A rejected request changes nothing.

Declared exits: `EXIT_DESTINATIONS = {"Side Control": "side_control", "Open Guard": "open_guard", "Closed Guard": "closed_guard"}`; no unresolved labels.
`transition_destinations()` is those three ids (never `mount`).

### 4.6 Admission (all before any mutation)

*Match level* (`BjjHalfGuardMatch._validate`, mirroring `BjjMountExchange._validate`): `missing_request` → context
(`missing_configuration_or_state`, `missing_stamina_pool`, `aliased_fighter_pools`, `invalid_stamina_state`, `invalid_exhaustion_latch`, `invalid_initiator`,
`invalid_clock_context`, **then** `terminal_exchange`, `invalid_half_guard_context`) → `invalid_commitment` → `invalid_response_commitment` →
`unsupported_cost_policy` → `unknown_action` → `incorrect_action_side_or_kind` (also: an action not owned by the initiator) → `unknown_response` →
`incorrect_response_side_or_kind` → `unsupported_matchup`.

*Contract level* (`BjjHalfGuardContract`, mirroring `BjjMountContract._command_error`): `missing_command` → `missing_position` / `unknown_position` →
`missing_position_state` → the context errors above → `missing_fighter_id` → `unknown_fighter` → `not_initiator` → the match-level codes.

*Gateway level* (`BjjHalfGuardWindowGateway`, mirroring `BjjMatchWindowGateway._admission_error`): `no_open_window` → `stale_window` → context →
`window_initiator_changed` → `missing_fighter_id` → `unknown_fighter` → `not_initiator` → `response_without_action` → `commitment_without_action`;
open: `window_already_open`, `invalid_duration`. `commitment_is_policy_selected` is removed (HG-7).

### 4.7 Lifecycle and views

`open_window()` is `open_window_for(null)`. `open_window_for(duration)` (the session-owner test seam, as in Mount) checks in this order: `window_already_open` →
context errors → `invalid_duration` (`duration` is neither `null` nor an `int`) → `invalid_window_request` (`duration < 0`). `null` means the match interval and
**`0` is a legal zero-time window**. It then advances the clock by `min(duration or interval, remaining)` seconds; if the clock reached 0 the report is `closed` and
nothing opens, otherwise the window id increments and the window opens for the initiator. `submit(window_id, fighter_id, action_id, response_id, commitment, response_commitment)`
accepts an exchange or (empty action) a pass; an empty `commitment` on an exchange means `selected_commitment()` (`MEDIUM`).

**Report schema** (the graph reads these keys; both gateways return the same nested `BjjMatchWindowGateway.Report` class):

| Report | Keys (all present) | Half Guard values |
| --- | --- | --- |
| open, window opened | `closed` (false), `window_open` (true), `free` (false), `advance`, `window_id`, `fighter_id`, `role`, `commitment`, `state` | `advance` = `{"elapsed_seconds": int, "clock_seconds": int}` (no drift or stamina flow); `commitment` = `MEDIUM` |
| open, match ended by time | `closed` (true), `window_open` (false), `free` (false), `advance`, `window_id` (unchanged), `state` | — |
| submit | `window_id`, `fighter_id`, `role`, `kind`, `detail`, `transition`, `state`, `ended` | `kind` ∈ {`"exchange"`, `"reset"`}; `detail` = `{"settlement": <dictionary>}` (the exchange or pass record); `transition` = `Transition.fields()`; `state` = `state_fields()` |

The graph copies `kind` into its `decision_accepted` event (`decision`), so Half Guard events read `exchange` / `reset` where Mount's read `top_exchange` /
`bottom_decision` / `reset`: a deliberate, documented difference. **Conformance** (B1b test, run on both gateways) means: the Report key sets and types above; the
common `state_fields()` key superset below (key names and types, not values); identical results for the shared admission codes in equivalent situations
(`no_open_window`, `stale_window`, `unknown_fighter`, `not_initiator`, `window_already_open`, `invalid_duration`, `invalid_window_request`, `terminal_exchange`);
and a twin test that Half Guard and Mount windows advance by the same seconds under the same interval. `history_fields()`, `detail` and the technique vocabularies are
position-specific and are **not** required to be equal.

Public views are the Mount gateway's set: `window_fields`, `state_fields`, `history_fields`, `controller_fields` (= `{}`), `behavior_fields`, `roles`,
`action_options`, `response_options`, `selected_commitment`, `is_terminal`. `state_fields()` carries the keys F0 and the graph read (`top_stamina`,
`bottom_stamina`, `top_maximum`, `bottom_maximum`, `top_band`, `bottom_band`, `clock_seconds`, `initial_clock`, `initiator`, `exit_destination`, `exit_reason`,
`ended`, `submission_tapped`) plus Half Guard's own (`axis` = tenths ÷ 10 as a view, `axis_tenths`, `band`, `band_name`, `authority`). `carryover_segment()` is **not**
part of the Half Guard gateway (HG-20). F1's Mount-specific labels are not adapted: the opt-in constructor guarantees F1 never meets a Half Guard segment (HG-22).

**View details a developer would otherwise guess.** `top_band` / `bottom_band` are the stamina band strings (`Fresh`, `Working`, `Tired`, `Exhausted`) F0 reads; `authority` is a
fighter id (`""` at axis 0); `band_change_history` entries are `"<before>-><after>"` using the integer bands −2…+2; the commitment histories use `""` for unfunded
(Mount spells it `UNFUNDED`; deliberately different, documented). `action_options(fighter_id)` lists the fighter's own techniques with `available = true`
for the initiator and `available = false, reason = "not_initiator"` otherwise (every technique is always legal in v0: there are no setup or submission gates);
`response_options(action_id)` lists the responder side's three responses, all available, or an error (`illegal_action`, `missing_fighter_id`, context errors) exactly as the
Mount contract reports them.

## 5. Entry specifications

### 5.1 Neutral entry request (B1b) — the only way to build Half Guard (HG-13)

```
{ "role_map": {"top": <id>, "bottom": <id>},
  "fighters": { <id>: {"stamina_current": int, "stamina_maximum": int,
                       "exhaustion_latched": bool, "behavior_remainder_units": int}, ... },   # exactly the two ids, keyed by FIGHTER ID
  "clock": {"initial_seconds": int, "remaining_seconds": int},
  "window": {"last_issued_id": int},
  "interval_seconds": int }
```

`BjjHalfGuardEntry.validate(request)` is pure and fails closed, building nothing, in this order: exact keys and types (no floats; `int` is not `bool`); ids pass
`BjjPositionContract.fighter_ids_error`, are distinct and equal the key set of `fighters`; `role_map` has exactly `top` and `bottom` and is a bijection onto those
ids; stamina `maximum` in `1..MAXIMUM_EXACT`, `current` in `0..maximum`, the latch consistent with the pool's thresholds (`current <= enter` ⇒ latched,
`current >= recover` ⇒ not latched, between ⇒ either); remainders within ±`MAXIMUM_EXACT`; clock `initial` in `1..MAXIMUM_EXACT`, `remaining` in `1..initial`;
`last_issued_id >= 0`; `interval_seconds >= 1`.

`BjjHalfGuardMatch.from_entry(request)` builds: the pool and meter of the fighter assigned to each role (**looked up by fighter id**, so a swapped role map gives
each fighter its own stamina), the clock, `axis_tenths = +5`, `band = 0`, `initiator = "top"` and an empty history. Tests and oracles use the same path; scenario and
normal-match starts are not registered (P-12).

### 5.2 Mount edge adapter (B1c)

`BjjHalfGuardMountEdge.entry_from_record(record, interval_seconds)` is pure: (1) `BjjMountCarryover.validate_segment(record)`; (2) `source_position_id == "mount"`,
`exit == {kind: "exit", raw_destination: "Half Guard", destination_position_id: "half_guard", resolved: true}`, `terminal.ended == true`, `submission_tapped == false`,
`clock.remaining_seconds >= 1`; (3) the edge's role map is the **identity** (`top` ← `fighter_by_role.top`, `bottom` ← `fighter_by_role.bottom`, D1); (4) the record's
role-keyed `fighters.top` / `fighters.bottom` are **re-keyed by fighter id** into the request (POSITION_TOPOLOGY §6.2's hazard: stamina must follow the
fighter, not the role label); (5) `interval_seconds` comes from the caller (HG-25). It reads no Mount object, so it cannot mutate one.

### 5.3 Role maps

The receiver accepts any validated bijection; an edge declares which one is legal. Mount → Half Guard declares the identity map. A future source (Standing after a
takedown) declares its own. No Half Guard rule reads a Mount role label.

### 5.4 Latch restoration (HG-15, T-7 option e)

If the latch is `false`: `BjjStaminaPool.create(current, maximum)`. If `true`: `create(0, maximum)` then `set_current(current)`. From the pool code: `create(0, max)`
latches for every capacity (`0 <= floor(0.25 × max)`), and `set_current` unlatches only at `current >= ceil(0.35 × max)`; a latched pool therefore stays
latched for every `current` the validator accepts as latched. This is the pattern `BjjMountMatch._copy_pool` already uses. The **proof obligation** is still tested (in B1b, because every oracle scenario depends on it):
for capacities `{1, 2, 3, 4, 7, 20, 37, 64, 100}` every (current, latched) pair the validator accepts, and for a large capacity (`9007199254740991`) the boundary grid
`current ∈ {0, 1, enter−1, enter, enter+1, recover−1, recover, recover+1, max−1, max}`: the restored pool equals the source pool field for field and, after fixed
spend/recover grids, stays equal. If any pair fails, fall back to a validated pool factory (option b) and re-propose.

### 5.5 Negative-first tests

Each refusal leaves its inputs untouched and builds nothing: every key missing/extra/wrong type/float/bool-for-int; ids duplicate/empty/padded; role map missing,
extra, duplicate, unknown, same fighter in both roles, not a bijection; stamina out of range, inconsistent latch; clock out of range or `remaining == 0`;
`interval_seconds` zero or negative. The Mount edge's own refusals (wrong source, wrong exit label/destination, unresolved exit, not ended, tapped, remaining 0, invalid
record) belong to B1c; the entry-request refusals and the latch proof belong to B1b. Positive: a grid of valid requests and records; state equality with the input; swapped role map follows the fighter id; determinism.

## 6. B1d — opt-in graph integration (atomic Mount → Half Guard)

### 6.1 Changes to the graph (additive; the only slice that touches qualified code)

* `BjjPositionGraphMatch.create(...)` is **unchanged** and builds a graph with **no receivers**, so every Mount exit halts exactly as today (HG-22).
* New `create_with_receivers(configuration, top_id, bottom_id, receivers)` builds the same graph with a receiver table. **Contract:** `receivers` is a `Dictionary`
  whose keys are a subset of `{"half_guard"}` (the only typed slot) and whose values are `Callable`s taking `(record: Dictionary, interval_seconds: int)` and returning a
  `BjjHalfGuardWindowGateway.Creation`; anything else is refused at construction with `invalid_receivers` and no graph is built. The table is the activation point, so an
  unknown key (for example `open_guard`) can never silently activate anything. At commit the returned object must be a `Creation` whose gateway's
  `roles().fighter_by_role` equals the graph's own fighter ids (POSITION_GRAPH §5 step 3, "identities unchanged"); otherwise the commit is the HG-18 halt.
  `BjjPositionGraphMatch.default_receivers()` returns the Half Guard edge for **future callers** (tests and the later owner flip; no production caller exists today,
  F1 uses `create`); a test may pass a faulty `Callable` to inject a failure. `create_with_receivers(..., {})` must be observably identical to `create`. The cadence is
  captured from the graph's own `configuration.interval` (HG-25).
* The typed `_gateway: BjjMatchWindowGateway` slot stays as the retained Mount segment; a second typed, nullable `_half_guard: BjjHalfGuardWindowGateway` slot holds the
  receiver; every pass-through (`state_fields`, `history_fields`, `controller_fields`, `window_fields`, `roles`, `action_options`, `response_options`,
  `selected_commitment`, `behavior_fields`, `open_window_for`, `submit`) branches on `_half_guard != null` (HG-16). `Report` locals are typed
  `BjjMatchWindowGateway.Report`, which the Half Guard gateway also returns.
* A read-only `active_position_id()` (`"mount"` or `"half_guard"`) is added; `submit()` uses it instead of the hard-coded `POSITION_ID` for the `blocked_transition`'s
  `from_position_id`, the exit classification and `_record_terminal`.
* **Classification (HG-23).** The static `classify_exit_from` is byte-identical and no classification code is added. For Mount, the instance takes the static answer
  (`blocked`, `destination_not_implemented`, `<id>`) and treats it as a `transition` only if `<id>` is a key of the receiver table; `Open Guard` (not in the table) and
  `Reversal` (`unresolved_destination`) stay blocked as today. For an active Half Guard segment the instance calls the same static function with Half Guard's declarations
  (`{"half_guard": {"exits": EXIT_DESTINATIONS, "unresolved": []}}`), so a Half Guard exit halts with `destination_not_implemented` and a correct `from_position_id`; a test pins
  that the static and instance answers differ only by this design.

### 6.2 Protocol (after an accepted decision whose outcome is a receiver exit)

1. Detect by the decision's transition and Mount's `exit_destination`, never by `ended`.
2. Classify (above).
3. Validate and build in isolation: `carryover_segment()` of the retained Mount gateway (the window is closed) → `BjjHalfGuardMountEdge.entry_from_record` →
   `BjjHalfGuardMatch.from_entry` → `BjjHalfGuardWindowGateway`. Nothing is mutated.
4. Commit: set `_half_guard`, append one `transition_committed {from_position_id, to_position_id, label}`. This step cannot fail. The Mount gateway object stays in
   `_gateway`, **frozen**: never advanced, submitted to or exported again (HG-24); its histories and D3-B record stay with it.
5. Open no window.

Event order (fixed, replay-checked): `decision_accepted` → `transition_committed` → later `window_opened`. Global indices stay monotonic; window ids continue
(`last_issued_id + 1`); the transition charges nothing and moves no clock.

**Failure semantics (HG-18).** The Mount exchange is already accepted and settled when step 3 runs, so a failure there cannot be a rollback. It is treated like an
unsupported destination: the exchange stands, the graph halts with `transition_blocked` reason `transition_entry_invalid`, and later commands are refused. This
**amends** the letter of `POSITION_GRAPH.md` §5 and §8 (both list failed construction under "leaves state unchanged"), which cannot be honored once the
exchange is settled; the owner approves the amendment explicitly. It is unreachable for a valid Mount export and is tested through the receiver-table
injection seam.

### 6.3 After the commit

`state_fields()`, `roles()`, `window_fields()`, `action_options()`, `response_options()`, `selected_commitment()`, `behavior_fields()`, `controller_fields()` (`{}`)
and `history_fields()` come from the Half Guard segment. **`carryover_export()` is refused** with `carryover_unsupported_position` while Half Guard is active (HG-20):
a Half Guard source schema is T-9 work. The v1 envelope validator is unchanged and accepts only `destination_not_implemented` / `unresolved_destination` halted reasons,
so a graph halted with `transition_entry_invalid` (Mount still the active segment) is refused by that validator with its existing `inconsistent_graph_segment`; both codes are pinned by B1d tests. A Half Guard exit (`Side Control`, `Open Guard`, `Closed Guard`) halts the graph exactly as
Mount's exits do today. Mount is not re-enterable.

## 7. Independent test-only oracle (D6, HG-19)

**Purpose.** There is no Python Half Guard. The oracle is a *new* Python implementation written from §4 after owner approval, so the GDScript engine is compared with
a second, independently written implementation, not with itself.

**Placement.** `tests/oracles/half_guard_v0.py` (importable module; no production engine; nothing under `src/` is edited), the generator
`GODOT_V1/tests/generate_half_guard_reference.py` (adds `tests/oracles` to `sys.path`; JSONL fixture in the ignored generated directory) and
`tests/test_half_guard_oracle.py` (Python unit tests with hand-computed literals; imports the oracle with the same `sys.path` insertion; whether CI discovery of
`tests/` resolves it is verified in B1b, since `tests/` is not a package). Names are provisional.

**Independence rules.**
1. Written from the approved rules sheet; table-driven, integer tenths; never reads the GDScript.
2. Imports only frozen, position-independent Python primitives (`StaminaCostPolicy`, `ExhaustionPolicy`, grade types) and **never constructs or runs a `MountMatch`**.
3. The three small commitment-settlement functions are re-implemented in the oracle, and a unit test asserts they equal Mount's Python helpers
   (`MountMatch._initiator_commitment_modifier`, `_response_undercommitment_modifier`, `_commitment_grade_transform`, `src/bjj_game/engine/match.py`) over the full
   grade × commitment grid (the one place Mount's private helpers are *called*, as an equality check, with `""` ↔ `None` and ints ↔ `Grade` mapped; the `engine.match` import lives inside that unit test, never in `half_guard_v0.py`).
4. **Latch expectations come from a literal two-state hysteresis model** in the oracle, not from building a pool with the same `create(low)` + `set_current` trick
   HG-15 proposes; the Godot side proves restore-versus-source equivalence separately.
5. **Mutation-sensitivity control:** a development-time check (evidence recorded in the B1b pull request, not a CI step) flips one raw grade and one threshold in a disposable copy of the fixture and confirms that the Godot replay fails.

**Scenario grids (counts measured, never asserted from this document).** Exchange: every axis (81) × every legal band × both initiators × every action × response ×
commitment × a boundary stamina grid (`current ∈ {0, 2, 3, 6, 7, 11, 12}` per fighter, latch enter/recover edges for capacities `1, 3, 4, 37, 100` and a large
one). Lifecycle: windows, passes, timeout, a window that brings the clock to 0. Entry: valid and invalid requests and role maps. Band update: every rule edge.
Non-mutation: every admission code against a full snapshot (pools, axis, band, initiator, history, clock, window state). Precedence: requests with several
simultaneous faults. Each scenario is replayed twice.

**CI mechanics.** The Godot reference test prints and asserts the measured scenario/operation/comparison counts inside the test and ends with the usual
`<name> PASS: N assertions` line, so the existing fail-closed validator (`--name`, `--exit-code`, `--expected-assertions`, exact pin) protects it; the generator step
fails on a missing or empty fixture. The older oracle-replay steps are error-scan-only; the new ones are stricter (a deliberate improvement, not a claim about
the old ones). A negative control proves the entry factory is not reachable from the registry or the graph's default constructor.

**Frozen evidence.** The Mount digest and every Mount fixture stay unchanged; the new fixture is generated, never edited to silence a mismatch.

## 8. Architecture feasibility (keep / adapter / refactor)

Counts quoted are CI-pinned values or are labelled estimates. No unpinned assertion counts are quoted.

| # | Change | Concrete need | Keep | Adapter | Refactor | Recommended | Measurable effect and regression risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | A second position's rules, state, contract | A real receiver | n/a | n/a | n/a | **New classes** (rules, catalog, resolver, match, contract, entry) | ~700–800 new lines (estimate); Mount files touched: 0 |
| 2 | Window lifecycle for Half Guard | Window id, admission order, reports | Copy Mount's gateway logic into a sibling gateway | A shared bookkeeping helper | Abstract base class on the Mount gateway | **Sibling gateway** (~240 lines, duplicated admission order) | A refactor would change a class covered by the gateway, graph, contract, F0 and F1 suites; the copy's risk is divergence, mitigated by a conformance test (views **and** the `Report` schema) run on both gateways, placed in B1b |
| 3 | Graph holds a second segment | Swap the active position | Single `_gateway` (impossible) | `Variant` segment | Segment base class | **Second typed nullable slot** (HG-16) | ~80 lines and a dozen branches in the graph; public API unchanged; `_gateway` and the tests that read it stay valid; two graph property-list pins change and the "one gateway" invariant is revised (§9.3, HG-16) |
| 4 | Default graph behavior | Do not disturb qualified suites or F1 | Commit by default | Opt-in constructor (HG-22) | Rewrite classification | **Opt-in constructor** | Default graphs byte-identical: the existing exit/classification/export/F1 tests are untouched; flipping the default later is one deliberate step |
| 5 | Settlement order | Same order as Mount | Re-implement once in Half Guard | Call a shared function | Extract Mount's settlement into a shared class | **Re-implement** (~60 lines) + oracle | Extraction would touch the exchange oracle's surface (14,631 scenarios / 8,851,698 comparisons) for no behavior gain |
| 6 | Carry-over entry | Preserve state without mutating the source | Hand over the same pools | Rebuild from a neutral request via public API (option e) | New pool factory | **Option e** with an exhaustive equivalence proof; fallback b | 0 new production API if the proof holds |
| 7 | F0/F1 read access | Work with a second position | Mount-specific adapter | Common `state_fields()` key set (§4.7) | A general snapshot interface | **Common key set**, no adapter change | F0 unchanged; F1 stays Mount-only because default graphs never hold Half Guard |
| 8 | Registry use | Validate destination ids | None | Test pins ids ⊆ registry | Derive constants from the registry | **Test pin** | No production edit |

## 9. Slice plan (HG-21)

### 9.1 B1b — Half Guard mechanics (after owner approval)

*Scope note (HG-26F):* B1b is either the direct baseline of §§4–5 or that baseline plus HG-26A/C (recommended, §12.6); it never includes feints or the sealed-intent protocol.

Files (new only): `scripts/positions/half_guard/{half_guard_rules,half_guard_catalog,half_guard_resolver,half_guard_match,half_guard_entry,half_guard_contract,half_guard_window_gateway}.gd`
(+ `.gd.uid`), `tests/test_half_guard_rules.gd`, `tests/test_half_guard_reference.gd`, `tests/test_half_guard_conformance.gd` (views and `Report` against the Mount gateway),
`tests/oracles/half_guard_v0.py`, `tests/test_half_guard_oracle.py`, `GODOT_V1/tests/generate_half_guard_reference.py`, `docs/HALF_GUARD_V0_RULES.md`, and one workflow
step per new Godot suite through the existing log validator (exact measured pins); no routing change. Negative-first order: refusals → catalog pins → rules/bands →
resolution → lifecycle → entry → oracle replay → determinism.

Definition of done: oracle reviewed and accepted first; Godot engine matches it with zero mismatches; the entry-request refusals (§5.5) and the latch equivalence proof (§5.4) pass; the conformance test passes; every Mount pin and suite unchanged
(256,992 / 431 / 750 / 1,036 and the Python parity steps); `git diff --check`, workflow validation; exact-head CI (Godot + Python 3.11/3.13). Python changes route as
shared, so full qualification runs on that PR (expected; not shortened).

### 9.2 B1c — Mount edge adapter and equivalence proofs

New: `half_guard_mount_edge.gd`, `tests/test_half_guard_mount_edge.gd`. Changes no existing file. DoD: the Mount edge refusals (§5.5), role re-keying (state follows the fighter id),
source-view equality before/after (the Mount gateway and graph views are identical after building an entry), zero Mount change.

### 9.3 B1d — opt-in graph integration

Changes: `graph_match.gd` only (second slot, receiver table, `create_with_receivers`, `active_position_id()`, commit, branched pass-throughs, export refusal), plus
documentation. Because `create` is unchanged:

* **Untouched by design:** `test_position_graph_classification.gd` (the static classifier is byte-identical), `test_position_registry.gd` (including its pinned
  `classify_exit_from("mount", "Half Guard")` answer and the 431 pin), `test_mount_practice.gd` and its 1,036 pin (F1 builds default graphs; its `_halted_controller("Half Guard")`
  and every `_gateway`/`graph._graph` use keep working; its "no public name contains gateway" check still passes with the three new public names), `test_position_graph_boundaries.gd` apart from the one pin below (exit search, lockstep tallies), `test_window_gateway_boundaries.gd`,
  `test_position_contract_boundaries.gd`, `test_mount_slice.gd` (A3d pins), `test_fighter_foundation.gd`, and the Mount/stamina/exchange/lifecycle/D3-B oracles.
* **Changes on purpose (two pins, verified by reading the tests):** (1) `test_carryover_export.gd` (~line 560) pins the graph's exact private property list
  `["_blocked", "_events", "_gateway", "_status", "_terminal_reason"]`; (2) `test_position_graph_boundaries.gd` (~lines 141–148) pins the same list under the name
  "graph holds only gateway, status, events, blocked, terminal reason" and asserts "one gateway, no second owner". Adding `_half_guard`, the receiver table and the
  cadence changes both, and HG-16 revises that invariant (the retained Mount gateway is still the only *Mount* owner; Half Guard has its own). The documentation text that says Half Guard is
  unimplemented stays true for default graphs and gains a note for opt-in graphs (`POSITION_GRAPH.md` §§5, 8 amendment per HG-18; `CARRYOVER_EXPORT.md` v1 note; `F1_MOUNT_PRACTICE.md` unchanged).
* **New tests:** whole-graph equality before/after for every refusal; transition tests (continuity of clock, pools, latches, remainders; the frozen Mount gateway's
  views and histories identical afterwards; zero charge; consumed window; no automatic window; event order and monotonic indices; window id continuity; token counts
  unchanged); Open Guard and Reversal still halt on an opt-in graph; every Half Guard exit halts with `destination_not_implemented` and `from_position_id = half_guard`; failure injection
  (HG-18); replay twice over the existing seed/axis/stamina grid; lockstep against a twin driven through the bare Mount gateway up to the exit; **a default graph with the
  same inputs halts at the same event index as before** and **`create_with_receivers(..., {})` is observably identical to `create`** (the opt-in proofs); a bad receiver table
  (`invalid_receivers`: non-dictionary, unknown key, non-`Callable` value) builds no graph; a wrong-identity or non-`Creation` receiver result is the HG-18 halt; after the commit a stale or duplicate
  window id, a Mount technique id, an unknown fighter and an identity mismatch are refused with whole-graph equality before and after; commands after a Half Guard halt are refused;
  a Half Guard timeout is a terminal outcome and never an exit; F1's controller is never given an opt-in graph.

Owner-flip of the default (making `create` commit) is a separate, later authorization that would carry the larger test update (classification ~20 assertions, exit-search
and export cases, the F1 blocked-state tests and the 431/1,036 pins).

### 9.4 Later slices (not proposed for approval now)

B1e: a measured stamina/recovery rule for Half Guard (pre-registered, like D3-B); B1f: Sweep/Wrestle-Up/Backstep with owner-approved landings; Open Guard, Closed Guard
and Side Control receivers; return routes and segment identity (P-11); a graph envelope v2 and carry-over export for non-Mount sources.

## 10. Prototype evidence (throwaway scripts, reproduced in the appendices)

Appendix A encodes §4.1–§4.5 **for raw grade + positional modifier only** (it omits the exhaustion, magnitude and undercommitment steps of Q5) in integer tenths and
checks, without any Godot or repository code:

* every axis in −40…+40 has a legal band and every band rule lands on a legal axis/band pair;
* every action has a counter (≤ −1) and a favorable response (≥ +1);
* breadth-first search over (axis, band, initiator) with free choices: 42 reachable states; the earliest exits are `Closed Guard` in 2 windows, `Side Control` in 3 and
  `Open Guard` in 4 (reachable only with cooperating or self-harming opponents);
* with a responder who always plays the best counter, no exit is reachable;
* 2,000 uniformly random 60-window games (seeds 0…1999) from the entry: `Side Control` 880, `Closed Guard` 671, `Open Guard` 413, timeout 36; median exit window 12–14.
  The random sampler ignores stamina, commitment and the real clock, and the 60-window horizon is arbitrary;
* stamina: with MEDIUM exchanges and no recovery a fresh fighter reaches the Exhausted latch at window 11.

Appendix B encodes the full grade pipeline of Q5 (shared position-independent functions transcribed from `BjjCommitmentSettlement` / `BjjExhaustionPolicy`) and finds that
the best final grade reachable from a raw −2 counter is `0` (CONTESTED) and from a raw −1 counter is `+1` (SUCCESS): the break-capable actions cannot beat their −2
counters, while ordinary counters can be lifted by exhaustion and under-commitment.

The first draft of the Recover Guard row had no `+1`, which made `Open Guard` unreachable; the prototype exposed it before the proposal was finalized. These numbers
describe the **proposed** tables only. They are not parity evidence, not a balance study and not an oracle; the appendices let anyone re-run them.

## 11. Risks and unresolved items

* **Stamina economy (highest risk, HG-6).** Without recovery, Half Guard is a mechanics-and-transition milestone, not a balanced position (Q4 lists the consequences).
* **New content.** Response names, the 15 grades, the break lines and the Recover Guard split are proposals that define gameplay; they need owner review, not only engineering review.
* **Duplicated settlement and admission order** (§8 rows 2 and 5) rely on the oracle and the conformance test, not on shared code.
* **Entry strength is flat** (fixed +5). Distinguishing SUCCESS from STRONG_SUCCESS needs a schema decision.
* **Deliberate v0 simplifications versus the Guide:** neutral is not a break (HG-3), initiative is strict alternation (HG-5), authority is reported only (HG-4).
* **Absent by design:** return to Mount, Sweep, Wrestle-Up, Backstep, opening-triggered initiative, behaviors/drift/RECOVER/D3-B, a graph envelope v2.
* **Opt-in receivers (HG-22)** keep every qualified suite and F1 unchanged but mean a "Half Guard commits" graph exists only through the new constructor until the owner flips the default.
* **Graph protocol amendment (HG-18)** edits the letter of `POSITION_GRAPH.md` §5/§8 when B1d lands.
* **HG-26 risks** (new numbers, the readiness coupling, the option-M ordinary-counter stalemate, the Bottom-favorable table asymmetry, a second gateway path for the sealed-intent protocol) are in §12.10–§12.11.

## 12. HG-26 — Tactical preparation, feints and defensive counterplay (proposal)

**Status.** The *direction* (positional preparation, feints, defensive effort; game-wide, position-specific details) is owner-approved. The owner has also **provisionally approved** these Half Guard v0
prototype choices: two local readiness tracks `top_base` and `bottom_frame`; `None/Partial/Ready` tiers starting `Partial/Partial`; **option M** (Knee Shield and Knee Pin are the readiness-governed powerful counters); positional preparation
and defensive effort in B1b; feints remain later B1g/B1h work. **These are Half Guard prototype choices, not frozen game-wide numerical rules.** **Every other number and rule in this section is a
proposal** until the owner accepts it by sub-decision id (the exact list is §12.13.1). The game-wide concepts, the information protocol and the test obligations are in
[TACTICAL_PREPARATION_AND_FEINTS.md](TACTICAL_PREPARATION_AND_FEINTS.md); this section holds only what is Half Guard-specific. Nothing here is implemented, no Mount behavior
changes, and §§1–11 stand as written except where §12.0 says otherwise.

### 12.0 What changes in the earlier sections if HG-26 is approved

* The property in §4.4 ("the two break-capable actions can never succeed against their −2 counter, even after exhaustion and commitment settlement") holds **only at the
  neutral readiness state**. With HG-26A it becomes the conditional statement of §12.1.4. At entry (both conditions `Partial`) §4.4 and Appendices A–B are unchanged.
* Q5's grade pipeline gains two saturating steps after the positional modifier (§12.1.3). Q4 (no behaviors, no drift) is unchanged: conditions do not decay.
* §9.1 (B1b) is conditional on HG-26F: B1b is either the direct baseline of §§4–5 or the baseline plus HG-26A/C (recommended). **Feints are never part of B1b.**
* The entry request (§5.1) and the Mount edge (§5.2) are **unchanged**: readiness is not carried from Mount and starts at `Partial` for both fighters.
* **Corrections after owner review (this revision):** §12.3 distinguishes requested, funded-effective and charged commitment and makes HIGH preservation depend on *paid* effort (Rule 1); §12.5 replaces the parity proposal
  for feints with a separately funded surcharge model (later slice only); §12.1.6 resolves the exit-consumption ambiguity; §12.12 reviews the 15 raw grades; §12.13 is the corrected B1b approval checklist.

### 12.1 HG-26A — Positional preparation (minimum viable)

**12.1.1 State.** Two integers owned by the Half Guard match (no shared class, HG-26F): `top_base` (the Top's pressure/weight structure) and `bottom_frame` (the Bottom's hip and
knee frame structure). Tier `0 = None`, `1 = Partial`, `2 = Ready` (Guide §21 names). **Entry: both `Partial`**, fixed, not derived from Mount (D1). Range `0..2`. **No decay** (v0 has
no drift, HG-6). `state_fields()` gains `top_base`, `bottom_frame` (ints) and their names; the history gains `readiness_change_history` (`"<track>:<before>-><after>:<technique>"`).
The carry-over export is untouched (HG-20). Names are proposals.

**12.1.2 Interaction of the five v0 techniques** (`final` = the full-pipeline final grade; "success" = `final >= SUCCESS`; an exit exchange is processed like any other accepted exchange, §12.1.6):

| Technique | Role | Reads (own condition) | Writes on success | Consumed on attempt |
| --- | --- | --- | --- | --- |
| Crossface (Top) | compromise | — | `bottom_frame` −1 | — |
| Flatten (Top) | establish | — | `top_base` +1 | — |
| Knee Slice (Top) | **prepared**, break-capable | `top_base`: shift +1 / 0 / −1 for Ready / Partial / None | — | at Ready: `top_base` −1 |
| Underhook (Bottom) | establish | — | `bottom_frame` +1 | — |
| Recover Guard (Bottom) | **prepared**, break-capable | `bottom_frame`: shift +1 / 0 / −1 | `top_base` −1 | at Ready: `bottom_frame` −1 |

Consumption applies to the attempt, whatever the result, so a prepared technique cannot be repeated for free. The single track a fighter owns powers *both* that fighter's prepared technique and that fighter's powerful
response (§12.3): attacking with Knee Slice spends the base that Knee Pin would use, and Recover Guard spends the frame that Knee Shield would use. This coupling is the intended positional tradeoff.

**12.1.3 Pipeline order (all steps saturate at ±2 after each step, like the existing settlement).**
`raw` → positional modifier (§4.5) → **attack readiness** (prepared technique only) → **defense readiness** (governed response only, §12.3) → exhaustion → magnitude → undercommitment.
Order matters because of saturation: a raw −2 shifted −1 stays −2 before a later +2 lifts it to 0. The oracle must reproduce this order exactly. Tier updates happen after grading **and after the stamina charges** (the paid-effort test needs the charge), in the fixed order of §12.1.6.

**12.1.4 What preparation does to the decisive counters (Appendix D §8, full pipeline, band 0).** Best final grade reachable by a break-capable action from a raw −2 counter:

| Attacker tier \ defender power tier | Ready | Partial | None |
| --- | --- | --- | --- |
| None (no stamina effects / with every exhaustion and commitment lift) | −2 / 0 | −2 / 0 | 0 / +2 |
| Partial | −2 / 0 | −2 / 0 | 0 / +2 |
| Ready | −2 / 0 | −1 / +1 | +1 / +2 |

So a **Ready** powerful defense cannot be beaten by a direct attack at all, a **Partial** one only by a **Ready** attacker who also gains every stamina lift, and an **unprepared** one by any attacker with lifts. At the neutral state
(Partial / Partial) the §4.4 property is unchanged.

**12.1.5 Option M versus option S (the owner chooses; Appendix D §§3, 6, 7).**

* **M (recommended): only the two decisive counters are governed** (Knee Shield by `bottom_frame`, Knee Pin by `top_base`). Smallest change that makes "powerful counters need preparation" real.
* **S: every response is governed** by its owner's track (shift −1 / 0 / +2). Evidence: against a defender who always plays the best counter to the visible technique the attacker can force an exit under S
  (windows 9 / 12) but not under M; under S a *Ready* defender holds every direct attack to −2 at the neutral state of the other fighter (a stronger fortress), and every counter wears the structure that powers it
  (more state coupling, a larger oracle, more tuning).
* Alternative **L**: one shared track or a continuous value — rejected for v0 (GP-7).

**12.1.6 Exit exchanges and the terminal state (resolves the exit-consumption ambiguity; recommended, HG-26A-5).** An accepted exchange that produces an exit is processed by the **same** readiness rules as every other accepted exchange; there is
no exit special case. Exact order for every accepted exchange: (1) all admission checks, before any mutation; (2) resolve the grade from the **pre-exchange** tiers (readers see the tiers as they were); (3) apply the axis, band, exit and
initiative rule of §4.5 (the exit decision uses the final grade and the proposed axis, never a tier); (4) spend stamina, initiator then responder, with the Rule 1 waiver of §12.3.1, so `paid_effort` is known; (5) consume the initiator's tier
(break-capable attempt at Ready); (6) wear the responder's governed tier (§12.3.2); (7) apply the builder/weakener effect (`final >= SUCCESS`); every step saturates at `0..2`; (8) append the histories and `readiness_change_history` in this order;
(9) set the terminal fields (`exit_destination`, `ended`). Consequences: the terminal tiers are the post-exchange values and appear in `state_fields()`; the exit exchange grants no extra action or window and leaves initiative unchanged (§4.5);
every later command is refused `terminal_exchange` before any tier is read, with whole-snapshot equality; no receiver is affected, because every Half Guard exit currently halts (all destinations are unimplemented), the entry request contains no
readiness field (an extra `top_base` / `bottom_frame` key is refused as an unknown key) and a future receiver declares its own entry preparation. One track can be changed twice in one exchange (a Recover Guard success wears `top_base` against Knee Pin and
weakens it), so the order is part of the oracle.
**Oracle tests for §12.1.6.** For each break technique × initiator tier `{0,1,2}` × responder governed-response tier `{0,1,2}` × outcome `{exit, success without exit, contested, failure}`: terminal tiers equal the oracle's; the tier-update function is the
same function for exit and non-exit (a property test that varies only the axis); double-touch cases; `readiness_change_history` order; post-exit refusal with no tier change and no extra history; the export is refused (HG-20) so no tier leaks; an entry request carrying
a tier key is refused; no extra window opens.

**Mount parity / compatibility.** None: new files only, no Mount file, record, fixture or digest changes; A3b record unchanged; F0 reads only existing keys; F1 never meets Half Guard (HG-22).
**Required tests.** Entry values; every builder/weakener/consumer cell; floor and ceiling; shift table over all 9 states × raw grades; saturation-order cases (e.g. raw −2, attacker None, defender None → 0, not −1);
readiness transition table; rejected commands change nothing; histories; oracle replay (grid × 9 states).
**Owner decisions.** HG-26A-1 (two tracks, tiers, entry: provisionally approved), HG-26A-2 (interaction table), HG-26A-3 (shifts and pipeline order), HG-26A-4 (option M: provisionally approved), **HG-26A-5 (uniform exit processing, §12.1.6)**.

### 12.2 HG-26B — Feint eligibility (explicit pairs, deferred slice)

Pairs are **listed, never derived**. A pair needs: different techniques; the real technique is **break-capable**; the apparent technique is **not** break-capable; real and apparent both belong to the acting side; no chains; and the
pair's condition holds in the *public* state.

| Id | Side | Apparent → real | Required condition | Status |
| --- | --- | --- | --- | --- |
| FP-1 | Top | Crossface → Knee Slice | `top_base >= Partial` | **recommended** |
| FP-2 | Bottom | Underhook → Recover Guard | `bottom_frame >= Partial` | **recommended** |
| FP-3 | Top | Flatten → Knee Slice | `top_base >= Partial` | **not recommended**: fails the counterplay rule (§12.4) |

Plausibility: pressure or control work that sets up a knee slice; an underhook fight that sets up guard recovery (names from Guide §11.4; no technique descriptions are invented). The apparent technique **never resolves**
and changes no condition; the *real* technique's reads, consumption and writes apply. **Bite adjustment (proposal):** if the response is a best counter to the apparent technique (Crossface → Underhook Fight; Underhook → Head Control)
the real technique's grade shifts **+1** for the attacker; otherwise **−1**; applied after the readiness shifts and before exhaustion. Finals at the neutral state, defender seeing only the apparent technique (Appendix D §5):

| Pair | vs Hip Frame / Head Control | vs Underhook Fight / Hip Pressure | vs Knee Shield / Knee Pin |
| --- | --- | --- | --- |
| FP-1 Crossface → Knee Slice (direct Crossface, direct Knee Slice) | −1 (+1, 0) | **+2** (−1, +2) | −2 (0, −2) |
| FP-2 Underhook → Recover Guard (direct Underhook, direct Recover Guard) | **+2** (−1, +2) | 0 (0, +1) | −2 (+1, −2) |

A feint is **never** a distinct gameplay window: it is one exchange (initiative flips once, the clock advances once, one history record with a `feint` sub-record). A feint resolved against a position-exit condition uses the real
technique's exit rule unchanged. Refusals: `feint_not_supported`, `feint_not_eligible`, `feint_real_equals_apparent`, `feint_requires_funding` (§12.5).
**Owner decisions.** HG-26B-1 (the pair list), HG-26B-2 (±1 bite adjustment), HG-26B-3 (apparent never resolves), HG-26B-4 (real must be break-capable).

### 12.3 HG-26C — Defensive effort

**Provisionally approved by the owner (Half Guard prototype choice, not a frozen game-wide rule):** option M — **Knee Shield** (reads `bottom_frame`) and **Knee Pin** (reads `top_base`) are the governed powerful counters.
**Defense readiness shift toward the initiator:** Ready −1, Partial 0, None **+2**. The numeric values remain proposals (§12.13.1). The +2 is deliberate: with +1 the constant Knee Shield defender is a structural fortress
(no forced exit, `cfg['none']=1` in Appendix D); with +2 preparation beats it (§12.7 S-4).

**12.3.1 Requested, funded effective and charged commitment (audit of the existing settlement).** In `mount_exchange.gd` (`attempt`), `BjjStaminaCostPolicy` and `BjjCommitmentSettlement` the responder's commitment is three different values:

| Quantity | Definition | Where it is recorded |
| --- | --- | --- |
| **Requested** | what the caller names (`response_commitment`; empty means `MEDIUM`) | the request |
| **Funded effective** | `determine(requested, pool.current)`: the highest tier `<= requested` whose cost the pool can afford; unfunded (`""`) if even LOW (3) is unaffordable; `funding_gap = requested_cost − effective_cost` | `responder_funding`, `response_effective_commitment_history` |
| **Charged** | `spend_up_to(effective_cost)`, or `0` when **Rule 1** waives it (the *initiator's* funded effective commitment is unfunded); the waived amount is recorded | `response_stamina.charged`, `response_stamina_waived_history` |

Facts that decide the treatment: (1) the waiver changes **only the charge**: the grade pipeline (undercommitment, exhaustion) already uses the *funded effective* commitment, so a HIGH-funded responder keeps its
capability when the charge is waived; (2) Rule 1 can apply only to an initiator with less than the LOW cost (3), so it coincides with the attacker's weakest moment; (3) charges are made after grading, initiator first, then
responder; (4) Rule 2 (the supplemental submission hold) does not exist in Half Guard.

**12.3.2 Recommended treatment (HG-26C-5): `paid_effort`.** Define `paid_effort = (effective_cost > 0) and (charged >= effective_cost)`. Then:

| Responder's funded effective commitment | Charge | Defense strength | Wear of the governed track (after grading) |
| --- | --- | --- | --- |
| LOW, or unfunded | any | counted as tier **None** (the effort was not made) | none |
| MEDIUM | paid **or** waived | tier-based | −1 if `final != 0` (decisive either way) |
| HIGH | **paid** | tier-based | −1 **only if the defense failed** (`final >= +1`); a successful HIGH defense preserves the structure |
| HIGH | **waived (Rule 1)** | tier-based | as MEDIUM: −1 if `final != 0`; **no preservation** (the benefit was not paid for) |

* *Strength* follows the funded effective commitment, exactly as Mount's grading already does, so a waiver never changes a grade. *Preservation* is a purchased benefit and follows the charge actually paid.
* This consults the recorded charge only. Rule 1, the cost policy, Mount's gateway and every frozen Mount behavior are untouched (HG forces Rule 1 ON, Rule 2 OFF as the Mount production policy does).
* **When a defense succeeds** the axis swings against the attacker by the existing rule. The defender keeps the structure only by actually paying HIGH (+5 over MEDIUM); at MEDIUM it loses one tier, so a defender starting at
  `Partial` answers one repeated decisive attack at full strength and is then at `None` until it rebuilds with its own initiative window (Underhook, which a correct counter denies). **When it fails** the structure wears at MEDIUM and
  HIGH. **At LOW** a defense is cheap and weak (Guide §27: a cheap threat can be answered cheaply). The prototype assumes MEDIUM responses; the LOW and HIGH rows are specified, not modeled.
* Arithmetic (cost policy 3/7/12, latch at `<= 25` of 100): a fresh defender paying HIGH every window reaches the Exhausted latch after 7 defenses (100 → 88 → … → 16), while an attacker paying MEDIUM per attack is at 51.

**12.3.3 Alternatives.** *W-A* use the funded effective commitment alone: a HIGH-funded responder obtains free preservation whenever the attacker is unfunded (exploitable, contradicts "paid effort"); rejected. *W-B* treat a waived
defense as no effort (strength None): changes grading relative to Mount's treatment and punishes the defender for the attacker's exhaustion; rejected. *W-C* (recommended) as above.

**12.3.4 Required tests (negative-first).** Pure helper `paid_effort(effective, charged, effective_cost)` plus whole-exchange cases:

1. Attacker stamina `{0, 1, 2}` (unfunded, Rule 1 waives), responder stamina `>= 12`, requested HIGH, tier Partial, defense succeeds: charge `0`, waived `12` recorded, **tier −1 (not preserved)**.
2. Same with attacker stamina `{3, 7, 12}` (funded): charge 12, tier preserved.
3. Responder stamina `{7..11}` and requested HIGH: funded MEDIUM, funding gap 5, wear as MEDIUM, no preservation.
4. Responder stamina `{3..6}` requested HIGH or MEDIUM: funded LOW, defense counted tier None, no wear; stamina `{0..2}`: unfunded, same.
5. Requested empty → MEDIUM; requested invalid → `invalid_response_commitment` with no mutation.
6. A waived exchange grades identically to a paid exchange of the same funded commitment (the waiver never changes a grade); undercommitment uses funded effective commitments.
7. Pure helper edge: `charged < effective_cost` (a synthetic shortfall) or `effective_cost == 0` → not paid.
8. Grid: attacker stamina × responder stamina × requested commitment × tier 0..2 × outcome class (failure / contested / success) with expected tiers from the oracle's own funding model.
9. Rule 1 stays ON and Rule 2 stays OFF: any other policy → `unsupported_cost_policy`; a source scan finds no Mount file in the B1b diff.

**Owner decisions.** HG-26C-1 (governed set: provisionally approved), HG-26C-2 (shift −1/0/+2), HG-26C-3 (effort/wear table), HG-26C-4 (effort uses the funded effective commitment), **HG-26C-5 (preservation requires paid effort)**.

### 12.4 HG-26D — Counterplay

A defender facing a possible feint has four documented routes, each computed from the published tables (Appendix D §§1, 2, 9):

1. **Anticipate:** the public view shows the apparent technique, the attacker's requested commitment and — if GP-2 is accepted — the eligible reals (FP-1: Crossface may conceal Knee Slice).
2. **Avoid committing completely:** answer at a lower response commitment. The existing undercommitment modifier (+1 for the attacker when the responder is funded strictly below) is the price; a LOW attacker can be answered LOW for free.
3. **Balanced response:** worst-case final grade for the attacker across the direct apparent technique and every eligible feint, neutral readiness:

| Apparent | Hip Frame / Head Control | Underhook Fight / Hip Pressure | Knee Shield / Knee Pin | Balanced response |
| --- | --- | --- | --- | --- |
| Crossface (feint FP-1) | +1 | +2 | **0** | Knee Shield |
| Underhook (feint FP-2) | +2 | **0** | +1 | Hip Pressure |
| Flatten (candidate FP-3) | +1 | +1 | +1 | **none** → FP-3 rejected |
| Knee Slice / Recover Guard (no feint exists) | 0 / +2 | +2 / +1 | −2 / −2 | the decisive counter (never worse) |

4. **Call:** choose the best counter to the real technique; it wins against the feint and may lose to a direct attack.

**Admissibility rule (proposed, gate for any future pair):** at the neutral state some response holds the attacker to `<= 0` across all modes. Outside the neutral state the rule can fail by design: Crossface fails when `bottom_frame = None` and
`top_base >= Partial`; Underhook when `bottom_frame = Ready` and `top_base <= Partial` (Appendix D §10; unchanged under the HG-9 candidate of §12.12). That is the payoff of preparation (a stripped defender may have no balanced answer);
the owner decides whether it is intended. No pure strategy dominates at the neutral state (Appendix D §2): no attacker mode dominates, and the only response that is never worse for the defender is the decisive counter against the
*direct* technique it counters, which is why attackers prepare or feint instead.
**Owner decisions.** HG-26D-1 (the four routes), HG-26D-2 (admissibility rule and its neutral-state scope), HG-26D-3 (outside-neutral failures accepted).

### 12.5 HG-26E — Stamina and funding (revised: separately funded feint surcharge; later feint slice only)

**Owner concept:** a feint costs more stamina than an ordinary technique. The earlier parity proposal (a feint costs exactly the direct cost) is kept below only as model **P0**; the owner-directed model is **P1**.
This section applies to the later feint implementation (B1h), **never to B1b**.

| Model | Cost of a feint at effective commitment `c` | Notes |
| --- | --- | --- |
| P0 (parity, superseded) | `cost(c)` | a feint would be free of premium, so repeated cheap feints cost the attacker no more than direct attacks |
| **P1 (candidate)** | `cost(c) + s` with illustrative **`s = +3`** (the LOW cost) | **The premium is `s`, at every tier.** Choosing HIGH is not itself a premium: a direct HIGH costs 12, a HIGH feint 15 (LOW 3 → 6, MEDIUM 7 → 10) |

**Funding procedure (pure, before any mutation):** (1) `available = initiator pool current`; (2) if `available < s` refuse; (3) `funding = determine(requested, available − s)` (the existing cost policy, so the commitment may downgrade
exactly as a direct technique's does); (4) if `funding.effective` is unfunded refuse; (5) `total = s + funding.effective_cost`; the exchange then grades with `funding.effective` as the initiator's effective commitment (magnitude,
undercommitment, the LOW-feint exit cap); (6) spending is one `spend_up_to(total)` on the initiator and, because funding was checked first, it charges the full `total` (a shortfall is an internal error, not a partial charge);
(7) the responder is charged exactly as for a direct technique (never a surcharge); (8) **all-or-nothing**: the surcharge is never partially paid, never waived and never drawn down by Rule 1 (an unfunded initiator cannot feint, so the
Rule 1 waiver predicate cannot hold); (9) a refusal is `feint_requires_funding`, leaves pools, tiers, history, events, clock and the sealed store untouched, and never converts the command into a direct technique.

| Item | Direct technique | Feint (P1, `s = 3`) |
| --- | --- | --- |
| Initiator cost at LOW / MEDIUM / HIGH | 3 / 7 / 12 | 6 / 10 / 15 |
| Minimum stamina to attempt | 0 (unfunded allowed; Rule 1 waives the responder's charge) | **6** (below that the feint is refused) |
| Downgrade | existing `determine` | the same function on `available − s` |
| Exhausted initiator / responder | −1 / +1 for the attacker | unchanged |
| Feint called | — | no extra charge; the real technique shifts −1 and may swing the axis (−10 per final −1, −20 per −2) |
| Optional cap (HG-26E-4) | — | a LOW-effective feint cannot cause a position exit (analogue of Guide §27's first-stage cap) |

Boundary table for `s = 3` (initiator stamina → effective commitment for requested HIGH / MEDIUM / LOW, total charge): `0–5` refused; `6–9` LOW (charge 6) for any request; `10–14` MEDIUM for HIGH or MEDIUM requests (charge 10), LOW for LOW
(6); `15+` HIGH (15) for a HIGH request, MEDIUM (10), LOW (6). Latch arithmetic (fresh 100, latch at `<= 25`; defender answering MEDIUM):

| Attack type | Cost | Attacks until the attacker is latched | Attacker then at | Defender at |
| --- | --- | --- | --- | --- |
| Direct MEDIUM | 7 | 11 | 23 | 23 |
| Direct HIGH | 12 | 7 | 16 | 51 |
| Feint LOW (+3) | 6 | 13 | 22 | 9 if the defender also answers MEDIUM, 61 if LOW |
| Feint MEDIUM (+3) | 10 | 8 | 20 | 44 |
| Feint HIGH (+3) | 15 | 5 | 25 | 65 |

Under P1 the attacker is always the faster drainer (a feint MEDIUM latches the attacker in 8 attacks while the defender is still at 44), so repeated feints cannot become the "nearly free stamina drain" that Guide §27 forbids.
Alternatives: `s = +7` (the MEDIUM cost; feint MEDIUM 14, latched in 6) and a surcharge proportional to the commitment (more state, rejected). **The value of `s` is the numeric decision to accept before B1h (not before the B1b oracle).**
**Required tests (B1h):** the boundary grid `{0, 2, 3, 5, 6, 8, 9, 10, 12, 14, 15, 16}` × requested `{LOW, MEDIUM, HIGH}` against the table above, whole-snapshot equality on every refusal, latch edges crossed by the combined spend,
exhaustion −1 on a funded feint, an unfunded attacker allowed a direct technique at stamina 3–5 but refused a feint, no responder surcharge, and replay determinism.
**Owner decisions.** HG-26E-1 (a surcharge exists), HG-26E-2 (value of `s`), HG-26E-3 (all-or-nothing funding with downgrade, refusal below `s + 3`), HG-26E-4 (LOW feint cannot exit).

### 12.6 HG-26F — Implementation boundary

**Provisionally approved by the owner:** B1b contains positional preparation and defensive effort; feints remain later B1g/B1h work.

| Belongs to B1b | Separate later slices |
| --- | --- |
| `top_base` / `bottom_frame` as two integers inside `BjjHalfGuardMatch`; constants and shift tables in `BjjHalfGuardRules`; readers, writers, consumption and wear in the existing resolution path | **B1g — sealed-intent protocol:** `seal_intent` / `respond`, the closed-schema public view, the probing-controller and indistinguishability tests, in the **Half Guard gateway only** (Mount gateway untouched); direct techniques may use it with `real = apparent` |
| New history/state keys (`readiness_change_history`, `top_base`, `bottom_frame`) | **B1h — Half Guard feint rules:** eligibility pairs, bite adjustment, the surcharge funding of §12.5, admission codes, oracle extension, counterplay-admissibility gate |
| Oracle replay including the 9 readiness states, the saturation order, the exit processing of §12.1.6 and the `paid_effort` rule of §12.3 | Generalization into a shared mechanism: only by the rule of three or on owner authorization to migrate Mount (GP-8) |
| The effort/wear rule (uses the existing response commitment and the recorded charge) | The measured economy and recovery rule (B1e) and further techniques (B1f) keep their names and scope |

**No shared runtime interface is introduced.** There is no `Preparation` class, registry entry, schema or base type: conditions are two ints and constants local to Half Guard, so a second position can adopt the *vocabulary* without importing code.
B1b reserves no feint hooks: admission codes and Report/history keys for feints are additive in B1g/B1h (the §4.7 conformance test requires only the shared key superset, so extra keys do not break it).

### 12.7 Adversarial test design (Task 4)

Each scenario is deterministic (no random seed, no wall clock) and states what it may claim. **S** = structural/exact (CI-gateable); **B** = balance measurement (population of policies; reports only, never a pass/fail gate unless the
owner preregisters a threshold). "Prototype" = already computed by Appendices C/D in this PR (structural, stamina ignored, **not** evidence of balance).

| # | Scenario | Setup and scripted policies | Assertion | Class | Prototype result |
| --- | --- | --- | --- | --- | --- |
| S-1 | Repeated best-counter defense | Responder always plays the best counter to the visible technique; attacker searched exactly (24 windows, pass allowed) | Option M, direct: **no forced exit** (documented stalemate); option S: exit at window 9 (Top) / 12 (Bottom); with feints: window 3 / 4 | S | yes (D §7) |
| S-2 | Attacker prepares before a pass | Bottom always Knee Shield; Top: Flatten, Crossface, Knee Slice (Bottom passes between) | Exact tier/axis trace: after Flatten axis 15, base Ready, frame None; after Crossface axis 35; Knee Slice exits (axis 40) at window 5 | S | yes (trace) |
| S-3 | Defender rebuilds preparation | Frame None; Bottom Underhook against each Top response | Frame +1 only if `final >= SUCCESS` (vs Knee Pin); never against Head Control; a pass or a response never builds | S | rules only (D §3 grid) |
| S-4 | Repeated Knee Shield | Bottom always Knee Shield | Preparation beats it (exit window 5); stamina arithmetic: MEDIUM defender wears a tier per decisive result; HIGH preserves only on success; LOW counted as None | S + arithmetic | yes (D §7) |
| S-5 | Repeated Knee Pin | Top always Knee Pin vs Bottom attacks | Bottom exits at window 6; the same wear table applies to `top_base` | S | yes (D §7) |
| S-6 | Successful and failed feints | Neutral state, FP-1 and FP-2 against each response | Exact finals of the §12.2 table; failed feint axis −10/−20; successful +20 | S | yes (D §5) |
| S-7 | Correctly anticipated feints | Defender plays the balanced / call response | Finals −1/−2/0; no attacker mode dominates at neutral; a feint is never weakly better than the better of the two direct techniques against a balanced response | S | yes (D §§2, 9) |
| S-8 | Repeated expensive feints until exhaustion (B1h) | Feints at HIGH (15 under the +3 candidate) vs MEDIUM responses until the latch | Attacker latched after 5 attacks while the defender is at 65 (parity model P0: 7 attacks, defender 51); called feints lose axis each time; unfunded or under-funded feint refused afterwards | S arithmetic, B for policy populations | arithmetic only (§12.5) |
| S-9 | Feint versus balanced defense | FP-1 vs Knee Shield, FP-2 vs Hip Pressure at all 9 readiness states | Worst case ≤ 0 at neutral; list of failing states equals the published list | S | yes (§12.9) |
| S-10 | Low-stamina and unfunded feints (B1h) | Initiator stamina `{0, 2, 3, 5, 6, 8, 9, 10, 12, 14, 15, 16}` × requested `{LOW, MEDIUM, HIGH}` | Boundary table of §12.5 (refused below 6 under `s = 3`; effective commitment and total charge as tabulated); refusal changes nothing; a direct technique at stamina 3–5 is still allowed; exhaustion −1 still applies | S | rules only |
| S-11 | Both fighters pass or defend without progress | Pass/pass; counter/counter loops | Pass/pass changes only the clock; counter loops leave axis and tiers oscillating; symmetric stamina drain; timeout | S (+B for how long) | symmetric optimal play: no forced exit in 16 windows (D/C) |
| S-12 | Protocol information tests | Public view indistinguishability, probing controller, mutation-sensitivity control | See TACTICAL_PREPARATION_AND_FEINTS.md §8.1 | S | not yet (B1g) |
| S-13 | Mirror symmetry | Run each Top scenario with the Bottom analogue | **Not asserted equal.** The tables are not mirrored: §12.9 F-3 records the asymmetry | S/B | yes |
| S-14 | Population measurement | Pre-registered policies (always-counter, mixed, greedy, prepared) over seeds of scripted choice | Exit distribution, durations, exhaustion timing, loop lengths; used for B1e, never a gate here | B | no |
| S-15 | Rule 1 waiver and defensive effort (B1b) | Attacker unfunded / funded × responder stamina grid × requested commitment × tiers | The nine cases of §12.3.4: a waived HIGH is not preserved; grading identical to a paid exchange | S | rules only |
| S-16 | Exit consumption (B1b) | Every break technique × tier × outcome incl. exits | Uniform §12.1.6 processing; terminal tiers recorded; refusal after the exit | S | rules only |

**What the structural checks do not prove:** balance, fun, human behavior, or the stamina economy. They prove reachability, dominance, exact arithmetic and the absence of a hidden extra window or charge.

### 12.8 Feasibility and compatibility (Task 5)

| Option | What it is | Cost / measurable effect (estimates unless pinned) | Regression risk | Verdict |
| --- | --- | --- | --- | --- |
| **1. Minimal local state (recommended)** | Two ints, constants and ~5 rule steps inside the Half Guard classes of B1b | ~+45 production lines, +2 state keys, +1 history, oracle +~40 lines and a ×9 readiness grid; existing Mount/F0/F1/graph files touched: **0**; entry request unchanged | None to Mount parity (256,992 / 14,631 / 8,851,698 evidence untouched) | **Smallest implementation that proves prepared techniques and decisive-counter effort** |
| 2. Generic preparation framework now | A shared `Preparation` type, registry and schema before a second user | ~250–350 lines, a carry-over schema decision, serialization and tests (estimate) | Speculative shape; likely re-cut when the second position arrives; touches the envelope | Rejected (violates "no framework for one feature") |
| 3. Modify Mount to adopt the new rules | Readiness and feints inside Mount | Changes Mount grades and state; the frozen Python reference and digest would no longer agree | Breaks the Mount parity evidence unless a new Python mode and fixtures are built first | Rejected without a separate owner-authorized parity plan |
| 4. Keep Mount frozen; migrate later | Mount unchanged; revisit after Half Guard and a third position | 0 now; trigger = rule of three or owner order | None now; migration needs its own parity slice | **Accepted as the policy**, combined with option 1 |

Preserved: all Mount parity evidence, the A3b/A3d/A3e/F0/F1 qualified interfaces, the existing window gateway, the graph's default behavior. The feint protocol needs a Half Guard-only gateway extension (B1g), never a Mount gateway edit.

### 12.9 B1b gate and staged sequence (Task 6)

**Owner decisions required before the independent oracle is written:** the exact list is §12.13.1 (N-1 and N-2 are provisionally approved; N-3…N-11 need acceptance). Feints are out of B1b either way.

**Staged sequence (existing milestones kept; names do not conflict with B1e/B1f):**

1. **B1b** — qualify the Half Guard mechanics with HG-26A/C and the independent oracle (direct techniques only).
2. **B1c → B1d** — Mount edge receiver, then opt-in graph integration (unchanged scope; readiness enters at `Partial/Partial`).
3. **B1g** — separately qualified sealed-intent commit-and-reveal protocol (Half Guard gateway only), then **B1h** — Half Guard feint rules and oracle extension.
4. **B1e** — measure the stamina economy, defensive loops and the recovery rule (pre-registered); may include a read-only first measurement after B1b and a re-measurement after B1h.
5. **Generalize** only after a second position requires the same mechanism (rule of three or explicit owner order, GP-8).

B1g and B1h do not depend on B1c/B1d (only on the Half Guard engine), so the owner may reorder them.

**Counterplay admissibility grid** (Appendix D §10, band 0, axis +5): FP-1 fails when `bottom_frame = None` and `top_base >= Partial`; FP-2 fails when `bottom_frame = Ready` and `top_base <= Partial`; FP-3 fails whenever `top_base >= Partial` and `bottom_frame <= Partial` — and at neutral.

### 12.10 Prototype findings and their limits (Appendices C, D and E)

The prototypes encode the proposed raw tables, the positional modifier, readiness, wear, feints and bite in integer tenths. They **ignore stamina, exhaustion, commitment settlement and the real clock**; "windows" count each fighter's window
including the opponent's pass windows. They are structural checks, **not** balance evidence and **not** an oracle.

* **F-1 — symmetric optimal play stalemates in every variant.** With the pass option, both fighters choosing optimally, no variant (direct, preparation M or S, with or without feints) forces an exit in 4, 8, 12 or 16 windows (value 0). The
  design does not guarantee attacking success.
* **F-2 — a direct attack is a losing choice against a perfect counter; preparation and feints change that.** At the neutral state the best guaranteed value of an attack is −1 (Top) and −1 (Bottom) against 0 for a pass, so a rational
  direct attacker passes. With feints −0.20 (Top) and 0.00 (Bottom). With preparation under M: `(top_base, bottom_frame) = (1, 0)` direct 0.00 / feint +0.20; `(2, 0)` direct +1.00 / feint +1.00 — attacking becomes positive only after the
  defender's frame is stripped. Full grid in Appendix D §6.
* **F-3 — the raw tables are not mirror-symmetric.** A Bottom that always answers with Hip Frame cannot be forced out by direct Top play under M (Top exits at window 5 with feints, window 3 under S); a Top that always answers with Hip Pressure
  concedes a Bottom exit at window 8 (window 6 under S). Owner attention is requested on HG-9, not an edit; §12.12 reviews the cells and recommends one single-cell candidate (C1) that is **not** applied.
* **F-4 — an unprepared decisive counter must be weak enough to be beaten by preparation.** With a None-tier shift of +1 a constant Knee Shield defender is a fortress; with +2 the prepared attacker exits at window 5 (Top) and a prepared Bottom
  against a constant Knee Pin at window 6.
* **F-5 — option M leaves the ordinary-counter loop alone; option S and feints break it.** Always playing the best counter to the visible technique: M no exit; S exits at 9 / 12; M with feints 3 / 4.
* **F-6 — decisive counters under the full pipeline:** the §12.1.4 table.
* **F-7 — pure dominance:** none for either side at the neutral state, except the decisive counter against the direct technique it counters.

### 12.11 Outstanding owner decisions for HG-26

The exact numerical decisions that still need acceptance before the B1b oracle is written are listed in §12.13.1; the decisions that can wait for B1h (feint slice) are listed in §12.13.2. The game-wide GP-1…GP-10 of
TACTICAL_PREPARATION_AND_FEINTS.md also remain open. Risks: the new numbers are design content; the readiness coupling (one track powers both an attack and a defense) is the key tuning surface; option M leaves a stalemate
against a perfect ordinary-counter defender that only feints (B1h), a measured recovery rule (B1e) or option S would break; the protocol slice (B1g) adds a second gateway path that must be kept in conformance with the first.

### 12.12 HG-9 review — plausibility of the 15 raw grades and the counter loops (no grade is rewritten here)

**Method.** Appendix E (`hg9_review.py`, built on Appendices C and D) evaluates the proposed grades (`C0`) and eight one-, two- or three-cell candidates (C1–C8) under the provisionally approved model (option M, None-tier shift +2, uniform exit
processing, passes allowed, **stamina, exhaustion, commitment and the clock ignored**). Criteria used to judge a candidate: **K1** it restores or preserves the mirror between the two break techniques; **K2** it introduces no pure dominance;
**K3** cooperative reachability and the earliest exits of all three labels are unchanged; **K4** symmetric optimal play still has no forced exit; **K5** it does not make exits materially easier without a structural reason. These are structural
checks, not balance evidence.

**Cell by cell.**

| Cell (initiator vs response) | Grade | Assessment |
| --- | --- | --- |
| Crossface vs Hip Frame / Underhook Fight / Knee Shield | +1 / −1 / 0 | Plausible: framing a hip concedes shoulder pressure; an underhook fight counters it |
| Flatten vs Hip Frame / Underhook Fight / Knee Shield | −1 / +1 / +1 | Plausible: a hip frame stops a flatten; the other two do not |
| **Knee Slice vs Hip Frame** | **0** | **Flag.** The only ordinary (ungoverned, wear-free) cell that holds a break technique |
| Knee Slice vs Underhook Fight | +2 | Plausible: fighting for the underhook exposes the knee line; it is the bite payoff of FP-1 |
| Knee Slice vs Knee Shield | −2 | The decisive counter (governed by `bottom_frame`) |
| Underhook vs Head Control / Hip Pressure / Knee Pin | −1 / 0 / +1 | Mirror of Crossface |
| Recover Guard vs Head Control | +2 | Plausible: head control commits the weight upward; the bite payoff of FP-2 |
| **Recover Guard vs Hip Pressure** | **+1** | Mirror partner of Knee Slice vs Hip Frame |
| Recover Guard vs Knee Pin | −2 | The decisive counter (governed by `top_base`) |

The two break rows are mirrors (Crossface ↔ Underhook; Knee Slice ↔ Recover Guard; Knee Shield ↔ Knee Pin; Underhook Fight ↔ Head Control) **except in one cell**: Knee Slice vs Hip Frame is `0` while Recover Guard vs Hip Pressure is `+1`.
Flatten has no Bottom analogue (Top has three actions, Bottom two).

**Results (Appendix E).** Selected rows; "T/B" = exit window for a Top / Bottom attacker against a constant responder, `-` = no forced exit in 24 windows, windows include the opponent's pass windows.

| Candidate | Change | Constant Hip Frame / Hip Pressure, direct | Responses holding Knee Slice `<= 0` | Uniform random play (Top exit / Bottom exit / timeout of 2000) | Unchanged |
| --- | --- | --- | --- | --- | --- |
| C0 | as proposed | **-** / 8 (Bottom's Hip Frame is a fortress; Top's Hip Pressure is not) | 2 | 1088 / 891 / 21 | — |
| **C1** | Knee Slice vs Hip Frame `0 → +1` | **5** / 8 | **1** | 1223 / 766 / 11 | cooperative states 376 and earliest exits 3/4/4; symmetric value 0; best-counter loop `-`/`-`; constant Knee Shield / Knee Pin 5/6; constant Underhook Fight 3/4; dominance; FP admissibility failures |
| C2 | Recover Guard vs Hip Pressure `+1 → 0` | `-` / `-` (a second fortress) | 2 | 1257 / 716 / 27 | — |
| C3 | C1 + C2 | 5 / `-` (the asymmetry reverses) | 1 | 1407 / 578 / 15 | — |
| C4 | Knee Slice vs Underhook Fight `+2 → +1` | `-` / 8 | 2 | 853 / 1091 / 56 | breaks the mirror (Knee Slice +1 vs Recover Guard +2) |
| C5 | Recover Guard vs Head Control `+2 → +1` | `-` / 8 | 2 | 1323 / 645 / 32 | constant Head Control exit 4 → 8; weakens the FP-2 bite payoff |
| C6 / C7 / C8 | pairs of the above | see Appendix E | — | 1106/802/92, 1042/926/32, 1286/666/48 | none reaches a different structural conclusion |

**Recommendation (not applied).** **C1 only: change Knee Slice vs Hip Frame from `0` to `+1`.**

* *Rationale.* (1) It makes the two break rows identical in shape (`+1 / +2 / −2` in both), completing the mirror (K1). (2) It removes the only direct-play fortress: today an ungoverned, wear-free Hip Frame holds a pass attempt at no cost, which makes the governed
  Knee Shield unnecessary against Knee Slice and undermines the defensive-effort rule of HG-26C. After C1 only Knee Shield holds Knee Slice (`1` response, like Recover Guard). (3) K2, K3, K4 and the admissibility failures are unchanged.
* *Cost, stated plainly.* It makes exits easier in exactly one policy pairing (constant Hip Frame: no exit → window 5), and uniform random play shifts toward Top (Top exits 1088 → 1223, Bottom exits 891 → 766). Uniform random play ignores stamina and choice quality and is
  not evidence of imbalance, but the lean toward Top is real in the model and the owner should accept it knowingly. The paired candidates that offset it (C4, C5) break the mirror or weaken the feint payoffs, so they are **not** recommended.
* *If the owner keeps C0.* The Hip Frame fortress stays a documented property; the effort rule then constrains only Knee Slice defenses that the defender chooses to make with Knee Shield, and the stalemate has to be addressed by B1h feints or the B1e measurement.
  The asymmetry against constant Hip Pressure (window 8) is then a stated feature, not a defect.
* *If C1 is accepted.* Update the §4.4 cell, then re-run Appendices A, B, C, D and E and restate the §10 and §12.10 numbers (with C1 the Appendix A random-play split becomes Side Control 1150, Closed Guard 536, Open Guard 307, timeout 7 of 2000; cooperative reachability is unchanged).

**Does option M give meaningful preparation decisions without feints?** Only partly. A viable direct attack (guaranteed value `>= 0`) exists only when `bottom_frame = None` (readiness states `(1,0)` and `(2,0)`; C1 adds `(0,0)`), and the only best action there is Knee Slice.
Reaching `bottom_frame = None` requires a successful Crossface (the defender must not play Underhook Fight) or the defender's own wear from repeated Knee Shield. Against a perfect-counter defender no such state is reached, so M yields attacker decisions
only against imperfect or over-committed defenders; for the defender it yields real decisions (effort tier, wear, when to rebuild). That is the honest scope of B1b: a mechanics baseline whose remaining stalemate is a recorded property.

### 12.13 B1b approval checklist (corrected)

Scope of B1b (provisionally approved direction): **direct techniques, positional preparation, defensive effort, valid receiver-entry state, deterministic windows and replay**, an independent test-only Python oracle first, then the typed GDScript engine.
Out of scope: UI or presentation changes, a generic tactical framework or shared interface, any Mount change, feints (automated or manual), the sealed-intent protocol, Standing, recovery or stamina-economy balancing.

**12.13.1 Exact numerical decisions the owner must accept before the oracle is written**

| # | Decision | Proposed value | Status |
| --- | --- | --- | --- |
| N-1 | Two tracks `top_base`, `bottom_frame`; tiers `None/Partial/Ready`; entry `Partial/Partial`; no decay | as stated | **provisionally approved** |
| N-2 | Option M: governed counters are Knee Shield (frame) and Knee Pin (base) | as stated | **provisionally approved** |
| N-3 | Attack readiness shift for Knee Slice (base) and Recover Guard (frame) | Ready +1, Partial 0, None −1 | accept / amend |
| N-4 | Defense readiness shift toward the initiator for the governed counters | Ready −1, Partial 0, None **+2** | accept / amend (+2 is the value that lets preparation beat a constant Knee Shield) |
| N-5 | Builder/weakener step and threshold | ±1 tier when `final >= SUCCESS`; Crossface −1 `bottom_frame`, Flatten +1 `top_base`, Underhook +1 `bottom_frame`, Recover Guard −1 `top_base`; floor 0, ceiling 2 | accept / amend |
| N-6 | Consumption | a break-capable attempt at tier Ready spends one tier, whatever the result | accept / amend |
| N-7 | Exit processing | **uniform**: consumption, wear and builders apply to every accepted exchange including exits; no extra action; receiver entry unaffected (§12.1.6) | accept / amend (recommended) |
| N-8 | Effort and wear | LOW or unfunded → tier None, no wear; MEDIUM → −1 when `final != 0`; HIGH → −1 only on failure | accept / amend |
| N-9 | `paid_effort` rule | HIGH preservation requires the charge actually paid; a Rule 1 waiver does not buy it (§12.3.2) | accept / amend (recommended) |
| N-10 | HG-9 | **C1** (Knee Slice vs Hip Frame `0 → +1`) applied, or C0 kept knowingly (§12.12) | **decide** |
| N-11 | Existing numbers still to be accepted | entry axis +5, break lines ±30, ±10 per final-grade step, band thresholds of Q1, positional modifier −1 at the opposing CONTROL band, 14 other raw grades, exit label map, strict alternation | accept as listed in §§3–4 |

**12.13.2 Decisions that can wait for B1h (not needed for the B1b oracle):** the surcharge value `s` (illustrative +3) and its all-or-nothing funding (§12.5), the bite ±1, the FP-1/FP-2 list, the LOW-feint exit cap, GP-1…GP-10.

**12.13.3 Independent Python test-only oracle checklist** (written from the approved rules sheet, not from the GDScript; `tests/oracles/half_guard_v0.py` plus its unit tests and generator)

1. Tables and constants literal: axis tenths, bands and hysteresis rules, the 15 raw grades (after N-10), exit map, readiness shifts, builders.
2. Entry validation exactly as §5.1 (fighter-id keyed, bijective role map, stamina/latch consistency, clock, interval) and the literal two-state latch model (no reuse of the `create` + `set_current` trick).
3. Funding: its own implementation of `determine` for 3/7/12 and the unfunded case; Rule 1 ON, Rule 2 OFF; the three requested/effective/charged quantities of §12.3.1.
4. Exhaustion modifiers and the commitment-settlement functions re-implemented, cross-checked against Mount's Python helpers **inside the unit test only** (never constructing a `MountMatch`).
5. The grade pipeline in the exact saturating order of §12.1.3 (positional → attack readiness → defense readiness → exhaustion → magnitude → undercommitment).
6. Resolution, exit and update order of §12.1.6 (spend, consume, wear, build; saturating each), uniform for exits; clamp and band update at an exit.
7. Admission: every code of §4.6 in order, whole-snapshot non-mutation matrix, multi-fault precedence matrix, terminal cases (`terminal_exchange` before any tier is read), unregistered-entry negative control, an extra `top_base`/`bottom_frame` key in an entry request refused.
8. Window lifecycle: open, zero-time and interval windows, pass, strict alternation, timeout without a window, window-id continuity from the entry's last issued id.
9. Histories and the `state_fields` subset (including both tiers) in a canonical, replayable record; the readiness-change history in the §12.1.6 order.
10. Scenario grids with counts **measured, never asserted from the document**: axis × band, exchange grid including the nine readiness states and the stamina boundary grid `{0..2, 3..6, 7..11, 12+}` for both fighters and `{LOW, MEDIUM, HIGH, empty}` response commitments, waiver cases of §12.3.4, exits of every break technique × tier × outcome, replay twice.
11. Independence and sensitivity: no GDScript read; a development-time mutation control flips one grade, one shift and one wear rule and confirms the Godot replay fails.
12. The generator fails on a missing or empty fixture; the Godot reference test asserts and prints the measured counts and ends with `PASS: N assertions`, validated by the existing fail-closed log validator with exact pins.

**12.13.4 Typed GDScript engine checklist** (new files only under `scripts/positions/half_guard/`, plus tests; written after the oracle is accepted)

1. `BjjHalfGuardRules` (constants, bands, shifts), `BjjHalfGuardCatalog`, `BjjHalfGuardResolver`, `BjjHalfGuardMatch` (state: axis tenths, band, initiator, two pools, two meters, clock, `top_base`, `bottom_frame`, histories), `BjjHalfGuardEntry`,
   `BjjHalfGuardContract`, `BjjHalfGuardWindowGateway` — typed values everywhere, `.gd.uid` for every new script.
2. Reuse only the position-independent policies unchanged (`BjjStaminaPool`, `BjjStaminaCostPolicy`, `BjjCommitment`, `BjjCommitmentSettlement`, `BjjExhaustionPolicy`, `BjjGrade`); read the recorded charge for `paid_effort`; no new stamina or commitment math.
3. Latch restoration with the public API and the exhaustive equivalence proof of §5.4; entry builds state **by fighter id** (swapped role map test).
4. Readiness: two ints, no class; the §12.1.6 order; no decay; entry `Partial/Partial`.
5. Window lifecycle and the Report/view schema of §4.7; the conformance test against the Mount gateway; `carryover_segment()` absent (HG-20).
6. Source scans: no Mount file edited; no reference to `BjjBehaviorStaminaPolicy` other than the `Meter` type; no D3-B controller; **no feint, seal, surcharge or sealed-intent identifier** in `scripts/positions/half_guard/`; no UI/presentation file touched; F0/F1 files unchanged.
7. Negative-first test order: refusals and precedence → catalog pins → rules/bands → pipeline and saturation → readiness → effort and waiver → exits → lifecycle → entry → oracle replay → determinism.
8. No automatic window, no hidden extra action, no wall-clock or random input anywhere (source scan).

**12.13.5 Test discipline and CI route.** During development run only focused suites: `godot --headless --path GODOT_V1 --script res://tests/<new_suite>.gd` for the suite being edited and `PYTHONPATH=src python -m unittest discover -s tests -p "test_half_guard_oracle.py"` for the oracle;
never the full Python CLI for routine iterations; preserve every frozen Mount baseline (256,992 / 431 / 750 / 1,036 pins, the Mount reference fixtures and digest) untouched. B1b changes Godot sources, Python tests and workflow steps, so the router classifies it as shared source:
**the full qualification route (Godot plus Python 3.11/3.13) must run on the exact head and must not be shortened.** A docs-only revision, by contrast, routes `DOCUMENTATION_ONLY` and skips the heavy jobs; that is never evidence for a B1b slice.

**12.13.6 Definition of done for the B1b approval.** The owner has accepted N-3…N-11; the oracle is reviewed and accepted first; the Godot engine matches it with zero mismatches; negative-first suites, the conformance test, the latch proof and the source scans pass;
every Mount and graph/F0/F1 pin is unchanged; exact-head CI green on Godot and both Python versions; no gameplay, UI or Mount change outside the listed new files.

## Appendix A — Reachability and consistency prototype (verbatim)

```python
"""Throwaway feasibility prototype of the PROPOSED Half Guard v0 numbers (not committed, not an oracle).
Integer tenths everywhere. Checks internal consistency and exit reachability."""
import itertools
from collections import deque

LO, HI = -40, 40
PASS_LINE, OUT_LINE = 30, -30
ENTRY = 5


def shift(g, s):
    return max(-2, min(2, g + s))


def initial_band(a):
    m = abs(a)
    sign = 1 if a > 0 else -1
    return 0 if m < 10 else sign * (1 if m < 25 else 2)


UP = {(0, 1): 12, (1, 2): 27, (-1, 0): -8, (-2, -1): -23}      # moving toward Top: a >= threshold
DOWN = {(2, 1): 23, (1, 0): 8, (0, -1): -12, (-1, -2): -27}     # moving toward Bottom: a <= threshold


def update_band(a, band):
    while True:
        nxt = None
        for (b0, b1), t in UP.items():
            if band == b0 and a >= t:
                nxt = b1
        for (b0, b1), t in DOWN.items():
            if band == b0 and a <= t:
                nxt = b1
        if nxt is None:
            return band
        band = nxt


def can_have(a, band):
    return {0: -12 < a < 12, 1: 8 < a < 27, 2: a > 23, -1: -27 < a < -8, -2: a < -23}[band]


# consistency: every axis has at least one legal band, and update_band lands on a legal band
for a in range(LO, HI + 1):
    assert any(can_have(a, b) for b in (-2, -1, 0, 1, 2)), a
    for b in (-2, -1, 0, 1, 2):
        if can_have(a, b):
            assert can_have(a, update_band(a, b)), (a, b)

TOP_RAW = {  # Top initiator, grade from Top's point of view; responses = Bottom's
    "crossface": {"hip_frame": 1, "underhook_fight": -1, "knee_shield": 0},
    "flatten": {"hip_frame": -1, "underhook_fight": 1, "knee_shield": 1},
    "knee_slice": {"hip_frame": 0, "underhook_fight": 2, "knee_shield": -2},
}
BOT_RAW = {  # Bottom initiator, grade from Bottom's point of view; responses = Top's
    "underhook": {"head_control": -1, "hip_pressure": 0, "knee_pin": 1},
    "recover_guard": {"head_control": 2, "hip_pressure": 1, "knee_pin": -2},
}


def pos_mod(initiator, band):
    if initiator == "top" and band == -2:
        return -1
    if initiator == "bottom" and band == 2:
        return -1
    return 0


def step(a, band, initiator, action, response):
    raw = (TOP_RAW if initiator == "top" else BOT_RAW)[action][response]
    g = shift(raw, pos_mod(initiator, band))
    delta = 10 * g if initiator == "top" else -10 * g
    proposed = a + delta
    exit_label = ""
    if initiator == "top" and action == "knee_slice" and g >= 1 and proposed >= PASS_LINE:
        exit_label = "Side Control"
    if initiator == "bottom" and action == "recover_guard" and g >= 1 and proposed <= OUT_LINE:
        exit_label = "Closed Guard" if g == 2 else "Open Guard"
    a2 = max(LO, min(HI, proposed))
    return a2, update_band(a2, band), g, exit_label


# BFS over (axis, band, initiator): cooperative play = both players choose freely (reachability).
start = (ENTRY, initial_band(ENTRY), "top")
dist = {start: 0}
queue = deque([start])
first_exit = {}
while queue:
    a, band, who = queue.popleft()
    nxt_who = "bottom" if who == "top" else "top"
    table = TOP_RAW if who == "top" else BOT_RAW
    for action in table:
        for response in table[action]:
            a2, b2, g, ex = step(a, band, who, action, response)
            if ex:
                first_exit.setdefault(ex, dist[(a, band, who)] + 1)
                continue
            state = (a2, b2, nxt_who)
            if state not in dist:
                dist[state] = dist[(a, band, who)] + 1
                queue.append(state)
print("entry", start, "band names -2..2 = BOTTOM_CONTROL..TOP_CONTROL")
print("states reachable under cooperative play:", len(dist))
print("earliest exit (windows, both players cooperating):", first_exit)

# Property mirrored from Mount: every action has a response giving the initiator <= -1.
for name, table in (("top", TOP_RAW), ("bottom", BOT_RAW)):
    for action, row in table.items():
        assert min(row.values()) <= -1, (name, action)
        assert max(row.values()) >= 1, (name, action)
print("every action has a counter (<= -1) and a favourable response (>= +1)")

# Perfect-counter responder: the initiator can never exit (same structural property as Mount).
def best_counter_exits():
    seen = {start}
    queue = deque([start])
    exits = set()
    while queue:
        a, band, who = queue.popleft()
        nxt_who = "bottom" if who == "top" else "top"
        table = TOP_RAW if who == "top" else BOT_RAW
        for action, row in table.items():
            response = min(row, key=lambda r: (row[r], r))
            a2, b2, g, ex = step(a, band, who, action, response)
            if ex:
                exits.add(ex)
                continue
            state = (a2, b2, nxt_who)
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return exits, len(seen)
print("exits reachable if the responder always plays the best counter:", best_counter_exits())

# Uniformly random responders: Monte-Carlo-free exact expectation is overkill; sample deterministic grid of seeds.
import random
def run(seed, windows=60):
    rnd = random.Random(seed)
    a, band, who = start
    for w in range(1, windows + 1):
        table = TOP_RAW if who == "top" else BOT_RAW
        action = rnd.choice(sorted(table))
        response = rnd.choice(sorted(table[action]))
        a, band, g, ex = step(a, band, who, action, response)
        if ex:
            return ex, w
        who = "bottom" if who == "top" else "top"
    return "timeout", windows
results = {}
for seed in range(2000):
    ex, w = run(seed)
    results.setdefault(ex, []).append(w)
for ex, ws in sorted(results.items()):
    print("random play: %-12s %4d of 2000, median window %s" % (ex, len(ws), sorted(ws)[len(ws) // 2]))

# Stamina economy of one exchange under the position-independent policy (costs 3/7/12, v04, Rule 1 ON).
COST = {"LOW": 3, "MEDIUM": 7, "HIGH": 12}
cap, enter, recover = 100, 25, 35
cur_i = cur_r = 100
trace = []
for w in range(1, 40):
    cur_i, cur_r = cur_r, cur_i  # alternate roles
    cost_i = min(cur_i, COST["MEDIUM"]) if cur_i >= 7 else (3 if cur_i >= 3 else 0)
    cur_i -= cost_i
    cost_r = 0 if cost_i == 0 else min(cur_r, COST["MEDIUM"])
    cur_r -= cost_r
    trace.append((w, cur_i, cur_r))
    if min(cur_i, cur_r) <= enter:
        print("with MEDIUM exchanges and no recovery, the first fighter reaches the Exhausted latch at window", w, trace[-1])
        break
```

## Appendix B — Full-pipeline counter check (verbatim)

```python
"""Throwaway check: can an initiator reach SUCCESS against a counter once exhaustion and commitment settlement apply?
Mirrors the shared position-independent functions (BjjCommitmentSettlement / BjjExhaustionPolicy) from the rules text."""
import itertools

def shift(g, s): return max(-2, min(2, g + s))
ORDER = ["LOW", "MEDIUM", "HIGH"]
def rank(e): return ORDER.index(e) + 1 if e in ORDER else 0
def magnitude(e, g):
    if e == "HIGH":
        if g == 1: return 1
        if g == -1: return -1
    if e in ("LOW", ""):
        if g == 2: return -1
        if g == -2: return 1
    return 0
def under(i, r): return 1 if rank(r) < rank(i) else 0

best = {}
for raw in (-2, -1):
    top = -9
    for pos, exh, ie, re_ in itertools.product((-1, 0), (-1, 0, 1), ("", "LOW", "MEDIUM", "HIGH"), ("", "LOW", "MEDIUM", "HIGH")):
        g_pos = shift(raw, pos)
        g_exh = shift(g_pos, exh)
        final = shift(shift(g_exh, magnitude(ie, g_exh)), under(ie, re_))
        top = max(top, final)
    best[raw] = top
print("best final grade reachable from a raw -2 counter:", best[-2])
print("best final grade reachable from a raw -1 counter:", best[-1])
```

## Appendix C — HG-26 structural model (verbatim; save as `hg26_proto.py`)

Encodes the proposed tables, readiness, wear, feints and bite; consumption, wear and builders apply to every accepted exchange including exits (§12.1.6); prints the full-game minimax value (horizons 4, 8, 12, 16) for six variants. Ignores stamina, exhaustion, commitment settlement and the clock; the Rule 1 and `paid_effort` rules of §12.3 are specified, not modeled.

```python
"""Throwaway structural prototype of PROPOSED HG-26 mechanics (not an oracle, not balance evidence).
Integer tenths. Models raw grades + positional modifier + preparation + feints ONLY.
It IGNORES stamina, exhaustion, commitment settlement and the real clock.
Terminal value from Top's view: +1 Top exits (Side Control), -1 Bottom exits (guard), 0 timeout at horizon."""
import sys
from fractions import Fraction
from functools import lru_cache
from itertools import combinations

sys.setrecursionlimit(10000)
LO, HI, ENTRY, PASS_LINE, OUT_LINE = -40, 40, 5, 30, -30

def shift(g, s): return max(-2, min(2, g + s))

UP = {(0, 1): 12, (1, 2): 27, (-1, 0): -8, (-2, -1): -23}
DOWN = {(2, 1): 23, (1, 0): 8, (0, -1): -12, (-1, -2): -27}
def initial_band(a):
    m = abs(a); sg = 1 if a > 0 else -1
    return 0 if m < 10 else sg * (1 if m < 25 else 2)
def update_band(a, band):
    while True:
        nxt = None
        for (b0, b1), t in UP.items():
            if band == b0 and a >= t: nxt = b1
        for (b0, b1), t in DOWN.items():
            if band == b0 and a <= t: nxt = b1
        if nxt is None: return band
        band = nxt

TOP_RAW = {"crossface": {"hip_frame": 1, "underhook_fight": -1, "knee_shield": 0},
           "flatten": {"hip_frame": -1, "underhook_fight": 1, "knee_shield": 1},
           "knee_slice": {"hip_frame": 0, "underhook_fight": 2, "knee_shield": -2}}
BOT_RAW = {"underhook": {"head_control": -1, "hip_pressure": 0, "knee_pin": 1},
           "recover_guard": {"head_control": 2, "hip_pressure": 1, "knee_pin": -2}}
RAW = {"top": TOP_RAW, "bottom": BOT_RAW}
BREAK = {"knee_slice": "top", "recover_guard": "bottom"}
# builders: action -> (track changed, delta); tracks: 'B' Top base, 'F' Bottom frame
BUILD = {"crossface": ("F", -1), "flatten": ("B", +1), "underhook": ("F", +1), "recover_guard": ("B", -1)}
OWN_TRACK = {"top": "B", "bottom": "F"}
POWER_M = {"knee_shield", "knee_pin"}                 # Option M: decisive counters only
POWER_S = {"hip_frame", "underhook_fight", "knee_shield", "head_control", "hip_pressure", "knee_pin"}
FEINTS = {"top": [("crossface", "knee_slice"), ("flatten", "knee_slice")], "bottom": [("underhook", "recover_guard")]}
def counters(side, action): return {r for r, g in RAW[side][action].items() if g <= -1}

def def_shift(cfg, tier):
    # governed-response shift toward the initiator: Ready -1, Partial 0, None cfg['none'] (default +2)
    return {2: -1, 1: 0, 0: cfg.get('none', 2)}[tier]

def pos_mod(side, band): return -1 if (side == "top" and band == -2) or (side == "bottom" and band == 2) else 0

def step(st, side, real, resp, cfg, bite=None):
    a, band, B, F, _ = st
    tr = {"B": B, "F": F}
    own = OWN_TRACK[side]; opp = "F" if side == "top" else "B"
    raw = RAW[side][real][resp]
    g = shift(raw, pos_mod(side, band))
    if cfg["prep"]:
        if real in BREAK:                                  # prepared technique reads own track
            g = shift(g, tr[own] - 1)
        if resp in cfg["power"]:                           # governed response reads responder track
            g = shift(g, def_shift(cfg, tr[opp]))
    if bite is not None:
        g = shift(g, +1 if bite else -1)
    delta = 10 * g if side == "top" else -10 * g
    proposed = a + delta
    ex = 0
    if side == "top" and real == "knee_slice" and g >= 1 and proposed >= PASS_LINE: ex = 1
    if side == "bottom" and real == "recover_guard" and g >= 1 and proposed <= OUT_LINE: ex = -1
    a2 = max(LO, min(HI, proposed)); b2 = update_band(a2, band)
    if cfg["prep"]:   # consumption, wear and builders apply to EVERY accepted exchange, exits included
        if real in BREAK and tr[own] == 2: tr[own] -= 1    # consumption on attempt at Ready
        if resp in cfg["power"] and g != 0 and tr[opp] > 0 and cfg["erode"]:
            tr[opp] -= 1                                   # worn structure (response commitment MEDIUM)
        if g >= 1 and real in BUILD:
            t, d = BUILD[real]
            tr[t] = max(0, min(2, tr[t] + d))
    return (a2, b2, tr["B"], tr["F"], "bottom" if side == "top" else "top"), ex

def solve_matrix(rows):
    """rows: list of lists (attacker rows x defender cols), payoff to the ROW player. returns value (float)."""
    n = len(rows[0])
    if len(rows) == 1:
        return min(rows[0])
    # row player maximises min over cols; solve by vertex enumeration of the row mixture.
    m = len(rows)
    best = None
    # variables x_1..x_m, v ; constraints: sum x =1, x>=0, sum_i x_i A[i][j] >= v for all j
    cons = []  # each tight constraint as (coeffs over [x..., v], rhs)
    for i in range(m):
        cons.append(([1.0 if k == i else 0.0 for k in range(m)] + [0.0], 0.0, "x%d" % i))
    for j in range(n):
        cons.append(([rows[i][j] for i in range(m)] + [-1.0], 0.0, "c%d" % j))
    simplex = ([1.0] * m + [0.0], 1.0)
    for pick in combinations(range(len(cons)), m):
        A = [simplex[0]] + [cons[k][0] for k in pick]
        b = [simplex[1]] + [cons[k][1] for k in pick]
        sol = _solve(A, b)
        if sol is None: continue
        x = sol[:m]; v = sol[m]
        if min(x) < -1e-9: continue
        if min(sum(x[i] * rows[i][j] for i in range(m)) for j in range(n)) < v - 1e-9: continue
        if best is None or v > best: best = v
    return best

def _solve(A, b):
    n = len(A)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12: return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1): M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]

def make(cfg, H):
    @lru_cache(maxsize=None)
    def V(st, depth):
        if depth == 0: return 0.0
        side = st[4]
        table = RAW[side]
        best = None
        for A in table:
            modes = [(A, None)]
            if cfg["feints"]:
                for (ap, re) in FEINTS[side]:
                    if ap == A and _eligible(st, side, ap, re): modes.append((ap, re))
            rows = []
            for (ap, re) in modes:
                row = []
                for resp in table[A]:
                    real = ap if re is None else re
                    bite = None if re is None else (resp in counters(side, ap))
                    ns, ex = step(st, side, real, resp, cfg, bite)
                    row.append(float(ex) if ex else V(ns, depth - 1))
                rows.append(row)
            sign = 1 if side == "top" else -1
            val = solve_matrix([[sign * x for x in r] for r in rows])   # initiator maximises own sign*value
            val *= sign
            score = sign * val
            if best is None or score > best[0]: best = (score, A, val)
        # a pass (no action) is always legal: nothing changes except who holds initiative
        pv = V((st[0], st[1], st[2], st[3], "bottom" if side == "top" else "top"), depth - 1)
        if sign * pv > best[0]: best = (sign * pv, "pass", pv)
        return best[2]
    return V

def _eligible(st, side, ap, re):
    a, band, B, F, _ = st
    if side == "top": return B >= 1
    return F >= 1

START = (ENTRY, initial_band(ENTRY), 1, 1, "top")

if __name__ == "__main__":
    variants = {
        "V0 direct, no preparation (Appendix A rules)": dict(prep=False, power=set(), erode=False, feints=False),
        "V1 direct + preparation, decisive counters governed (Option M)": dict(prep=True, power=POWER_M, erode=True, feints=False),
        "V2 direct + preparation, every response governed (Option S)": dict(prep=True, power=POWER_S, erode=True, feints=False),
        "V3 = V1 + feints": dict(prep=True, power=POWER_M, erode=True, feints=True),
        "V4 = V2 + feints": dict(prep=True, power=POWER_S, erode=True, feints=True),
        "V5 feints only (no preparation)": dict(prep=False, power=set(), erode=False, feints=True),
    }
    print("Value from Top's view at entry (axis +5, base/frame Partial, Top initiates). +1 = Top forces a pass, -1 = Bottom forces a guard exit,\n0 = neither can force an exit within the horizon. Fractional = exit probability balance under optimal mixing.\n")
    for H in (4, 8, 12, 16):
        print("horizon", H, "windows")
        for name, cfg in variants.items():
            v = make(cfg, H)(START, H)
            print("  %-64s optimal-play value %+0.3f" % (name, v + 0.0))
```

## Appendix D — HG-26 one-window and constant-defender analysis (verbatim; save as `hg26_window.py` next to Appendix C and run `python3 -B hg26_window.py`)

Imports Appendix C. Sections: 1 entry-state one-window values; 2 dominance; 3 readiness grid; 4 scripted loop traces; 5 feint finals; 6 value by readiness; 7 exact best attacker against constant defenders; 8 full pipeline against decisive counters; 9 balanced-response worst cases; 10 admissibility over all readiness states.

```python
"""One-window tactical analysis of the PROPOSED HG-26 mechanics (throwaway, structural, not balance evidence).
Imports hg26_proto's pure model. Payoff = final grade (-2..+2) from the INITIATOR's point of view before any
stamina/exhaustion/commitment modifier. Pass = 0."""
import sys; sys.path.insert(0, '.')
from hg26_proto import *
from hg26_proto import _eligible

CFGS = {
 "V0 direct, no preparation": dict(prep=False, power=set(), erode=False, feints=False),
 "V1 prep, decisive counters governed (M)": dict(prep=True, power=POWER_M, erode=True, feints=False),
 "V2 prep, every response governed (S)": dict(prep=True, power=POWER_S, erode=True, feints=False),
}

def g_of(st, side, real, resp, cfg, bite=None):
    # recompute grade exactly as step() does (so the table is not distorted by clamps/exits)
    a, band, B, F, _ = st
    tr = {"B": B, "F": F}; own = OWN_TRACK[side]; opp = "F" if side == "top" else "B"
    g = shift(RAW[side][real][resp], pos_mod(side, band))
    if cfg["prep"]:
        if real in BREAK: g = shift(g, tr[own] - 1)
        if resp in cfg["power"]: g = shift(g, def_shift(cfg, tr[opp]))
    if bite is not None: g = shift(g, 1 if bite else -1)
    return g

def apparent_matrix(st, side, A, cfg, feints):
    modes = [(A, None)] + ([(ap, re) for (ap, re) in FEINTS[side] if ap == A and feints and _eligible(st, side, ap, re)])
    rows, labels = [], []
    for ap, re in modes:
        real = ap if re is None else re
        rows.append([g_of(st, side, real, r, cfg, None if re is None else (r in counters(side, ap))) for r in RAW[side][A]])
        labels.append("direct %s" % ap if re is None else "feint %s->%s" % (ap, re))
    return labels, rows

print("== 1. Entry state (Top/Bottom readiness Partial): one-window game per apparent technique ==")
st = START
for name, cfg in CFGS.items():
    for feints in (False, True):
        if feints and not cfg["prep"] and False: continue
        print("\n%s%s" % (name, " + feints" if feints else ""))
        best_top = max(solve_matrix(apparent_matrix(st, "top", A, cfg, feints)[1]) for A in TOP_RAW)
        best_bot = max(solve_matrix(apparent_matrix((st[0], st[1], 1, 1, "bottom"), "bottom", A, cfg, feints)[1]) for A in BOT_RAW)
        for A in TOP_RAW:
            labels, rows = apparent_matrix(st, "top", A, cfg, feints)
            print("  Top   apparent %-11s modes=%s  value %+0.2f" % (A, "; ".join(labels), solve_matrix(rows)))
        for A in BOT_RAW:
            labels, rows = apparent_matrix((st[0], st[1], 1, 1, "bottom"), "bottom", A, cfg, feints)
            print("  Bottom apparent %-13s modes=%s  value %+0.2f" % (A, "; ".join(labels), solve_matrix(rows)))
        print("  best attack value for Top %+0.2f, for Bottom %+0.2f (a pass is 0)" % (best_top, best_bot))

print("\n== 2. Pure-strategy dominance at the entry state (apparent technique visible; feints on; Option M) ==")
cfg = CFGS["V1 prep, decisive counters governed (M)"]
for side, tbl in (("top", TOP_RAW), ("bottom", BOT_RAW)):
    for A in tbl:
        labels, rows = apparent_matrix(START if side == "top" else (START[0], START[1], 1, 1, "bottom"), side, A, cfg, True)
        cols = list(tbl[A])
        dom_col = [cols[j] for j in range(3) if all(all(rows[i][j] >= rows[i][k] for i in range(len(rows))) for k in range(3) if k != j)]
        dom_row = [labels[i] for i in range(len(rows)) if len(rows) > 1 and all(all(rows[i][j] >= rows[k][j] for j in range(3)) for k in range(len(rows)) if k != i)]
        never_worse = [cols[j] for j in range(3) if all(all(rows[i][j] <= rows[i][k] for i in range(len(rows))) for k in range(3) if k != j)]
        print("  %-6s %-14s dominant attacker mode: %-6s | response never worse for the defender than the other two (weak dominance): %s" % (side, A, dom_row or "none", never_worse or "none"))

print("\n== 3. Readiness grid, Top initiator, Knee Slice vs each response (direct): final grade ==")
for name, cfg in list(CFGS.items())[1:]:
    print(name)
    print("    base\\frame   " + "   ".join("F=%d" % f for f in range(3)) + "   (cells: vs hip_frame/underhook_fight/knee_shield)")
    for B in range(3):
        row = []
        for F in range(3):
            s = (5, 0, B, F, "top")
            row.append("/".join("%+d" % g_of(s, "top", "knee_slice", r, cfg) for r in ("hip_frame", "underhook_fight", "knee_shield")))
        print("    B=%d         " % B + "  ".join(row))

print("\n== 4. Repeated best-counter defender vs a scripted attacker, direct only, 12 own windows each (stamina ignored) ==")
for name, cfg in list(CFGS.items())[1:]:
    st = START; trace = []
    plan = ["crossface", "flatten", "knee_slice"]
    sidetop = 0
    for w in range(1, 13):
        side = st[4]; tbl = RAW[side]
        A = plan[sidetop % 3] if side == "top" else "underhook"
        if side == "top": sidetop += 1
        c = sorted(counters(side, A), key=lambda r: (tbl[A][r], r))[0]
        g = g_of(st, side, A, c, cfg)
        st, ex = step(st, side, A, c, cfg)
        trace.append("%s:%s/%s g=%+d -> a=%d B=%d F=%d%s" % (side[0].upper(), A[:3], c[:3], g, st[0], st[2], st[3], " EXIT" if ex else ""))
    print(name); print("  " + "\n  ".join(trace))

print("\n== 5. Feint read by the defender: self-damage to the attacker, defender plays best counter to the REAL technique ==")
cfg = CFGS["V1 prep, decisive counters governed (M)"]
for ap, re in FEINTS["top"] + FEINTS["bottom"]:
    side = "top" if ap in TOP_RAW else "bottom"
    s = START if side == "top" else (START[0], START[1], 1, 1, "bottom")
    out = []
    for r in RAW[side][re]:
        out.append("%s=%+d" % (r, g_of(s, side, re, r, cfg, r in counters(side, ap))))
    direct = ", ".join("%s=%+d" % (r, g_of(s, side, ap, r, cfg)) for r in RAW[side][ap])
    realdirect = ", ".join("%s=%+d" % (r, g_of(s, side, re, r, cfg)) for r in RAW[side][re])
    print("  %s %s->%s feint finals: %s | direct %s: %s | direct %s: %s" % (side, ap, re, ", ".join(out), ap, direct, re, realdirect))

print("\n== 6. Feint game value of the best apparent technique by readiness (Top initiator, axis +5, band 0) ==")
for name, cfg in list(CFGS.items())[1:]:
    print(name, "(cells: direct-only best / with feints best; a pass is 0)")
    print("    base\\frame   " + "      ".join("F=%d" % f for f in range(3)))
    for B in range(3):
        cells = []
        for F in range(3):
            s = (5, 0, B, F, "top")
            d = max(solve_matrix(apparent_matrix(s, "top", A, cfg, False)[1]) for A in TOP_RAW)
            f = max(solve_matrix(apparent_matrix(s, "top", A, cfg, True)[1]) for A in TOP_RAW)
            cells.append("%+0.2f/%+0.2f" % (d, f))
        print("    B=%d         " % B + "  ".join(cells))

print("\n== 7. Exact best attacker vs a CONSTANT defender policy (stamina ignored, 24-window horizon, direct only vs with feints) ==")
from functools import lru_cache as _lc
def best_vs_constant(cfg, policy, H=24):
    @_lc(maxsize=None)
    def go(st, depth, who_goal):
        # `side` below is the ATTACKER; policy(side, A) returns the RESPONDER's response. who_goal: the fighter we optimise exits for ('top' wants +1, 'bottom' wants -1); both fighters follow `policy` when RESPONDING;
        # the optimised fighter chooses attacks when initiating; the other fighter, when initiating, passes.
        if depth == 0: return (0, 0)
        side = st[4]
        if side != who_goal:
            ns = (st[0], st[1], st[2], st[3], who_goal); return go(ns, depth - 1, who_goal)
        best = None
        tbl = RAW[side]
        for A in tbl:
            modes = [(A, None)] + ([(ap, re) for (ap, re) in FEINTS[side] if ap == A and cfg["feints"] and _eligible(st, side, ap, re)])
            for ap, re in modes:
                real = ap if re is None else re
                resp = policy(side, A)
                bite = None if re is None else (resp in counters(side, ap))
                ns, ex = step(st, side, real, resp, cfg, bite)
                if ex: cand = (1, -(H - depth + 1))
                else:
                    r = go(ns, depth - 1, who_goal); cand = (r[0], r[1])
                if best is None or cand > best: best = cand
        # a pass is always available
        nsp = (st[0], st[1], st[2], st[3], "bottom" if side == "top" else "top")
        r = go(nsp, depth - 1, who_goal)
        if best is None or r > best: best = r
        return best
    return go
POL = {
 "always the best counter to the visible technique": lambda side, A: sorted(counters(side, A), key=lambda r: (RAW[side][A][r], r))[0],
  "Bottom always Knee Shield (Top always Knee Pin)": lambda side, A: ("knee_shield" if side == "top" else "knee_pin"),
 "Bottom always Hip Frame (Top always Hip Pressure)": lambda side, A: ("hip_frame" if side == "top" else "hip_pressure"),
 "Bottom always Underhook Fight (Top always Head Control)": lambda side, A: ("underhook_fight" if side == "top" else "head_control"),
}
cfgs7 = {"V1 (M)": dict(prep=True, power=POWER_M, erode=True, feints=False), "V1 + feints": dict(prep=True, power=POWER_M, erode=True, feints=True),
         "V2 (S)": dict(prep=True, power=POWER_S, erode=True, feints=False), "V2 + feints": dict(prep=True, power=POWER_S, erode=True, feints=True)}
for pname, pol in POL.items():
    print(pname)
    for cname, cfg in cfgs7.items():
        out = []
        for goal in ("top", "bottom"):
            r = best_vs_constant(cfg, pol)(START, 24, goal)
            out.append("%s exits? %s (exit window, counting the opponent's pass windows: %s)" % (goal, "yes" if r[0] == 1 else "no", -r[1] if r[0] == 1 else "-"))
        print("   %-12s %s" % (cname, " | ".join(out)))

print("\n== 8. Full grade pipeline with preparation: best final grade reachable from a RAW -2 decisive counter ==")
print("order: positional -> attack readiness -> defense readiness -> exhaustion -> magnitude -> undercommitment (each saturating)")
import itertools
ORDER = ["LOW", "MEDIUM", "HIGH"]
def _rank(e): return ORDER.index(e) + 1 if e in ORDER else 0
def _mag(e, g):
    if e == "HIGH":
        if g == 1: return 1
        if g == -1: return -1
    if e in ("LOW", ""):
        if g == 2: return -1
        if g == -2: return 1
    return 0
def _under(i, r): return 1 if _rank(r) < _rank(i) else 0
def best_final(raw, atk, dfn, lifts):
    top = -9
    for pos, exh, ie, re_ in itertools.product((-1, 0), (-1, 0, 1) if lifts else (0,), ("", "LOW", "MEDIUM", "HIGH") if lifts else ("MEDIUM",), ("", "LOW", "MEDIUM", "HIGH") if lifts else ("MEDIUM",)):
        g = shift(raw, pos); g = shift(g, atk); g = shift(g, dfn); g = shift(g, exh)
        top = max(top, shift(shift(g, _mag(ie, g)), _under(ie, re_)))
    return top
print("attacker tier / defender power tier        no stamina effects | with every exhaustion & commitment lift")
for atk_t, atk in ((0, -1), (1, 0), (2, 1)):
    for def_t, dfn in ((2, -1), (1, 0), (0, 2)):
        print("  attacker %-7s defender %-7s            %+d                 | %+d" % (("None", "Partial", "Ready")[atk_t], ("None", "Partial", "Ready")[def_t], best_final(-2, atk, dfn, False), best_final(-2, atk, dfn, True)))

print("\n== 9. Counterplay admissibility: worst-case final grade (initiator's view) of each response across {direct apparent} + eligible feints, neutral readiness ==")
print("rule proposed for any feint pair: some response must hold the attacker to <= 0 whatever mode was chosen")
cfg = CFGS["V1 prep, decisive counters governed (M)"]
for side, tbl, st0 in (("top", TOP_RAW, START), ("bottom", BOT_RAW, (START[0], START[1], 1, 1, "bottom"))):
    for A in tbl:
        labels, rows = apparent_matrix(st0, side, A, cfg, True)
        cols = list(tbl[A])
        worst = {cols[j]: max(rows[i][j] for i in range(len(rows))) for j in range(3)}
        verdict = "balanced response exists" if min(worst.values()) <= 0 else "NO response holds the attacker to <= 0"
        feint = "with feint" if len(rows) > 1 else "direct only"
        print("  %-6s %-14s (%s) worst-case by response: %s -> %s" % (side, A, feint, worst, verdict))

print("\n== 10. Counterplay admissibility over all 9 readiness states (band 0, axis +5, Option M): states where NO response holds the attacker to <= 0 ==")
for side, tbl in (("top", TOP_RAW), ("bottom", BOT_RAW)):
    for A in tbl:
        if not any(len(apparent_matrix((5, 0, B, F, side), side, A, cfg, True)[1]) > 1 for B in range(3) for F in range(3)):
            print("  %-6s %-14s no feint exists" % (side, A)); continue
        fails = []
        for B in range(3):
            for F in range(3):
                labels, rows = apparent_matrix((5, 0, B, F, side), side, A, cfg, True)
                if len(rows) == 1: continue
                if min(max(rows[i][j] for i in range(len(rows))) for j in range(3)) > 0: fails.append("(top_base=%d, bottom_frame=%d)" % (B, F))
        print("  %-6s %-14s fails at: %s" % (side, A, ", ".join(fails) or "none"))
```

## Appendix E — HG-9 raw-grade review (verbatim; save as `hg9_review.py` next to Appendices C and D and run `python3 -B hg9_review.py`)

Imports Appendices C and D (quietly). Evaluates the proposed grades and the candidates C1–C8 of §12.12; the reported results are the output of this script.

```python
"""Throwaway structural review of the 15 PROPOSED Half Guard raw grades (HG-9). Not an oracle, not balance evidence.
Needs hg26_proto.py and hg26_window.py in the same directory. Stamina, exhaustion, commitment settlement and the clock are ignored.
Option M readiness, None-tier shift +2, uniform exit updates, passes allowed, direct techniques only unless stated."""
import sys, io, contextlib
sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):          # hg26_window prints its own report on import
    import hg26_window as W
from collections import deque
from hg26_proto import *

CFG = dict(prep=True, power=POWER_M, erode=True, feints=False, none=2)
CFGF = dict(CFG, feints=True)
BASE = {side: {a: dict(r) for a, r in RAW[side].items()} for side in RAW}

def apply(edits):
    for side in RAW:
        for a in RAW[side]:
            RAW[side][a].clear(); RAW[side][a].update(BASE[side][a])
    for (side, action, resp), v in edits.items():
        RAW[side][action][resp] = v

def label_of(st, side, real, resp):
    return "Side Control" if side == "top" else ("Closed Guard" if W.g_of(st, side, real, resp, CFG) == 2 else "Open Guard")

def cooperative_exits():
    seen = {START: 0}; q = deque([START]); first = {}
    while q:
        st = q.popleft(); side = st[4]
        for A in RAW[side]:
            for r in RAW[side][A]:
                ns, ex = step(st, side, A, r, CFG)
                if ex:
                    first.setdefault(label_of(st, side, A, r), seen[st] + 1); continue
                if ns not in seen:
                    seen[ns] = seen[st] + 1; q.append(ns)
    return len(seen), first

def non_conceding():
    out = {}
    for side in RAW:
        for A, row in RAW[side].items():
            out["%s %s" % (side[0].upper(), A)] = sum(1 for g in row.values() if g <= 0)
    return out

def constants():
    res = {}
    for pname, pol in W.POL.items():
        for cname, cfg in (("M", CFG), ("M+f", CFGF)):
            r = []
            for goal in ("top", "bottom"):
                x = W.best_vs_constant(cfg, pol)(START, 24, goal)
                r.append(str(-x[1]) if x[0] == 1 else "-")
            res[(pname, cname)] = "/".join(r)
    return res

def random_split(games=2000, windows=60):
    """Uniform random actions and responses for both fighters, no passes; seeds 0..games-1. Ignores stamina: a shape check, not balance evidence."""
    import random
    tally = {"Top exit": 0, "Bottom exit": 0, "timeout": 0}
    for seed in range(games):
        rnd = random.Random(seed); st = START; done = False
        for _ in range(windows):
            side = st[4]; A = rnd.choice(sorted(RAW[side])); r = rnd.choice(sorted(RAW[side][A]))
            st, ex = step(st, side, A, r, CFG)
            if ex:
                tally["Top exit" if ex == 1 else "Bottom exit"] += 1; done = True; break
        if not done: tally["timeout"] += 1
    return tally

def decisions():
    best_sets = {}
    for B in range(3):
        for F in range(3):
            st = (5, 0, B, F, "top")
            vals = {A: min(W.g_of(st, "top", A, r, CFG) for r in RAW["top"][A]) for A in RAW["top"]}
            m = max(vals.values()); best_sets[(B, F)] = (m, tuple(sorted(a for a, v in vals.items() if v == m)))
    viable = [k for k, (m, _) in best_sets.items() if m >= 0]
    distinct = {v[1] for v in best_sets.values() if v[0] >= 0}
    return best_sets, viable, distinct

def neutral_value():
    st = START
    top = max(min(W.g_of(st, "top", A, r, CFG) for r in RAW["top"][A]) for A in RAW["top"])
    sb = (st[0], st[1], 1, 1, "bottom")
    bot = max(min(W.g_of(sb, "bottom", A, r, CFG) for r in RAW["bottom"][A]) for A in RAW["bottom"])
    return top, bot

CANDIDATES = {
    "C0 as proposed": {},
    "C1 Knee Slice vs Hip Frame 0 -> +1": {("top", "knee_slice", "hip_frame"): 1},
    "C2 Recover Guard vs Hip Pressure +1 -> 0 (mirror cell)": {("bottom", "recover_guard", "hip_pressure"): 0},
    "C3 = C1 + C2": {("top", "knee_slice", "hip_frame"): 1, ("bottom", "recover_guard", "hip_pressure"): 0},
    "C4 Knee Slice vs Underhook Fight +2 -> +1": {("top", "knee_slice", "underhook_fight"): 1},
    "C5 Recover Guard vs Head Control +2 -> +1": {("bottom", "recover_guard", "head_control"): 1},
    "C6 = C4 + C5": {("top", "knee_slice", "underhook_fight"): 1, ("bottom", "recover_guard", "head_control"): 1},
    "C7 = C1 + C4 (remove the Hip Frame hold, trim the Underhook Fight punishment; breaks the mirror)": {("top", "knee_slice", "hip_frame"): 1, ("top", "knee_slice", "underhook_fight"): 1},
    "C8 = C1 + C4 + C5 (both break rows become +1/+1/-2; mirror kept)": {("top", "knee_slice", "hip_frame"): 1, ("top", "knee_slice", "underhook_fight"): 1, ("bottom", "recover_guard", "head_control"): 1},
}

if __name__ == "__main__":
    for name, edits in CANDIDATES.items():
        apply(edits)
        n, first = cooperative_exits()
        const = constants()
        top, bot = neutral_value()
        sets, viable, distinct = decisions()
        sym = make(CFG, 12)(START, 12) + 0.0
        print("\n=== %s ===" % name)
        print("  cooperative play: %d reachable states; earliest exit windows %s" % (n, dict(sorted(first.items()))))
        print("  responses that hold each attack to <= 0: %s" % non_conceding())
        print("  best guaranteed direct attack value at neutral: Top %+d, Bottom %+d (a pass is 0)" % (top, bot))
        print("  symmetric optimal play, 12 windows, passes allowed: value %+0.3f" % sym)
        print("  constant responder policies, exit window for Top/Bottom attacker ('-' = no forced exit in 24 windows; passes by the opponent count as windows):")
        for pname in W.POL:
            print("    %-58s direct %-6s with feints %s" % (pname, const[(pname, "M")], const[(pname, "M+f")]))
        print("  uniform random play, 2000 games x 60 windows (shape check only): %s" % random_split())
        print("  readiness states with a viable (>= 0) direct attack for Top: %s; distinct best direct action sets there: %s" % (viable, sorted(distinct)))
    apply({})

    print("\n=== Dominance and counterplay admissibility, as proposed (C0) versus C1 ===")
    for name in ("C0 as proposed", "C1 Knee Slice vs Hip Frame 0 -> +1"):
        apply(CANDIDATES[name])
        print(name)
        for side, tbl in (("top", RAW["top"]), ("bottom", RAW["bottom"])):
            st = START if side == "top" else (START[0], START[1], 1, 1, "bottom")
            for A in tbl:
                labels, rows = W.apparent_matrix(st, side, A, CFG, True)
                cols = list(tbl[A])
                never_worse = [cols[j] for j in range(3) if all(all(rows[i][j] <= rows[i][k] for i in range(len(rows))) for k in range(3) if k != j)]
                worst = {cols[j]: max(rows[i][j] for i in range(len(rows))) for j in range(3)}
                print("  %-6s %-14s %-22s response never worse for the defender: %-16s worst-case by response: %s" % (side, A, "(direct + feint)" if len(rows) > 1 else "(direct only)", never_worse or "none", worst))
        fails = []
        for side, A in (("top", "crossface"), ("bottom", "underhook")):
            for B in range(3):
                for F in range(3):
                    st = (5, 0, B, F, side)
                    labels, rows = W.apparent_matrix(st, side, A, CFG, True)
                    if len(rows) > 1 and min(max(rows[i][j] for i in range(len(rows))) for j in range(3)) > 0:
                        fails.append("%s %s (top_base=%d, bottom_frame=%d)" % (side, A, B, F))
        print("  admissibility failures for FP-1 / FP-2 over the 9 readiness states: %s" % (fails or "none"))
    apply({})
```
