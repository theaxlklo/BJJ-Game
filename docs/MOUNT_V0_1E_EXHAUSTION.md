# Mount v0.1e — Exhaustion Consequences

## Status

Mount v0.1e is implemented before v0.1d on purpose.

The reason is simple: STABILIZE cannot be judged against PRESSURE, HOLD, PROTECT, ESCAPE, or CONSERVE until low stamina has an actual consequence.

v0.1d remains reserved for the STABILIZE distinction and will be implemented after the first exhaustion playtests.

## Minimal exhaustion rule

The only new mechanical consequence is:

```text
Initiator starts the action in Exhausted stamina band
→ final initiated-action grade shifts down one grade
```

Stamina bands remain:

```text
76–100  Fresh
51–75   Working
26–50   Tired
0–25    Exhausted
```

Fresh, Working, and Tired have no grade penalty in v0.1e.

## Exact ordering

The Exhausted check is made at the **start of the initiated action**, after normal-speed behavior stamina has already been processed for that decision window and before the action's commitment cost is charged.

Therefore:

```text
Start action at 30 stamina
MEDIUM costs 7
→ action resolves with no exhaustion penalty
→ stamina becomes 23
→ next initiated action starts Exhausted and gets -1 grade
```

This avoids retroactively weakening an action because its own cost pushed the fighter across the threshold.

## Resolution boundary

The frozen Mount-v0 engine still knows nothing about stamina.

`MountResolutionEngine.resolve_action()` now accepts a generic optional:

```text
external_grade_modifier = 0
```

The frozen path always uses zero.

The v0.1e match layer computes:

```text
Exhausted → -1
otherwise → 0
```

and passes that generic modifier only for `attempt()`.

Ordering for v0.1e attempts is:

```text
raw matchup
→ behavior modifier
→ positional modifier
→ exhaustion/external modifier
→ grade clamp
→ unchanged axis / clamp / escape / Exit Map logic
```

The v0 enumerate path uses an external modifier of zero and remains byte-identical.

## Compatibility

`MountMatch.decide()` remains the frozen v0 path:

- no commitment cost
- no behavior stamina cost
- no exhaustion penalty

`MountMatch.attempt()` is the modern v0.1 path:

- requested/effective commitment
- action stamina cost
- exhaustion consequence
- unchanged Mount-v0 lookup data

`mount_v0` continues to use the legacy path.

## Commitment funding

Requested and effective commitment remain separate.

Example:

```text
Request HIGH at 5 stamina
→ effective LOW
→ charge 3
→ requested/effective funding gap = 9
```

Because 5 stamina is already Exhausted, that action also gets the -1 exhaustion grade modifier.

At 0 stamina:

```text
Request HIGH
→ effective UNFUNDED
→ action cost 0
→ exhaustion modifier -1
```

This prevents HIGH from becoming a free full-effort attack while still allowing the prototype to continue before zero-stamina lockouts are designed.

## Pacing diagnostics

`bjj_game --check` now reports exact current pacing for always-active PRESSURE/ESCAPE under the temporary alternating-initiative scaffold.

Starting stamina: 100.

Current default costs:

```text
LOW = 3
MEDIUM = 7
HIGH = 12
active behavior upkeep = 1 / 5s
```

Projected entry into Exhausted:

```text
LOW:
Top 2:30
Bottom 2:30

MEDIUM:
Top 1:25
Bottom 1:30

HIGH:
Top 0:55
Bottom 1:00
```

Projected zero stamina:

```text
LOW:
Top 3:20
Bottom 3:20

MEDIUM:
Top 1:55
Bottom 1:55

HIGH:
Top 1:20
Bottom 1:20
```

These numbers are diagnostics, not tuning approval.

Do not retune 3/7/12 or the behavior rates until exhaustion playtests show whether the pacing feels too fast in actual play.

## CONSERVE / HOLD / PROTECT tuning watch

v0.1e intentionally does not yet change the v0.1c rates:

```text
PRESSURE / ESCAPE  -1 / 5s
HOLD / PROTECT      0 / 5s
CONSERVE           +2 / 5s
```

Now that Exhausted actions are penalized, playtests can finally tell us whether:

- CONSERVE dominates PROTECT
- CONSERVE dominates HOLD
- HOLD/PROTECT need a small recovery
- CONSERVE needs worse positional drift
- the default MEDIUM stamina pace is too fast

Those decisions should use logs rather than static speculation.

## Fixed-point carry logging

Behavior stamina is continuous even though the visible pool is integer-valued.

The logger now always prints fixed-point carry.

Example:

```text
4s PRESSURE
carry +0 → -4/5

then 4s CONSERVE
carry -4 → +4/5
```

The integer stamina value may be unchanged in the second window, but `+4/5` shows the stored +0.8 stamina balance.

This prevents a playtester from mistaking mathematically correct carried remainder for a recovery bug.

## Frozen-v0 identity gate

The frozen enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

CI compares the actual digest against that exact value and fails on mismatch.

## Next step

Do **not** implement STABILIZE immediately after this file lands.

First run targeted v0.1e playtests:

1. default MEDIUM with PRESSURE vs ESCAPE
2. deliberate CONSERVE cycles from both sides
3. HOLD vs CONSERVE
4. PROTECT vs CONSERVE
5. one run beginning near the 25/26 stamina boundary
6. one all-LOW and one all-HIGH run

Use those logs to decide pacing and whether CONSERVE needs a positional or recovery adjustment.

Then implement **v0.1d — STABILIZE** against an economy whose consequences have actually been observed.
