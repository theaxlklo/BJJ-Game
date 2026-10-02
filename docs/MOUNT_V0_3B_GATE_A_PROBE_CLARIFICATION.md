# Mount v0.3b — Gate A One-Sided Probe Clarification

> **FULL-MATCH CLARIFICATION:** Gate A must run this isolated ownership probe through the entire 5:00 match. Stopping immediately after the first positional penalty is insufficient. The authoritative corrected evidence and escalation are recorded in `MOUNT_V0_3B_FULL_MATCH_STALLING_FAILURE.md` and `MOUNT_V0_3B_POSITION_RESET_FINAL_MEASUREMENT.md`.

## Status

FROZEN BEFORE v0.3b CHECKER IMPLEMENTATION.

The stalling mechanic itself is unchanged.

This note clarifies how Gate A isolates one competitor's advancement obligation.

## Why a normal alternating full-match probe is confounded

v0.3b deliberately counts legal defensive response as engagement.

Therefore:

```text
Bottom initiates a real progress attempt
Top responds legally
-> Top defensive engagement
-> Top advancement clock resets to 0
```

A probe that says:

```text
Top RESETs every own turn
Bottom attacks normally every Bottom turn
```

does **not** isolate Top stalling.

Top is repeatedly engaged as a defender between RESETs, so resetting Top's clock is the correct rule.

Using that probe to demand a Top penalty would contradict the frozen defensive-engagement semantics.

## Gate A probe is one-sided

Gate A therefore uses an isolated sequence of **Top initiation opportunities**.

The probe:

1. starts Top in dominant Mount with a real progress-capable submission route;
2. advances simulated time between Top opportunities using the normal 20-second clock;
3. gives Top repeated initiation opportunities;
4. Top deliberately chooses RESET whenever the route exists;
5. Bottom does not receive intervening initiation windows in this isolated ownership probe;
6. no Bottom stalling status is adjudicated in this probe.

This is analogous to the isolated submission/exhaustion probes already used elsewhere: it measures one mechanic without introducing an unrelated competing action.

## Gate A closure

PASS requires the Top-only sequence to produce:

```text
first offense -> Warning
later offense -> one-band penalty toward Bottom
```

and therefore make unchanged Locked retention impossible.

Gate C remains the separate symmetry proof that the exact same tracker/cadence/consequence can penalize Bottom.

The historical full alternating RESET-lock probe remains visible as an observation, but Gate 2 closure is based on the isolated one-sided stalling evidence because that evidence has unambiguous ownership.
