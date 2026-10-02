# Mount v0.1c — Behavior Stamina Economy and CONSERVE

## Status

Mount v0.1c adds continuous stamina upkeep/recovery to the normal-speed behavior layer while preserving frozen Mount-v0 positional resolution.

It also settles the three commitment questions that had to be decided before stamina recovery could be tuned.

## Behavior stamina policy

Default behavior economy:

```text
Top PRESSURE   -1 stamina / 5 simulated seconds
Top HOLD        0 stamina / 5 simulated seconds
Top CONSERVE   +2 stamina / 5 simulated seconds

Bottom ESCAPE  -1 stamina / 5 simulated seconds
Bottom PROTECT  0 stamina / 5 simulated seconds
Bottom CONSERVE +2 stamina / 5 simulated seconds
```

The rates are prototype tuning values.

The implementation uses fixed-point carry. Five 1-second windows therefore cost/recover exactly the same total stamina as one 5-second window.

## CONSERVE positional meaning

CONSERVE is not a new Mount-v0 positional formula.

For positional drift only:

```text
Top CONSERVE    projects to Top HOLD drift
Bottom CONSERVE projects to Bottom PROTECT drift
```

This keeps the original four frozen drift rates authoritative.

However, CONSERVE does **not** inherit the action-response modifier attached to HOLD or PROTECT.

Examples:

- Top CONSERVE does not get HOLD's -1 grade modifier against Bridge/Trap-and-Roll.
- Bottom CONSERVE does not get PROTECT's -1 grade modifier against Americana Arm Isolation.

This is the tradeoff:

> recover stamina, but give up active pressure/escape and the special defensive behavior modifier.

## Frozen-v0 compatibility path

`MountMatch.drift()` remains stamina-free.

`MountMatch.advance()` is the v0.1c path:

```text
frozen positional drift
→ behavior stamina upkeep/recovery
→ log both
```

The primary `bjj_game` CLI uses `advance()`.

The legacy `mount_v0` CLI uses `drift()` and does not expose CONSERVE.

## Commitment choice: standard play defaults MEDIUM

LOW still costs less than MEDIUM/HIGH while all three produce the same frozen Mount resolution.

That means LOW currently strictly dominates as a player choice.

Rather than present a fake tactical decision, standard v0.1c play no longer prompts for commitment each action.

Default:

```text
MEDIUM
```

Targeted testing can override it:

```bash
PYTHONPATH=src python -m bjj_game --commitment LOW
PYTHONPATH=src python -m bjj_game --commitment HIGH
```

`--check` explicitly reports the dominance debt.

Commitment effects remain deferred.

## Requested vs effective commitment

A requested commitment is not automatically available when stamina is low.

The effective commitment is the highest requested-or-lower level the fighter can fully pay for.

Default costs:

```text
LOW = 3
MEDIUM = 7
HIGH = 12
```

Examples:

```text
Stamina 100, request HIGH
→ effective HIGH
→ cost 12
```

```text
Stamina 5, request HIGH
→ effective LOW
→ cost 3
→ 2 stamina remains
```

```text
Stamina 0, request HIGH
→ effective UNFUNDED
→ cost 0
```

This prevents future HIGH effects from becoming free at zero stamina.

v0.1c still applies no grade/axis benefit from effective commitment; it only establishes the funding rule now so later tuning has a stable foundation.

Logs retain:

- requested commitment
- effective commitment
- requested cost
- effective cost
- funding gap
- charged stamina

## Commitment visibility

Commitment remains public information in v0.1c.

This is explicitly temporary.

The v0.2 recognition/feint information layer will decide when commitment is hidden, partially recognized, or revealed.

`--check` reports this as an information-layer debt so it is not forgotten.

## Responses

Responses still have no direct per-response stamina cost in v0.1c.

Continuous behavior upkeep is the first cost imposed on both competitors:

- active PRESSURE costs stamina
- active ESCAPE costs stamina
- passive HOLD/PROTECT preserve stamina
- CONSERVE recovers stamina at a positional/defensive tradeoff

Response commitment/cost can be revisited only if playtests show free responses remain exploitable after triggered initiative exists.

## Frozen enumerate gate

The frozen Mount-v0 enumerate output remains:

```text
SHA-256
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

CI now compares the actual digest to the expected digest and fails in a dedicated step if they differ.

The checker intentionally enumerates only the original v0 behavior set:

```text
Top: PRESSURE, HOLD
Bottom: ESCAPE, PROTECT
```

CONSERVE is a v0.1c extension layered around that frozen core.

## Next phase

The next natural slice is **v0.1d — STABILIZE**.

STABILIZE must be distinct from CONSERVE:

- STABILIZE protects/improves position
- STABILIZE does not restore stamina for free
- CONSERVE restores stamina but yields positional/defensive leverage
