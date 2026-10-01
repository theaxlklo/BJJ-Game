# BJJ Game Concept — Current Design Recap v9 — Mount v0 CODE-READY FREEZE

## Status

This document is the current consolidated design direction and the **implementation-ready frozen spec for Mount v0**.

It replaces the earlier turn-count model and resolves the major contradictions identified through v8.

The current core identity is:

> **A tactical BJJ roguelike built around continuous simulated matches, slow-motion decision windows, broad positional struggles, style-driven physical identity, belt-driven knowledge, temporary run builds, multiple rulesets, and staged submissions.**

The game should reward:

- BJJ understanding
- positional awareness
- setup recognition
- timing
- stamina management
- risk management
- chaining
- adaptation

It should **not** primarily reward:

- twitch reactions
- button mashing
- memorized fighting-game combos
- arbitrary hidden move priority
- frame-perfect execution

## Freeze Rule

The broad architecture is now frozen for Mount v0.

Do not reopen systems that are not needed by Mount v0 unless the running prototype exposes a concrete failure.

Submission-specific unresolved items are explicitly deferred to **Mount v0.3**.

The next source of truth should be:

> **Prototype behavior and logs, not another architecture rewrite.**

---

# 1. Match Structure

The default match currently uses:

```text
5:00 GAME TIME
```

This is **simulated grappling time**, not necessarily five minutes of real-world play time.

There is no fixed number of turns or exchanges.

The match flows continuously through:

- standing
- takedown entries
- scrambles
- guard
- half guard
- side control
- mount
- back control
- turtle
- leg entanglements if included
- submission threats
- reversals
- escapes
- transitions

The player should not lose because an arbitrary number of actions expired.

---

# 2. Real-Time Presentation, Event-Driven Decisions

The game is continuous in presentation but **event-driven in decision logic**.

At normal speed, the grapplers continue carrying out their current broad behaviors.

Examples:

```text
HOLD
PRESSURE
RETAIN
ESCAPE
DISENGAGE
HUNT SUBMISSION
CONSERVE
```

These behaviors are not just cosmetic.

They create **small continuous drift** in:

- the positional struggle axis
- setup progress
- stamina
- threat progression

Meaningful events create decision windows.

---

# 3. Behavior Drift

Normal-speed behavior must have a mechanical purpose.

The preferred direction is a **small behavior-vs-behavior drift table**.

Example concepts:

```text
PRESSURE vs ESCAPE
→ slight drift toward controlling player
→ stamina cost to both

HUNT SUBMISSION vs ESCAPE
→ submission setup rises
→ positional security may weaken

CONSERVE vs PRESSURE
→ conserving player recovers stamina
→ opponent may gain positional progress

RETAIN vs PASS
→ axis moves according to style, position, setup, and attributes
```

The exact rates are not yet final.

Behavior drift should be:

- slow
- predictable
- easy to tune
- strong enough to create events
- weak enough that major position changes still require meaningful actions

**Behavior drift cannot cross Neutral.**

Drift may weaken a position down to the Loose band, but only a deliberate action may actually break the position and trigger an Exit Map.

```text
Locked
→ Strong
→ Stable
→ Loose
→ STOP
```

Then:

```text
Loose
+ successful action
→ cross Neutral
→ Exit Map
```

This keeps drift responsible for creating opportunities while actions remain responsible for major position changes.

Decision windows can be triggered when drift causes a threshold to be crossed.

Examples:

- setup becomes Ready
- threat moves to a new stage
- position becomes unstable
- scramble begins
- submission becomes dangerous
- scoring position reaches Stable
- player manually invokes Read / Act

---

# 4. Slow-Motion Decision Windows

When a meaningful tactical event occurs:

```text
NORMAL SPEED
↓
Event develops
↓
SLOW-MOTION VISUAL
↓
MATCH CLOCK PAUSES
↓
Player reads situation
↓
Player chooses
↓
Choice locks
↓
MATCH CLOCK RESUMES
↓
Normal-speed resolution
```

The slow motion is primarily visual.

The match clock **pauses completely** during the decision window.

This avoids punishing slow thinkers and keeps the game strategic rather than reaction-based.

---

# 5. Manual Read / Act Windows

The player may manually invoke a **Read / Act** window.

This prevents the game from becoming purely reactive.

However, manual windows must not allow unlimited frame-by-frame micromanagement.

## Manual Window Rules

A manual window always allows the player to:

- inspect the current tactical state
- change broad behavior

A technique must always be **legal from the current state**.

In addition, at least one of the following must be true:

- a valid positional opening exists
- a setup is Ready
- the current situation grants initiative

Invoking a manual window costs approximately:

```text
~1 simulated second
```

The exact cost is tunable.

This means the player can take control proactively, but repeated pausing has a strategic cost.

---

# 6. Fast-Forward Through Stable Stretches

A five-minute simulated match should not automatically become a ten-minute real-world match.

If neither player is:

- building a meaningful setup
- creating a threat
- changing position
- spending major stamina
- approaching a scoring threshold
- approaching a stalling threshold

the simulation may accelerate toward the next meaningful event.

The player should still see the flow of the match.

The system should simply avoid wasting real-world time on uneventful holding periods.

---

# 7. Strategic Timing

Being "late" means:

> You allowed a threat or setup to develop too far.

It should not mean:

> You failed a 1.5-second reaction check.

Example:

```text
Underhook begins
↓
Deep underhook
↓
Opponent posts
↓
Opponent comes to knees
↓
Wrestle-up / sweep becomes dangerous
```

Earlier reactions provide:

- more options
- safer options
- lower stamina cost

Later reactions provide:

- fewer options
- higher-risk options
- worse positional consequences

---

# 8. Broad Two-Sided Struggle Axis

The game should not ask the player to manage every:

- wrist
- hook
- elbow
- shoulder angle
- grip
- hip angle
- chest connection

Instead, each position uses a broad **two-sided struggle axis**.

Conceptually:

