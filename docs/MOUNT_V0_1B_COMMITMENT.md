# Mount v0.1b — Commitment and Stamina Costs

## Status

Mount v0.1b adds explicit commitment and stamina cost accounting around the frozen Mount-v0 resolution engine.

It does **not** change the Mount matchup matrix, grade math, drift, hysteresis, clamps, escape threshold, Exit Maps, or checker output.

## Commitment

Every initiated action in the primary `bjj_game` flow now carries one of:

```text
LOW
MEDIUM
HIGH
```

The commitment is represented by an `ActionAttempt`:

```text
ActionAttempt
├── initiator
├── action_id
└── commitment
```

The responder does not choose a commitment in v0.1b. Response effort/cost is intentionally deferred so this slice tests one new variable at a time.

## Prototype cost policy

The default `StaminaCostPolicy` is:

```text
LOW       3
MEDIUM    7
HIGH     12
```

These are prototype tuning values, not final BJJ truths.

The cost policy is separate from:

- `TechniqueEntity`
- `MatchupTable`
- `MountRuleSet`
- `MountResolutionEngine`

and is injected into `MountMatch`.

This means cost tuning cannot silently alter the 18 hand-authored BJJ grades.

## Resolution effect

LOW, MEDIUM, and HIGH all resolve through the **same frozen Mount-v0 mechanics**. Commitment changes only the stamina request.

There is currently:

- no commitment grade modifier
- no commitment axis modifier
- no commitment legality bonus
- no technique-specific stamina multiplier
- no exhaustion penalty

This is deliberate.

## Stamina transaction

The initiator's `StaminaPool` receives a request from the cost policy.

The transaction records:

```text
before
requested
charged
shortfall
after
```

If enough stamina exists:

```text
before = 100
MEDIUM request = 7
charged = 7
shortfall = 0
after = 93
```

If the pool cannot fully pay:

```text
before = 5
HIGH request = 12
charged = 5
shortfall = 7
after = 0
```

The action still resolves normally in v0.1b.

This temporary shortfall behavior exists because recovery, CONSERVE, lockouts, and exhaustion consequences have not been implemented yet. Blocking actions at zero stamina now would create dead-end matches before the system contains any way to recover.

A later v0.1 slice may turn shortfall into a legality or resolution consequence.

## Ordering

For a valid attempt:

```text
choose initiated action
→ choose commitment
→ responder chooses response
→ validate frozen Mount resolution
→ charge initiator stamina
→ apply unchanged Mount resolution
→ log stamina transaction
```

Validation occurs before stamina is spent. An invalid action/response request therefore spends nothing.

## Compatibility

`MountMatch.decide()` remains the frozen v0 decision path and spends no stamina.

`MountMatch.attempt()` is the v0.1b path and charges stamina.

The primary command:

```bash
PYTHONPATH=src python -m bjj_game
```

uses `attempt()` and prompts for commitment.

The legacy command:

```bash
PYTHONPATH=src python -m mount_v0
```

uses the old prompt sequence and `decide()`, with no commitment prompt and no stamina cost.

## Logging

Each v0.1b attempt prints:

```text
COMMITMENT / STAMINA
Commitment: MEDIUM
Stamina before: 100
Requested cost: 7
Charged: 7
Shortfall: 0
Stamina after: 93
Commitment resolution effect: None (v0.1b)
```

Run summaries also retain:

- commitment initiator history
- commitment history
- stamina requested history
- stamina charged history
- stamina shortfall history

The explicit initiator history is retained even though v0 alternates initiative, because v0.2 will not.

## Frozen-v0 identity gate

The exact frozen `--enumerate` bytes remain protected by:

```text
SHA-256
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

v0.1b must continue producing that exact digest.

Tests also require LOW, MEDIUM, and HIGH versions of the same exchange to produce identical `ResolutionResult` objects.

## Floor-clamp naming cleanup

The generic result field is now:

```text
floor_clamp_used
```

rather than `bridge_clamp_used`.

The old `bridge_clamp_used` name remains a read-only compatibility alias for Mount-v0 callers.

New logs use the generic label `Floor clamp used?`.

## Not in v0.1b

Do not add yet:

- stamina recovery
- CONSERVE
- STABILIZE
- response stamina costs
- technique-specific stamina costs
- commitment bonuses/penalties
- exhaustion grade penalties
- commitment lockouts
- zero-stamina action lockouts

## Next phase

The natural next slice is **v0.1c: CONSERVE + stamina recovery**.

That gives a fighter a real way to trade positional ambition for energy before any exhaustion penalties or commitment restrictions are introduced.


## v0.1c funding update

v0.1c supersedes the temporary partial-charge shortfall rule documented above.

Requested commitment now downgrades to the highest fully payable commitment:

```text
request HIGH with 5 stamina
→ effective LOW
→ charge 3
→ 2 stamina remains
```

At less than LOW's cost, effective commitment is `UNFUNDED` and no action stamina is charged.

The frozen Mount resolution is still unchanged. See `MOUNT_V0_1C_CONSERVE.md`.
