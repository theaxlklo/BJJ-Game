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