```text
PLAYER 2 CONTROL                 PLAYER 1 CONTROL

Locked Strong Stable Loose | Neutral | Loose Stable Strong Locked
```

Internally this uses a continuous numeric axis:

```text
-4.0 ... 0.0 ... +4.0
```

The player does not need to see the numbers.

## Mount v0 Band Boundaries

For Mount v0, integers are **band edges**, not centers.

Raw initialization ranges on the Top side are:

```text
+0.10 <= axis < +1.00   Loose
+1.00 <= axis < +2.00   Stable
+2.00 <= axis < +3.00   Strong
+3.00 <= axis <= +4.00  Locked
```

The broader engine may later mirror these negatively for the opposite player, but a live Mount v0 run ends when Mount breaks, so it never persists into a Bottom-owned negative state.

Neutral is exactly:

```text
0.00 = Neutral / Mount broken
```

Values in this range are never stored:

```text
0.00 < axis < +0.10
```

### Mount v0 Escape Threshold

For an **escape-capable Bottom action** with a final result of `Success` or `Strong Success`:

```text
proposed axis <= +0.10
= Mount breaks
```

This includes a proposed landing at `+0.10`, `0.00`, any value between `0.00` and `+0.10`, or a negative value.

Therefore Loose is intentionally a **one-more-success-can-escape** band.

Behavior drift may approach Neutral but clamps at `+0.10`. Only a successful deliberate escape-capable action may break Mount.

The axis answers:

> Who currently has positional authority, and how secure is it?

## Hard Cap

The ends of the axis are hard limits.

```text
-4 = Player 2 Locked
+4 = Player 1 Locked
```

Reaching Locked does **not** automatically transition to another position or submission.

Example:

```text
Mount reaches Top +4
→ Mount remains Mount
```

Progressing to:

- S-Mount
- Back Control
- Armbar
- Arm Triangle
- another position or attack

requires an explicit legal action.

The axis represents **quality of the current position**, not automatic progression to a new one.

The same core system can be renamed depending on context:

- mount control vs escape
- guard pass vs retention
- takedown finish vs defense
- turtle breakdown vs recovery
- back retention vs escape
- scramble initiative
- leg-entanglement control if implemented

## Hysteresis

The internal axis may be continuous, but visible bands should not flicker around thresholds.

The hysteresis margin is `0.20` at **every visible band edge**.

```text
Loose → Stable: enter at >= +1.20
Stable → Loose: leave at <= +0.80

Stable → Strong: enter at >= +2.20
Strong → Stable: leave at <= +1.80

Strong → Locked: enter at >= +3.20
Locked → Strong: leave at <= +2.80
```

At run initialization only, the raw ranges define the initial visible band. After initialization, hysteresis governs all visible-band changes.

**All Mount v0 positional modifiers use the visible band, not the raw axis value.** What the tester sees is therefore exactly what explains the modifier.

Each threshold event fires once per entry.

This prevents:

- repeated decision windows
- scoring-hold resets
- shot-clock reset abuse
- visible band flicker

---

# 9. Crossing Neutral Does Not Choose the Destination

Crossing Neutral means the current struggle has broken.

It does **not** automatically determine the next position.

Each position needs an **Exit Map**.

The action that caused the crossing determines the outcome.

If an Exit Map action has more than one possible destination, the **result grade** selects the branch.

For Mount v0:

```text
Elbow Escape

Success + reaches the escape threshold
→ Half Guard

Strong Success + reaches the escape threshold
→ Open Guard
```

How far the proposed axis numerically travels does **not** choose the branch. The **final result grade** does.

The same principle can later apply to submission escapes and other multi-destination exits.

## Example: Mount Exit Map

```text
Elbow Escape crosses Neutral
→ Half Guard

Knee-Elbow Escape crosses Neutral
→ Half Guard or Open Guard

Trap-and-Roll crosses Neutral
→ Reversal
→ former bottom becomes top

Backdoor Escape crosses Neutral
→ Scramble
```

Some actions have a deterministic exit.

Others intentionally lead to a scramble.

## Mount v0 Failure Boundary Rule

In Mount v0, a failed initiated action cannot break the position.

If the initiator receives `Failure` or `Strong Failure`, the resulting axis movement may collapse their control down to **Loose**, but it cannot cross Neutral.

Example:

```text
Top Arm Isolation from +1.5
Strong Failure = -2
Raw result = -0.5
Mount v0 clamp = +0.1 / Top Loose
```

Only a **successful initiated action** may break Mount and trigger an Exit Map. This prevents v0 from needing response-specific Exit Maps.

## Mount v0 Bridge Rule

`Bridge` is **not escape-capable** in Mount v0. It weakens Mount but never finishes an escape by itself.

If Bridge would otherwise reach or pass the escape threshold:

```text
clamp axis to +0.10
remain in Mount
```

Bridge can therefore move Mount toward Loose, but it cannot fire an Exit Map.

This preserves BJJ-specific consequences without tracking anatomy at excessive granularity.

---

# 10. Initiative Is Triggered, Not Owned Permanently

Initiative does **not** simply belong to the player who is on top or currently winning the axis.

That would prevent guard players and bottom players from initiating offense.

Initiative belongs to the player who creates the meaningful event.

Examples:

```text
Mount:
Top begins Arm Isolation
→ Top is initiator
```

```text
Closed Guard:
Bottom reaches Triangle Setup: READY
→ Bottom is initiator
```

```text
Half Guard:
Bottom invokes Read / Act
and has a valid Wrestle-Up opening
→ Bottom is initiator
```

The current positional axis still matters.

It affects how strong the initiated action is.

It does **not** monopolize who is allowed to act.

---

# 11. Established Positions: Initiator → Responder

When a player triggers a meaningful action from an established position:

```text
INITIATOR
↓
Action locks
↓
RESPONDER reads it
↓
Responder chooses
↓
Resolution
```

The initiator's first action is committed before the responder chooses.

The AI or opponent cannot secretly change that first action after seeing the response.

A follow-up may become available afterward based on:

- Chain Depth
- setup
- position
- stamina
- technique knowledge

