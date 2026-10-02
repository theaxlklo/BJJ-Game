# Mount v0.3b — Gate A Steady-State Measurement Amendment

## Status

FROZEN BEFORE CHECKER IMPLEMENTATION.

This amendment replaces the timeout-band sample used by the prior Gate-A closure measurement.

No stalling mechanics change in this amendment.

## Why the previous Gate-A measurement is insufficient

The full 5:00 probe removed the original 40-second false positive, but it still judged Gate A from the band at one terminal instant.

That terminal sample can depend on phase alignment between:

- the 20-second stalling offense cycle;
- behavior drift;
- the match duration;
- the decision interval.

A deliberate staller can therefore be outside Locked at one timeout and back in Locked at another timeout even though the underlying long-run behavior is similar.

Gate A is about whether Locked remains a **steady state under deliberate stalling**, not whether one selected timeout lands inside or outside Locked.

## Authoritative Gate-A interpretation

Gate A now measures two steady-state properties:

1. **Locked occupancy share**
2. **Longest uninterrupted Locked dwell**

The final band at timeout remains diagnostic only.

It is no longer a PASS criterion.

## Frozen sweep

Gate A uses the following deterministic sweep:

```text
interval_seconds:
  5
  7

match_length_seconds:
  240, 245, 250, ..., 300
```

That is:

```text
2 intervals × 13 match lengths = 26 cases
```

Every case uses the same one-sided ownership semantics already frozen for Gate A:

- Top starts in dominant Mount with a real progress-capable Americana route;
- Top deliberately RESETs on its own eligible initiation opportunities;
- Bottom's intervening initiation is suppressed so defensive engagement cannot reset Top's advancement clock and confound ownership;
- normal simulated-time drift remains active.

## Metric 1 — Locked decision-window share

For each sweep case:

```text
Locked share =
  decision windows observed in Locked
  /
  total observed decision windows
```

Frozen threshold:

```text
Locked share < 0.50
```

This threshold is not derived from the current measured 24/59 or 9/40 examples.

It encodes the requirement:

> Locked may be revisited transiently, but it may not be the majority steady state while the favored player deliberately stalls.

Exactly 50% does not pass.

## Metric 2 — longest uninterrupted Locked dwell

For each sweep case, measure the longest continuous span of simulated game time for which the persisted visible band remains Locked.

Frozen threshold:

```text
longest Locked dwell < 20 simulated seconds
```

The threshold is the already-frozen advancement period.

A continuous Locked run lasting a full stalling period would mean the system permits the offender to preserve the strongest control state for an entire offense cycle despite continued deliberate inactivity.

Exactly 20 seconds does not pass.

The dwell metric is expressed in simulated seconds, not number of windows, so it does not become a window-count rule.

## Gate A PASS formula

Every one of the 26 sweep cases must satisfy:

```text
Warning count >= 1
one-band penalty count >= 1
Position Reset count >= 1

Locked share < 0.50

longest uninterrupted Locked dwell < 20s
```

PASS is all-cases, not average-of-cases.

A single failing interval/length combination keeps Gate A OPEN.

## Gate 2 dependency

v0.2 Gate 2 may remain PASS only when the revised Gate A passes this entire fixed sweep.

Gate 2 must no longer depend on:

- final band at one timeout;
- one selected 5:00 match;
- one selected interval.

The historical timeout result remains visible only as diagnostic evidence.

## Final-band diagnostics

The checker should continue to expose how many sweep cases end in Locked.

This is observational.

A case ending in Locked does **not** fail Gate A by itself if both steady-state thresholds pass.

This deliberately removes phase luck from the gate.

## Normal-play guard

The existing normal-play guard remains unchanged and required:

```text
random standard batch:
  warnings=0/0
  one-band penalties=0/0
  Position Resets=0/0

informed standard batch:
  warnings=0/0
  one-band penalties=0/0
  Position Resets=0/0
```

## Stall-versus-active-Bottom observation

v0.3b will additionally report a non-gating outcome probe:

```text
Top:
  deliberately RESET whenever given an initiation window

Bottom:
  normal escape-first policy

responses:
  normal random response mix

matches:
  100 matched seeds
```

At minimum report:

- timeout / Mount-retained count;
- escape count;
- stalling warnings;
- one-band penalties;
- Position Resets.

This probe is **observational only**.

v0 does not yet define whether:

```text
TIMEOUT — Mount retained
```

is a win, draw, or loss across rulesets.

Points-mode consequences belong to the later scoring/ruleset layer described by Section 33.

Therefore this observation must not be used to retune the v0.3b stalling mechanics.

## Change-control rule

If the fixed Gate-A sweep fails:

1. record the failed cases and metrics;
2. do not move either threshold;
3. do not remove interval 7 or inconvenient match lengths;
4. do not alter the 20-second cadence post-hoc;
5. return to design review before another mechanics change.
