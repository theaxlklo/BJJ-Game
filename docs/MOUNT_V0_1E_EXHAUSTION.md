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

Stamina uses a 25/35 hysteresis boundary for Exhausted:

```text
enter Exhausted: <=25
remain Exhausted while recovering: 26..34
leave Exhausted: >=35
```

A newly initialized pool at 26+ starts outside Exhausted. Once a competitor has crossed into Exhausted, however, recovery must reach 35 before the penalty clears.

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

## Boundary exploit fix

The original 25/26 stateless cutoff created a mechanical exploit:

```text
24 stamina
→ CONSERVE one 5s window
→ 26 stamina
→ immediately avoid exhaustion penalty
```

That loop was confirmed against the implementation.

The 25/35 hysteresis removes it:

```text
24
→ CONSERVE to 26
→ still Exhausted
→ no penalty relief until 35
```

This mirrors the existing Mount-axis hysteresis idea: entering a bad state and leaving it use different thresholds.

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

## Exhausted exit reachability

The primary `--check` path now runs a separate exhausted-initiator reachability pass without changing frozen `--enumerate`.

Current consequences include:

```text
Elbow-Knee Escape, exhausted:
Open Guard → unreachable
Half Guard → +0.10..+1.10

Trap-and-Roll, exhausted:
Top PRESSURE → Reversal +0.10..+1.10
Top HOLD → Reversal unreachable
```

This makes the positional + exhaustion stack visible instead of hiding it inside individual playtests.

## v0.2 responder-stamina debt

Exhaustion still affects initiated actions only.

An exhausted responder currently:

- defends at full grade
- pays no direct response stamina cost

Alternating initiative makes that tolerable in the current scaffold, but triggered initiative in v0.2 could let an exhausted player stay reactive indefinitely.

That is now reported by `bjj_game --check` as a v0.2 design debt and must be revisited with triggered initiative.

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

## Forced-action recovery deadlock

After the 25/35 hysteresis fix, a larger structural issue remained in the fixed alternating scaffold.

Pure CONSERVE restores:

```text
+4 stamina per 10-second initiative cycle
```

Nominal action-cycle balance is therefore:

```text
LOW    +4 - 3  = +1
MEDIUM +4 - 7  = -3
HIGH   +4 - 12 = -8
```

Under forced MEDIUM or HIGH attacks, an Exhausted competitor cannot climb from the recovery band to 35 while fully funding every scheduled action.

This is not treated as a recovery-number problem. It comes from the v0 scaffold forcing a technique every scheduled decision window.

The broader frozen design is event-driven: a player may maintain/change broad behavior without necessarily initiating a technique every window.

### RESET / NO ACTION

The modern v0.1 flow now allows:

```text
RESET / NO ACTION
```

Effect:

- no initiated technique
- no response prompt
- no action stamina cost
- no immediate axis change
- no extra simulated-second cost inside the paused decision window
- initiative yields to the opponent
- another normal-speed interval occurs before the next decision window

The opportunity cost is the lost attack opportunity plus the positional drift/time that occurs before the next chance.

With both competitors at 25 stamina, both using CONSERVE and RESET on every initiative:

```text
25 → 27 → 29 → 31 → 33 → 35
```

Both clear Exhausted after 25 simulated seconds.

This makes recovery structurally possible without changing the temporary 3/7/12 action costs or +2/5s CONSERVE rate.

### Stalling debt

RESET is intentionally available outside Exhausted too, because the long-term design does not require a technique every decision window.

However, repeated RESET can be used to burn clock without progress in the current prototype.

That is not solved inside v0.1e. The frozen design already contains progress-based stalling rules, so `bjj_game --check` now reports RESET/stalling as an explicit future debt.

## Perfect-response lock and blind playtests

Adding RESET exposed another v0 scaffold artifact more strongly: with full information, every initiated action has a Failure-or-worse unrestricted best response, while RESET has no immediate resolution risk.

The checker now includes an explicit always-RESET probe:

```text
Top PRESSURE + RESET
vs
Bottom ESCAPE + RESET

→ TIMEOUT — Mount retained
→ final axis +4.00
→ Locked
→ Top stamina 40
→ Bottom stamina 40
```

This confirms that standard full-information hot-seat play is a bad environment for judging RESET frequency.

### --blind

For the v0.1e playtests only:

```bash
PYTHONPATH=src python -m bjj_game --blind
```

Blind sequence:

```text
normal-speed drift
→ responder secretly locks response
→ initiator chooses action or RESET
→ if action: frozen resolver uses the locked response
→ if RESET: locked response is unused
```

The hidden response entry is not echoed to the other hot-seat player.

`--blind` changes no:

- matchup grade
- behavior modifier
- positional modifier
- stamina rule
- Exit Map
- action/response legality

It is an information-order testing harness only.

The legacy `mount_v0` entry point rejects `--blind`.

The eventual v0.2 recognition/feint/setup layer remains responsible for the actual information model.

### Seeded solo responder

A single tester cannot be blind to a response they personally typed. Solo sessions therefore use:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed N \
  --log docs/playtest/<session>.txt
```

The responder policy is deterministic:

```text
Bottom response to Top:
Forearm Frame 4/7
Tight-Elbow Arm Defense 3/7
Turn-In Recovery 0/7