Design rule:

> Every response should close some follow-ups while leaving others open.

The responder should understand the **current threat**, but the initiator's exact chained follow-up remains hidden until committed.

This prevents initiator/responder windows from collapsing into a permanently solved "one correct defense" table.

Recognition may narrow the likely follow-up without revealing it with certainty.

This creates a readable attack-response structure while preserving mind games.

---

# 12. Standing, Neutral Positions, and Scrambles: Simultaneous Choice

When neither player has established meaningful positional authority, both can act simultaneously.

This includes:

- standing neutral
- open scrambles
- loose transition states
- some neutral guard situations
- moments immediately after a position breaks

Example:

```text
Standing Neutral

Player 1:
Single Leg

Player 2:
Snapdown
```

Both choices lock simultaneously.

Another example:

```text
Scramble

Player 1:
Come on Top

Player 2:
Attack Back
```

The engine resolves both.

## Near-Simultaneous Events

Two meaningful events do not need to land on the exact same simulation tick.

If they become Ready within approximately:

```text
0.5 simulated seconds
```

they are grouped into a **simultaneous-choice window**.

Example:

```text
Top Arm Isolation becomes Ready
AND
Bottom Trap-and-Roll becomes Ready
within 0.5 simulated seconds
```

Result:

```text
SIMULTANEOUS WINDOW
```

Both commit before resolution.

The exact simultaneity window is tunable.

This also applies when a defensive response is itself an offensive action.

## State Transition

```text
Neutral / Scramble
→ Simultaneous

Established Action Trigger
→ Initiator / Responder

Position Breaks
→ Simultaneous

New Position Established
→ Triggered Initiative resumes
```

---

# 13. Simultaneous Resolution Uses Action Tags

A giant move-vs-move priority table should be avoided.

Instead, actions can carry a small interaction tag.

Possible tags:

```text
ENTRY
PRESSURE
RETREAT
FRAME
ANGLE
SCRAMBLE
```

A compact tag-vs-tag matrix determines the broad interaction.

Example concepts:

```text
FRAME tends to resist PRESSURE
PRESSURE can disrupt ENTRY
ANGLE can bypass some FRAME actions
RETREAT can deny some ENTRY actions
```

Then the result is modified by:

- Power
- Speed
- Base
- Mobility
- Stamina
- commitment
- setup
- belt knowledge
- technique specifics

This preserves BJJ-specific interaction without requiring hundreds of unique move pairings.

---

# 14. Local Success Is Not the Same as Winning the Position

A player can win a local interaction while remaining in a bad overall position.

Example:

```text
Bottom player bridges successfully

Mount axis:
Top Strong
→ Top Stable
```

The bottom player improved their position.

They did not automatically escape.

Likewise, the top player can fail an attack without automatically losing mount.

---

# 15. Setup Progress

Some techniques require preparation.

Use broad setup states rather than detailed anatomy.

Example:

```text
Reversal Setup:
None
Partial
Ready
```

or:

```text
Triangle Setup:
None
Partial
Ready
```

Setups can:

- build through behavior drift
- build through successful actions
- decay if ignored too long
- be consumed when used
- be disrupted by a correct response

Internally, setups may use a continuous percentage while the player sees broad tiers.

```text
0–39%    None
40–79%   Partial
80–100%  Ready
```

Hysteresis should also apply to setup-tier boundaries.

The exact persistence and decay rules still need tuning.

---

# 16. Conflict Resolution Factors

When actions interact, the engine may consider:

- current position
- struggle-axis state
- setup progress
- action tag matchup
- technique matchup
- commitment
- Power
- Speed
- Stamina
- Base
- Mobility
- timing
- belt knowledge

The goal is not:

> Which move is universally stronger?

The goal is:

> Which player can impose their action from the current state?

## Mount v0 Positional Modifier

The hand-authored lookup result is modified by the current band.

Use a simple one-grade positional modifier in Mount v0.

```text
Top is Strong or Locked
+ Bottom initiates
→ shift Bottom result down 1 grade

Top is Loose
+ Top initiates
→ shift Top result down 1 grade

Top is Stable
→ no modifier
```

Mirror the logic for Bottom-owned states.

Result-grade ladder:

```text
Strong Failure
Failure
Contested
Success
Strong Success
```

A one-grade modifier moves the result one step on this ladder. This gives the axis a direct gameplay effect in v0 without adding another table.

The player should be able to understand why the result happened without seeing a giant spreadsheet.

## Randomness

The current preferred direction is **deterministic resolution**.

There should be no hidden dice roll deciding whether a correctly built action randomly works or fails.

Uncertainty instead comes from:

- simultaneous hidden choices
- AI policy variation
- incomplete Recognition
- feints
- style differences
- stamina differences
- opponent tendencies

The game may still show descriptive labels such as:

```text
Favorable
Contested
Dangerous
```

These summarize the known state rather than hidden RNG.

---

# 17. Style System

Styles define **physical identity**.

The current preferred attributes are:

- Power
- Speed
- Stamina
- Base
- Mobility

Technique is **not** a style stat.

Technique knowledge belongs to the belt system.

---

# 18. Attribute Roles

## Power

Power means:

> Ability to move the opponent.

It can affect:

- takedown finishes
- bridges
- explosive reversals
- breaking posture
- forcing movement
- submission finishing force

## Base

Base means:

> Ability to resist being moved.

It affects:

- stability
- balance
- structural integrity
- resisting displacement
- maintaining position under force

## Speed

Speed does **not** reduce the human player's decision time.

It affects the character.

Possible effects:

- faster action completion
- faster setup progression
- better capitalization on openings
- better outcome in tied simultaneous contests

Speed should **not** grant automatic scramble initiative.

Scrambles are simultaneous.

## Mobility

Mobility affects:

- guard retention
- recovery
- inversion
- scrambling
- movement through awkward positions

## Stamina

Stamina represents sustainable effort.

Possible costs:

```text
Low commitment      small cost
Medium commitment   moderate cost
High commitment     high cost
Explosive action    very high cost
```

