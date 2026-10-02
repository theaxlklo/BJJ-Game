# Mount v0.2 — Definition of Done

## Status

v0.1 is closed.

v0.2 begins only against explicit debts already demonstrated by the frozen Mount-v0 rules and the v0.1 playtest/batch harness.

The purpose of this document is to prevent v0.2 from being considered complete merely because setup/Ready/initiative code exists.

Every debt below must either:

1. pass its measurable completion condition, or
2. be explicitly deferred in a later accepted design decision with the checker still reporting that deferral.

The frozen Mount-v0 enumerate digest remains authoritative and must stay byte-identical unless a separate versioned ruleset intentionally replaces it.

## Gate 1 — Perfect-response lock

### Current debt

With unrestricted full information, every initiated action has a legal response that holds it to Failure or worse.

### v0.2 is done when

With v0.2 setup/Ready/initiative legality enabled:

- at least one Top action can be Ready in a state where no currently legal response forces Failure-or-worse; and
- at least one Bottom action can be Ready in a state where no currently legal response forces Failure-or-worse.

This must be demonstrated by an exhaustive checker over the v0.2 legal-response set, not by hiding the action from the checker.

### Measurement

The current `PERFECT-RESPONSE LOCK` diagnostic becomes a v0.2 Ready-aware probe and reports Top and Bottom separately.

## Gate 2 — RESET / stalling lock

### Current debt

Top PRESSURE + repeated RESET against Bottom ESCAPE + repeated RESET reaches Locked and times out with Mount retained.

### v0.2 is done when

The standardized RESET-lock probe no longer has a guaranteed Locked-timeout path under the v0.2 progress / initiative / stalling rules.

The replacement rule must not simply remove RESET; passing remains a legitimate BJJ choice.

### Measurement

Reuse the current RESET-lock probe with v0.2 progress state enabled and report the terminal result plus any stalling/progress intervention.

## Gate 3 — Responder stamina

### Current debt

Exhaustion penalizes initiated actions, while responders defend at full strength and pay no direct response cost.

The 25-stamina matrix showed this asymmetry affects Bottom much more strongly than Top.

### v0.2 is done when

At least one controlled batch condition produces a measurable disadvantage for an Exhausted responder compared with the otherwise-identical non-Exhausted responder.

No specific mechanic is mandated: response cost, response legality, setup loss, recognition loss, or another v0.2 system may create the effect.

### Measurement

Run paired seeded batches with identical state except responder exhaustion and report the changed outcome/legality/response distribution.

## Gate 4 — Bridge has a setup role

### Current debt

Bridge is dominated by Trap-and-Roll in the current no-setup matrix and the escape-first batch policy never selects it.

### v0.2 is done when

Under at least one Ready/setup state, Bridge is selected by the scripted batch policy because it improves future setup/readiness, not because its frozen raw matchup grades were artificially buffed.

### Measurement

Batch summaries must expose setup-producing action counts. At least one standardized v0.2 condition must record Bridge usage above zero for setup value.

## Gate 5 — Top is no longer passive after the opening

### Current debt

The v0.1 batch harness commonly produces about one Top positional attack per match because Strong/Locked offers no productive continuation.

### v0.2 is done when

In at least one standardized 100-stamina batch condition, Top averages more than 1.0 meaningful position/setup initiations per match before terminal state.

RESET does not count.

The metric should distinguish:

- positional attacks;
- setup-building actions;
- submission actions when v0.3 exists.

### Measurement

Batch summary: total Top meaningful initiations / matches.

## Gate 6 — Exhausted Bottom escape reachability

### Current debt

Some v0.1 conditions remove every positive-weight Bottom escape route while Exhausted.

### v0.2 is done when

One of these is true:

A. at least one Exhausted-Bottom escape route remains reachable in a standardized v0.2 Ready/setup condition; or
B. complete lockout is deliberately retained and explicitly documented as an intended rule with a separate recovery/setup route that prevents a dead state.

This gate is intentionally not prescriptive about which outcome is correct.

### Measurement

Extend the current Exhausted-reachability report to include v0.2 Ready/setup state and show whether each Exit Map destination is reachable.

## Gate 7 — Commitment meaning

### Current debt

LOW/MEDIUM/HIGH currently change cost only, so LOW strictly dominates whenever outcome effects are off.

### v0.2 is done when

One of these is explicitly true:

A. effective commitment changes a v0.2 outcome-relevant quantity such as setup speed, readiness, initiative, recognition, or action effect; or
B. commitment outcome effects are explicitly deferred again, with LOW dominance still reported as an accepted debt.

Requested commitment may never grant an effect the effective commitment cannot fund.

### Measurement

The current commitment-dominance checker must either:

- stop reporting strict LOW dominance because a tested effect exists; or
- report an explicit versioned deferral.

## Standard verification discipline

Every v0.2 mechanics change must preserve these existing gates unless the versioned design explicitly says otherwise:

```text
python -m unittest discover -s tests -v
python -m bjj_game --check
python -m mount_v0 --check
frozen --enumerate SHA-256
```

The current frozen digest is:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

## Current baseline

Before any v0.2 mechanics are implemented:

```text
Gate 1  Perfect-response lock             OPEN
Gate 2  RESET/stalling lock               OPEN
Gate 3  Responder stamina                 OPEN
Gate 4  Bridge setup role                 OPEN
Gate 5  Top post-opening activity         OPEN
Gate 6  Exhausted Bottom escape routes    OPEN / design choice unresolved
Gate 7  Commitment meaning                OPEN / explicit deferral allowed
```

v0.2 is not complete until every gate is either PASS or an explicitly accepted DEFERRED state where this document allows deferral.
