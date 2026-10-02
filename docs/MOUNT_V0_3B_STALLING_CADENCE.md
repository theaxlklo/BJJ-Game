# Mount v0.3b — Stalling Cadence Amendment

## Status

FROZEN BEFORE v0.3b MECHANICS IMPLEMENTATION.

This amendment resolves the only intentionally-open item in `MOUNT_V0_3B_DEFINITION_OF_DONE.md`: the stalling trigger cadence.

The values come from the existing v9 design freeze rather than a new tuning pass.

## Source in the v9 freeze

Section 32, **Stalling and Position Shot Clocks**, gives the only advancement-timer value on record:

```text
MOUNT ADVANCEMENT
20s
```

In v9 that value is presented as an example rather than a fixed rule.

Section 33, **Stalling Penalties**, gives the only penalty ladder/consequence on record:

```text
Warning
-> penalty consequence
```

and in submission-only mode fixes the positional consequence:

```text
Locked
-> Strong
-> Stable
-> Loose
-> STOP
```

A penalty never crosses Neutral.

If the offender is already at Loose, or the axis cannot move meaningfully, the non-stalling player receives a:

```text
FREE INITIATIVE WINDOW
```

which costs 0 simulated seconds and still requires a legal technique.

v0.3b promotes these historical values into executable rules.

## Advancement clock ownership

v9 Section 32 says the persistent advancement clock follows the player favored by the positional axis.

v0.3b deliberately changes that ownership model.

Each competitor owns an independent advancement clock:

```text
Top advancement clock
Bottom advancement clock
```

Reason:

- v0.3b requires symmetric stalling attribution;
- Gate C requires proving either competitor can be penalized;
- temporary initiative and current axis ownership are not sufficient to assign individual responsibility for repeated RESET choices.

This is an explicit versioned change from Section 32, not an accidental contradiction.

The future multi-position model may revisit ownership semantics for Guard/Neutral. Mount-v0.3b uses per-player clocks.

## Clock unit

Each advancement clock is measured in **simulated game seconds**, not number of windows.

Frozen threshold:

```text
20 simulated seconds
```

This makes the rule independent of `--interval`.

Changing the simulation interval must not make the same real-time stalling behavior easier or harder to exploit.

## Clock accumulation

A player's advancement clock tracks simulated time since that player's last engagement.

It advances with game time.

It does not advance merely because a zero-time administrative operation occurs.

At every game-time advance of `dt` seconds:

```text
Top advancement clock += dt
Bottom advancement clock += dt
```

subject to ordinary match termination.

## Engagement resets the player's clock

Any engagement resets that player's advancement clock to:

```text
0
```

Engagement retains the definition frozen in the v0.3b DoD:

### Initiated engagement

The player takes a legal non-RESET action through a route that is progress-capable in the pre-response state.

Success is **not** required.

A Contested submission hold still counts as engagement for the attacker because the attacker made a legitimate attempt.

### Defensive engagement

The player legally responds to an opponent's progress-capable initiated action.

That defender's advancement clock also resets to 0.

An informed Turn-In that holds Americana at Contested is therefore active defense, not stalling.

## RESET with no progress route

If the current player has no progress-capable legal route:

```text
RESET
-> legitimate
-> no offense
```

The player's advancement clock is not reset merely by RESET.

The clock continues to represent time since their last real engagement.

However, no warning/penalty can be issued from a RESET when the rules provide no progress-capable route.

## Stalling offense

A stalling offense occurs only when all are true:

```text
1. player has the initiation opportunity
2. at least one progress-capable legal route exists
3. player chooses RESET
4. player's advancement clock >= 20 simulated seconds
```

If the clock is below 20 seconds:

```text
progress route exists + RESET
-> recorded stalling opportunity
-> no offense yet
```

RESET itself does not reset the advancement clock.

Therefore repeated RESETs continue toward the same threshold.

## Default 5-second interval example

At the normal 5-second simulation interval, initiative alternates between fighters.

A given fighter normally receives an initiation opportunity every 10 simulated seconds.

If a progress route remains available and the fighter repeatedly RESETs:

```text
first repeated opportunity:
clock approximately 10s
-> RESET
-> no offense

second repeated opportunity:
clock approximately 20s
-> RESET
-> first offense
-> Warning
```

This is a consequence of the time rule, not a hardcoded "two RESETs" rule.

At another interval, the same 20-second simulated threshold remains authoritative.

## Warning persistence

The first stalling offense for a player produces:

```text
Warning
```

The warning persists for the rest of the match.