Stamina recovery should come from low-threat choices such as:
- CONSERVE
- RESET
- slowing the pace

**STABILIZE does not restore stamina for free.**

Stabilize protects or improves position.

Conserve restores stamina but gives up pressure or initiative and may allow the opponent to progress.

---

# 19. Example Styles

Final numbers are not locked.

All styles should use a controlled or equal stat budget.

## Smasher

Identity:

- passing
- pressure
- pins
- mount
- top submissions
- positional grinding

Strengths:

- Power
- Base
- pressure progression
- top stabilization

Weaknesses:

- loose scrambles
- inversion
- mobility-heavy situations

## Lanky

Identity:

- guard
- triangles
- long-range attacks
- flexible movement
- unusual angles

Strengths:

- Mobility
- guard retention
- triangles
- armbar chains
- bottom attacks

Weaknesses:

- raw force contests
- pressure battles
- explosive takedown exchanges

## Explosive

Identity:

- scrambles
- reversals
- wrestling bursts
- unstable-position attacks
- unconventional transitions

Strengths:

- Power
- Speed
- sudden reversals
- emergency escapes
- scramble attacks

Weaknesses:

- burns stamina rapidly
- weaker prolonged control
- failed high-commitment actions are costly

## Technician

Identity:

- efficiency
- clean positioning
- low wasted movement
- strong Base
- strong Stamina
- high stamina efficiency

Hard weakness:

- low Power
- cannot reliably brute-force finishes without proper setup

## Wrestler

Identity:

- standing
- takedowns
- mat returns
- scrambles
- turtle rides
- wrestle-ups

Hard weaknesses:

- weaker guard from bottom
- weaker submission defense from bottom

This keeps Wrestler separate from Smasher.

---

# 20. Belt System

Belts define **BJJ knowledge**.

The belt determines:

- legal technique pool
- counters
- recognition
- Chain Depth
- advanced options
- submission complexity
- unusual techniques

Higher belts should not simply receive stronger physical stats.

Their main advantage is:

> They understand more BJJ.

---

# 21. Recognition Adds Information

Recognition should never punish beginners by hiding basic tactical truth.

Every belt sees the fundamental state.

Example:

```text
White Belt:
"Your arm is being isolated."
Threat: Building
```

Higher belts gain more detail.

```text
Blue Belt:
"Armbar setup developing."
```

```text
Purple Belt:
"Armbar setup developing.
Likely follow-up: triangle or back transition."
```

Higher belts may gain:

- technique names
- likely follow-ups
- counter-chain prediction
- better feint recognition
- more specific defensive options

---

# 22. Feints

Feints should not make the UI lie.

The preferred model is:

> Feints are real threats with low commitment.

Everyone may see:

```text
Threat: Building
```

Higher belts may additionally see:

```text
Commitment: Low
```

The deception is in:

- commitment
- likely follow-up
- whether the attacker intends to continue

not in falsely displaying a threat that does not exist.

A **low-commitment feint cannot advance beyond THREAT**.

A cheap threat should also be answerable with a similarly cheap defensive response.

This prevents repeated feints from becoming a nearly free stamina-drain exploit.

Feints may also be especially useful in simultaneous neutral situations.

---

# 23. Belt vs Run Rewards

The current preferred structure is:

```text
BELT
determines legal technique pool

RUN
selects and develops from that pool
```

A white belt should not randomly receive a fully mastered advanced technique.

## Technique Variants

Early-run rewards can deepen known moves.

Examples:

```text
Armbar
→ now available from Mount
```

```text
Triangle
→ stronger from Closed Guard
```

```text
Double Leg
→ improved follow-up into Side Control
```

## Drilled Techniques

A rarer reward may temporarily grant a next-belt technique in a weaker form.

Example:

```text
DRILLED:
Granby Roll

- higher stamina cost
- weaker setup
- fewer follow-ups
```

Successful use can contribute toward promotion progress.

Drilled techniques should **accelerate** promotion, not determine it through reward luck.

---

# 24. Promotion and Meta-Progression

Promotion should primarily come from **milestones**.

Possible examples:

- win a tournament at current belt
- complete a belt challenge
- demonstrate required technique families
- achieve a promotion milestone set

Drilled techniques may speed progress.

They should not be required.

Opponents can be grouped by belt division, similar to real tournaments.

Because stronger belts also bring stronger opponents, the game needs additional permanent progression.

Possible permanent unlocks:

- new styles
- starting traits
- gym upgrades
- coaches
- starting technique choices
- cosmetics
- training bonuses

This lets the player feel stronger even when belt promotion raises the competition level.

---

# 25. Submission System

Submissions use a universal 3-stage structure:

```text
THREAT
↓
CONTROL
↓
FINISH
```

The defender pushes backward:

```text
FINISH
↓ successful defense
CONTROL
↓ successful defense
THREAT
↓ successful defense
OFF
```

**OFF** means the submission has been escaped.

## Finish State

Reaching FINISH does not instantly end the match, but it does trigger the final submission decision.

The flow is:

```text
FINISH reached
↓
Emergency Submission Window
↓
Defender chooses:
TAP or REFUSE TAP
↓
If TAP:
match ends immediately

If REFUSE TAP:
one hidden simultaneous final contest
↓
Escape
OR
Stoppage / Injury / Unconsciousness
```

The previous concept of a passive 2–3 second Finish Hold plus another later escape attempt is removed.

The visual presentation may still show a brief finishing struggle, but mechanically there is only **one final Refuse-Tap contest** after FINISH is secured.

---

# 26. Submission Track Sits on Top of Position

The positional struggle axis remains active while a submission is being attacked.

Example:

```text
Position:
Mount
Axis:
Top +2

Submission:
Armbar CONTROL
```

A successful submission defense can also damage positional control.

Example:

```text
Armbar CONTROL
→ THREAT

Mount axis:
Top +2
→ Top +1
```

A full submission escape may shift the position again.

If the defense pushes the positional axis through Neutral, the result uses an **Exit Map row specific to that submission escape**.

