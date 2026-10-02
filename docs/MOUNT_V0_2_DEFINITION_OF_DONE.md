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

- Ready must actually be reachable against best-counter play;
- at least one reachable Top Ready state must have no legal response that forces Failure-or-worse;
- at least one reachable Bottom Ready state must have no legal response that forces Failure-or-worse; and
- no reachable Ready state may make the attacker guaranteed to receive Success-or-better against every legal response.

This must be demonstrated by an exhaustive checker over the v0.2 builder path and legal-response set, not by constructing Ready state by hand.

### Measurement

The frozen `PERFECT-RESPONSE LOCK` diagnostic remains an unrestricted-v0 diagnostic.

Gate 1 uses a separate Ready-aware exhaustive probe. It first drives each setup to Ready while the responder always selects the legal best counter, then reports per side:

- reachable Ready states;
- lock-free Ready states;
- guaranteed-attacker Ready states.

PASS requires Ready reachability for both sides, at least one lock-free Ready state per side, and zero guaranteed-attacker Ready states.

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

The automatic checker first runs an exhaustive one-exchange differential with the initiator held fresh and only responder stamina changed from Fresh to Exhausted. This isolates responder-side effects from the existing initiator exhaustion rule.

When responder-side v0.2 mechanics exist, paired seeded batch confirmation should also be added for outcome/legality/response distributions.

## Gate 4 — Bridge has a setup role

### Current debt

Bridge is dominated by Trap-and-Roll in the current no-setup matrix and the escape-first batch policy never selects it.

### v0.2 is done when

Under at least one Ready/setup state, Bridge is selected by the scripted batch policy because it improves future setup/readiness, not because its frozen raw matchup grades were artificially buffed.

### Measurement

Batch summaries must expose setup-producing action counts and completed setup chains. At least one standardized v0.2 condition must record Bridge setup work that later contributes to a consumed Trap-and-Roll Ready chain.

## Gate 5 — Top is no longer passive after the opening

### Current debt

The v0.1 batch harness commonly produces about one Top positional attack per match because Strong/Locked offers no productive continuation.

### v0.2 is done when

In at least one standardized 100-stamina batch condition, Top averages more than 1.0 **follow-up** meaningful position/setup initiations per match after Top's first actual initiation.

The opening initiation is excluded from the metric. RESET does not count.

The metric should distinguish:

- opening initiation;
- follow-up positional attacks;
- setup-building actions;
- submission actions when v0.3 exists.

### Measurement

The follow-up numerator contains:

```text
Top follow-up positional attacks
+
Top follow-up setup-builder actions whose target is later consumed
```

A setup builder that creates Ready but is never followed through does not count toward Gate 5.

## Gate 6 — Exhausted Bottom escape reachability

### Current debt

Some v0.1 conditions remove every positive-weight Bottom escape route while Exhausted.

### v0.2 is done when

One of these is true:

A. at least one positive-weight Exhausted-Bottom escape route remains reachable under **every current Top behavior** (PRESSURE, HOLD, CONSERVE) in the standardized v0.2 Ready/setup condition; or
B. a behavior-specific complete lockout is deliberately retained and explicitly documented as an intended rule with a separate recovery/setup route that prevents a dead state.

This gate is intentionally not prescriptive about which outcome is correct, but one favorable behavior may not hide a lockout under another behavior.

### Measurement

The automatic checker reports positive-weight Exhausted-Bottom route counts separately for:

```text
Top PRESSURE
Top HOLD
Top CONSERVE
```

The PASS path requires every behavior count to be greater than zero. When Ready/setup state exists, extend the same per-behavior probe rather than collapsing the conditions.

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

- measure that LOW no longer strictly dominates because MEDIUM/HIGH has a strictly better outcome in at least one fully funded state (or LOW loses its strict cost advantage); or
- report an explicit versioned deferral.

The automatic probe currently compares final grade, terminal exit, and realized initiator-favorable axis movement. If v0.2 adds setup/readiness/recognition state, that outcome comparison must be extended to include it rather than manually flipping the gate.

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

## Automatic gate evaluation

`bjj_game --check` computes gate status from executable evidence.

The current evaluator uses:

```text
Gate 1  best-counter-reachable Ready states + lock-free/guaranteed checks
Gate 2  standardized RESET-lock probe
Gate 3  exhaustive fresh-vs-Exhausted responder exchange differential
Gate 4  Bridge setup work credited to completed Trap-and-Roll chains
Gate 5  Top follow-up position + completed-chain setup builds / match
Gate 6  positive-weight Exhausted-Bottom routes under every Top behavior
Gate 7  exhaustive funded LOW strict-dominance probe
```

The shared standard batch for Gates 4 and 5 is pinned to:

```text
100 matches
base seed 42
Top PRESSURE
Bottom ESCAPE
MEDIUM commitment
5:00 clock
starting axis +1.50
5-second interval
100 / 100 starting stamina
escape-first initiator policy
v0.2 setup/Ready enabled
```

Tests verify each printed status against its measurement formula. They do not assert a literal `[OPEN]` or `[PASS]` label.

When v0.2 adds Ready/setup/initiative state, the relevant measurement hook must be extended to consume that state; the gate is not manually flipped.

### Pre-v0.2 measured baseline

Before v0.2a, all seven gates were OPEN.

Notable pre-v0.2 values were:

```text
Gate 4  Bridge setup role                 OPEN — 0 setup selections
Gate 5  Top post-opening activity         OPEN — 0.110 follow-up position attacks/match
Gate 6  Exhausted Bottom escape routes    OPEN — PRESSURE:1, HOLD:0, CONSERVE:1
```

### Current measured state after v0.2a

The minimal Setup/Ready slice moves three gates automatically:

```text
Gate 1  Perfect-response lock             OPEN — Top 36 reachable / 6 lock-free / 0 guaranteed
                                                 Bottom 36 reachable / 36 lock-free / 24 guaranteed
Gate 2  RESET/stalling lock               OPEN
Gate 3  Responder stamina                 OPEN
Gate 4  Bridge setup role                 PASS — 590 Bridge builds credited to 295 completed Bottom chains
Gate 5  Top post-opening activity         PASS — 3.120 meaningful follow-ups/match
                                                 position 1.370, completed setup builds 1.750
Gate 6  Exhausted Bottom escape routes    OPEN — PRESSURE:1, HOLD:0, CONSERVE:1
Gate 7  Commitment meaning                OPEN
```

Gate 5 excludes the opening attack because the debt is specifically post-opening passivity. Gate 6 evaluates each Top behavior separately because the debt is a condition-specific exhausted lockout.

If a future completion criterion changes, change the criterion openly first and let the checker recompute the status. Do not hand-edit a gate label.

v0.2 is not complete until every required gate is PASS or an explicitly accepted DEFERRED state where this document allows deferral.

## Measurement integrity

Gate status must be derived from a metric, never from a hand-edited label.

A documentation-only decision may mark a gate DEFERRED only where this document explicitly allows deferral; a PASS requires executable evidence.

The current v0.2 checker evaluator is implemented in `diagnostics/checker.py` as typed gate measurements containing:

- gate number
- gate name
- status
- metric
- evidence

Rendering happens after measurement.
