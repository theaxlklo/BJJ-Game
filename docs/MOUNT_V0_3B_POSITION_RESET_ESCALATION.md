# Mount v0.3b — Position Reset Escalation Amendment

## Status

FROZEN BEFORE ESCALATION IMPLEMENTATION.

This amendment follows the corrected full-match Gate-A failure recorded in:

`docs/MOUNT_V0_3B_FULL_MATCH_STALLING_FAILURE.md`.

It completes the next consequence already named in v9 Section 33 rather than tuning the 20-second cadence or enlarging the first axis penalty until Gate A happens to pass.

## Source

v9 Section 33 records the escalation concept:

```text
Warning
-> penalty consequence
-> Second major offense: Position Reset
-> Further escalation
```

and later:

```text
Repeated offense may cause:
Position Reset
```

v0.3b now freezes that unfinished rung for Mount-only play.

## Offense ladder

The 20-second per-player advancement clock is unchanged.

For each player independently:

```text
offense 1
-> persistent Warning

offense 2
-> one visible-band positional penalty
   or the existing free-initiative boundary consequence

offense 3
-> Position Reset

offense 4+
-> repeat Position Reset
```

Every adjudicated offense resets that player's advancement clock to 0.

The Warning remains set for the rest of the match.

Engagement still resets the clock without erasing the Warning or offense history.

## Position Reset value

Mount-v0 Position Reset uses the canonical Mount starting control value:

```text
axis = +1.50
band = Stable
```

This is the existing `DEFAULT_AXIS`, not a newly tuned number.

The reset is not expressed as a numeric subtraction and is not derived from the offender's current axis.

## Time and initiative semantics

Position Reset is processed during the offender's RESET decision.

It:

- costs 0 additional simulated seconds;
- does not itself advance either advancement clock;
- preserves the normal RESET handoff of initiative to the opponent;
- does not create an extra free-initiative window on top of that ordinary handoff.

The next ordinary decision still follows the normal simulation interval unless another rule explicitly grants a free initiative window.

## State preserved by Position Reset

The Mount-only position reset changes only persisted Mount control:

```text
axis
visible band
```

It does **not** reset:

- stamina;
- exhaustion latch;
- behavior selection;
- setup tiers;
- Americana submission stage;
- submission-hold stamina history;
- the persistent stalling Warning;
- prior offense count;
- the match clock.

This is deliberate.

Americana is not modeled as inherently Mount-exclusive. Resetting Mount control must not encode a false rule that an Americana threat can exist only in Mount.

Future multi-position work may define a broader positional transition consequence; v0.3b does not.

## First positional penalty remains a visible-band penalty

Offense 2 keeps the existing one-visible-band rule.

The numeric axis change therefore depends on the offender's current location within the band.

Example:

```text
+4.00 Locked -> +2.80 Strong = -1.20
+3.21 Locked -> +2.80 Strong = -0.41
```

That is explicitly documented as band-based, not a fixed axis cost.

No numeric penalty magnitude is added.

## Neutral boundary rule remains

The offense-2 positional penalty still may not cross Neutral.

At the existing Loose/boundary case, the non-stalling player receives the frozen zero-time free initiative window.

The new Position Reset consequence is a later escalation rung and does not alter that offense-2 boundary rule.

## Why escalation is needed

The corrected full-match probe measured:

```text
Warning=1
one-band penalties=13
final axis=+4.00
final band=Locked
locked_timeout=True
```

PRESSURE / ESCAPE drift adds:

```text
+0.10 axis / second
```

so a one-band drop from:

```text
+4.00 -> +2.80
```

can re-enter Locked after approximately 4 seconds, far sooner than the next 20-second offense.

Position Reset to +1.50 creates the stronger, already-designed escalation needed after the first positional penalty.

## Gate A measurement

Gate A must continue to run through the full 5:00 match.

It may not stop after:

- Warning;
- first positional penalty;
- first Position Reset.

PASS requires the completed match to show that deliberate Top RESET with a persistent progress route does **not** finish:

```text
TIMEOUT — Mount retained
final band Locked
```

The checker must report at least:

- Warning count;
- offense-2 positional penalty count;
- Position Reset count;
- final axis;
- final band;
- timeout status;
- Locked decision-window count / total decision windows.

## Gate 2

v0.2 Gate 2 may return to PASS only if the corrected full-match Gate-A evidence passes.

A temporary early-match Strong band is not sufficient.

## Normal-play guard

The stronger escalation must remain absent from already-engaged standard play.

The checker/test surface must pin the matched standard PRESSURE / ESCAPE batches to:

```text
Top warnings=0
Bottom warnings=0
Top positional penalties=0
Bottom positional penalties=0
Top Position Resets=0
Bottom Position Resets=0
```

for both random and informed responder probes unless future mechanics intentionally change the engagement model.

This guard is executable but is not a new lettered DoD gate.

Its purpose is to prevent stronger consequences from leaking into normal engaged play.

## Existing gates

The escalation must preserve:

```text
v0.3b Gate B:
stalemated attacker/defender remain engaged

v0.3b Gate C:
both sides can receive stalling consequences

v0.3b Gate D:
offense-2 axis penalty cannot cross Neutral

v0.3b Gate E:
response_commitment_present=False
recognition_present=False
v0.3a Gate B remains DEFERRED
```

## Non-goals

This amendment does not:

- change the 20-second threshold;
- count windows instead of simulated time;
- add response commitment;
- add Recognition/information;
- change stamina costs;
- change exhaustion effects;
- change the provisional LOW=3 submission-hold cost;
- change matchup grades or response weights;
- tune the setup-policy debt;
- add a new submission;
- clear submission state on Position Reset.

## Change-control rule

If the full-match probe remains Locked at timeout after this exact escalation:

1. record the failed measurement;
2. do not change the 20-second threshold post-hoc;
3. do not increase the one-band penalty post-hoc;
4. return to design review before another mechanics change.