Example candidates:

```text
Armbar from Mount
+ successful stack escape
→ Top Half Guard
```

```text
Armbar from Mount
+ successful stack escape
→ Top Closed Guard
```

```text
Armbar from Mount
+ chaotic escape
→ Scramble
```

The defensive action determines the destination.

This represents the attacker sacrificing positional security while committing to the submission.

---

# 27. Submission Switching

Switching submissions preserves some progress but not all.

Preferred rule:

```text
Current submission at FINISH
↓ switch
New submission begins at CONTROL
```

```text
Current submission at CONTROL
↓ switch
New submission begins at THREAT
```

Switching costs:

- stamina
- one chain use
- submission progress

## Chain Depth Cap

Chain Depth limits consecutive switches.

Example:

```text
Blue Belt Chain Depth: 2

Armbar
→ Triangle
→ Omoplata

Cannot immediately chain again
without resetting or rebuilding.
```

Chain Depth resets only when:

- the submission returns to OFF
- the positional axis crosses Neutral
- or a new position becomes established

Ordinary movement between visible bands, such as:

```text
Top +2 → Top +1
```

does **not** refill Chain Depth.

This prevents submission defense from accidentally restoring the attacker's entire chain and reintroducing infinite loops.

---

# 28. Emergency Submission Defense

If a submission becomes immediately dangerous, an emergency defense window **always opens**.

This applies at every belt.

White belts may receive simpler information and fewer technical counters.

They are never denied the opportunity to respond.

---

# 29. Tap, Refuse, Injury, and Unconsciousness

At a fully secured submission, the defender has agency over whether to concede.

## Tap

The normal safe option:

```text
TAP
→ immediate loss
→ no major injury consequence
```

Tapping should be the rational default when the submission is fully lost.

## Refuse Tap

The defender may choose:

```text
REFUSE TAP
```

Refusing does **not** introduce RNG.

Instead, it creates one final **hidden simultaneous contest**.

Example structure:

```text
Attacker secretly chooses finishing action:
- extend
- change angle
- compress
- switch control

Defender secretly chooses emergency defense:
- rotate
- stack
- clear line
- posture
```

Both choices lock before resolution.

The result is still deterministic once both choices are known.

This preserves the game's deterministic philosophy while keeping Refuse Tap uncertain at decision time.

## Joint Lock Consequence

If the defender refuses to tap to a secured joint lock and loses the final contest:

```text
Joint Injury
→ Match Stoppage
```

Possible run-level consequences:

- reduced effectiveness with that limb
- certain techniques temporarily unavailable
- worse Base in relevant situations
- reduced submission resistance
- forced medical or rest node

Possible severity tiers:

```text
Minor Strain
→ lasts 1 match

Moderate Injury
→ lasts rest of run unless treated

Serious Injury
→ may end the run
```

The exact severity model remains open.

## Choke Consequence

If the defender refuses to tap to a fully secured choke and loses the final contest:

```text
Unconsciousness
→ Match Stoppage
```

Possible run-level consequences:

- forced recovery
- reduced stamina ceiling next match
- forced rest node
- temporary recovery debuff

Do not use permanent neurological-damage systems.

The purpose is strategic consequence, not graphic injury simulation.

## Referee Stoppage

Some competitive modes may allow the referee to intervene when:

- the player is unconscious
- a joint lock has clearly reached a catastrophic state
- continued resistance is no longer reasonable

Possible submission endings:

```text
TAP
REFEREE STOPPAGE
JOINT INJURY
UNCONSCIOUSNESS
```

## Final-Match Consequences

Refusing must still carry meaningful risk in the final match of a run.

Possible meta consequences include:

- delayed promotion progress
- forced recovery before the next run
- missing the first match of the next run
- temporary training restriction

The exact meta penalty is still open, but Refuse Tap should never become a free choice simply because no later match remains in the current run.

## Strategic Meaning

Example:

```text
Tournament Semifinal
Caught in Armbar

TAP
→ lose safely

REFUSE
→ one hidden final contest
→ possible escape
→ possible injury affecting later matches
```

This creates run-management consequences without needing a traditional HP bar.

---

# 30. Flash Submissions

Fast submissions can exist.

They should require exceptional circumstances such as:

- excellent setup
- major defensive mistake
- exhausted defender
- strong positional advantage
- specialist build
- meaningful knowledge advantage

Even a flash submission still triggers the mandatory emergency defense window.

If the defender refuses to tap after the finish is fully secured, the same injury or unconsciousness rules apply.

---

# 31. Match Rulesets

The same grappling engine should support different competitive rules.

## Points Mode

Possible scoring events:

- takedowns
- sweeps
- passes
- mount
- back control
- advantages
- penalties

A submission ends the match immediately.

Current preferred scoring trigger:

```text
Reach scoring position at Stable
↓
Hold 3 simulated seconds
↓
Score awarded
```

A scoring position scores **once per positional entry**.

```text
Enter Mount
→ Stable for 3s
→ score

Stable → Loose → Stable
→ no second Mount score

Cross Neutral, lose Mount, later re-enter Mount
→ eligible to score Mount again
```

Exact point values are still open.

## Submission-Only Mode

No positional points.

Only a submission ends the match normally.

If time reaches 0:00, possible mode-specific outcomes include:

- draw
- overtime
- judges' decision
- dominance tiebreak
- tournament rule

This is still unresolved.

It does not block Mount v0, but it must be decided before full-match and standing-neutral simulations.

---

# 32. Stalling and Position Shot Clocks

Stalling should measure **progress**, not button activity.

Spamming fake escape attempts or meaningless actions should not count as active grappling.

## Dominant Position Shot Clock

A dominant position can create a visible advancement timer.

Example:

```text
MOUNT ADVANCEMENT
20s
```

The timer may reset when the player with initiative:

- advances position
- creates a real submission threat
- forces a meaningful defensive reaction
- transitions to another attacking position

## Guard and Other Two-Sided Positions

The persistent advancement clock follows **who is currently favored by the positional axis**, not temporary initiative.