Engagement resets the player's advancement clock but does **not** erase the warning.

This prevents:

```text
stall to Warning
-> engage once
-> reset warning
-> stall to Warning again forever
```

Each player has their own persistent warning state.

## Later offenses

After a player has already received their warning, every later offense applies one submission-only stalling consequence.

The player's advancement clock is reset to 0 after an offense consequence is processed.

The warning remains set.

This means a later penalty requires another full 20 seconds without engagement before another offense can occur.

## Axis penalty

If the axis can move one nominal Mount step toward the non-stalling player without crossing Neutral:

```text
later offense
-> one axis step toward non-stalling player
```

Examples:

```text
Top offender:
Locked -> Strong
Strong -> Stable
Stable -> Loose

Bottom offender:
axis moves one nominal step toward Top
```

The penalty cannot cross Neutral or directly create an escape/reversal.

## Loose / boundary consequence

If the offending player is already at the Loose boundary, or the axis cannot move meaningfully without violating the Neutral boundary:

```text
later offense
-> non-stalling player receives FREE INITIATIVE WINDOW
```

This is inherited directly from v9 Section 33.

## Free initiative window

A free initiative window:

```text
costs 0 simulated seconds
does not advance either advancement clock
does not itself require Ready
still requires the chosen technique to be legal
```

It gives the non-stalling player the next initiation opportunity immediately.

The free window does not bypass normal action legality, setup-target legality, submission-stage legality, stamina costs, or resolution rules.

It bypasses only the normal time cost / initiative wait.

### No recursive free-window abuse

A free initiative window is an initiative consequence, not an automatic technique.

If the beneficiary chooses RESET during that free window:

- normal RESET/stalling eligibility is evaluated for that player;
- no simulated time passes;
- the beneficiary does not gain a second free window merely because the first was unused.

## Offense processing order

At a player's initiation opportunity:

```text
1. determine whether at least one progress-capable route exists
2. player chooses action or RESET
3. if progress-capable legal action chosen:
     record initiated engagement
     reset attacker's advancement clock to 0
4. if RESET chosen:
     if no progress route:
       legitimate RESET
     else if advancement clock < 20s:
       record stalling opportunity only
     else:
       record stalling offense
       if never warned:
         issue persistent Warning
       else:
         apply one-step axis penalty
         or free initiative at boundary
       reset offender advancement clock to 0
```

If a legal progress-capable action is attempted and receives a legal response:

```text
5. record responder defensive engagement
6. reset responder advancement clock to 0
```

The actual final grade does not alter whether either engagement occurred.

## Gate consequences

This cadence amendment does not change the v0.3b gates.

It supplies the previously-missing trigger for them.

### Gate A

Repeated Top RESET while a progress route exists must eventually produce:

```text
Warning
then positional penalty / boundary initiative consequence
```

and must not retain Locked through timeout.

### Gate B

Repeated legal submission attempts against informed Turn-In:

```text
attacker advancement clock resets
defender advancement clock resets
stalling penalties = 0 for both
```

even when every result is Contested.

### Gate C

The same 20-second threshold and persistent-warning ladder applies independently to Top and Bottom.

### Gate D

One-step penalties stop at the Neutral boundary. At Loose/boundary, use the free initiative window rather than crossing Neutral.

### Gate E

This amendment adds no response commitment and no Recognition/information mechanic.

The existing Gate-B expiry flags must remain:

```text
response_commitment_present=False
recognition_present=False
```

## Interval-invariance requirement

The checker must include an interval-invariance regression.

For otherwise-identical stalling behavior, the first offense must occur at the same simulated-time threshold under at least:

```text
--interval 2
--interval 5
--interval 7
```

The number of windows may differ.

The offense threshold may not.

This is the same design principle used by the stamina remainder work: mechanics expressed in simulated time must not be exploitable by changing simulation granularity.

## Non-goals

This cadence amendment does not:

- add response commitment;
- add Recognition/information;
- change the provisional LOW=3 submission hold cost;
- change commitment costs;
- change submission grades;
- change setup progression;
- change stamina recovery;
- change the generic mutual-exhaustion cancellation;
- tune Gate B;
- create points-mode penalties;
- implement repeated-offense Position Reset from Section 33.

The only v0.3b ladder is:

```text
first offense -> persistent Warning
later offense -> one-step axis penalty
boundary later offense -> free initiative window
```

## Implementation authorization

With this amendment committed, v0.3b mechanics implementation may begin.

Do not alter this cadence based on the first batch result. If a gate fails, record the failed measurement before changing the rule.
