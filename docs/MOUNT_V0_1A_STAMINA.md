# Mount v0.1a — Stamina State and Telemetry

## Status

Mount v0.1a is an additive instrumentation phase built on the frozen Mount v0 mechanics.

Its purpose is to give each competitor explicit stamina state **without allowing stamina to affect resolution yet**.

This means v0.1a must not change:

- matchup grades
- behavior drift
- positional modifiers
- hysteresis
- clamps
- escape thresholds
- Exit Maps
- initiative alternation
- checker output

## Domain model

Each `Competitor` owns an independent `StaminaPool`.

Default state:

```text
current = 100
maximum = 100
band = Fresh
```

The observational bands are:

```text
76–100  Fresh
51–75   Working
26–50   Tired
0–25    Exhausted
```

These boundaries are **telemetry only in v0.1a**. No grade, drift, legality, or action availability depends on them.

They may be tuned before mechanical stamina effects are introduced.

## CLI telemetry

Interactive runs accept:

```bash
--top-stamina 0..100
--bottom-stamina 0..100
```

The run header and summary print both competitors' stamina and band.

The CLI also prints:

```text
Stamina effects: OFF (v0.1a telemetry only)
```

This is deliberate. A tester should never have to guess whether an Exhausted label is already modifying results.

## Frozen-v0 identity gate

Before stamina was added, the exact CLI bytes from:

```bash
PYTHONPATH=src python -m bjj_game --enumerate
```

were hashed on both supported CI Python versions.

Frozen SHA-256:

```text
3ee55429434f8f95c592183317292d3e824768135d7834c44bae82a6c1a59ff2
```

`tests/test_stamina.py` recomputes the hash from the current checker output and fails if even one byte changes.

It also directly compares the same Mount exchange with Fresh and Exhausted stamina and requires the `ResolutionResult`, axis, band, and destination to remain identical.

This is the v0.1 equivalent of the OOP migration's behavior-preservation gate.

## Not in v0.1a

Do not add yet:

- stamina costs
- stamina recovery
- commitment levels
- stamina-based grade shifts
- action lockouts
- CONSERVE
- STABILIZE
- technique-specific stamina costs
- exhaustion penalties

Those belong to later v0.1 slices after the state/telemetry layer is proven stable.

## Next phase

v0.1b should introduce commitment and explicit action costs while keeping the cost policy separate from the frozen Mount lookup matrix.