Top response to Bottom:
Wide Mount Base 2/3
Hip Follow and Knee Re-Pummel 1/3
Hand Post and Base 0/3
```

The implementation uses integer weighted draws rather than rounded floating-point percentages.

The seed is printed at run start. Each random response records its ordinal, canonical response name, and raw draw only after the initiator has selected an action or RESET. A RESET records the locked response as unused.

That makes a saved log replayable without leaking the hidden choice during the decision.

### Fixed behavior experiments

Solo blind play still leaves behavior choice under the tester's control. To isolate behavior questions, the modern CLI now accepts:

```text
--top-behavior PRESSURE|HOLD|CONSERVE
--bottom-behavior ESCAPE|PROTECT|CONSERVE
```

Example:

```bash
PYTHONPATH=src python -m bjj_game \
  --blind \
  --blind-responder random \
  --seed 42 \
  --top-behavior HOLD \
  --bottom-behavior CONSERVE \
  --log docs/playtest/hold-vs-conserve-seed-42.txt
```

With both flags supplied, the experimental condition stays fixed for the whole match. The human tester chooses only action versus RESET and which action to attempt; the hidden response comes from the seeded policy.

This is preferred over a scripted opponent for v0.1e because it adds no new attack/RESET strategy model that could contaminate the behavior comparison.

### Per-band seeded-mix report

`--check` now reports, for every side / visible band / action:

1. expected attacker-favorable proposed axis delta against the fixed response mix, after current behavior/positional modifiers;
2. escape probability as a min/max over the existing 0.01 legal-axis grid.

Those values remain separate from the MEDIUM stamina cost.

No conversion weight is assigned between:

- one axis point
- one stamina point
- an escape

so the checker reports evidence rather than selecting an overall best action.

The report also exposes a correction to the raw simultaneous-game shorthand: **Top initiating from Loose receives the frozen -1 positional modifier**, so the raw response mix is not an equilibrium there in the same sense as Stable.

### Clamp-aware axis report

The per-band report now keeps both the pre-clamp and realized signals visible:

```text
raw attacker-axis
realized-axis min..max
escape min..max
MEDIUM stamina cost shown separately
```

`realized-axis` is calculated across every legal 0.01 axis value in the visible band using the actual floor/cap resolver. This prevents edge-band predictions from treating a nominal -2 grade as a full -2 axis loss when the Mount floor stops it at +0.10, or from treating a +2 grade as full upside when the +4.00 cap absorbs it.

Escape crossings keep their crossing axis in the realized-axis calculation; escape probability remains a separate column, so no terminal-value conversion is invented.

### Deterministic batch statistics

For fixed-condition statistics:

```bash
PYTHONPATH=src python -m bjj_game \
  --batch 1000 \
  --initiator-policy greedy \
  --seed 42 \
  --top-behavior HOLD \
  --bottom-behavior CONSERVE
```

The batch harness:

1. creates an independent seeded random responder for each match using `base_seed + match_index`;
2. holds the selected Top/Bottom behaviors constant;
3. uses the exact current axis, band, stamina/exhaustion state, and behavior modifiers;
4. attacks only when some action has positive expected **realized** attacker-axis movement;
5. otherwise RESETs;
6. reports outcome frequencies, final stamina statistics, final-axis mean, RESET counts, and action counts.

Run paired conditions with the same base seed and count. Example:

```text
HOLD vs CONSERVE, seed 42, 1000 matches
HOLD vs PROTECT,  seed 42, 1000 matches
```

This controls the per-match response streams.

The greedy rule is not an AI claim and does not combine escape, stamina, clock, and axis into a utility function. It exists only to turn the current checker signal into reproducible distributions.

Fixed behavior is intentionally an extreme-condition experiment. CONSERVE is expected to be switched tactically in real play, so a full-match CONSERVE batch cannot by itself decide whether short recovery bursts are healthy.

### Pre-session predictions

Before tuning numbers, the first solo blind sessions should test these predictions:

- Top should prefer attacking over RESET under the seeded response mix.
- Bottom should RESET more often while Mount is Strong/Locked and attack more near Loose.
- Bridge should see little or no voluntary use because Trap-and-Roll dominates it in the current no-setup v0 matrix.
- PROTECT vs CONSERVE should favor CONSERVE unless Top repeatedly threatens Americana.
- HOLD vs CONSERVE should be a closer choice because HOLD affects two Bottom escapes.

## Frozen-v0 identity gate

The frozen enumerate digest remains:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

CI compares the actual digest against that exact value and fails on mismatch.

## StaminaPool encapsulation

`StaminaPool.current` is now read-only to callers.

All mutation must use:

- `set_current()`
- `spend_up_to()`
- `recover_up_to()`

This guarantees the 25/35 exhaustion latch is refreshed on every supported state change, mirroring the controlled-write approach used by `MountAxis`.

When a competitor is latched Exhausted above 25, display text explains the hysteresis directly:

```text
30/100 (Exhausted — recovers at 35)
```

## Next step

Do **not** implement STABILIZE immediately after this file lands.

First run targeted v0.1e playtests using `--blind` unless the session is specifically testing the full-information lock:

1. default MEDIUM with PRESSURE vs ESCAPE
2. deliberate CONSERVE cycles from both sides
3. HOLD vs CONSERVE
4. PROTECT vs CONSERVE
5. one run beginning near the 25/26 stamina boundary
6. one all-LOW and one all-HIGH run

Use those logs to decide pacing and whether CONSERVE needs a positional or recovery adjustment.

Then implement **v0.1d — STABILIZE** against an economy whose consequences have actually been observed.