A guard player who is winning the positional struggle can therefore own the advancement obligation even while on bottom.

Meaningful initiated events reset the relevant advancement clock.

## Neutral Standing

Neutral positions use a shared activity clock.

Both players are expected to create meaningful progress.

Exact neutral-stalling attribution still needs tuning.

---

# 33. Stalling Penalties

## Points Mode

The penalty ladder should hurt enough that intentionally eating penalties is not profitable.

Possible progression:

```text
Warning
↓
Point / penalty consequence
↓
Second major offense:
Position Reset
↓
Further escalation
```

The exact values remain open.

## Submission-Only Mode

Avoid invisible stat reductions.

The penalty always benefits the **non-stalling player**.

Examples:

```text
Top stalls in Mount
→ axis shifts one step toward Bottom
```

```text
Bottom stalls while shelling
→ axis shifts one step toward Top
```

Stalling penalties follow the same boundary rule as behavior drift:

```text
Locked
→ Strong
→ Stable
→ Loose
→ STOP
```

A stalling penalty does **not** cross Neutral by itself.

If the offending player is already at Loose, or the axis is Neutral and cannot move meaningfully:

```text
Non-stalling player
→ receives a FREE INITIATIVE WINDOW
```

A free initiative window:

- costs 0 simulated seconds
- does not require a Ready setup
- still requires the chosen technique to be legal from the current position

Repeated offense may cause:

```text
Position Reset
```

This is:

- visible
- understandable
- reusable
- directly connected to the core system

---

# 34. Time as a Strategic Resource

The clock should influence risk.

Example:

```text
0:35 remaining
Down on points
```

Possible choices:

```text
SAFE:
Recover Guard

RISKY:
Wrestle Up

VERY RISKY:
Expose position to create submission threat
```

A player ahead may choose safer control.

A player behind may increase commitment.

In submission-only, static holding does not directly score, so the attacker eventually needs to create meaningful offense.

---

# 35. Roguelike Structure

Possible run flow:

```text
Opponent
↓
Match
↓
Technique / Trait Reward
↓
Opponent
↓
Training / Rest
↓
Stronger Opponent
↓
Boss / Tournament Match
```

Possible rewards:

- technique variants
- new techniques from legal belt pool
- upgrades
- style traits
- stamina improvements
- position-specific bonuses
- synergies
- Drilled techniques

---

# 36. Run Length and Pacing

Five-minute simulated matches can become long in wall-clock time.

Pacing tools include:

- fast-forward through stable stretches
- shorter early-round match formats
- longer finals
- varied tournament rules

Possible example:

```text
Early Rounds:
3:00 simulated

Semifinal / Final:
5:00 simulated
```

This is a possible pacing tool, not yet a locked rule.

---

# 37. Current Character Model

```text
STYLE
- Power
- Speed
- Stamina
- Base
- Mobility

BELT
- Technique Pool
- Recognition
- Chain Depth
- Advanced Counters
- Submission Complexity

RUN
- Temporary Traits
- Technique Selection
- Upgrades
- Synergies
- Injuries / Recovery State

META
- Belt Promotion
- Styles
- Coaches
- Gym Upgrades
- Starting Traits
```

---

# 38. Gi vs No-Gi

Still unresolved.

This affects:

- grips
- chokes
- guard systems
- passing
- animations
- available techniques
- style viability

Possible directions:

- no-gi first
- gi first
- both eventually
- separate rulesets
---

# 39. Leg Entanglements

Leg locks have been discussed but are not fully modeled yet.

Possible v1 approaches:

- remove advanced leg locks
- create one broad **Leg Entanglement** position
- later split into multiple families

The broad position currently fits the abstraction level best.

---

# 40. Three.js Animation Scope

Two-body grappling animation is a major technical risk.

Preferred direction:

- authored canonical poses
- authored transitions
- procedural IK for contact
- limited physics
- stylized pose-to-pose transitions
- game state remains authoritative

Do not rely on full-body physics to decide BJJ legality.

---

# 41. AI

Opponent AI eventually needs to understand:

- style
- belt
- score
- clock
- stamina
- position
- struggle-axis state
- initiative
- simultaneous situations
- setup progress
- submission danger
- risk
- stalling
- technique pool
- Chain Depth

AI personalities should differ because of strategy and knowledge, not merely stat bonuses.

---

# 42. Multiplayer

Future multiplayer questions include:

- paused decision-window synchronization
- simultaneous hidden commitments
- initiator/responder windows
- latency
- disconnect handling
- anti-stalling
- fairness

This should remain deferred until the single-player core is proven.

---

# 43. Main Design Principles

1. **BJJ decisions over fighting-game combos**
2. **Strategic timing over twitch reactions**
3. **Continuous simulated time instead of fixed turns**
4. **Decision windows pause the match clock**
5. **Normal-speed behaviors have mechanical drift**
6. **Manual Read / Act is proactive but not free**
7. **Broad states over limb-by-limb micromanagement**
8. **One two-sided struggle framework across positions**
9. **Exit Maps determine where broken positions lead**
10. **Initiative is triggered, not permanently owned by top/control**
11. **Established-position actions use initiator → responder**
12. **Standing, scrambles, and neutral situations can use simultaneous choices**
13. **Simultaneous resolution uses small action-tag interactions**
14. **Local success differs from winning the position**
15. **Setups matter**
16. **Styles define physical identity**
17. **Belts define knowledge**
18. **Runs define temporary builds**
19. **Meta-progression exists outside belt rank**
20. **Recognition adds information instead of hiding basics**
21. **Feints are real low-commitment threats**
22. **Submissions use Threat → Control → Finish**
23. **Submission defense always gets an emergency window when critically threatened**
24. **Submission switching costs stamina and Chain Depth**
25. **Stalling is measured by progress, not button activity**
26. **Stalling penalties should be visible and meaningful**
27. **Different rulesets reuse the same core engine**
28. **The game should feel like BJJ, not a UFC grappling clone**

---

# 44. Mount v0 — Code-Ready Frozen Specification

The architecture review is closed for Mount v0.

Mount v0 tests only:

```text
AXIS
↓
BEHAVIOR DRIFT
↓
FIXED TEST WINDOW
↓
INITIATED ACTION
↓
RESPONSE
↓
HAND-AUTHORED RESULT
↓
BEHAVIOR MODIFIER
↓
POSITIONAL MODIFIER
↓
AXIS DELTA
↓
EXIT MAP OR CONTINUE
```

It does **not** test stamina, setups, submissions, belts, scoring, stalling, AI, or final UI.

---

# 45. Default Run Configuration

Default values:

```text
Clock: 5:00
Starting Axis: +1.50
Initial Visible Band: Stable
Decision Interval: 5 simulated seconds
Drift Tick: 1 simulated second
First Initiator: Top
```

Starting at `+1.50` avoids beginning on a band edge.

## Optional CLI Overrides

The script should support targeted testing:

```text
--axis 0.50
--clock 0:30
--interval 5
```

Validation:

```text
0.10 <= --axis <= 4.00
--clock > 0
--interval > 0
```

A zero or negative starting axis is invalid for Mount v0 because Mount is already broken.

---

# 46. Exact Simulation Cycle

At `5:00`, before time advances:

1. Choose Top behavior.
2. Choose Bottom behavior.

Then repeat:

```text
A. Simulate drift for up to 5 seconds.
B. If clock hits 0:00, end run.
C. Open decision window.
D. Scheduled player initiates.
E. Other player chooses response.
F. Resolve immediately; decision time costs 0 simulated seconds.
G. If Mount breaks, end run.
H. Both players may KEEP or CHANGE behavior.
I. Alternate initiator.
J. Resume drift.
```

Temporary initiator schedule:

```text
Window 1: Top
Window 2: Bottom
Window 3: Top
Window 4: Bottom
...
```

This is scaffolding only and is replaced by triggered initiative in v0.2.

---

# 47. Drift

Internal drift tick:

```text
1 simulated second
```

Placeholder rates:

```text
Top PRESSURE vs Bottom ESCAPE   = +0.10 / sec
Top PRESSURE vs Bottom PROTECT  = +0.15 / sec
Top HOLD     vs Bottom ESCAPE   = -0.10 / sec
Top HOLD     vs Bottom PROTECT  =  0.00 / sec
```

Positive = toward Top control. Negative = toward Bottom escape.

Drift never breaks Mount. If drift would reduce the axis below `+0.10`, clamp to `+0.10`.

---

# 48. Behavior Effects

Mount v0 keeps `HOLD` and `PROTECT` meaningful before stamina exists.

## Top: PRESSURE

- uses the drift table above
- no resolution bonus

## Top: HOLD

When Top is responding to:

```text
Bridge
Trap-and-Roll
```

shift the Bottom initiator's grade **down one grade**.

Example:

```text
Success → Contested
```

## Bottom: ESCAPE

- uses the drift table above
- no resolution bonus

## Bottom: PROTECT

When Bottom is responding to:

```text
Arm Isolation
```

shift the Top initiator's grade **down one grade**.

Result grades are always clamped to the five-grade ladder.

---

# 49. Mount v0 Actions

## Top Initiated

```text
Climb High
Pressure Shift
Arm Isolation
```

## Bottom Initiated

```text
Bridge
Elbow Escape
Trap-and-Roll
```

## Top Responses

```text
Post
Widen Base
Follow Hips
```

## Bottom Responses

```text
Frame
Turn In
Protect Arm
```

Total hand-authored entries:

```text
3 × 3 Top initiated = 9
3 × 3 Bottom initiated = 9
Total = 18
```

---

# 50. Raw Lookup Grades

Each action/response pair returns exactly one raw grade from the initiator's perspective:

```text
Strong Failure
Failure
Contested
Success
Strong Success
```

Numeric values:

```text
Strong Failure = -2
Failure        = -1
Contested      =  0
Success        = +1
Strong Success = +2
```

No RNG.

The 18-entry table must live in one easy-to-edit data structure.

---

# 51. Exact Resolution Order

Every decision resolves in this order:

```text
1. Read raw lookup grade.
2. Apply behavior modifier, if any.
3. Apply visible-band positional modifier.
4. Clamp to Strong Failure ... Strong Success.
5. Convert final grade to numeric value.
6. Convert numeric value into axis direction based on initiator.
7. Apply Bridge special rule if Bridge initiated.
8. Apply failure clamp if needed.
9. Check escape threshold if action is escape-capable.
10. If escaped, resolve Exit Map and end run.
11. Otherwise clamp axis to [+0.10, +4.00].
12. Update visible band through hysteresis.
13. Log full calculation.
```

This order is frozen for Mount v0.

---

# 52. Axis Direction by Initiator

Grades are always stored from the initiator's perspective.

## Top Initiates

```text
axis_delta = grade_value
```

Examples:

```text
Top Success = +1.0
Top Failure = -1.0
```

## Bottom Initiates

```text
axis_delta = -grade_value
```

Examples:

```text
Bottom Success        = -1.0
Bottom Strong Success = -2.0
Bottom Failure        = +1.0
```

---

# 53. Positional Modifier

The modifier reads the **visible band after hysteresis**.

## Top Strong or Locked

When Bottom initiates:

```text
shift Bottom result down 1 grade
```

Examples:

```text
Strong Success → Success
Success → Contested
Contested → Failure
```

## Top Stable

```text
no positional modifier
```

for either initiator.

## Top Loose

When Top initiates:

```text
shift Top result down 1 grade
```

Bottom receives no automatic extra grade at Loose; being one successful escape from breaking Mount is already the advantage.

---

# 54. Escape Threshold and Invalid Gap Rule

For an **escape-capable Bottom action**:

```text
Final grade is Success or Strong Success
AND
proposed axis <= +0.10
→ Mount breaks
```

This rule covers all edge cases:

```text
+0.10 exactly → break
+0.05 → break
0.00 exactly → break
negative proposed axis → break
```

No value between `0.00` and `+0.10` is ever stored.

If the action is not escape-capable, use its special rule instead.

---

# 55. Failure Clamp

A `Failure` or `Strong Failure` can never break Mount.

If a failure would produce `axis <= +0.10`:

```text
stored axis = +0.10
position = Mount
```

Example:

```text
Top at +1.50
Top Strong Failure = -2
Raw proposed axis = -0.50
Stored axis = +0.10
Band = Loose
```

No Exit Map fires.

---

# 56. Bridge Rule

`Bridge` is not escape-capable in Mount v0.

If Bridge would produce `axis <= +0.10`:

```text
stored axis = +0.10
position = Mount
```

No Exit Map fires.

Bridge represents disruption and creation of opportunity, not a completed escape.

---

# 57. Exit Map

Mount v0 has two escape-capable Bottom actions.

## Elbow Escape

If the escape threshold is reached:

```text
Final grade = Success
→ Half Guard
```

```text
Final grade = Strong Success
→ Open Guard
```

The **grade**, not numerical overshoot, chooses the destination.

## Trap-and-Roll

If the escape threshold is reached:

```text
Success or Strong Success
→ Reversal
```

The run ends immediately after the destination is recorded.

---

# 58. Known Elbow-Escape Tuning Watch

Do not fix this before logs exist.

Whole-number deltas may initially make the Half Guard / Open Guard distribution unrealistic.

The checker should specifically report:

```text
How often Elbow Escape reaches Half Guard
How often Elbow Escape reaches Open Guard
Which starting bands permit each branch
```

If solid Mount disproportionately produces Open Guard, tune after observing the prototype.

---

# 59. Input Mode

Mount v0 is command-line **hot-seat**.

The tester chooses for both players:

- behaviors
- initiated actions
- responses

No AI is used in v0.

---

# 60. Exhaustive Checker

Provide:

```text
--enumerate
```

It prints all 18 raw action/response pairings.

Also support checking each pairing under:

```text
Loose
Stable
Strong
Locked
```

so modifiers can be inspected.

The checker should flag:

- a response that beats every initiated action
- an initiated action that never succeeds
- an initiated action that always succeeds
- unreachable exit branches
- grade modifications that repeatedly hit caps

HOLD and PROTECT are intentionally narrow-purpose in v0 and should not be flagged merely because their drift is weaker.

---

# 61. Logging

Drift still ticks every 1 simulated second internally, but default output prints **one drift summary per decision interval**.

Example:

```text
DRIFT SUMMARY
Clock: 5:00 → 4:55
Top: PRESSURE
Bottom: ESCAPE
Start Axis: +1.50
Total Drift: +0.50
End Axis: +2.00
Visible Band: Stable
```

If a hysteresis transition occurs during the interval, also print:

```text
Band Change: Stable → Strong at 4:53
```

For every decision, print:

```text
Clock
Axis before
Visible band before
Top behavior
Bottom behavior
Initiator
Initiated action
Response
Raw grade
Behavior modifier
Positional modifier
Final grade
Grade numeric value
Axis delta
Proposed axis
Failure clamp used?
Bridge clamp used?
Escape threshold reached?
Exit-capable action?
Axis after
Visible band after
Exit destination
```

---

# 62. Run End

A Mount v0 run ends when:

```text
Elbow Escape breaks Mount
```

or:

```text
Trap-and-Roll breaks Mount
```

or:

```text
Clock reaches 0:00
```

No reset-to-Mount loop.

At timeout, report:

```text
TIMEOUT — Mount retained
```

This is a prototype result, not the final game's match rule.

---

# 63. Run Summary

Print:

```text
Initial clock
Elapsed simulated time
Mount duration
Starting axis
Final axis
Final visible band
Top behavior history
Bottom behavior history
Top initiation count
Bottom initiation count
Initiated-action history
Response history
Raw-grade history
Modified-grade history
Clamp count
Escape threshold reached?
Exit reason
Exit destination
```

---

# 64. Deferred Systems

Do not add these to Mount v0.

## v0.1

- stamina
- commitment
- CONSERVE
- STABILIZE distinction

## v0.2

- setup percentages
- triggered initiative
- manual Read / Act
- 0.5-second near-simultaneous event grouping

## v0.3

- Armbar from Mount
- submission-state cleanup
- final normal defense rule
- Tap / Refuse
- hidden simultaneous final Refuse contest
- AI Refuse personality
- injury / unconsciousness consequences
- submission Exit Maps
- Chain Depth

## v0.4

- scoring
- stabilization scoring
- stalling
- advancement clock

## v0.5

- AI
- weighted policy
- styles
- batch simulation

---

# 65. Before Later Prototypes

Gi vs no-gi must be decided before Guard.

The submission-only timeout/end condition must be decided before full-match, Standing Neutral, and tournament-flow testing.

Neither blocks Mount v0.

---

# 66. Mount v0 Success Criteria

Mount v0 is successful if:

- every numeric state has an unambiguous meaning
- exact `0.00` and the `0.00–0.10` gap are handled explicitly
- hysteresis prevents band flicker
- visible bands explain positional modifiers
- drift never breaks Mount
- failures never break Mount
- Bridge never breaks Mount
- Elbow Escape and Trap-and-Roll exit deterministically
- behavior choices have at least a narrow mechanical distinction
- the 18-entry table is easy to edit
- hot-seat flow is readable
- checker output exposes bad table entries
- logs explain every calculation

Mount v0 does **not** need to prove deep strategic balance.

---

# 67. Final Freeze

**Mount v0 is code-ready and frozen at v9.**

Do not run another architecture review before implementation.

From this point, change Mount v0 only when the running prototype shows concrete evidence such as:

- impossible numeric states
- an undefined transition
- a dominant lookup loop
- an unreachable branch
- hysteresis behaving incorrectly
- an obviously wrong BJJ interaction
- a log that cannot explain its own outcome

The next task is:

> **Implement Mount v0 with an editable 18-entry lookup table.**